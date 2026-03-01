from __future__ import annotations

import curses

PAIR_BASE = 1
PAIR_DIM = 2
PAIR_BRIGHT = 3
PAIR_SELECTED = 4


def init_theme(stdscr: curses.window) -> None:
    if not curses.has_colors():
        return

    curses.start_color()
    try:
        curses.use_default_colors()
    except curses.error:
        pass

    bg = -1
    if curses.COLORS >= 256:
        # grayscale ramp (dark -> bright), transparent background
        colors = {
            PAIR_BASE: 250,
            PAIR_DIM: 244,
            PAIR_BRIGHT: 255,
            PAIR_SELECTED: 254,
        }
    else:
        colors = {
            PAIR_BASE: curses.COLOR_WHITE,
            PAIR_DIM: curses.COLOR_WHITE,
            PAIR_BRIGHT: curses.COLOR_WHITE,
            PAIR_SELECTED: curses.COLOR_WHITE,
        }

    for pair, fg in colors.items():
        try:
            curses.init_pair(pair, fg, bg)
        except curses.error:
            continue

    try:
        stdscr.bkgd(" ", curses.color_pair(PAIR_BASE))
    except curses.error:
        pass


def attr_base() -> int:
    return curses.color_pair(PAIR_BASE)


def attr_dim() -> int:
    return curses.color_pair(PAIR_DIM)


def attr_bright() -> int:
    return curses.color_pair(PAIR_BRIGHT)


def attr_selected() -> int:
    return curses.color_pair(PAIR_SELECTED) | curses.A_BOLD
