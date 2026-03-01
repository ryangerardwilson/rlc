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
    progress_line = _progress_line(max(10, w), state)
    _safe_addstr(stdscr, h - 2, 0, progress_line, attr_dim())

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
    progress_line = _progress_line(max(10, w), state)
    _safe_addstr(stdscr, h - 2, 0, progress_line, attr_dim())

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
        "Seek forward/back: f / b",
        "Stop: x",
        "Delete selected track: dd",
        "Shuffle playlist: s",
        "Move track down/up: Ctrl+j / Ctrl+k",
        "Command bar: :",
        "Search prompt: /",
        "Search next/prev: n / N",
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


def _progress_line(width: int, state: AppState) -> str:
    elapsed = _projected_elapsed_seconds(state)
    duration = state.playback.duration_seconds
    time_text = f"{_fmt_time(elapsed)} / {_fmt_time(duration)}"

    min_bar = 10
    # total line = "[" + bar + "]" + " " + time_text
    #            = bar_w + 3 + len(time_text)
    bar_w = max(min_bar, width - len(time_text) - 3)
    if duration and duration > 0:
        pct = min(1.0, max(0.0, elapsed / duration))
    else:
        pct = 0.0
    filled = int(round(bar_w * pct))
    bar = "[" + ("#" * filled).ljust(bar_w, "-") + "]"
    line = f"{bar} {time_text}"
    return line[:width].ljust(width)


def _projected_elapsed_seconds(state: AppState) -> float:
    elapsed = max(0.0, state.playback.elapsed_seconds + state.ui.pending_seek_delta)
    duration = state.playback.duration_seconds
    if duration is not None and duration > 0:
        return min(duration, elapsed)
    return elapsed


def _fmt_time(value: float | None) -> str:
    if value is None:
        return "--:--"
    total = max(0, int(value))
    minutes, seconds = divmod(total, 60)
    hours, minutes = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"
