from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


def is_supported_youtube_url(value: str) -> bool:
    url = value.strip().lower()
    return url.startswith("https://youtube.com/") or url.startswith(
        "https://www.youtube.com/"
    ) or url.startswith("https://youtu.be/")


def download_youtube_audio(
    url: str,
    output_dir: Path,
    target_name: str,
) -> tuple[bool, str]:
    yt_dlp = shutil.which("yt-dlp")
    ffmpeg = shutil.which("ffmpeg")

    if not yt_dlp:
        return False, "yt-dlp not found in PATH"
    if not ffmpeg:
        return False, "ffmpeg not found in PATH"

    safe_name = _normalize_mp3_name(target_name)
    if not safe_name:
        return False, "Invalid target file name"

    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        yt_dlp,
        "-x",
        "--audio-format",
        "mp3",
        "--audio-quality",
        "0",
        "--embed-thumbnail",
        "--add-metadata",
        "--embed-chapters",
        "--no-playlist",
        "-o",
        str(output_dir / f"{safe_name[:-4]}.%(ext)s"),
        url,
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode == 0:
        return True, f"Downloaded: {safe_name}"

    err = (proc.stderr or proc.stdout or "download failed").strip().splitlines()
    return False, f"Download failed: {err[-1] if err else 'download failed'}"


def _normalize_mp3_name(value: str) -> str | None:
    name = value.strip()
    if not name:
        return None
    if "/" in name or "\\" in name:
        return None
    if not name.lower().endswith(".mp3"):
        name = f"{name}.mp3"
    if name in {".mp3", "..mp3"}:
        return None
    return name
