from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    music_dir: Path
    fps: int = 20
    startup_track: Path | None = None


@dataclass(slots=True)
class UserConfig:
    music_dir: str | None = None
    fps: int | None = None


def default_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME")
    if base:
        return Path(base).expanduser() / "rlc" / "config.json"
    return Path("~/.config/rlc/config.json").expanduser()


def load_user_config(config_path: Path) -> UserConfig:
    if not config_path.exists() or not config_path.is_file():
        return UserConfig()

    try:
        raw = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return UserConfig()

    if not isinstance(raw, dict):
        return UserConfig()

    music_dir = raw.get("music_dir")
    fps = raw.get("fps")

    if not isinstance(music_dir, str):
        music_dir = None
    if not isinstance(fps, int):
        fps = None

    return UserConfig(music_dir=music_dir, fps=fps)


def save_user_config(
    config_path: Path,
    *,
    music_dir: str | None = None,
    fps: int | None = None,
) -> None:
    existing: dict[str, object] = {}
    if config_path.exists() and config_path.is_file():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                existing = raw
        except (OSError, json.JSONDecodeError):
            existing = {}

    if music_dir is not None:
        existing["music_dir"] = music_dir
    if fps is not None:
        existing["fps"] = fps

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(existing, indent=2) + "\n", encoding="utf-8")


def resolve_music_dir(cli_value: str | None, file_value: str | None) -> Path:
    if cli_value:
        return Path(cli_value).expanduser().resolve()
    if file_value:
        return Path(file_value).expanduser().resolve()
    return Path("~/Music").expanduser().resolve()


def build_app_config(
    *,
    cli_music_dir: str | None,
    cli_fps: int | None,
    config_path: Path,
) -> AppConfig:
    user_cfg = load_user_config(config_path)
    music_dir = resolve_music_dir(cli_music_dir, user_cfg.music_dir)

    fps = cli_fps if cli_fps is not None else user_cfg.fps
    fps = max(5, int(fps)) if fps is not None else 20

    return AppConfig(music_dir=music_dir, fps=fps)
