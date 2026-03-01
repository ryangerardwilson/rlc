from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from rlc import __version__
from rlc.app import run_app
from rlc.config import build_app_config, default_config_path, load_user_config, save_user_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="rlc terminal music player",
        add_help=False,
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="Optional file path to play directly, or directory path to use as music dir",
    )
    parser.add_argument("-f", type=int, help="UI frames per second")
    parser.add_argument(
        "-c",
        help="Path to config file (defaults to $XDG_CONFIG_HOME/rlc/config.json)",
    )
    parser.add_argument(
        "-v",
        action="version",
        version=__version__,
        help="Show version and exit",
    )
    parser.add_argument(
        "-u",
        dest="upgrade",
        action="store_true",
        help="Upgrade to latest release using install.sh",
    )
    parser.add_argument(
        "-h",
        action="help",
        help="Show usage summary",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    if args.upgrade:
        return _upgrade_to_latest()

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


def _upgrade_to_latest() -> int:
    curl = shutil.which("curl")
    bash = shutil.which("bash")
    if not curl:
        print("curl not found in PATH.", file=sys.stderr)
        return 1
    if not bash:
        print("bash not found in PATH.", file=sys.stderr)
        return 1

    url = "https://raw.githubusercontent.com/ryangerardwilson/rlc/main/install.sh"
    with tempfile.NamedTemporaryFile(suffix=".sh", delete=False) as tmp:
        tmp_path = Path(tmp.name)

    try:
        fetch = subprocess.run([curl, "-fsSL", url, "-o", str(tmp_path)])
        if fetch.returncode != 0:
            return fetch.returncode
        run = subprocess.run([bash, str(tmp_path)])
        return run.returncode
    finally:
        try:
            tmp_path.unlink(missing_ok=True)
        except OSError:
            pass


if __name__ == "__main__":
    raise SystemExit(main())
