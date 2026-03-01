from __future__ import annotations

from rlc.config import AppConfig
from rlc.ui import run_curses_app


def run_app(config: AppConfig) -> int:
    return run_curses_app(config)
