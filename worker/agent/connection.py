"""Control-plane connection scaffolding."""

from __future__ import annotations

import asyncio
import contextlib
import copy
import logging
import random
import re
import socket
from collections import deque
from collections.abc import Awaitable, Callable, Iterator
from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from pathlib import Path
from typing import Any, Deque, Dict, List, Optional, Set

from pydantic import BaseModel, ValidationError

from shared.models.ws.envelope import Ack, Role, Sender, WsEnvelope
from shared.models.ws.cmd.dispatch import CommandDispatchPayload
from shared.models.ws.result import Artifact, ResultPayload, Status as ResultStatus
from shared.models.ws.feedback import FeedbackPayload
from shared.models.ws.error import ErrorPayload
from shared.models.ws.pkg.event import PackageEvent
from shared.models.ws.handshake import Auth, HandshakePayload, Mode, Worker
from shared.models.ws.heartbeat import HeartbeatPayload, Metrics
from shared.models.ws.register import Capabilities, Concurrency, Package, RegisterPayload, Status
from shared.models.ws.next import NextRequestPayload, NextResponsePayload

from .packages import AdapterRegistry, PackageManager
from .runner import Runner
from .concurrency import ConcurrencyGuard
from .resource_registry import ResourceRegistry, ResourceHandle

from .config import WorkerSettings
from .session import SessionState, SessionTracker

LOGGER = logging.getLogger(__name__)
_ABORTED_NEXT_MAX = 512


class TransportNotReady(RuntimeError):
    """Raised when control-plane IO is invoked without an established transport."""


class ResourceLeaseError(RuntimeError):
    """Raised when required resources cannot be leased from the registry."""


class MiddlewareNextError(RuntimeError):
    """Raised when middleware next invocation returns an error."""

    def __init__(
        self,
        message: str,
        *,
        code: Optional[str] = None,
        trace: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.trace = trace


class ControlPlaneTransport:
    """Abstracts the underlying WebSocket transport.

    A concrete implementation will be wired later; for now, methods raise NotImplementedError.
    """

    async def connect(self) -> None:
        raise NotImplementedError

    async def send(self, message: dict[str, Any]) -> None:
        raise NotImplementedError

    async def receive(self) -> dict[str, Any]:
        raise NotImplementedError

    async def close(self) -> None:
        raise NotImplementedError


@dataclass
class ControlPlaneConnection:
    """Manages handshake, registration, and heartbeat sequencing."""

    settings: WorkerSettings
    transport_factory: Callable[[WorkerSettings], ControlPlaneTransport]
    command_handler: Optional[Callable[[dict[str, Any]], Awaitable[None]]] = None
    package_handler: Optional[Callable[[str, dict[str, Any]], Awaitable[None]]] = None
    adapter_registry: Optional[AdapterRegistry] = None
    runner: Optional[Runner] = None
    package_manager: Optional[PackageManager] = None
    resource_registry: Optional[ResourceRegistry] = None
    session: SessionTracker = field(default_factory=SessionTracker)
    concurrency_guard: ConcurrencyGuard = field(default_factory=ConcurrencyGuard)

    _transport: Optional[ControlPlaneTransport] = None
    _heartbeat_task: Optional[asyncio.Task[None]] = None
    _receive_task: Optional[asyncio.Task[None]] = None
    _message_counter: Iterator[int] = field(default_factory=lambda: count())
    _pending_acks: dict[str, "PendingAck"] = field(default_factory=dict)
    _dispatch_tasks: Set[asyncio.Task[None]] = field(default_factory=set)
    # Tracks in-flight middleware.next requests: request_id -> (future, task_id, run_id)
    _pending_next: Dict[str, tuple[asyncio.Future, str, str]] = field(default_factory=dict)
    _next_lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    _aborted_next: Deque[str] = field(default_factory=deque)
    _aborted_next_index: Set[str] = field(default_factory=set)

    async def start(self) -> None:
        """Establish the control-plane connection and kick off heartbeat loop."""

        LOGGER.info("Starting control-plane session with scheduler %s", self.settings.scheduler_ws_url)
        self.session.transition(SessionState.HANDSHAKING)
        await self._ensure_transport()
        self._receive_task = asyncio.create_task(self._receive_loop(), name="worker-receive")
        await self._send_handshake()

        self.session.transition(SessionState.REGISTERED)
        await self._send_register()

        self.session.transition(SessionState.HEARTBEATING)
        await self._send_heartbeat()
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop(), name="worker-heartbeat")

    async def stop(self) -> None:
        """Close the control-plane connection and heartbeat."""

        LOGGER.info("Stopping control-plane session")
        heartbeat = self._heartbeat_task
        if heartbeat:
            heartbeat.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await heartbeat
        receive_task = self._receive_task
        if receive_task:
            receive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await receive_task
        await self._cancel_dispatch_tasks()
        self._cancel_pending_next()
        self._cancel_pending_acks()
        self.session.transition(SessionState.CLOSED)
        if self._transport:
            await self._transport.close()
        self._transport = None
        self._heartbeat_task = None
        self._receive_task = None

    async def _ensure_transport(self) -> None:
        if self._transport is None:
            self._transport = self.transport_factory(self.settings)
            await self._transport.connect()

    async def _send_handshake(self) -> None:
        payload = self._build_handshake_payload()
        message = self._build_envelope("handshake", payload, request_ack=True)
        await self._send(message)
        LOGGER.debug("Handshake payload dispatched")

    async def _send_register(self) -> None:
        payload = self._build_register_payload()
        message = self._build_envelope("register", payload, request_ack=True)
        await self._send(message)
        LOGGER.debug("Register payload dispatched")

    async def _heartbeat_loop(self) -> None:
        try:
            while True:
                interval = float(self.settings.heartbeat_interval_seconds)
                jitter = float(self.settings.heartbeat_jitter_seconds)
                if jitter > 0:
                    interval += random.uniform(0, jitter)
                await asyncio.sleep(interval)
                await self._send_heartbeat()
        except asyncio.CancelledError:
            LOGGER.debug("Heartbeat loop cancelled")
            raise

    async def _send_heartbeat(self) -> None:
        payload = self._build_heartbeat_payload()
        message = self._build_envelope("heartbeat", payload)
        await self._send(message)
        LOGGER.debug("Heartbeat payload dispatched")

    def _build_handshake_payload(self) -> HandshakePayload:
        mode = Mode(self.settings.auth_mode)
        auth_kwargs: dict[str, Any] = {"mode": mode}
        if mode == Mode.token and self.settings.auth_token:
            auth_kwargs["token"] = self.settings.auth_token
        elif mode == Mode.mtls and self.settings.auth_fingerprint:
            auth_kwargs["fingerprint"] = self.settings.auth_fingerprint
        auth = Auth(**auth_kwargs)
        worker_info = Worker(
            id=self.settings.worker_id,
            version=self.settings.worker_version,
            hostname=socket.gethostname(),
        )
        return HandshakePayload(
            protocol=self.settings.handshake_protocol_version,
            auth=auth,
            worker=worker_info,
        )

    def _build_register_payload(self) -> RegisterPayload:
        runtimes = list(self.settings.runtime_names or ["python"])
        concurrency = Concurrency(
            max_parallel=self.settings.concurrency_max_parallel,
            per_node_limits=self.settings.concurrency_per_node_limits,
        )
        capabilities = Capabilities(
            concurrency=concurrency,
            runtimes=runtimes,
            features=self.settings.feature_flags or [],
        )
        # refresh handler registry before register payload so scheduler sees latest
        packages, manifests = self._collect_package_inventory()
        return RegisterPayload(
            capabilities=capabilities,
            packages=packages,
            manifests=manifests,
        )

    def _build_heartbeat_payload(self) -> HeartbeatPayload:
        metrics_payload: dict[str, Any] = {
            "inflight": self.concurrency_guard.inflight(),
        }
        if self.resource_registry:
            handles = self.resource_registry.list()
            metrics_payload["resource_handles"] = len(handles)
            metrics_payload["resource_bytes"] = sum(handle.size_bytes or 0 for handle in handles)
        metrics = Metrics(**metrics_payload)
        return HeartbeatPayload(
            healthy=True,
            metrics=metrics,
        )

    def _collect_package_inventory(self) -> tuple[list[Package], list[dict[str, Any]]]:
        inventory: list[Package] = []
        manifest_payloads: list[dict[str, Any]] = []
        if not self.package_manager:
            return inventory, manifest_payloads
        for package_path in self.package_manager.list_installed():
            package_dir = Path(package_path)
            try:
                manifest = self.package_manager._load_manifest(package_dir)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning("Failed to load manifest from %s: %s", package_dir, exc)
                continue
            name = manifest.get("name") or package_dir.name
            version = manifest.get("version") or "unknown"
            try:
                self.package_manager._register_handlers(package_dir, manifest)  # type: ignore[attr-defined]
            except Exception as exc:  # noqa: BLE001
                LOGGER.warning('Failed to register handlers for %s@%s: %s', name, version, exc)
            inventory.append(
                Package(
                    name=name,
                    version=version,
                    status=Status.installed,
                )
            )
            manifest_payloads.append({"name": name, "version": version, "manifest": manifest})
        return inventory, manifest_payloads

    async def _send(self, message: dict[str, Any]) -> None:
        if not self._transport:
            raise TransportNotReady("Transport has not been initialised")
        ack_request = message.get("ack", {}).get("request")
        message_id = message.get("id")
        if ack_request:
            self._register_ack(message)
        try:
            await self._transport.send(message)
        except Exception:
            if ack_request and message_id:
                self._remove_pending_ack(message_id)
            raise

    def _next_message_id(self, prefix: str) -> str:
        counter = next(self._message_counter)
        return f"{prefix}-{counter}"

    def _build_envelope(
        self,
        message_type: str,
        payload: dict[str, Any] | BaseModel,
        *,
        request_ack: bool = False,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> dict[str, Any]:
        payload_dict = (
            payload.model_dump(exclude_none=True, by_alias=True)
            if isinstance(payload, BaseModel)
            else payload
        )
        envelope = WsEnvelope(
            type=message_type,
            id=self._next_message_id(message_type),
            ts=datetime.now(timezone.utc),
            corr=corr,
            seq=seq,
            tenant=self.settings.tenant,
            sender=Sender(role=Role.worker, id=self.settings.worker_id),
            ack=Ack(request=True) if request_ack else None,
            payload=payload_dict,
        )
        data = envelope.model_dump(by_alias=True, exclude_none=True)
        data["ts"] = envelope.ts.isoformat()
        return data

    async def _receive_loop(self) -> None:
        assert self._transport is not None
        try:
            while True:
                message = await self._transport.receive()
                await self._handle_incoming(message)
        except asyncio.CancelledError:
            LOGGER.debug("Receive loop cancelled")
            raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Receive loop terminated due to error: %s", exc)
            self.session.transition(SessionState.BACKOFF)
            self._cancel_pending_next()

    async def _handle_incoming(self, message: dict[str, Any]) -> None:
        LOGGER.debug("Received envelope: %s", message)
        envelope = WsEnvelope.model_validate(message)

        if envelope.ack and envelope.ack.for_:
            LOGGER.debug(
                "Ack envelope received id=%s for=%s",
                envelope.id,
                envelope.ack.for_,
            )
            self._resolve_ack(envelope.ack.for_)

        if envelope.ack and envelope.ack.request:
            await self._send_ack(envelope)

        payload = envelope.payload
        message_type = envelope.type
        if message_type == "cmd.dispatch":
            LOGGER.info("Received dispatch command corr=%s", envelope.corr)
            self._schedule_dispatch(envelope)
        elif message_type == "middleware.next_response":
            await self._handle_next_response(envelope)
        elif message_type == "pkg.install":
            LOGGER.info("Received package install instruction: %s", payload)
            if self.package_handler:
                await self.package_handler("install", envelope.model_dump(by_alias=True))
        elif message_type == "pkg.uninstall":
            LOGGER.info("Received package uninstall instruction: %s", payload)
            if self.package_handler:
                await self.package_handler("uninstall", envelope.model_dump(by_alias=True))
        elif message_type == "ack":
            pass  # Already processed via ack handling above
        else:
            LOGGER.debug("Unhandled message type %s", message_type)

    def _schedule_dispatch(self, envelope: WsEnvelope) -> None:
        task = asyncio.create_task(self._process_dispatch(envelope), name=f"dispatch-{envelope.id}")
        self._dispatch_tasks.add(task)
        def _finalise(completed: asyncio.Task[None]) -> None:
            self._dispatch_tasks.discard(completed)
            with contextlib.suppress(asyncio.CancelledError, Exception):
                completed.result()
        task.add_done_callback(_finalise)

    async def _process_dispatch(self, envelope: WsEnvelope) -> None:
        try:
            if self.command_handler:
                await self.command_handler(envelope.model_dump(by_alias=True))
                return
            if not self.runner:
                LOGGER.debug("No command handler registered")
                return
            dispatch = CommandDispatchPayload.model_validate(envelope.payload)
            await self._default_command_handler(envelope, dispatch)
        except asyncio.CancelledError:
            LOGGER.debug("Dispatch task %s cancelled", envelope.id)
            raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Dispatch handling failed for envelope %s: %s", envelope.id, exc)
            raise

    async def _default_command_handler(
        self,
        envelope: WsEnvelope,
        dispatch: CommandDispatchPayload,
    ) -> None:
        if not self.runner:
            LOGGER.error("Runner not configured; cannot execute command")
            return
        corr = envelope.id
        seq = envelope.seq
        try:
            context = self._build_execution_context(dispatch)
            handler_key = dispatch.node_type
            concurrency_key = dispatch.concurrency_key or ""
            async with self.concurrency_guard.acquire(concurrency_key) as acquired:
                if not acquired:
                    LOGGER.warning("Concurrency key %s already in-flight; rejecting task", concurrency_key)
                    await self.send_command_error(
                        ErrorPayload(
                            code="E.CMD.CONCURRENCY_VIOLATION",
                            message=f"Concurrency key {concurrency_key} already running",
                            context={
                                "where": "worker.concurrency",
                                "details": {
                                    "run_id": dispatch.run_id,
                                    "task_id": dispatch.task_id,
                                    "node_id": dispatch.node_id,
                                },
                            },
                        ),
                        corr=corr,
                        seq=seq,
                    )
                    return
                leased_resources: dict[str, ResourceHandle] = {}
                try:
                    if self.resource_registry:
                        try:
                            leased_resources = self._lease_resources(dispatch)
                        except ResourceLeaseError as exc:
                            LOGGER.warning("Resource lease failed: %s", exc)
                            await self.send_command_error(
                                ErrorPayload(
                                    code="E.RESOURCE.MISSING",
                                    message=str(exc),
                                    context={
                                        "where": "worker.resources",
                                        "details": {
                                            "run_id": dispatch.run_id,
                                            "task_id": dispatch.task_id,
                                            "node_id": dispatch.node_id,
                                        },
                                    },
                                ),
                                corr=corr,
                                seq=seq,
                            )
                            return
                        context.leased_resources = leased_resources
                        context.resource_registry = self.resource_registry
                    start = asyncio.get_event_loop().time()
                    result = await self.runner.execute(context, handler_key, corr=corr, seq=seq)
                    duration_ms = int((asyncio.get_event_loop().time() - start) * 1000)
                    artifacts = self._coerce_artifacts(result.artifacts)
                    metadata_payload: dict[str, Any] = {}
                    if context.metadata:
                        metadata_payload.update(context.metadata)
                    if result.metadata:
                        metadata_payload.update(result.metadata)
                    if not metadata_payload:
                        metadata_payload = {}
                    result_payload = ResultPayload(
                        run_id=context.run_id,
                        task_id=context.task_id,
                        status=self._normalise_result_status(result.status),
                        result=result.outputs,
                        duration_ms=duration_ms,
                        metadata=metadata_payload or None,
                        artifacts=artifacts,
                    )
                    await self.send_result(
                        result_payload,
                        corr=corr,
                        seq=seq,
                    )
                finally:
                    if self.resource_registry:
                        for resource_id in leased_resources:
                            self.resource_registry.release(resource_id)
        except asyncio.CancelledError:
            current = asyncio.current_task()
            LOGGER.warning(
                "Task cancelled run=%s task=%s node=%s corr=%s seq=%s current_task=%s",
                dispatch.run_id,
                dispatch.task_id,
                dispatch.node_id,
                corr,
                seq,
                getattr(current, "get_name", lambda: None)(),
            )
            # Capture a lightweight stack to help identify the canceller
            try:
                import traceback

                LOGGER.debug("Cancellation stack:\n%s", "".join(traceback.format_stack()))
            except Exception:  # pragma: no cover - best-effort logging
                LOGGER.debug("Cancellation stack unavailable")
            try:
                await self._interrupt_pending_next(
                    dispatch.run_id, dispatch.task_id, code="next_cancelled", message="task cancelled"
                )
                await self.send_command_error(
                    ErrorPayload(
                        code="E.RUNNER.CANCELLED",
                        message="task cancelled",
                        context={
                            "where": "worker.runner",
                            "details": {
                                "run_id": dispatch.run_id,
                                "task_id": dispatch.task_id,
                                "node_id": dispatch.node_id,
                            },
                        },
                    ),
                    corr=corr,
                    seq=seq,
                )
            finally:
                raise
        except Exception as exc:  # noqa: BLE001
            LOGGER.exception("Command execution failed: %s", exc)
            await self.send_command_error(
                ErrorPayload(
                    code="E.RUNNER.FAILURE",
                    message=str(exc),
                    context={
                        "where": "worker.runner",
                        "details": {
                            "run_id": dispatch.run_id,
                            "task_id": dispatch.task_id,
                            "node_id": dispatch.node_id,
                        },
                    },
                ),
                corr=corr,
                seq=seq,
            )
        finally:
            self._cancel_pending_next_for_task(dispatch.run_id, dispatch.task_id)

    def _coerce_artifacts(self, artifacts: Optional[List[Any]]) -> Optional[List[Artifact]]:
        if not artifacts:
            return None
        coerced: List[Artifact] = []
        for entry in artifacts:
            if isinstance(entry, Artifact):
                coerced.append(entry)
                continue
            try:
                coerced.append(Artifact.model_validate(entry))
            except ValidationError as exc:  # noqa: BLE001
                LOGGER.warning("Dropping invalid artifact descriptor %s: %s", entry, exc)
        return coerced or None

    def _build_execution_context(self, dispatch: CommandDispatchPayload) -> "ExecutionContext":
        from .runner import ExecutionContext  # local import to avoid cycles
        from .feedback import FeedbackPublisher

        run_id = dispatch.run_id
        task_id = dispatch.task_id
        node_id = dispatch.node_id
        package_name = dispatch.package_name
        package_version = dispatch.package_version
        parameters = dispatch.parameters or {}
        safe_task_id = self._sanitize_path_segment(task_id)
        data_dir = (self.settings.data_dir / run_id / safe_task_id)
        data_dir.mkdir(parents=True, exist_ok=True)
        # trace is currently not defined in schema; placeholder for future extension
        trace = None
        metadata = {
            "concurrency_key": dispatch.concurrency_key,
            "constraints": dispatch.constraints.model_dump(exclude_none=True),
        }
        if dispatch.host_node_id:
            metadata["host_node_id"] = dispatch.host_node_id
        if dispatch.middleware_chain:
            metadata["middleware_chain"] = list(dispatch.middleware_chain)
        if dispatch.chain_index is not None:
            metadata["chain_index"] = dispatch.chain_index
        resource_refs = list(dispatch.resource_refs) if dispatch.resource_refs else None
        if resource_refs:
            metadata["resource_refs"] = [ref.model_dump(exclude_none=True) for ref in resource_refs]
        if dispatch.affinity:
            metadata["affinity"] = dispatch.affinity.model_dump(exclude_none=True)
        context = ExecutionContext(
            run_id=run_id,
            task_id=task_id,
            node_id=node_id,
            package_name=package_name,
            package_version=package_version,
            params=parameters,
            data_dir=data_dir,
            tenant=self.settings.tenant,
            host_node_id=dispatch.host_node_id,
            middleware_chain=dispatch.middleware_chain,
            chain_index=dispatch.chain_index,
            trace=trace,
            metadata=metadata,
            resource_refs=resource_refs,
            resource_registry=self.resource_registry,
            feedback=FeedbackPublisher(self, run_id=run_id, task_id=task_id),
        )
        context.next_handler = self._middleware_next
        return context

    @staticmethod
    def _sanitize_path_segment(segment: str) -> str:
        cleaned = re.sub(r'[<>:"/\\\\|?*]', "_", segment)
        cleaned = cleaned.strip(". ")
        return cleaned or "task"

    def _normalise_result_status(self, status: str) -> ResultStatus:
        if not status:
            LOGGER.warning("Adapter returned empty status; defaulting to FAILED")
            return ResultStatus.FAILED
        upper = status.upper()
        mapping = {
            "SUCCESS": ResultStatus.SUCCEEDED.value,
            "SUCCEED": ResultStatus.SUCCEEDED.value,
            "SUCCEEDED": ResultStatus.SUCCEEDED.value,
            "ALLOWED": ResultStatus.SUCCEEDED.value,
            "BLOCKED": ResultStatus.SUCCEEDED.value,
            "OK": ResultStatus.SUCCEEDED.value,
            "DONE": ResultStatus.SUCCEEDED.value,
            "ERROR": ResultStatus.FAILED.value,
            "FAIL": ResultStatus.FAILED.value,
            "FAILED": ResultStatus.FAILED.value,
            "CANCEL": ResultStatus.CANCELLED.value,
            "CANCELLED": ResultStatus.CANCELLED.value,
            "SKIP": ResultStatus.SKIPPED.value,
            "SKIPPED": ResultStatus.SKIPPED.value,
        }
        canonical = mapping.get(upper, upper)
        try:
            return ResultStatus(canonical)
        except ValueError:
            LOGGER.warning("Adapter returned unsupported status '%s'; defaulting to FAILED", status)
        return ResultStatus.FAILED

    def _lease_resources(self, dispatch: CommandDispatchPayload) -> dict[str, ResourceHandle]:
        leased: dict[str, ResourceHandle] = {}
        if not self.resource_registry or not dispatch.resource_refs:
            return leased
        for ref in dispatch.resource_refs:
            if ref.worker_id and ref.worker_id != self.settings.worker_id:
                raise ResourceLeaseError(
                    f"resource {ref.resource_id} pinned to {ref.worker_id}, current worker {self.settings.worker_id}"
                )
            try:
                handle = self.resource_registry.lease(ref.resource_id)
            except KeyError as exc:
                raise ResourceLeaseError(f"resource {ref.resource_id} missing on worker") from exc
            leased[ref.resource_id] = handle
        return leased

    async def _send_ack(self, envelope: WsEnvelope) -> None:
        ack_for = envelope.id
        ack_payload = {"for": ack_for}
        ack_envelope = self._build_envelope(
            "ack",
            payload=ack_payload,
            request_ack=False,
            corr=envelope.corr,
            seq=envelope.seq,
        )
        ack_envelope["ack"] = {"for": ack_for}
        await self._send_without_tracking(ack_envelope)

    def _register_ack(self, message: dict[str, Any]) -> None:
        message_id = message["id"]
        if message_id in self._pending_acks:
            return
        pending = PendingAck(message=copy.deepcopy(message))
        LOGGER.debug("Tracking ack for message %s", message_id)
        pending.task = asyncio.create_task(self._ack_retry_loop(message_id), name=f"ack-retry-{message_id}")
        self._pending_acks[message_id] = pending

    async def _ack_retry_loop(self, message_id: str) -> None:
        base_delay = max(self.settings.ack_retry_base_ms / 1000.0, 0.05)
        max_delay = max(self.settings.ack_retry_max_ms / 1000.0, base_delay)
        while True:
            pending = self._pending_acks.get(message_id)
            if not pending:
                return
            if pending.attempts >= self.settings.ack_retry_attempts:
                LOGGER.error("Message %s exceeded ack retries; dropping", message_id)
                self._pending_acks.pop(message_id, None)
                return
            delay = min(base_delay * (2**pending.attempts), max_delay)
            LOGGER.debug(
                "Ack retry loop sleeping %s s before attempt %s for message %s",
                delay,
                pending.attempts + 1,
                message_id,
            )
            await asyncio.sleep(delay)
            if message_id not in self._pending_acks:
                return
            pending = self._pending_acks[message_id]
            try:
                LOGGER.warning("Resending message %s (attempt %s)", message_id, pending.attempts + 1)
                await self._send_without_tracking(pending.message)
            except Exception as exc:  # noqa: BLE001
                LOGGER.exception("Failed to resend message %s: %s", message_id, exc)
                return
            pending.attempts += 1

    async def _send_without_tracking(self, message: dict[str, Any]) -> None:
        if not self._transport:
            raise TransportNotReady("Transport has not been initialised")
        await self._transport.send(message)

    def _remove_pending_ack(self, message_id: str) -> None:
        pending = self._pending_acks.pop(message_id, None)
        if pending and pending.task:
            pending.task.cancel()

    def _resolve_ack(self, message_id: str) -> None:
        pending = self._pending_acks.pop(message_id, None)
        if not pending:
            LOGGER.debug("Received ack for unknown message %s", message_id)
            return
        if pending.task:
            pending.task.cancel()
        LOGGER.info("Ack received for message %s after %s attempts", message_id, pending.attempts)

    def _track_aborted_next(self, request_id: str) -> None:
        """Record a locally-cancelled next waiter so late responses can be ignored noiselessly."""

        if request_id in self._aborted_next_index:
            return
        self._aborted_next.append(request_id)
        self._aborted_next_index.add(request_id)
        if len(self._aborted_next) > _ABORTED_NEXT_MAX:
            oldest = self._aborted_next.popleft()
            self._aborted_next_index.discard(oldest)

    def _pop_aborted_next(self, request_id: str) -> bool:
        if request_id not in self._aborted_next_index:
            return False
        self._aborted_next_index.discard(request_id)
        try:
            self._aborted_next.remove(request_id)
        except ValueError:
            pass
        return True

    def _cancel_pending_acks(self) -> None:
        if self._pending_acks:
            LOGGER.debug("Cancelling %s pending ack waiters", len(self._pending_acks))
        for pending in self._pending_acks.values():
            if pending.task:
                pending.task.cancel()
        self._pending_acks.clear()

    def _cancel_pending_next(self) -> None:
        if self._pending_next:
            LOGGER.debug("Cancelling %s pending next requests", len(self._pending_next))
        for req_id, (fut, _, _) in list(self._pending_next.items()):
            if not fut.done():
                fut.cancel()
            self._track_aborted_next(req_id)
        self._pending_next.clear()

    def _cancel_pending_next_for_task(self, run_id: str, task_id: str) -> None:
        to_cancel = [req_id for req_id, (_, tid, rid) in self._pending_next.items() if tid == task_id and rid == run_id]
        if to_cancel:
            LOGGER.debug("Cancelling %s pending next requests for task=%s", len(to_cancel), task_id)
        for req_id in to_cancel:
            fut, _, _ = self._pending_next.pop(req_id, (None, task_id, run_id))
            if fut and not fut.done():
                fut.cancel()
            self._track_aborted_next(req_id)

    async def _interrupt_pending_next(self, run_id: str, task_id: str, *, code: str, message: str) -> None:
        """Actively fail pending ctx.next waits for a task with an error."""

        async with self._next_lock:
            targets = [
                (req_id, fut)
                for req_id, (fut, tid, rid) in self._pending_next.items()
                if tid == task_id and rid == run_id
            ]
            if targets:
                LOGGER.debug(
                    "Interrupting %s pending next requests for task=%s with code=%s message=%s",
                    len(targets),
                    task_id,
                    code,
                    message,
                )
            for req_id, fut in targets:
                self._pending_next.pop(req_id, None)
                if fut and not fut.done():
                    fut.set_exception(MiddlewareNextError(message, code=code))
                self._track_aborted_next(req_id)

    async def _cancel_dispatch_tasks(self) -> None:
        if not self._dispatch_tasks:
            return
        tasks = list(self._dispatch_tasks)
        self._dispatch_tasks.clear()
        LOGGER.debug("Cancelling %s dispatch tasks", len(tasks))
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)

    async def send_result(self, payload: dict[str, Any] | BaseModel, *, corr: Optional[str] = None, seq: Optional[int] = None) -> None:
        """Emit a task result frame."""

        message = self._build_envelope("result", payload, request_ack=True, corr=corr, seq=seq)
        await self._send(message)

    async def send_feedback(self, payload: FeedbackPayload | dict[str, Any] | BaseModel, *, corr: Optional[str] = None, seq: Optional[int] = None) -> None:
        """Emit an incremental task feedback frame."""

        message = self._build_envelope("feedback", payload, request_ack=False, corr=corr, seq=seq)
        await self._send(message)

    async def send_command_error(
        self,
        payload: dict[str, Any] | BaseModel,
        *,
        corr: Optional[str] = None,
        seq: Optional[int] = None,
    ) -> None:
        """Emit a command error frame."""

        message = self._build_envelope("command.error", payload, request_ack=True, corr=corr, seq=seq)
        await self._send(message)

    async def send_package_event(self, payload: dict[str, Any] | BaseModel) -> None:
        """Emit a package lifecycle event frame."""

        message = self._build_envelope("pkg.event", payload, request_ack=False)
        await self._send(message)

    async def _middleware_next(
        self,
        context: "ExecutionContext",
        payload: Optional[Dict[str, Any]],
        host_ctx: Optional[Dict[str, Any]],
        middleware_ctx: Optional[Dict[str, Any]],
        timeout_ms: Optional[int],
    ) -> Dict[str, Any]:
        if not context.middleware_chain or context.chain_index is None:
            raise RuntimeError("middleware chain metadata missing; cannot call next()")
        request_id = self._next_message_id("next")
        timeout_seconds = timeout_ms / 1000.0 if timeout_ms and timeout_ms > 0 else None
        next_payload = NextRequestPayload(
            requestId=request_id,
            runId=context.run_id,
            nodeId=context.node_id,
            middlewareId=context.node_id,
            chainIndex=context.chain_index,
            hostCtx=host_ctx,
            middlewareCtx=middleware_ctx,
            payload=payload,
            timeoutMs=timeout_ms,
        )
        loop = asyncio.get_running_loop()
        future: asyncio.Future = loop.create_future()
        async with self._next_lock:
            self._pending_next[request_id] = (future, context.task_id, context.run_id)
        try:
            message = self._build_envelope(
                "middleware.next_request",
                next_payload,
                request_ack=True,
                corr=context.task_id,
                seq=None,
            )
            await self._send(message)
        except Exception:
            async with self._next_lock:
                self._pending_next.pop(request_id, None)
            raise

        try:
            if timeout_seconds:
                return await asyncio.wait_for(future, timeout=timeout_seconds)
            return await future
        except asyncio.TimeoutError as exc:
            future.cancel()
            self._track_aborted_next(request_id)
            raise MiddlewareNextError(
                "middleware next timed out locally",
                code="next_timeout",
            ) from exc
        except asyncio.CancelledError:
            future.cancel()
            self._track_aborted_next(request_id)
            raise
        finally:
            async with self._next_lock:
                self._pending_next.pop(request_id, None)

    async def _handle_next_response(self, envelope: WsEnvelope) -> None:
        payload = NextResponsePayload.model_validate(envelope.payload)
        request_id = payload.request_id
        async with self._next_lock:
            entry = self._pending_next.pop(request_id, None)
        if not entry:
            if self._pop_aborted_next(request_id):
                LOGGER.debug(
                    "Ignored late middleware.next_response for aborted waiter req=%s run=%s",
                    request_id,
                    payload.run_id,
                )
            else:
                LOGGER.warning(
                    "Received middleware.next_response with no pending waiter req=%s run=%s",
                    request_id,
                    payload.run_id,
                )
            return
        future, *_ = entry
        if future.done():
            return
        if payload.error:
            code = payload.error.get("code") if isinstance(payload.error, dict) else None
            message = payload.error.get("message") if isinstance(payload.error, dict) else "middleware next failed"
            future.set_exception(MiddlewareNextError(message, code=code, trace=payload.trace))
            return
        future.set_result(payload.result or {})


@dataclass
class PendingAck:
    message: dict[str, Any]
    attempts: int = 0
    task: Optional[asyncio.Task[None]] = None


class DummyTransport(ControlPlaneTransport):
    """Temporary transport placeholder until WebSocket integration lands."""

    def __init__(self, settings: WorkerSettings | None = None) -> None:
        self._settings = settings

    async def connect(self) -> None:
        LOGGER.debug("Dummy transport connect()")

    async def send(self, message: dict[str, Any]) -> None:
        LOGGER.debug("Dummy transport send(): %s", message)

    async def receive(self) -> dict[str, Any]:
        LOGGER.debug("Dummy transport receive() (no-op)")
        await asyncio.sleep(3600)
        return {}

    async def close(self) -> None:
        LOGGER.debug("Dummy transport close()")
