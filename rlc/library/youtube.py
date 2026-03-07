from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from urllib.parse import parse_qs, urlparse


def is_supported_youtube_url(value: str) -> bool:
    return _extract_youtube_video_id(value) is not None


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

    canonical_url = _canonical_youtube_watch_url(url)
    if not canonical_url:
        return False, "Command expects a YouTube video URL"

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
        canonical_url,
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


def _canonical_youtube_watch_url(value: str) -> str | None:
    video_id = _extract_youtube_video_id(value)
    if not video_id:
        return None
    return f"https://www.youtube.com/watch?v={video_id}"


def _extract_youtube_video_id(value: str) -> str | None:
    raw = value.strip()
    if not raw:
        return None
    parsed = urlparse(raw)
    if parsed.scheme != "https":
        return None

    host = parsed.netloc.lower()
    path = parsed.path.strip("/")

    if host in {"youtu.be"}:
        return path.split("/", 1)[0] or None

    if host not in {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "music.youtube.com",
    }:
        return None

    if parsed.path == "/watch":
        query = parse_qs(parsed.query)
        video_ids = query.get("v", [])
        if not video_ids:
            return None
        return video_ids[0].strip() or None

    if path.startswith("shorts/"):
        short_id = path.split("/", 2)[1]
        return short_id.strip() or None

    return None
