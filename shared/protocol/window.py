"""Sliding window helpers for session sequencing."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Generic, List, Tuple, TypeVar

T = TypeVar("T")


def is_seq_acked(seq: int, ack_seq: int | None, ack_bitmap: int | None, window_size: int) -> bool:
    if ack_seq is None:
        return False
    if seq <= ack_seq:
        return True
    if ack_bitmap is None:
        return False
    offset = seq - ack_seq - 1
    if offset < 0 or offset >= window_size:
        return False
    return bool(ack_bitmap & (1 << offset))


@dataclass
class ReceiveWindow(Generic[T]):
    size: int
    base_seq: int = 0
    bitmap: int = 0
    buffer: Dict[int, T] = field(default_factory=dict)

    def record(self, seq: int, item: T) -> Tuple[List[T], bool]:
        if seq <= self.base_seq:
            return [], False
        offset = seq - self.base_seq - 1
        if offset >= self.size:
            return [], False
        if seq in self.buffer:
            return [], False
        self.buffer[seq] = item
        self.bitmap |= 1 << offset
        ready: List[T] = []
        while self.bitmap & 1:
            next_seq = self.base_seq + 1
            entry = self.buffer.pop(next_seq, None)
            if entry is None:
                break
            ready.append(entry)
            self.base_seq += 1
            self.bitmap >>= 1
        return ready, True

    def ack_state(self) -> Tuple[int, int, int]:
        return self.base_seq, self.bitmap, self.size

    def reset(self) -> None:
        self.base_seq = 0
        self.bitmap = 0
        self.buffer.clear()
