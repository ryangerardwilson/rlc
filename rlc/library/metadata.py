from __future__ import annotations

from pathlib import Path


def display_name(track_path: Path) -> str:
    return track_path.stem
