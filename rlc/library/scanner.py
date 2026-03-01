from __future__ import annotations

from pathlib import Path

SUPPORTED_EXTS = {".mp3", ".flac", ".wav", ".ogg", ".m4a"}


def scan_music_files(root: Path) -> list[Path]:
    if not root.exists() or not root.is_dir():
        return []
    tracks = [
        path
        for path in root.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_EXTS
    ]
    tracks.sort(key=lambda p: p.name.lower())
    return tracks
