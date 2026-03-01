from __future__ import annotations

import argparse
import sys

from rlc import __version__
from rlc.app import run_app
from rlc.config import AppConfig, resolve_music_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="rlc terminal music player")
    parser.add_argument(
        "--music-dir",
        help="Directory to scan for music files (defaults to ~/Music)",
    )
    parser.add_argument("--fps", type=int, default=20, help="UI frames per second")
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

    config = AppConfig(music_dir=resolve_music_dir(args.music_dir), fps=max(5, args.fps))
    return run_app(config)


if __name__ == "__main__":
    raise SystemExit(main())
