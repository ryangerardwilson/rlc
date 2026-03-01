from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path


class PlayerBackend(ABC):
    @abstractmethod
    def play(self, track_path: Path) -> None:
        raise NotImplementedError

    @abstractmethod
    def stop(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def is_playing(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def toggle_pause(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def is_paused(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def seek_relative(self, delta_seconds: float) -> float | None:
        raise NotImplementedError

    @abstractmethod
    def current_position(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def close(self) -> None:
        raise NotImplementedError
