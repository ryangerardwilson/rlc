from __future__ import annotations

from pathlib import Path


def short_path(path: Path, max_len: int = 60) -> str:
    text = str(path)
    if len(text) <= max_len:
        return text
    return "..." + text[-(max_len - 3) :]
