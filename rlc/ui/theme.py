from __future__ import annotations

import curses


def init_theme(stdscr: curses.window) -> None:
    if curses.has_colors():
        curses.start_color()
        try:
            curses.use_default_colors()
        except curses.error:
            pass

    try:
        stdscr.bkgd(" ", attr_base())
    except curses.error:
        pass


def attr_base() -> int:
    return curses.A_NORMAL


def attr_dim() -> int:
    return curses.A_NORMAL


def attr_bright() -> int:
    return curses.A_BOLD


def attr_selected() -> int:
    return curses.A_BOLD | curses.A_REVERSE
