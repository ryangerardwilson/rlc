from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def display_name(track_path: Path) -> str:
    return track_path.stem


def duration_seconds(track_path: Path) -> float | None:
    try:
        from mutagen import File as MutagenFile
    except Exception:
        mutagen_duration = None
    else:
        try:
            audio = MutagenFile(track_path)
        except Exception:
            audio = None
        if audio is not None and getattr(audio, "info", None):
            length = getattr(audio.info, "length", None)
            try:
                mutagen_duration = float(length) if length is not None else None
            except (TypeError, ValueError):
                mutagen_duration = None
        else:
            mutagen_duration = None

    if mutagen_duration is not None and mutagen_duration >= 0:
        return mutagen_duration

    ffprobe = shutil.which("ffprobe")
    if not ffprobe:
        return None

    try:
        proc = subprocess.run(
            [
                ffprobe,
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(track_path),
            ],
            capture_output=True,
            text=True,
        )
    except Exception:
        return None

    if proc.returncode != 0:
        return None

    raw = (proc.stdout or "").strip()
    if not raw:
        return None

    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value >= 0 else None
