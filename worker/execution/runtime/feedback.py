"""Utilities for streaming task feedback back to the scheduler."""

from __future__ import annotations

import asyncio
from typing import Any, Iterable, Optional, Protocol, TYPE_CHECKING, Union

from shared.models.biz.exec.feedback import Channel, FeedbackChunk, ExecFeedbackPayload

if TYPE_CHECKING:  # pragma: no cover
    from shared.models.biz.exec.feedback import ExecFeedbackPayload as _ExecFeedbackPayload


class _FeedbackSender(Protocol):
    async def send_feedback(self, payload: "_ExecFeedbackPayload", *, corr: Optional[str] = None, seq: Optional[int] = None) -> None: ...

FeedbackChunkLike = Union[FeedbackChunk, dict[str, Any]]


class FeedbackPublisher:
    """Publishes incremental task feedback over the control-plane connection.

    Adapters obtain an instance via ``ExecutionContext.feedback`` and may call
    :meth:`send` (awaitable) or :meth:`send_nowait` (fire-and-forget) to stream
    progress, logs, or LLM tokens while a node is running.
    """

    def __init__(
        self,
        connection: "_FeedbackSender",
        *,
        run_id: str,
        task_id: str,
        default_channel: Channel = Channel.log,
    ) -> None:
        self._connection = connection
        self._run_id = run_id
        self._task_id = task_id
        self._default_channel = default_channel
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:  # pragma: no cover - fallback for sync contexts
            self._loop = asyncio.get_event_loop()

    async def send(
        self,
        *,
        stage: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        chunks: Optional[Iterable[FeedbackChunkLike]] = None,
        metrics: Optional[dict[str, float]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Send a feedback frame.

        Parameters mirror :class:`FeedbackPayload`. ``chunks`` may contain instances
        of :class:`FeedbackChunk` or plain dictionaries conforming to the schema.
        """

        chunk_payload: Optional[list[FeedbackChunk]] = None
        if chunks:
            chunk_payload = []
            for chunk in chunks:
                if isinstance(chunk, FeedbackChunk):
                    chunk_payload.append(chunk)
                else:
                    parsed = FeedbackChunk.model_validate(
                        {"channel": self._default_channel, **chunk}
                        if "channel" not in chunk
                        else chunk
                    )
                    chunk_payload.append(parsed)

        payload = ExecFeedbackPayload(
            run_id=self._run_id,
            task_id=self._task_id,
            stage=stage,
            progress=progress,
            message=message,
            chunks=chunk_payload,
            metrics=metrics,
            metadata=metadata,
        )
        await self._connection.send_feedback(payload, corr=self._task_id)

    def send_nowait(
        self,
        *,
        stage: Optional[str] = None,
        progress: Optional[float] = None,
        message: Optional[str] = None,
        chunks: Optional[Iterable[FeedbackChunkLike]] = None,
        metrics: Optional[dict[str, float]] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> asyncio.Task[None]:
        """Convenience fire-and-forget wrapper for synchronous adapters."""

        return self._loop.create_task(
            self.send(
                stage=stage,
                progress=progress,
                message=message,
                chunks=chunks,
                metrics=metrics,
                metadata=metadata,
            )
        )

    async def emit_text(
        self,
        text: str,
        *,
        channel: Channel | str = Channel.log,
        stage: Optional[str] = None,
        progress: Optional[float] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> None:
        """Shortcut for emitting a textual chunk."""

        feedback_channel = Channel(channel) if isinstance(channel, str) else channel
        await self.send(
            stage=stage,
            progress=progress,
            chunks=[FeedbackChunk(channel=feedback_channel, text=text, metadata=metadata)],
        )
