"""Session tracking for the scheduler control-plane connection."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import uuid


class SessionState(enum.Enum):
    """Worker-side state machine per comm-protocol.md §2."""

    NEW = "NEW"
    HANDSHAKING = "HANDSHAKING"
    REGISTERED = "REGISTERED"
    HEARTBEATING = "HEARTBEATING"
    DRAINING = "DRAINING"
    CLOSED = "CLOSED"
    BACKOFF = "BACKOFF"


@dataclass
class SessionTracker:
    """In-memory session metadata."""

    state: SessionState = SessionState.NEW
    session_id: Optional[str] = None
    session_token: Optional[str] = None
    worker_instance_id: Optional[str] = None
    last_transition_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))
    instance_file: Path = field(default_factory=lambda: Path("./var/worker_instance_id"))

    def transition(self, next_state: SessionState) -> None:
        """Move the session into a new state, validating allowed transitions."""

        if not self._is_valid_transition(self.state, next_state):
            raise ValueError(f"Invalid transition {self.state.value} → {next_state.value}")
        self.state = next_state
        self.last_transition_at = datetime.now(tz=timezone.utc)

    @staticmethod
    def _is_valid_transition(current: SessionState, nxt: SessionState) -> bool:
        allowed = {
            SessionState.NEW: {SessionState.HANDSHAKING},
            SessionState.HANDSHAKING: {SessionState.REGISTERED, SessionState.BACKOFF},
            SessionState.REGISTERED: {SessionState.HEARTBEATING, SessionState.BACKOFF, SessionState.CLOSED},
            SessionState.HEARTBEATING: {
                SessionState.DRAINING,
                SessionState.CLOSED,
                SessionState.BACKOFF,
            },
            SessionState.DRAINING: {SessionState.CLOSED, SessionState.BACKOFF},
            SessionState.CLOSED: {SessionState.NEW, SessionState.BACKOFF},
            SessionState.BACKOFF: {SessionState.NEW},
        }
        return nxt in allowed.get(current, set())

    def load_or_create_instance_id(self) -> str:
        """Load a persisted worker_instance_id or generate and persist a new one."""

        if self.worker_instance_id:
            return self.worker_instance_id
        path = self.instance_file
        try:
            if path.is_file():
                existing = path.read_text(encoding="utf-8").strip()
                if existing:
                    self.worker_instance_id = existing
                    return existing
        except OSError:
            # fall through to create
            pass

        new_id = str(uuid.uuid4())
        self.worker_instance_id = new_id
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(new_id, encoding="utf-8")
        except OSError:
            # ignore persistence failure; runtime still uses generated id
            pass
        return new_id
