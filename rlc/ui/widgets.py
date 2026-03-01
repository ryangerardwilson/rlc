from __future__ import annotations

import curses


def draw_box(
    win: curses.window,
    y: int,
    x: int,
    h: int,
    w: int,
    title: str,
    *,
    border_attr: int = 0,
    title_attr: int = 0,
) -> None:
    if h < 3 or w < 4:
        return
    try:
        win.addstr(y, x, "+" + "-" * (w - 2) + "+", border_attr)
        for row in range(y + 1, y + h - 1):
            win.addstr(row, x, "|", border_attr)
            win.addstr(row, x + w - 1, "|", border_attr)
        win.addstr(y + h - 1, x, "+" + "-" * (w - 2) + "+", border_attr)
    except curses.error:
        return

    if title and w > 6:
        label = f" {title[: w - 6]} "
        try:
            win.addstr(y, x + 2, label, title_attr or border_attr)
        except curses.error:
            return
