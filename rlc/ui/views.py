from __future__ import annotations

import curses
from pathlib import Path

from rlc.library import display_name
from rlc.state import AppState
from rlc.ui.theme import attr_base, attr_bright, attr_dim, attr_selected
from rlc.ui.widgets import draw_box
from rlc.util.paths import short_path
from rlc.visualizer import render_bars


def _safe_addstr(win: curses.window, y: int, x: int, text: str, attr: int = 0) -> None:
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    if not text:
        return

    # Curses may raise when writing into the bottom-right cell.
    max_len = max_x - x
    if y == max_y - 1:
        max_len -= 1
    if max_len <= 0:
        return

    safe_text = text.replace("\n", " ").replace("\r", " ")
    if not safe_text:
        return

    try:
        win.addnstr(y, x, safe_text, max_len, attr)
    except curses.error:
        # Keep UI running even when tiny terminal geometry causes edge writes.
        return


def render(
    stdscr: curses.window,
    state: AppState,
    tracks: list[Path],
) -> None:
    stdscr.erase()
    h, w = stdscr.getmaxyx()

    if state.ui.show_shortcuts:
        _render_shortcuts(stdscr, h, w)
        stdscr.refresh()
        return

    if state.ui.single_track_mode:
        _render_single_track(stdscr, state, h, w)
        stdscr.refresh()
        return

    left_w = max(30, w // 2)
    left_w = min(left_w, w - 20)
    right_w = w - left_w

    draw_box(
        stdscr,
        0,
        0,
        h - 2,
        left_w,
        "Library",
        border_attr=attr_dim(),
        title_attr=attr_bright(),
    )
    draw_box(
        stdscr,
        0,
        left_w,
        h - 2,
        right_w,
        "Now Playing",
        border_attr=attr_dim(),
        title_attr=attr_bright(),
    )

    list_y = 1
    max_list_rows = max(1, h - 4)
    start = max(0, state.ui.selected_index - max_list_rows + 1)
    visible_tracks = tracks[start : start + max_list_rows]

    for i, track in enumerate(visible_tracks):
        idx = start + i
        marker = ">" if idx == state.ui.selected_index else " "
        line = f"{marker} {display_name(track)}"
        attr = attr_selected() if idx == state.ui.selected_index else attr_base()
        _safe_addstr(stdscr, list_y + i, 1, line, attr)

    info_y = 1
    now_playing = state.playback.now_playing or "(nothing)"
    _safe_addstr(stdscr, info_y, left_w + 1, f"Track: {now_playing}", attr_bright())
    _safe_addstr(
        stdscr,
        info_y + 1,
        left_w + 1,
        f"Status: {_playback_status(state)}",
        attr_base(),
    )

    vis_y = info_y + 3
    vis_h = max(3, h - vis_y - 3)
    vis_w = max(6, right_w - 2)
    bars = render_bars(
        vis_w,
        vis_h,
        state.playback.spectrum_levels,
        state.playback.spectrum_peaks,
    )
    for row, line in enumerate(bars):
        if vis_h > 2:
            frac = row / max(1, vis_h - 1)
            if frac < 0.33:
                vis_attr = attr_bright()
            elif frac < 0.66:
                vis_attr = attr_base()
            else:
                vis_attr = attr_dim()
        else:
            vis_attr = attr_base()
        _safe_addstr(stdscr, vis_y + row, left_w + 1, line, vis_attr)

    _safe_addstr(stdscr, h - 2, 0, "-" * max(0, w - 1), attr_dim())
    if state.ui.command_mode:
        prompt = state.ui.command_prefix + state.ui.command_buffer
        _safe_addstr(stdscr, h - 1, 0, prompt, attr_bright())
    else:
        _safe_addstr(stdscr, h - 1, 0, state.ui.status_line, attr_base())
        if tracks:
            selected = tracks[state.ui.selected_index]
            suffix = f" | Selected: {short_path(selected)}"
            _safe_addstr(stdscr, h - 1, len(state.ui.status_line), suffix, attr_dim())

    stdscr.refresh()


def _playback_status(state: AppState) -> str:
    if state.playback.is_paused:
        return "Paused"
    if state.playback.is_playing:
        return "Playing"
    return "Stopped"


def _render_single_track(
    stdscr: curses.window,
    state: AppState,
    h: int,
    w: int,
) -> None:
    draw_box(
        stdscr,
        0,
        0,
        h - 2,
        w,
        "Now Playing",
        border_attr=attr_dim(),
        title_attr=attr_bright(),
    )
    info_y = 1
    now_playing = state.playback.now_playing or "(nothing)"
    _safe_addstr(stdscr, info_y, 1, f"Track: {now_playing}", attr_bright())
    _safe_addstr(stdscr, info_y + 1, 1, f"Status: {_playback_status(state)}", attr_base())

    vis_y = info_y + 3
    vis_h = max(3, h - vis_y - 3)
    vis_w = max(6, w - 2)
    bars = render_bars(
        vis_w,
        vis_h,
        state.playback.spectrum_levels,
        state.playback.spectrum_peaks,
    )
    for row, line in enumerate(bars):
        if vis_h > 2:
            frac = row / max(1, vis_h - 1)
            if frac < 0.33:
                vis_attr = attr_bright()
            elif frac < 0.66:
                vis_attr = attr_base()
            else:
                vis_attr = attr_dim()
        else:
            vis_attr = attr_base()
        _safe_addstr(stdscr, vis_y + row, 1, line, vis_attr)

    _safe_addstr(stdscr, h - 2, 0, "-" * max(0, w - 1), attr_dim())
    if state.ui.command_mode:
        prompt = state.ui.command_prefix + state.ui.command_buffer
        _safe_addstr(stdscr, h - 1, 0, prompt, attr_bright())
    else:
        _safe_addstr(stdscr, h - 1, 0, state.ui.status_line, attr_base())


def _render_shortcuts(stdscr: curses.window, h: int, w: int) -> None:
    draw_box(
        stdscr,
        0,
        0,
        h - 1,
        w,
        "Shortcuts",
        border_attr=attr_dim(),
        title_attr=attr_bright(),
    )
    lines = [
        "Navigation: j/k",
        "Play selected: l",
        "Pause/resume: Space",
        "Stop: s",
        "Delete selected track: dd",
        "Command bar: :",
        "Search prompt: /",
        "Search next/prev: n / p",
        "Toggle shortcuts: ?",
        "Quit: q",
        "",
        "Command bar:",
        "  :name.mp3 <youtube-url>  download to music dir",
        "  /query                   startswith > contains > fuzzy",
    ]

    y = 2
    for line in lines:
        if y >= h - 2:
            break
        _safe_addstr(stdscr, y, 2, line, attr_base())
        y += 1

    _safe_addstr(stdscr, h - 1, 0, "Press ? to close", attr_dim())
