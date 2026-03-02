from __future__ import annotations

import os
import signal
import shutil
import subprocess
import time
from pathlib import Path

from rlc.player.backend import PlayerBackend


class FFplayBackend(PlayerBackend):
    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._ffplay_path = shutil.which("ffplay")
        self._paused = False
        self._track_path: Path | None = None
        self._position_offset = 0.0
        self._started_at = 0.0
        self._paused_position: float | None = None

    def available(self) -> bool:
        return self._ffplay_path is not None

    def play(self, track_path: Path) -> None:
        self.stop()
        if not self._ffplay_path:
            raise RuntimeError("ffplay not found in PATH")
        self._start(track_path, position=0.0)
        self._paused = False

    def stop(self) -> None:
        if not self._proc:
            return
        if self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=1.0)
            except subprocess.TimeoutExpired:
                self._proc.kill()
                self._proc.wait(timeout=1.0)
        self._proc = None
        self._paused = False
        self._track_path = None
        self._position_offset = 0.0
        self._started_at = 0.0
        self._paused_position = None

    def is_playing(self) -> bool:
        alive = self._proc is not None and self._proc.poll() is None
        if not alive:
            self._paused = False
        return alive

    def toggle_pause(self) -> bool:
        if not self.is_playing() or not self._proc:
            return False
        if self._paused:
            # Resume: continue from frozen position.
            os.kill(self._proc.pid, signal.SIGCONT)
            if self._paused_position is not None:
                self._position_offset = self._paused_position
            self._started_at = time.monotonic()
            self._paused_position = None
            self._paused = False
        else:
            # Pause: freeze current position.
            self._paused_position = self.current_position()
            os.kill(self._proc.pid, signal.SIGSTOP)
            self._paused = True
        return self._paused

    def is_paused(self) -> bool:
        if not self.is_playing():
            return False
        return self._paused

    def seek_relative(self, delta_seconds: float) -> float | None:
        if not self.is_playing() or not self._track_path:
            return None
        if self._paused:
            return None

        current = self._position_offset + max(0.0, time.monotonic() - self._started_at)
        target = max(0.0, current + delta_seconds)
        track = self._track_path
        self.stop()
        self._start(track, position=target)
        return target

    def current_position(self) -> float:
        if not self.is_playing():
            return 0.0
        if self._paused and self._paused_position is not None:
            return max(0.0, self._paused_position)
        return max(0.0, self._position_offset + (time.monotonic() - self._started_at))

    def close(self) -> None:
        self.stop()

    def _start(self, track_path: Path, *, position: float) -> None:
        if not self._ffplay_path:
            raise RuntimeError("ffplay not found in PATH")
        cmd = [
            self._ffplay_path,
            "-nodisp",
            "-autoexit",
            "-loglevel",
            "quiet",
        ]
        if position > 0:
            cmd.extend(["-ss", f"{position:.3f}"])
        cmd.append(str(track_path))
        self._proc = subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self._paused = False
        self._track_path = track_path
        self._position_offset = position
        self._started_at = time.monotonic()
        self._paused_position = None
