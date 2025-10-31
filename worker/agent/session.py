"""Session tracking for the scheduler control-plane connection."""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


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
    last_transition_at: datetime = field(default_factory=lambda: datetime.now(tz=timezone.utc))

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
