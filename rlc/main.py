from __future__ import annotations

import argparse
import sys
from pathlib import Path

from _version import __version__
from rgw_cli_contract import AppSpec, resolve_install_script_path, run_app

from rlc.app import run_app as run_tui
from rlc.config import build_app_config, default_config_path, load_user_config, save_user_config

INSTALL_SCRIPT = resolve_install_script_path(Path(__file__).resolve().parents[1] / "main.py")
HELP_TEXT = """rlc

flags:
  rlc -h
    show this help
  rlc -v
    print the installed version
  rlc -u
    upgrade to the latest release

features:
  launch the curses music player with your saved library
  # rlc
  rlc

  play a specific track immediately
  # rlc <track_path>
  rlc ~/Music/song.mp3

  use a directory for this run without changing saved config
  # rlc <music_dir>
  rlc ~/Music

  open the user config in your editor
  # rlc conf
  rlc conf
"""
CONFIG_BOOTSTRAP_TEXT = '{\n  "music_dir": "",\n  "fps": 20\n}\n'
APP_SPEC = AppSpec(
    app_name="rlc",
    version=__version__,
    help_text=HELP_TEXT,
    install_script_path=INSTALL_SCRIPT,
    no_args_mode="dispatch",
    config_path_factory=default_config_path,
    config_bootstrap_text=CONFIG_BOOTSTRAP_TEXT,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rlc",
        add_help=False,
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Optional file path to play directly, or directory path to use as music dir",
    )
    parser.add_argument("-f", dest="fps", type=int, help="UI frames per second")
    parser.add_argument(
        "-c",
        dest="config",
        help="Path to config file (defaults to $XDG_CONFIG_HOME/rlc/config.json)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    return run_app(APP_SPEC, args, _dispatch)


def _dispatch(argv: list[str]) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    target_music_dir: str | None = None
    startup_track: Path | None = None
    if args.target:
        target_path = Path(args.target).expanduser().resolve()
        if target_path.is_file():
            startup_track = target_path
            target_music_dir = str(target_path.parent)
        if target_path.is_dir():
            target_music_dir = str(target_path)
        elif startup_track is None:
            print(f"Path not found: {target_path}", file=sys.stderr)
            return 1

    config_path = default_config_path()
    if args.config:
        config_path = Path(args.config).expanduser().resolve()

    if not args.target:
        _bootstrap_first_run_config(config_path=config_path, cli_music_dir=None)

    effective_music_dir = target_music_dir

    config = build_app_config(
        cli_music_dir=effective_music_dir,
        cli_fps=args.fps,
        config_path=config_path,
    )
    config.startup_track = startup_track
    return run_tui(config)


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
