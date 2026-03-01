from __future__ import annotations

from collections import deque
from pathlib import Path


class TrackQueue:
    def __init__(self) -> None:
        self._items: deque[Path] = deque()

    def __len__(self) -> int:
        return len(self._items)

    def enqueue(self, track: Path) -> None:
        self._items.append(track)

    def enqueue_many(self, tracks: list[Path]) -> None:
        self._items.extend(tracks)

    def next(self) -> Path | None:
        if not self._items:
            return None
        return self._items.popleft()

    def clear(self) -> None:
        self._items.clear()
