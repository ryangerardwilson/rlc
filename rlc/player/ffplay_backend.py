from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from rlc.player.backend import PlayerBackend


class FFplayBackend(PlayerBackend):
    def __init__(self) -> None:
        self._proc: subprocess.Popen[bytes] | None = None
        self._ffplay_path = shutil.which("ffplay")

    def available(self) -> bool:
        return self._ffplay_path is not None

    def play(self, track_path: Path) -> None:
        self.stop()
        if not self._ffplay_path:
            raise RuntimeError("ffplay not found in PATH")
        self._proc = subprocess.Popen(
            [
                self._ffplay_path,
                "-nodisp",
                "-autoexit",
                "-loglevel",
                "quiet",
                str(track_path),
            ],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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

    def is_playing(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def close(self) -> None:
        self.stop()
