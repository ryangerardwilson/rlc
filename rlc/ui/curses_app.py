from __future__ import annotations

import curses
import difflib
import queue
import random
import shutil
import threading
import time
from pathlib import Path

from rlc.config import AppConfig
from rlc.library import (
    display_name,
    duration_seconds,
    download_youtube_audio,
    is_supported_youtube_url,
    list_playlists,
    scan_playlist_tracks,
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
    # Make bare Esc responsive in terminals that otherwise wait too long for
    # possible escape sequences.
    try:
        curses.set_escdelay(25)
    except (AttributeError, curses.error):
        pass
    curses.curs_set(0)
    init_theme(stdscr)
    stdscr.nodelay(True)
    input_timeout_ms = max(1, int(1000 / max(1, config.fps)))
    stdscr.timeout(input_timeout_ms)

    state = AppState()
    state.ui.playlists_root = config.music_dir
    state.ui.current_dir = config.music_dir
    if config.startup_track and config.startup_track.exists() and config.startup_track.is_file():
        tracks = [config.startup_track]
        state.ui.single_track_mode = True
    else:
        tracks = list_playlists(config.music_dir)
    player = FFplayBackend()
    analyzer = FFMpegSpectrumAnalyzer(bands=len(state.playback.spectrum_levels))
    download_results: queue.Queue[tuple[bool, str]] = queue.Queue()
    download_thread: threading.Thread | None = None
    last_d_time = 0.0

    if not tracks:
        if state.ui.single_track_mode:
            state.ui.status_line = f"No tracks found in {config.music_dir}. Press q to quit."
        else:
            state.ui.status_line = (
                f"No playlists found in {config.music_dir}. Press , then name to create one."
            )
    elif not player.available():
        state.ui.status_line = "ffplay not found in PATH. Install ffmpeg package."
    elif not analyzer.available():
        state.ui.status_line = (
            f"Loaded {len(tracks)} items. ffmpeg not found, visualizer disabled."
        )
    elif config.startup_track:
        state.ui.status_line = f"Startup track: {config.startup_track.name}"
    else:
        state.ui.status_line = f"Loaded {len(tracks)} playlists. ? for shortcuts"

    if config.startup_track and tracks and player.available():
        _play_index(0, state, tracks, player, analyzer)

    last_frame = 0.0
    frame_interval = 1.0 / max(1, config.fps)
    last_cursor_mode = False

    try:
        while not state.ui.should_quit:
            _flush_pending_seek(state, tracks, player, analyzer)
            should_rescan = _process_download_events(state, download_results)
            if should_rescan:
                previous_selected = _selected_entry(tracks, state.ui.selected_index)
                tracks = _reload_entries(state, config.startup_track)
                _restore_selection(
                    state,
                    tracks,
                    preferred=state.playback.now_playing_path,
                    fallback=previous_selected,
                )
                _recompute_search_results(state, tracks)
            if download_thread and not download_thread.is_alive():
                download_thread = None
            if state.ui.download_in_progress:
                previous_selected = _selected_entry(tracks, state.ui.selected_index)
                updated_tracks = _reload_entries(state, config.startup_track)
                if len(updated_tracks) != len(tracks):
                    tracks = updated_tracks
                    _restore_selection(
                        state,
                        tracks,
                        preferred=state.playback.now_playing_path,
                        fallback=previous_selected,
                    )
                    _recompute_search_results(state, tracks)

            key = stdscr.getch()
            if key != -1:
                if state.ui.command_mode:
                    if key == 27:
                        key = _read_alt_key(stdscr, input_timeout_ms)
                    download_thread = _handle_command_key(
                        key,
                        state,
                        tracks,
                        download_thread,
                        download_results,
                    )
                else:
                    if key == ord("d"):
                        now = time.monotonic()
                        if now - last_d_time <= 0.6:
                            tracks = _delete_selected_entry(state, tracks)
                            _recompute_search_results(state, tracks)
                            last_d_time = 0.0
                        else:
                            if state.ui.in_playlist_view or state.ui.single_track_mode:
                                state.ui.status_line = "Press d again quickly to delete track"
                            else:
                                state.ui.status_line = (
                                    "Press d again quickly to delete playlist"
                                )
                            last_d_time = now
                        continue
                    _handle_key(key, state, tracks, player, analyzer)

            was_playing = state.playback.is_playing
            is_playing = player.is_playing()
            state.playback.is_playing = is_playing
            state.playback.is_paused = player.is_paused()
            state.playback.elapsed_seconds = player.current_position()
            state.playback.spectrum_levels = analyzer.levels()
            state.playback.spectrum_peaks = analyzer.peaks()

            if was_playing and not is_playing:
                if state.playback.suppress_autonext_once:
                    state.playback.suppress_autonext_once = False
                    analyzer.stop()
                    state.playback.spectrum_levels = analyzer.levels()
                    state.playback.spectrum_peaks = analyzer.peaks()
                    state.playback.is_paused = False
                    state.playback.elapsed_seconds = 0.0
                    state.playback.duration_seconds = None
                elif _can_play_entries(state) and tracks and len(tracks) > 1:
                    next_index = (state.ui.selected_index + 1) % len(tracks)
                    _play_index(next_index, state, tracks, player, analyzer)
                else:
                    analyzer.stop()
                    state.playback.spectrum_levels = analyzer.levels()
                    state.playback.spectrum_peaks = analyzer.peaks()
                    state.playback.is_paused = False
                    state.playback.elapsed_seconds = 0.0
                    state.playback.duration_seconds = None

            now = time.monotonic()
            if now - last_frame >= frame_interval:
                if state.ui.command_mode != last_cursor_mode:
                    try:
                        curses.curs_set(1 if state.ui.command_mode else 0)
                    except curses.error:
                        pass
                    last_cursor_mode = state.ui.command_mode
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
    if key == 27 and state.ui.search_query:
        _clear_search_state(state)
        state.ui.status_line = "Search cleared"
        return

    if (
        key == ord("n")
        and state.ui.search_query
        and state.ui.search_results
        and not state.ui.command_mode
    ):
        if _jump_search_result(state, step=1):
            state.ui.status_line = _search_status(state)
        return

    action = KEY_ACTIONS.get(key)
    if not action:
        return

    if action.name == "toggle_help":
        state.ui.show_shortcuts = not state.ui.show_shortcuts
        _reset_command_input(state)
        state.ui.status_line = "Shortcuts" if state.ui.show_shortcuts else "Ready"
        return

    if action.name == "quit":
        state.ui.should_quit = True
        return

    if state.ui.show_shortcuts:
        return

    if action.name == "down" and tracks:
        state.ui.selected_index = min(len(tracks) - 1, state.ui.selected_index + 1)
        return

    if action.name == "up" and tracks:
        state.ui.selected_index = max(0, state.ui.selected_index - 1)
        return

    if action.name == "move_item_down" and tracks:
        if not _can_play_entries(state):
            state.ui.status_line = "Open a playlist to reorder tracks"
            return
        i = state.ui.selected_index
        if i < len(tracks) - 1:
            tracks[i], tracks[i + 1] = tracks[i + 1], tracks[i]
            state.ui.selected_index = i + 1
            _recompute_search_results(state, tracks)
            state.ui.status_line = "Moved track down"
        return

    if action.name == "move_item_up" and tracks:
        if not _can_play_entries(state):
            state.ui.status_line = "Open a playlist to reorder tracks"
            return
        i = state.ui.selected_index
        if i > 0:
            tracks[i], tracks[i - 1] = tracks[i - 1], tracks[i]
            state.ui.selected_index = i - 1
            _recompute_search_results(state, tracks)
            state.ui.status_line = "Moved track up"
        return

    if action.name == "command_mode":
        state.ui.command_mode = True
        state.ui.command_prefix = ":"
        state.ui.command_buffer = ""
        state.ui.command_cursor = 0
        state.ui.command_intent = None
        return

    if action.name == "leader_mode":
        if state.ui.single_track_mode:
            state.ui.status_line = "Leader commands unavailable in single-track mode"
            return
        state.ui.command_mode = True
        state.ui.command_prefix = ","
        state.ui.command_buffer = ""
        state.ui.command_cursor = 0
        state.ui.command_intent = "leader"
        return

    if action.name == "new_playlist_mode":
        if state.ui.single_track_mode:
            state.ui.status_line = "Playlist creation not available in single-track mode"
            return
        if state.ui.in_playlist_view:
            _open_ytd_prompt(state)
            return
        _open_new_playlist_prompt(state)
        return

    if action.name == "search_mode":
        state.ui.command_mode = True
        state.ui.command_prefix = "/"
        state.ui.command_buffer = ""
        state.ui.command_cursor = 0
        state.ui.command_intent = None
        return

    if action.name == "stop":
        state.ui.pending_seek_delta = 0.0
        state.ui.pending_seek_deadline = 0.0
        player.stop()
        analyzer.stop()
        state.playback.spectrum_levels = analyzer.levels()
        state.playback.spectrum_peaks = analyzer.peaks()
        state.playback.is_playing = False
        state.playback.is_paused = False
        state.playback.elapsed_seconds = 0.0
        state.playback.duration_seconds = None
        state.playback.suppress_autonext_once = True
        state.ui.status_line = "Stopped"
        return

    if action.name == "toggle_pause":
        state.ui.pending_seek_delta = 0.0
        state.ui.pending_seek_deadline = 0.0
        now = time.monotonic()
        if now - state.ui.last_pause_toggle_at < 0.15:
            return
        state.ui.last_pause_toggle_at = now
        if not state.playback.is_playing:
            state.ui.status_line = "Nothing is playing"
            return
        paused = player.toggle_pause()
        analyzer.set_paused(paused)
        state.playback.is_paused = paused
        state.ui.status_line = "Paused" if paused else "Resumed"
        return

    if action.name == "seek_forward":
        _queue_seek(state, +10.0)
        return

    if action.name == "seek_backward":
        _queue_seek(state, -10.0)
        return

    if action.name == "search_next":
        if _jump_search_result(state, step=1):
            state.ui.status_line = _search_status(state)
        return

    if action.name == "search_prev":
        if _jump_search_result(state, step=-1):
            state.ui.status_line = _search_status(state)
        return

    if action.name == "shuffle_playlist":
        if not _can_play_entries(state):
            state.ui.status_line = "Open a playlist to shuffle tracks"
            return
        if state.ui.single_track_mode:
            state.ui.status_line = "Single track mode: nothing to shuffle"
            return
        if len(tracks) < 2:
            state.ui.status_line = "Need at least 2 tracks to shuffle"
            return
        random.shuffle(tracks)
        state.ui.selected_index = 0
        _recompute_search_results(state, tracks)
        _play_index(0, state, tracks, player, analyzer)
        state.ui.status_line = f"Shuffled playlist ({len(tracks)} tracks)"
        return

    if action.name == "play_selected":
        if not state.ui.single_track_mode and not state.ui.in_playlist_view:
            if not tracks:
                state.ui.status_line = "No playlists available"
                return
            playlist = tracks[state.ui.selected_index]
            state.ui.current_dir = playlist
            state.ui.in_playlist_view = True
            state.ui.selected_index = 0
            _clear_search_state(state)
            updated = scan_playlist_tracks(playlist)
            tracks.clear()
            tracks.extend(updated)
            state.ui.status_line = f"Opened playlist: {playlist.name}"
            return
        state.ui.pending_seek_delta = 0.0
        state.ui.pending_seek_deadline = 0.0
        _play_index(state.ui.selected_index, state, tracks, player, analyzer)
        return

    if action.name == "go_parent":
        if state.ui.single_track_mode:
            state.ui.status_line = "Already at top level"
            return
        if not state.ui.in_playlist_view:
            state.ui.status_line = "Already at playlists root"
            return
        previous = state.ui.current_dir
        state.ui.in_playlist_view = False
        state.ui.current_dir = state.ui.playlists_root
        _clear_search_state(state)
        updated = list_playlists(state.ui.playlists_root or Path("."))
        tracks.clear()
        tracks.extend(updated)
        if previous in updated:
            state.ui.selected_index = updated.index(previous)
        else:
            state.ui.selected_index = 0
        state.ui.status_line = "Playlists"
        return


def _handle_command_key(
    key: int,
    state: AppState,
    tracks: list[Path],
    download_thread: threading.Thread | None,
    download_results: queue.Queue[tuple[bool, str]],
) -> threading.Thread | None:
    if key in (27,):  # Esc
        if state.ui.command_prefix == "/":
            _clear_search_state(state)
            state.ui.status_line = "Search cleared"
        else:
            state.ui.status_line = "Command cancelled"
        _reset_command_input(state)
        return download_thread

    if key in (10, 13):  # Enter
        command = state.ui.command_buffer.strip()
        prefix = state.ui.command_prefix
        intent = state.ui.command_intent
        was_command_active = state.ui.command_mode
        state.ui.command_mode = False
        state.ui.command_prefix = ":"
        state.ui.command_buffer = ""
        state.ui.command_cursor = 0
        state.ui.command_intent = None
        if not command:
            state.ui.status_line = "Command cancelled"
            return download_thread

        if prefix == "/":
            _run_search_command(state, tracks, command)
            return download_thread

        if prefix == ":name> " and intent == "new_playlist":
            root = state.ui.playlists_root
            if root is None:
                state.ui.status_line = "No playlists root configured"
                return download_thread
            ok, message, created = _create_playlist(root, command)
            state.ui.status_line = message
            if ok:
                updated = list_playlists(root)
                tracks.clear()
                tracks.extend(updated)
                if created in updated:
                    state.ui.selected_index = updated.index(created)
                else:
                    _clamp_selection(state, tracks)
                _clear_search_state(state)
            return download_thread

        if prefix == ":name> " and intent == "rename_playlist":
            ok, message, renamed = _rename_selected_playlist(state, tracks, command)
            state.ui.status_line = message
            if ok:
                root = state.ui.playlists_root
                if root is not None:
                    updated = list_playlists(root)
                    tracks.clear()
                    tracks.extend(updated)
                    if renamed in updated:
                        state.ui.selected_index = updated.index(renamed)
                    else:
                        _clamp_selection(state, tracks)
                    _clear_search_state(state)
            return download_thread

        if prefix == ",":
            if command == "rn":
                if _open_rename_prompt(state, tracks):
                    return download_thread
                return download_thread
            state.ui.status_line = "Unknown leader command. Use ,rn"
            return download_thread

        if prefix == ":ytd_cmd> " and intent == "youtube_download":
            if download_thread and download_thread.is_alive():
                state.ui.status_line = "Download already in progress"
                return download_thread

            output_dir = _current_download_dir(state)
            if output_dir is None:
                state.ui.status_line = "Open a playlist first (l), then download"
                return download_thread

            parsed = _parse_download_command(command)
            if not parsed:
                state.ui.status_line = "Use: name.mp3 <youtube-url>"
                return download_thread
            target_name, url = parsed
            if not is_supported_youtube_url(url):
                state.ui.status_line = "Command expects a YouTube URL"
                return download_thread

            state.ui.download_in_progress = True
            state.ui.status_line = f"Downloading {target_name}..."
            thread = threading.Thread(
                target=_download_worker,
                args=(target_name, url, output_dir, download_results),
                daemon=True,
            )
            thread.start()
            return thread

        if prefix == ":" and was_command_active:
            state.ui.status_line = "No ':' command implemented yet"
            return download_thread

    if key in (curses.KEY_BACKSPACE, 127, 8):
        if state.ui.command_cursor > 0:
            cur = state.ui.command_cursor
            state.ui.command_buffer = (
                state.ui.command_buffer[: cur - 1] + state.ui.command_buffer[cur:]
            )
            state.ui.command_cursor -= 1
        return download_thread

    if key == curses.KEY_DC:
        cur = state.ui.command_cursor
        if cur < len(state.ui.command_buffer):
            state.ui.command_buffer = (
                state.ui.command_buffer[:cur] + state.ui.command_buffer[cur + 1 :]
            )
        return download_thread

    if key in (curses.KEY_LEFT,):
        state.ui.command_cursor = max(0, state.ui.command_cursor - 1)
        return download_thread

    if key in (curses.KEY_RIGHT,):
        state.ui.command_cursor = min(
            len(state.ui.command_buffer), state.ui.command_cursor + 1
        )
        return download_thread

    if key in (curses.KEY_HOME, 1):  # Home / Ctrl+A
        state.ui.command_cursor = 0
        return download_thread

    if key in (curses.KEY_END, 5):  # End / Ctrl+E
        state.ui.command_cursor = len(state.ui.command_buffer)
        return download_thread

    if key == 23:  # Ctrl+W
        _delete_prev_word(state)
        return download_thread

    if key == 1002:  # Alt+b
        _move_prev_word(state)
        return download_thread

    if key == 1006:  # Alt+f
        _move_next_word(state)
        return download_thread

    if 32 <= key <= 126:
        cur = state.ui.command_cursor
        state.ui.command_buffer = (
            state.ui.command_buffer[:cur] + chr(key) + state.ui.command_buffer[cur:]
        )
        state.ui.command_cursor += 1
        if state.ui.command_prefix == "," and state.ui.command_buffer == "rn":
            _open_rename_prompt(state, tracks)
            return download_thread
        if len(state.ui.command_buffer) > 2048:
            state.ui.command_buffer = state.ui.command_buffer[:2048]
            state.ui.command_cursor = min(state.ui.command_cursor, 2048)

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
    output_dir: Path,
    output: queue.Queue[tuple[bool, str]],
) -> None:
    ok, message = download_youtube_audio(url, output_dir, target_name)
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
    return f"{mode} '{state.ui.search_query}': {idx}/{total} (n/N)"


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
) -> list[Path]:
    if not _can_play_entries(state):
        state.ui.status_line = "Open a playlist to delete tracks"
        return tracks
    if not tracks:
        state.ui.status_line = "No track selected"
        return tracks

    track = tracks[state.ui.selected_index]
    try:
        track.unlink()
    except OSError as exc:
        state.ui.status_line = f"Delete failed: {exc}"
        return tracks

    current_dir = state.ui.current_dir
    if current_dir is None:
        state.ui.status_line = "No playlist selected"
        return tracks
    updated = scan_playlist_tracks(current_dir)
    if updated:
        state.ui.selected_index = min(state.ui.selected_index, len(updated) - 1)
    else:
        state.ui.selected_index = 0
    state.ui.status_line = f"Deleted: {track.name}"
    return updated


def _delete_selected_entry(state: AppState, tracks: list[Path]) -> list[Path]:
    if state.ui.in_playlist_view or state.ui.single_track_mode:
        return _delete_selected_track(state, tracks)
    return _delete_selected_playlist(state, tracks)


def _delete_selected_playlist(
    state: AppState,
    playlists: list[Path],
) -> list[Path]:
    root = state.ui.playlists_root
    if root is None:
        state.ui.status_line = "No playlists root configured"
        return playlists
    if not playlists:
        state.ui.status_line = "No playlist selected"
        return playlists

    playlist = playlists[state.ui.selected_index]
    try:
        shutil.rmtree(playlist)
    except OSError as exc:
        state.ui.status_line = f"Delete failed: {exc}"
        return playlists

    updated = list_playlists(root)
    if updated:
        state.ui.selected_index = min(state.ui.selected_index, len(updated) - 1)
    else:
        state.ui.selected_index = 0
    state.ui.status_line = f"Deleted playlist: {playlist.name}"
    return updated


def _clamp_selection(state: AppState, tracks: list[Path]) -> None:
    if not tracks:
        state.ui.selected_index = 0
        return
    state.ui.selected_index = min(state.ui.selected_index, len(tracks) - 1)


def _selected_entry(tracks: list[Path], index: int) -> Path | None:
    if not tracks:
        return None
    safe_index = max(0, min(index, len(tracks) - 1))
    return tracks[safe_index]


def _restore_selection(
    state: AppState,
    tracks: list[Path],
    *,
    preferred: Path | None,
    fallback: Path | None,
) -> None:
    if not tracks:
        state.ui.selected_index = 0
        return
    if preferred in tracks:
        state.ui.selected_index = tracks.index(preferred)
        return
    if fallback in tracks:
        state.ui.selected_index = tracks.index(fallback)
        return
    _clamp_selection(state, tracks)


def _reload_entries(state: AppState, startup_track: Path | None) -> list[Path]:
    if startup_track and startup_track.exists() and startup_track.is_file():
        return [startup_track]

    if state.ui.in_playlist_view:
        current_dir = state.ui.current_dir
        if current_dir is None:
            return []
        return scan_playlist_tracks(current_dir)

    root = state.ui.playlists_root
    if root is None:
        return []
    return list_playlists(root)


def _clear_search_state(state: AppState) -> None:
    state.ui.search_query = ""
    state.ui.search_results = []
    state.ui.search_cursor = -1
    state.ui.search_is_fuzzy = False
    state.ui.search_mode_label = "Search"


def _can_play_entries(state: AppState) -> bool:
    return state.ui.single_track_mode or state.ui.in_playlist_view


def _current_download_dir(state: AppState) -> Path | None:
    if state.ui.single_track_mode:
        return state.ui.playlists_root
    if not state.ui.in_playlist_view:
        return None
    return state.ui.current_dir


def _reset_command_input(state: AppState) -> None:
    state.ui.command_mode = False
    state.ui.command_prefix = ":"
    state.ui.command_buffer = ""
    state.ui.command_cursor = 0
    state.ui.command_intent = None


def _open_new_playlist_prompt(state: AppState) -> None:
    state.ui.command_mode = True
    state.ui.command_prefix = ":name> "
    state.ui.command_buffer = ""
    state.ui.command_cursor = 0
    state.ui.command_intent = "new_playlist"


def _open_ytd_prompt(state: AppState) -> None:
    state.ui.command_mode = True
    state.ui.command_prefix = ":ytd_cmd> "
    state.ui.command_buffer = ""
    state.ui.command_cursor = 0
    state.ui.command_intent = "youtube_download"


def _open_rename_prompt(state: AppState, playlists: list[Path]) -> bool:
    if state.ui.in_playlist_view:
        _reset_command_input(state)
        state.ui.status_line = "Go to playlists root (h) to rename a playlist"
        return False
    if not playlists:
        _reset_command_input(state)
        state.ui.status_line = "No playlist selected"
        return False
    selected = playlists[state.ui.selected_index]
    state.ui.command_mode = True
    state.ui.command_prefix = ":name> "
    state.ui.command_buffer = selected.name
    state.ui.command_cursor = len(state.ui.command_buffer)
    state.ui.command_intent = "rename_playlist"
    return True


def _create_playlist(root: Path, raw_name: str) -> tuple[bool, str, Path | None]:
    name = _normalize_playlist_name(raw_name)
    if not name:
        return False, "Invalid playlist name", None

    try:
        root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"Cannot access playlists root: {exc}", None

    playlist_dir = root / name
    if playlist_dir.exists():
        if playlist_dir.is_dir():
            return False, f"Playlist already exists: {name}", None
        return False, f"Cannot create playlist, file exists: {name}", None

    try:
        playlist_dir.mkdir(parents=True, exist_ok=False)
    except OSError as exc:
        return False, f"Create playlist failed: {exc}", None
    return True, f"Created playlist: {name}", playlist_dir


def _rename_selected_playlist(
    state: AppState,
    playlists: list[Path],
    raw_name: str,
) -> tuple[bool, str, Path | None]:
    root = state.ui.playlists_root
    if root is None:
        return False, "No playlists root configured", None
    if not playlists:
        return False, "No playlist selected", None

    new_name = _normalize_playlist_name(raw_name)
    if not new_name:
        return False, "Invalid playlist name", None

    current = playlists[state.ui.selected_index]
    target = root / new_name
    if current == target:
        return False, "Playlist name unchanged", None
    if target.exists():
        return False, f"Playlist already exists: {new_name}", None

    try:
        current.rename(target)
    except OSError as exc:
        return False, f"Rename playlist failed: {exc}", None
    return True, f"Renamed playlist: {current.name} -> {new_name}", target


def _normalize_playlist_name(raw_name: str) -> str | None:
    name = raw_name.strip().strip("\"'")
    if not name:
        return None
    if "/" in name or "\\" in name:
        return None
    if name in {".", ".."}:
        return None
    return name


def _play_index(
    index: int,
    state: AppState,
    tracks: list[Path],
    player: FFplayBackend,
    analyzer: FFMpegSpectrumAnalyzer,
) -> None:
    if not tracks:
        state.ui.status_line = "No tracks available"
        return
    safe_index = max(0, min(index, len(tracks) - 1))
    track = tracks[safe_index]
    try:
        player.play(track)
        analyzer.start(track)
        state.ui.selected_index = safe_index
        state.playback.now_playing = track.name
        state.playback.now_playing_path = track
        state.playback.is_playing = True
        state.playback.is_paused = False
        state.playback.elapsed_seconds = 0.0
        state.playback.duration_seconds = duration_seconds(track)
        state.playback.suppress_autonext_once = False
        state.ui.status_line = f"Playing: {track.name}"
    except Exception as exc:  # pragma: no cover
        state.ui.status_line = f"Playback error: {exc}"


def _queue_seek(state: AppState, delta: float) -> None:
    state.ui.pending_seek_delta += delta
    state.ui.pending_seek_deadline = time.monotonic() + 0.5
    target = max(0.0, state.playback.elapsed_seconds + state.ui.pending_seek_delta)
    state.ui.status_line = _seek_status_text("Seek target", target, state.playback.duration_seconds)


def _flush_pending_seek(
    state: AppState,
    tracks: list[Path],
    player: FFplayBackend,
    analyzer: FFMpegSpectrumAnalyzer,
) -> None:
    if not _can_play_entries(state):
        state.ui.pending_seek_delta = 0.0
        state.ui.pending_seek_deadline = 0.0
        return
    if state.ui.pending_seek_delta == 0:
        return
    if time.monotonic() < state.ui.pending_seek_deadline:
        return

    delta = state.ui.pending_seek_delta
    state.ui.pending_seek_delta = 0.0
    state.ui.pending_seek_deadline = 0.0

    if not tracks:
        state.ui.status_line = "No tracks available"
        return

    pos = player.seek_relative(delta)
    if pos is None:
        state.ui.status_line = "Cannot seek while stopped/paused"
        return

    analyzer.start(tracks[state.ui.selected_index], position=pos)
    state.playback.elapsed_seconds = pos
    state.ui.status_line = _seek_status_text("Seeked to", pos, state.playback.duration_seconds)


def _seek_status_text(prefix: str, position: float, duration: float | None) -> str:
    if duration and duration > 0:
        pct = int(round(min(100.0, max(0.0, (position / duration) * 100.0))))
        return f"{prefix}: {pct}%"
    return f"{prefix}: --%"


def _read_alt_key(stdscr: curses.window, restore_timeout_ms: int) -> int:
    stdscr.timeout(30)
    try:
        nxt = stdscr.getch()
    finally:
        stdscr.timeout(restore_timeout_ms)
    if nxt == -1:
        return 27
    if nxt == ord("b"):
        return 1002
    if nxt == ord("f"):
        return 1006
    return nxt


def _delete_prev_word(state: AppState) -> None:
    s = state.ui.command_buffer
    cur = state.ui.command_cursor
    if cur <= 0:
        return
    i = cur
    while i > 0 and s[i - 1].isspace():
        i -= 1
    while i > 0 and not s[i - 1].isspace():
        i -= 1
    state.ui.command_buffer = s[:i] + s[cur:]
    state.ui.command_cursor = i


def _move_prev_word(state: AppState) -> None:
    s = state.ui.command_buffer
    i = state.ui.command_cursor
    while i > 0 and s[i - 1].isspace():
        i -= 1
    while i > 0 and not s[i - 1].isspace():
        i -= 1
    state.ui.command_cursor = i


def _move_next_word(state: AppState) -> None:
    s = state.ui.command_buffer
    i = state.ui.command_cursor
    n = len(s)
    while i < n and not s[i].isspace():
        i += 1
    while i < n and s[i].isspace():
        i += 1
    state.ui.command_cursor = i
