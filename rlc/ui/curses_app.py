from __future__ import annotations

import curses
import difflib
import queue
import threading
import time
from pathlib import Path

from rlc.config import AppConfig
from rlc.library import (
    display_name,
    download_youtube_audio,
    is_supported_youtube_url,
    scan_music_files,
)
from rlc.player.ffplay_backend import FFplayBackend
from rlc.state import AppState
from rlc.ui.keymap import KEY_ACTIONS
from rlc.ui.theme import init_theme
from rlc.ui.views import render
from rlc.visualizer.analyzer import FFMpegSpectrumAnalyzer


def run_curses_app(config: AppConfig) -> int:
    return curses.wrapper(_run, config)


def _run(stdscr: curses.window, config: AppConfig) -> int:
    curses.curs_set(0)
    init_theme(stdscr)
    stdscr.nodelay(True)
    stdscr.timeout(max(1, int(1000 / max(1, config.fps))))

    state = AppState()
    if config.startup_track and config.startup_track.exists() and config.startup_track.is_file():
        tracks = [config.startup_track]
        state.ui.single_track_mode = True
    else:
        tracks = scan_music_files(config.music_dir)
    player = FFplayBackend()
    analyzer = FFMpegSpectrumAnalyzer(bands=len(state.playback.spectrum_levels))
    download_results: queue.Queue[tuple[bool, str]] = queue.Queue()
    download_thread: threading.Thread | None = None
    last_d_time = 0.0

    if not tracks:
        state.ui.status_line = f"No tracks found in {config.music_dir}. Press q to quit."
    elif not player.available():
        state.ui.status_line = "ffplay not found in PATH. Install ffmpeg package."
    elif not analyzer.available():
        state.ui.status_line = (
            f"Loaded {len(tracks)} tracks. ffmpeg not found, visualizer disabled."
        )
    elif config.startup_track:
        state.ui.status_line = f"Startup track: {config.startup_track.name}"
    else:
        state.ui.status_line = f"Loaded {len(tracks)} tracks."

    if config.startup_track and tracks and player.available():
        try:
            track = tracks[0]
            player.play(track)
            analyzer.start(track)
            state.playback.now_playing = track.name
            state.playback.is_playing = True
            state.playback.is_paused = False
            state.ui.selected_index = 0
            state.ui.status_line = f"Playing: {track.name}"
        except Exception as exc:  # pragma: no cover
            state.ui.status_line = f"Playback error: {exc}"

    last_frame = 0.0
    frame_interval = 1.0 / max(1, config.fps)

    try:
        while not state.ui.should_quit:
            should_rescan = _process_download_events(state, download_results)
            if should_rescan:
                tracks = (
                    [config.startup_track]
                    if config.startup_track
                    and config.startup_track.exists()
                    and config.startup_track.is_file()
                    else scan_music_files(config.music_dir)
                )
                _clamp_selection(state, tracks)
                _recompute_search_results(state, tracks)
            if download_thread and not download_thread.is_alive():
                download_thread = None
            if state.ui.download_in_progress:
                updated_tracks = (
                    [config.startup_track]
                    if config.startup_track
                    and config.startup_track.exists()
                    and config.startup_track.is_file()
                    else scan_music_files(config.music_dir)
                )
                if len(updated_tracks) != len(tracks):
                    tracks = updated_tracks
                    _clamp_selection(state, tracks)
                    _recompute_search_results(state, tracks)

            key = stdscr.getch()
            if key != -1:
                if state.ui.command_mode:
                    download_thread = _handle_command_key(
                        key,
                        state,
                        tracks,
                        config.music_dir,
                        download_thread,
                        download_results,
                    )
                else:
                    if key == ord("d"):
                        now = time.monotonic()
                        if now - last_d_time <= 0.6:
                            tracks = _delete_selected_track(state, tracks, config.music_dir)
                            _recompute_search_results(state, tracks)
                            last_d_time = 0.0
                        else:
                            state.ui.status_line = "Press d again quickly to delete track"
                            last_d_time = now
                        continue
                    _handle_key(key, state, tracks, player, analyzer)

            was_playing = state.playback.is_playing
            is_playing = player.is_playing()
            state.playback.is_playing = is_playing
            state.playback.is_paused = player.is_paused()
            state.playback.spectrum_levels = analyzer.levels()
            state.playback.spectrum_peaks = analyzer.peaks()

            if was_playing and not is_playing:
                analyzer.stop()
                state.playback.spectrum_levels = analyzer.levels()
                state.playback.spectrum_peaks = analyzer.peaks()
                state.playback.is_paused = False

            now = time.monotonic()
            if now - last_frame >= frame_interval:
                render(stdscr, state, tracks)
                last_frame = now
    finally:
        analyzer.close()
        player.close()

    return 0


def _handle_key(
    key: int,
    state: AppState,
    tracks: list[Path],
    player: FFplayBackend,
    analyzer: FFMpegSpectrumAnalyzer,
) -> None:
    action = KEY_ACTIONS.get(key)
    if not action:
        return

    if action.name == "toggle_help":
        state.ui.show_shortcuts = not state.ui.show_shortcuts
        state.ui.command_mode = False
        state.ui.command_prefix = ":"
        state.ui.command_buffer = ""
        state.ui.status_line = "Shortcuts" if state.ui.show_shortcuts else "Ready"
        return

    if state.ui.show_shortcuts:
        return

    if action.name == "quit":
        state.ui.should_quit = True
        return

    if action.name == "down" and tracks:
        state.ui.selected_index = min(len(tracks) - 1, state.ui.selected_index + 1)
        return

    if action.name == "up" and tracks:
        state.ui.selected_index = max(0, state.ui.selected_index - 1)
        return

    if action.name == "command_mode":
        state.ui.command_mode = True
        state.ui.command_prefix = ":"
        state.ui.command_buffer = ""
        return

    if action.name == "search_mode":
        state.ui.command_mode = True
        state.ui.command_prefix = "/"
        state.ui.command_buffer = ""
        return

    if action.name == "stop":
        player.stop()
        analyzer.stop()
        state.playback.spectrum_levels = analyzer.levels()
        state.playback.spectrum_peaks = analyzer.peaks()
        state.playback.is_playing = False
        state.playback.is_paused = False
        state.ui.status_line = "Stopped"
        return

    if action.name == "toggle_pause":
        if not state.playback.is_playing:
            state.ui.status_line = "Nothing is playing"
            return
        paused = player.toggle_pause()
        state.playback.is_paused = paused
        state.ui.status_line = "Paused" if paused else "Resumed"
        return

    if action.name == "search_next":
        if _jump_search_result(state, step=1):
            state.ui.status_line = _search_status(state)
        return

    if action.name == "search_prev":
        if _jump_search_result(state, step=-1):
            state.ui.status_line = _search_status(state)
        return

    if action.name == "play_selected":
        if not tracks:
            state.ui.status_line = "No tracks available"
            return
        track = tracks[state.ui.selected_index]
        try:
            player.play(track)
            analyzer.start(track)
            state.playback.now_playing = track.name
            state.playback.is_playing = True
            state.playback.is_paused = False
            state.ui.status_line = f"Playing: {track.name}"
        except Exception as exc:  # pragma: no cover
            state.ui.status_line = f"Playback error: {exc}"


def _handle_command_key(
    key: int,
    state: AppState,
    tracks: list[Path],
    music_dir: Path,
    download_thread: threading.Thread | None,
    download_results: queue.Queue[tuple[bool, str]],
) -> threading.Thread | None:
    if key in (27,):  # Esc
        state.ui.command_mode = False
        state.ui.command_prefix = ":"
        state.ui.command_buffer = ""
        state.ui.status_line = "Command cancelled"
        return download_thread

    if key in (10, 13):  # Enter
        command = state.ui.command_buffer.strip()
        prefix = state.ui.command_prefix
        state.ui.command_mode = False
        state.ui.command_prefix = ":"
        state.ui.command_buffer = ""
        if not command:
            state.ui.status_line = "Command cancelled"
            return download_thread

        if prefix == "/":
            _run_search_command(state, tracks, command)
            return download_thread

        if download_thread and download_thread.is_alive():
            state.ui.status_line = "Download already in progress"
            return download_thread

        parsed = _parse_download_command(command)
        if not parsed:
            state.ui.status_line = "Use: :name.mp3 <youtube-url>"
            return download_thread
        target_name, url = parsed
        if not is_supported_youtube_url(url):
            state.ui.status_line = "Command expects a YouTube URL"
            return download_thread

        state.ui.download_in_progress = True
        state.ui.status_line = f"Downloading {target_name}..."
        thread = threading.Thread(
            target=_download_worker,
            args=(target_name, url, music_dir, download_results),
            daemon=True,
        )
        thread.start()
        return thread

    if key in (curses.KEY_BACKSPACE, 127, 8):
        state.ui.command_buffer = state.ui.command_buffer[:-1]
        return download_thread

    if 32 <= key <= 126:
        state.ui.command_buffer += chr(key)
        if len(state.ui.command_buffer) > 2048:
            state.ui.command_buffer = state.ui.command_buffer[:2048]

    return download_thread


def _parse_download_command(command: str) -> tuple[str, str] | None:
    parts = command.strip().split(maxsplit=1)
    if len(parts) != 2:
        return None
    name, url = parts
    if not name:
        return None
    if "/" in name or "\\" in name:
        return None
    if not name.lower().endswith(".mp3"):
        name = f"{name}.mp3"
    if name in {".mp3", "..mp3"}:
        return None
    return name, url.strip()


def _download_worker(
    target_name: str,
    url: str,
    music_dir: Path,
    output: queue.Queue[tuple[bool, str]],
) -> None:
    ok, message = download_youtube_audio(url, music_dir, target_name)
    output.put((ok, message))


def _process_download_events(
    state: AppState,
    events: queue.Queue[tuple[bool, str]],
) -> bool:
    needs_rescan = False
    while True:
        try:
            ok, message = events.get_nowait()
        except queue.Empty:
            return needs_rescan
        state.ui.download_in_progress = False
        state.ui.status_line = message if ok else message
        needs_rescan = needs_rescan or ok


def _run_search_command(state: AppState, tracks: list[Path], raw_query: str) -> None:
    query = raw_query.strip().lower()
    state.ui.search_query = query
    if not query:
        state.ui.search_results = []
        state.ui.search_cursor = -1
        state.ui.search_is_fuzzy = False
        state.ui.search_mode_label = "Search"
        state.ui.status_line = "Search cleared"
        return

    startswith_results = [
        i for i, track in enumerate(tracks) if display_name(track).lower().startswith(query)
    ]
    contains_results = [
        i for i, track in enumerate(tracks) if query in display_name(track).lower()
    ]

    results = startswith_results or contains_results
    is_fuzzy = False
    mode_label = "Prefix" if startswith_results else "Search"
    if not results:
        results = _fuzzy_search_indices(tracks, query)
        is_fuzzy = bool(results)
        if is_fuzzy:
            mode_label = "Fuzzy"

    state.ui.search_results = results
    state.ui.search_is_fuzzy = is_fuzzy
    state.ui.search_mode_label = mode_label
    if not results:
        state.ui.search_cursor = -1
        state.ui.search_mode_label = "Search"
        state.ui.status_line = f"No results for '{query}'"
        return

    state.ui.search_cursor = 0
    state.ui.selected_index = results[0]
    state.ui.status_line = _search_status(state)


def _jump_search_result(state: AppState, *, step: int) -> bool:
    if not state.ui.search_results:
        return False
    count = len(state.ui.search_results)
    cur = state.ui.search_cursor if state.ui.search_cursor >= 0 else 0
    cur = (cur + step) % count
    state.ui.search_cursor = cur
    state.ui.selected_index = state.ui.search_results[cur]
    return True


def _search_status(state: AppState) -> str:
    total = len(state.ui.search_results)
    idx = state.ui.search_cursor + 1 if state.ui.search_cursor >= 0 else 0
    mode = state.ui.search_mode_label
    return f"{mode} '{state.ui.search_query}': {idx}/{total} (n/p)"


def _recompute_search_results(state: AppState, tracks: list[Path]) -> None:
    if not state.ui.search_query:
        return
    _run_search_command(state, tracks, state.ui.search_query)


def _fuzzy_search_indices(
    tracks: list[Path],
    query: str,
    *,
    min_score: float = 0.28,
    max_results: int = 200,
) -> list[int]:
    scored: list[tuple[float, int]] = []
    for i, track in enumerate(tracks):
        name = display_name(track).lower()
        normalized = name.replace("_", " ").replace("-", " ")

        ratio = max(
            difflib.SequenceMatcher(a=query, b=name).ratio(),
            difflib.SequenceMatcher(a=query, b=normalized).ratio(),
        )
        if _is_subsequence(query, name) or _is_subsequence(query, normalized):
            ratio += 0.25
        if query and query[0] == (name[:1] or ""):
            ratio += 0.05
        if ratio >= min_score:
            scored.append((ratio, i))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [idx for _, idx in scored[:max_results]]


def _is_subsequence(needle: str, haystack: str) -> bool:
    it = iter(haystack)
    return all(ch in it for ch in needle)


def _delete_selected_track(
    state: AppState,
    tracks: list[Path],
    music_dir: Path,
) -> list[Path]:
    if not tracks:
        state.ui.status_line = "No track selected"
        return tracks

    track = tracks[state.ui.selected_index]
    try:
        track.unlink()
    except OSError as exc:
        state.ui.status_line = f"Delete failed: {exc}"
        return tracks

    updated = scan_music_files(music_dir)
    if updated:
        state.ui.selected_index = min(state.ui.selected_index, len(updated) - 1)
    else:
        state.ui.selected_index = 0
    state.ui.status_line = f"Deleted: {track.name}"
    return updated


def _clamp_selection(state: AppState, tracks: list[Path]) -> None:
    if not tracks:
        state.ui.selected_index = 0
        return
    state.ui.selected_index = min(state.ui.selected_index, len(tracks) - 1)
