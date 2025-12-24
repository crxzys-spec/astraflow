"""Run state service for the scheduler control plane."""

from __future__ import annotations

import asyncio
import copy
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple
from scheduler_api.models.list_runs200_response import ListRuns200Response
from scheduler_api.models.start_run_request import StartRunRequest
from shared.models.biz.exec.result import ExecResultPayload
from shared.models.biz.exec.error import ExecErrorPayload
from shared.models.biz.exec.feedback import ExecFeedbackPayload
from shared.models.biz.exec.next.request import ExecMiddlewareNextRequest
from shared.models.biz.exec.next.response import ExecMiddlewareNextResponse
from scheduler_api.models.start_run_request_workflow import StartRunRequestWorkflow
from scheduler_api.catalog import PackageCatalogError, catalog
from scheduler_api.resources import ResourceNotFoundError, get_resource_grant_store, get_resource_provider_for
from ..domain.models import DispatchRequest, FrameRuntimeState, NodeState, RunRecord, FINAL_STATUSES, _utc_now
from ..domain.bindings import _merge_result_updates
from ..domain.graph import apply_edge_bindings, apply_frame_edge_bindings, apply_middleware_output_bindings
from ..domain.frames import activate_frame, build_container_frames, current_frame, pop_frame
from ..events.format import build_workflow_snapshot
from ..engine import dispatch, frames, initialise, lifecycle, lookup, status
from ..events import emit
from ..engine.next import handle_next_request as process_next_request
from ..engine.pending import (
    collect_expired_next_requests as collect_pending_next_expired,
    finalise_pending_next as finalise_pending_next_request,
    resolve_next_response_worker as resolve_pending_next_worker,
)
from ..engine.updates import (
    apply_command_error,
    apply_feedback,
    apply_record_result,
)

LOGGER = logging.getLogger(__name__)

RESOURCE_BINDINGS_KEY = "__resourceBindings"
RESOURCE_BINDING_ERRORS_KEY = "__resourceBindingErrors"
MAX_INLINE_RESOURCE_BYTES = 64 * 1024
INLINE_RESOURCE_TYPES = {"secret", "token", "api_key", "apikey", "key", "credential"}


def _should_inline_value(requirement: Any) -> bool:
    req_type = str(getattr(requirement, "type", "") or "").strip().lower()
    metadata = getattr(requirement, "metadata", None) or {}
    if isinstance(metadata, dict):
        if metadata.get("inline") is True or metadata.get("exposeValue") is True:
            return True
    return req_type in INLINE_RESOURCE_TYPES


def _is_required(requirement: Any) -> bool:
    required = getattr(requirement, "required", True)
    return required is not False


def _select_grant(
    grants: List[Any],
    *,
    package_version: Optional[str],
) -> Optional[Any]:
    if not grants:
        return None
    eligible = [
        grant
        for grant in grants
        if not getattr(grant, "package_version", None)
        or getattr(grant, "package_version", None) == package_version
    ]
    if not eligible:
        return None
    return max(eligible, key=_grant_created_at)


def _grant_created_at(grant: Any) -> datetime:
    value = getattr(grant, "created_at", None)
    if isinstance(value, datetime):
        return value
    return datetime.min.replace(tzinfo=timezone.utc)


def _read_resource_value(provider, resource_id: str) -> Optional[str]:
    path, stored = provider.open(resource_id)
    if stored.size_bytes and stored.size_bytes > MAX_INLINE_RESOURCE_BYTES:
        return None
    data = path.read_bytes()
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", "ignore")
    return text.strip() if text else None


def _load_package_requirements(
    package_name: str,
    package_version: str,
    cache: Dict[Tuple[str, str], List[Any]],
) -> List[Any]:
    if not package_name or not package_version:
        return []
    key = (package_name, package_version)
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        manifest = catalog.get_manifest(package_name, package_version)
    except PackageCatalogError:
        cache[key] = []
        return []
    requirements = []
    if manifest and getattr(manifest, "requirements", None):
        requirements = list(getattr(manifest.requirements, "resources", []) or [])
    cache[key] = requirements
    return requirements


def _resolve_grant(
    store,
    *,
    workflow_id: str,
    package_name: str,
    package_version: Optional[str],
    resource_key: str,
) -> Optional[Any]:
    workflow_grants = store.list(
        workflow_id=workflow_id,
        package_name=package_name,
        resource_key=resource_key,
        scope="workflow",
    )
    selected = _select_grant(workflow_grants, package_version=package_version)
    if selected:
        return selected
    global_grants = store.list(
        package_name=package_name,
        resource_key=resource_key,
        scope="global",
    )
    return _select_grant(global_grants, package_version=package_version)


class RunStateService:
    """Thread-safe run state service for REST and WebSocket layers."""

    def __init__(self) -> None:
        self._runs: Dict[str, RunRecord] = {}
        self._lock = asyncio.Lock()
        # pending middleware next requests keyed by request_id -> (run_id, worker_instance_id, worker_name, deadline, node_id, middleware_id, target_task_id)
        self._pending_next_requests: Dict[
            str,
            Tuple[str, Optional[str], Optional[str], Optional[datetime], Optional[str], Optional[str], Optional[str]],
        ] = {}
        self._emitter = emit.build_run_registry_emitter()

    async def create_run(
        self,
        *,
        run_id: str,
        request: StartRunRequest,
        tenant: str,
    ) -> RunRecord:
        async with self._lock:
            record = initialise.build_run_record(run_id=run_id, request=request, tenant=tenant)
            self._runs[run_id] = record
            snapshot = copy.deepcopy(record)
        tasks = emit.build_run_state_tasks(self._emitter, snapshot)
        await asyncio.gather(*tasks)
        return snapshot

    async def get(self, run_id: str) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            return copy.deepcopy(record) if record else None

    async def get_by_task(self, task_id: str) -> Optional[RunRecord]:
        async with self._lock:
            for record in self._runs.values():
                if record.task_id == task_id:
                    return copy.deepcopy(record)
                if record.find_node_by_task(task_id):
                    return copy.deepcopy(record)
        return None

    async def get_workflow_with_state(self, run_id: str) -> Optional[StartRunRequestWorkflow]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            snapshot = copy.deepcopy(record)
        return build_workflow_snapshot(snapshot)

    async def snapshot(self) -> List[RunRecord]:
        async with self._lock:
            return [copy.deepcopy(record) for record in self._runs.values()]

    async def collect_ready_nodes(self, run_id: Optional[str] = None) -> List[DispatchRequest]:
        state_events: List[Tuple[RunRecord, NodeState]] = []
        workflow_ids: Dict[str, str] = {}
        async with self._lock:
            records: Iterable[RunRecord]
            if run_id:
                record = self._runs.get(run_id)
                records = [record] if record else []
            else:
                records = self._runs.values()
            requests: List[DispatchRequest] = []
            for record in records:
                if not record or record.status in FINAL_STATUSES:
                    continue
                workflow_ids[record.run_id] = record.workflow.id
                active_frame = current_frame(record)
                if active_frame:
                    requests.extend(self._collect_ready_for_frame(record, active_frame, state_events))
                else:
                    requests.extend(self._collect_ready_for_record(record, state_events))
        # Emit container state updates after releasing the lock.
        if state_events:
            tasks = emit.build_state_event_tasks(self._emitter, state_events)
            await asyncio.gather(*tasks)
        if requests and workflow_ids:
            self._apply_resource_bindings(requests, workflow_ids=workflow_ids)
        return requests

    async def mark_dispatched(
        self,
        run_id: str,
        *,
        worker_name: str,
        task_id: str,
        node_id: str,
        node_type: str,
        package_name: str,
        package_version: str,
        seq_used: int,
        resource_refs: Optional[List[Dict[str, Any]]] = None,
        affinity: Optional[Dict[str, Any]] = None,
        dispatch_id: Optional[str] = None,
        ack_deadline: Optional[datetime] = None,
    ) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)
            outcome = lifecycle.mark_dispatched(
                record,
                worker_name=worker_name,
                task_id=task_id,
                node_id=node_id,
                node_type=node_type,
                package_name=package_name,
                package_version=package_version,
                seq_used=seq_used,
                resource_refs=resource_refs,
                affinity=affinity,
                dispatch_id=dispatch_id,
                ack_deadline=ack_deadline,
                resolve_node_state=lookup.resolve_node_state,
                pending_next_requests=self._pending_next_requests,
                utc_now=_utc_now,
                final_statuses=FINAL_STATUSES,
            )
            previous_status = outcome.previous_status
            record_snapshot = outcome.record_snapshot
            node_snapshot = outcome.node_snapshot
        tasks = emit.build_node_state_tasks(
            self._emitter,
            record_snapshot,
            node_snapshot,
            previous_status=previous_status,
        )
        await asyncio.gather(*tasks)
        return record_snapshot

    async def mark_acknowledged(
        self,
        run_id: str,
        *,
        node_id: str,
        dispatch_id: str,
    ) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)
            outcome = lifecycle.mark_acknowledged(
                record,
                node_id=node_id,
                dispatch_id=dispatch_id,
                find_node_by_dispatch=lookup.find_node_by_dispatch,
            )
            if not outcome:
                return copy.deepcopy(record)
            previous_status = outcome.previous_status
            record_snapshot = outcome.record_snapshot
            node_snapshot = outcome.node_snapshot
        tasks = emit.build_node_state_tasks(
            self._emitter,
            record_snapshot,
            node_snapshot,
            previous_status=previous_status,
        )
        await asyncio.gather(*tasks)
        return record_snapshot

    async def cancel_run(self, run_id: str) -> tuple[Optional[RunRecord], List[Tuple[str, str, str, Optional[str], Optional[str]]]]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None, []
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record), []
            outcome = lifecycle.cancel_run(
                record,
                run_id=run_id,
                pending_next_requests=self._pending_next_requests,
                utc_now=_utc_now,
                final_statuses=FINAL_STATUSES,
            )
            record_snapshot = outcome.record_snapshot
            cancelled_next = outcome.cancelled_next

        tasks = emit.build_run_state_tasks(self._emitter, record_snapshot)
        await asyncio.gather(*tasks)
        return record_snapshot, cancelled_next

    async def reset_after_ack_timeout(
        self,
        run_id: str,
        *,
        node_id: str,
        dispatch_id: str,
    ) -> Optional[RunRecord]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)
            outcome = lifecycle.reset_after_ack_timeout(
                record,
                node_id=node_id,
                dispatch_id=dispatch_id,
                find_node_by_dispatch=lookup.find_node_by_dispatch,
            )
            if not outcome:
                return copy.deepcopy(record)
            previous_status = outcome.previous_status
            record_snapshot = outcome.record_snapshot
            node_snapshot = outcome.node_snapshot
        tasks = emit.build_node_state_tasks(
            self._emitter,
            record_snapshot,
            node_snapshot,
            previous_status=previous_status,
        )
        await asyncio.gather(*tasks)
        return record_snapshot

    async def reset_after_worker_cancel(
        self,
        run_id: Optional[str],
        *,
        node_id: Optional[str],
        task_id: Optional[str],
    ) -> Optional[RunRecord]:
        """Reset a node after a worker-side cancellation so it can be retried."""

        async with self._lock:
            record = self._runs.get(run_id) if run_id else None
            if not record and task_id:
                record = next(
                    (candidate for candidate in self._runs.values() if candidate.task_id == task_id),
                    None,
                )
            if not record:
                return None
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record)

            node_state, _frame_state = lookup.resolve_node_state(
                record,
                node_id=node_id,
                task_id=task_id,
            )
            if not node_state:
                return copy.deepcopy(record)

            outcome = lifecycle.reset_after_worker_cancel(
                record,
                node_state,
                pending_next_requests=self._pending_next_requests,
            )
            previous_status = outcome.previous_status
            record_snapshot = outcome.record_snapshot
            node_snapshot = outcome.node_snapshot
        tasks = emit.build_node_state_tasks(
            self._emitter,
            record_snapshot,
            node_snapshot,
            previous_status=previous_status,
        )
        await asyncio.gather(*tasks)
        return record_snapshot

    async def record_result(
        self,
        run_id: str,
        payload: ExecResultPayload,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest], List[Tuple[Optional[str], ExecMiddlewareNextResponse]]]:
        async with self._lock:
            record = self._runs.get(run_id)
            if not record:
                return None, [], []
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record), [], []
            outcome = apply_record_result(
                record,
                payload,
                resolve_node_state=lookup.resolve_node_state,
                is_host_with_middleware=dispatch.is_host_with_middleware,
                is_middleware_node=dispatch.is_middleware_node,
                apply_edge_bindings=apply_edge_bindings,
                apply_frame_edge_bindings=apply_frame_edge_bindings,
                apply_middleware_output_bindings=apply_middleware_output_bindings,
                release_dependents=lambda record, node_state, frame_state, ready, state_events=None: frames.release_dependents(
                    record,
                    node_state,
                    frame_state,
                    ready,
                    state_events=state_events,
                    is_container_node=dispatch.is_container_node,
                    is_host_with_middleware=dispatch.is_host_with_middleware,
                    should_auto_dispatch=dispatch.should_auto_dispatch,
                    start_container_execution=self._start_container_execution,
                    build_dispatch_request_for_node=dispatch.build_dispatch_request_for_node,
                ),
                complete_frame_if_needed=lambda record, frame: frames.complete_frame_if_needed(
                    record,
                    frame,
                    pending_next_requests=self._pending_next_requests,
                    is_host_with_middleware=dispatch.is_host_with_middleware,
                    get_parent_graph=lookup.get_parent_graph,
                    pop_frame=pop_frame,
                    build_dispatch_request_for_node=dispatch.build_dispatch_request_for_node,
                    utc_now=_utc_now,
                    final_statuses=FINAL_STATUSES,
                ),
                finalise_pending_next=lambda payload, node_state, status: finalise_pending_next_request(
                    self._pending_next_requests,
                    payload,
                    node_state,
                    status=status,
                ),
                utc_now=_utc_now,
                normalise_status=status.normalise_status,
                final_statuses=FINAL_STATUSES,
            )
        tasks = emit.build_record_result_tasks(
            self._emitter,
            outcome,
            final_statuses=FINAL_STATUSES,
        )
        await asyncio.gather(*tasks)
        if outcome.ready and record:
            self._apply_resource_bindings(outcome.ready, workflow_ids={record.run_id: record.workflow.id})
        return outcome.record_snapshot, outcome.ready, outcome.next_responses

    async def record_feedback(
        self,
        payload: ExecFeedbackPayload,
    ) -> None:
        async with self._lock:
            record = self._runs.get(payload.run_id)
            if not record:
                return
            outcome = apply_feedback(
                record,
                payload,
                resolve_node_state=lookup.resolve_node_state,
                merge_result_updates=_merge_result_updates,
                utc_now=_utc_now,
            )
        tasks = emit.build_feedback_tasks(self._emitter, outcome)
        if tasks:
            await asyncio.gather(*tasks)

    async def handle_next_request(
        self,
        payload: ExecMiddlewareNextRequest,
        *,
        worker_name: Optional[str],
        worker_instance_id: Optional[str],
    ) -> Tuple[List[DispatchRequest], Optional[str]]:
        async with self._lock:
            record = self._runs.get(payload.runId)
            if not record or record.status in FINAL_STATUSES:
                return [], "next_run_finalised"
            outcome = process_next_request(
                record=record,
                payload=payload,
                worker_name=worker_name,
                worker_instance_id=worker_instance_id,
                pending_next_requests=self._pending_next_requests,
                resolve_node_state=lookup.resolve_node_state,
                is_container_node=dispatch.is_container_node,
                is_middleware_node=dispatch.is_middleware_node,
                is_host_with_middleware=dispatch.is_host_with_middleware,
                start_container_execution=self._start_container_execution,
                build_dispatch_request=dispatch.build_dispatch_request,
                utc_now=_utc_now,
                final_statuses=FINAL_STATUSES,
            )
            if outcome.error_code:
                return [], outcome.error_code
        publish_tasks = emit.build_next_request_tasks(self._emitter, outcome)
        if publish_tasks:
            await asyncio.gather(*publish_tasks)
        if outcome.ready and record:
            self._apply_resource_bindings(outcome.ready, workflow_ids={record.run_id: record.workflow.id})
        return outcome.ready, None

    async def resolve_next_response_worker(self, request_id: str) -> Optional[str]:
        async with self._lock:
            return resolve_pending_next_worker(
                self._pending_next_requests,
                request_id,
                utc_now=_utc_now,
            )

    async def collect_expired_next_requests(self) -> List[Tuple[str, str, str, Optional[str], Optional[str]]]:
        async with self._lock:
            expired, remaining = collect_pending_next_expired(
                self._pending_next_requests,
                utc_now=_utc_now,
            )
            self._pending_next_requests = remaining
            return expired

    async def record_command_error(
        self,
        payload: ExecErrorPayload,
        *,
        run_id: Optional[str] = None,
        task_id: Optional[str] = None,
    ) -> tuple[Optional[RunRecord], List[DispatchRequest]]:
        async with self._lock:
            record = None
            if run_id:
                record = self._runs.get(run_id)
            if not record and task_id:
                record = next(
                    (candidate for candidate in self._runs.values() if candidate.task_id == task_id),
                    None,
                )
            if not record:
                return None, []
            if record.status in FINAL_STATUSES:
                return copy.deepcopy(record), []
            outcome = apply_command_error(
                record,
                payload,
                task_id=task_id,
                resolve_node_state=lookup.resolve_node_state,
                complete_frame_if_needed=lambda record, frame: frames.complete_frame_if_needed(
                    record,
                    frame,
                    pending_next_requests=self._pending_next_requests,
                    is_host_with_middleware=dispatch.is_host_with_middleware,
                    get_parent_graph=lookup.get_parent_graph,
                    pop_frame=pop_frame,
                    build_dispatch_request_for_node=dispatch.build_dispatch_request_for_node,
                    utc_now=_utc_now,
                    final_statuses=FINAL_STATUSES,
                ),
                utc_now=_utc_now,
            )
        tasks = emit.build_command_error_tasks(self._emitter, outcome)
        if tasks:
            await asyncio.gather(*tasks)
        return outcome.record_snapshot, outcome.ready

    async def to_list_response(
        self,
        *,
        limit: int,
        cursor: Optional[str],
        status: Optional[str],
        client_id: Optional[str],
    ) -> ListRuns200Response:
        runs = await self.snapshot()
        runs.sort(key=lambda r: r.created_at)
        filtered: Iterable[RunRecord] = runs
        if status:
            filtered = [r for r in filtered if r.status == status]
        if client_id:
            filtered = [r for r in filtered if r.client_id == client_id]
        filtered_list = list(filtered)

        start_index = 0
        if cursor:
            for idx, candidate in enumerate(filtered_list):
                if candidate.run_id == cursor:
                    start_index = idx + 1
                    break

        window = filtered_list[start_index : start_index + limit]
        items = [r.to_summary() for r in window]
        next_cursor = None
        if start_index + len(window) < len(filtered_list):
            next_cursor = filtered_list[start_index + len(window) - 1].run_id
        return ListRuns200Response(items=items, nextCursor=next_cursor)

    def _apply_resource_bindings(
        self,
        requests: List[DispatchRequest],
        *,
        workflow_ids: Dict[str, str],
    ) -> None:
        if not requests:
            return
        grant_store = get_resource_grant_store()
        requirements_cache: Dict[Tuple[str, str], List[Any]] = {}
        provider_cache: Dict[str, Any] = {}
        resource_cache: Dict[str, Any] = {}
        for request in requests:
            workflow_id = workflow_ids.get(request.run_id)
            if not workflow_id:
                continue
            requirements = _load_package_requirements(
                request.package_name,
                request.package_version,
                requirements_cache,
            )
            if not requirements:
                continue
            bindings: Dict[str, Any] = {}
            errors: List[Dict[str, Any]] = []
            for requirement in requirements:
                resource_key = getattr(requirement, "key", None)
                if not resource_key:
                    continue
                grant = _resolve_grant(
                    grant_store,
                    workflow_id=workflow_id,
                    package_name=request.package_name,
                    package_version=request.package_version,
                    resource_key=str(resource_key),
                )
                if not grant:
                    if _is_required(requirement):
                        errors.append({"key": str(resource_key), "error": "missing_grant"})
                    continue
                resource_id = str(getattr(grant, "resource_id", "") or "")
                if not resource_id:
                    continue
                try:
                    stored = resource_cache.get(resource_id)
                    if stored is None:
                        provider = provider_cache.get(resource_id)
                        if provider is None:
                            provider = get_resource_provider_for(resource_id)
                            provider_cache[resource_id] = provider
                        stored = provider.get(resource_id)
                        resource_cache[resource_id] = stored
                except (ResourceNotFoundError, ValueError):
                    errors.append(
                        {"key": str(resource_key), "error": "resource_not_found", "resourceId": resource_id}
                    )
                    continue
                binding: Dict[str, Any] = {
                    "resourceId": stored.resource_id,
                    "type": stored.type,
                    "filename": stored.filename,
                    "mimeType": stored.mime_type,
                    "sizeBytes": stored.size_bytes,
                    "metadata": stored.metadata or {},
                }
                if _should_inline_value(requirement):
                    try:
                        provider = provider_cache.get(stored.resource_id)
                        if provider is None:
                            provider = get_resource_provider_for(stored.resource_id)
                            provider_cache[stored.resource_id] = provider
                        value = _read_resource_value(provider, stored.resource_id)
                    except (ResourceNotFoundError, ValueError):
                        value = None
                    if value is None:
                        errors.append(
                            {
                                "key": str(resource_key),
                                "error": "resource_value_unavailable",
                                "resourceId": stored.resource_id,
                            }
                        )
                    else:
                        binding["value"] = value
                bindings[str(resource_key)] = binding

            if not bindings and not errors:
                continue
            request.parameters = copy.deepcopy(request.parameters) if request.parameters else {}
            if bindings:
                existing = request.parameters.get(RESOURCE_BINDINGS_KEY)
                if isinstance(existing, dict):
                    merged = {**existing, **bindings}
                else:
                    merged = bindings
                request.parameters[RESOURCE_BINDINGS_KEY] = merged
            if errors:
                request.parameters[RESOURCE_BINDING_ERRORS_KEY] = errors

    def _collect_ready_for_record(
        self,
        record: RunRecord,
        state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
    ) -> List[DispatchRequest]:
        return dispatch.collect_ready_for_record(
            record,
            is_container_node=dispatch.is_container_node,
            is_container_ready=dispatch.is_container_ready,
            should_auto_dispatch=dispatch.should_auto_dispatch,
            start_container_execution=self._start_container_execution,
            build_dispatch_request_for_node=dispatch.build_dispatch_request_for_node,
            state_events=state_events,
        )

    def _collect_ready_for_frame(
        self,
        record: RunRecord,
        frame: FrameRuntimeState,
        state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
    ) -> List[DispatchRequest]:
        return dispatch.collect_ready_for_frame(
            record,
            frame,
            is_container_node=dispatch.is_container_node,
            is_container_ready=dispatch.is_container_ready,
            should_auto_dispatch=dispatch.should_auto_dispatch,
            start_container_execution=self._start_container_execution,
            build_dispatch_request_for_node=dispatch.build_dispatch_request_for_node,
            state_events=state_events,
        )

    def _start_container_execution(
        self,
        record: RunRecord,
        container_node: NodeState,
        *,
        parent_frame_id: Optional[str],
        state_events: Optional[List[Tuple[RunRecord, NodeState]]] = None,
    ) -> List[DispatchRequest]:
        return dispatch.start_container_execution(
            record,
            container_node,
            parent_frame_id=parent_frame_id,
            state_events=state_events,
            find_frame_for_container=lookup.find_frame_for_container,
            build_container_frames=build_container_frames,
            activate_frame=activate_frame,
            collect_ready_for_frame=self._collect_ready_for_frame,
            utc_now=_utc_now,
            logger=LOGGER,
        )

run_state_service = RunStateService()
