from __future__ import annotations

import argparse
from pathlib import Path
import sys

from rlc import __version__
from rlc.app import run_app
from rlc.config import build_app_config, default_config_path, load_user_config, save_user_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="rlc terminal music player")
    parser.add_argument(
        "--music-dir",
        help="Directory to scan for music files (overrides config file)",
    )
    parser.add_argument("--fps", type=int, help="UI frames per second")
    parser.add_argument(
        "--config",
        help="Path to config file (defaults to $XDG_CONFIG_HOME/rlc/config.json)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=__version__,
        help="Show version and exit",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    config_path = default_config_path()
    if args.config:
        config_path = Path(args.config).expanduser().resolve()

    _bootstrap_first_run_config(config_path=config_path, cli_music_dir=args.music_dir)

    config = build_app_config(
        cli_music_dir=args.music_dir,
        cli_fps=args.fps,
        config_path=config_path,
    )
    return run_app(config)


def _bootstrap_first_run_config(*, config_path: Path, cli_music_dir: str | None) -> None:
    user_cfg = load_user_config(config_path)
    if user_cfg.music_dir:
        return

    if cli_music_dir:
        save_user_config(
            config_path,
            music_dir=str(Path(cli_music_dir).expanduser().resolve()),
        )
        return

    default_dir = str(Path("~/Music").expanduser().resolve())
    if not sys.stdin.isatty():
        save_user_config(config_path, music_dir=default_dir)
        return

    print("First run setup: choose your music directory.")
    print(f"Press Enter to use default: {default_dir}")
    raw = input("Music directory: ").strip()
    chosen = raw or default_dir
    resolved = str(Path(chosen).expanduser().resolve())
    save_user_config(config_path, music_dir=resolved)


if __name__ == "__main__":
    raise SystemExit(main())
