from __future__ import annotations

import curses
import time
from pathlib import Path

from rlc.config import AppConfig
from rlc.library import scan_music_files
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
    tracks = scan_music_files(config.music_dir)
    player = FFplayBackend()
    analyzer = FFMpegSpectrumAnalyzer(bands=len(state.playback.spectrum_levels))

    if not tracks:
        state.ui.status_line = f"No tracks found in {config.music_dir}. Press q to quit."
    elif not player.available():
        state.ui.status_line = "ffplay not found in PATH. Install ffmpeg package."
    elif not analyzer.available():
        state.ui.status_line = (
            f"Loaded {len(tracks)} tracks. ffmpeg not found, visualizer disabled."
        )
    else:
        state.ui.status_line = (
            f"Loaded {len(tracks)} tracks. Enter=play j/k=navigate s=stop q=quit"
        )

    last_frame = 0.0
    frame_interval = 1.0 / max(1, config.fps)

    try:
        while not state.ui.should_quit:
            key = stdscr.getch()
            if key != -1:
                _handle_key(key, state, tracks, player, analyzer)

            was_playing = state.playback.is_playing
            is_playing = player.is_playing()
            state.playback.is_playing = is_playing
            state.playback.spectrum_levels = analyzer.levels()
            state.playback.spectrum_peaks = analyzer.peaks()

            if was_playing and not is_playing:
                analyzer.stop()
                state.playback.spectrum_levels = analyzer.levels()
                state.playback.spectrum_peaks = analyzer.peaks()

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

    if action.name == "quit":
        state.ui.should_quit = True
        return

    if action.name == "down" and tracks:
        state.ui.selected_index = min(len(tracks) - 1, state.ui.selected_index + 1)
        return

    if action.name == "up" and tracks:
        state.ui.selected_index = max(0, state.ui.selected_index - 1)
        return

    if action.name == "stop":
        player.stop()
        analyzer.stop()
        state.playback.spectrum_levels = analyzer.levels()
        state.playback.spectrum_peaks = analyzer.peaks()
        state.playback.is_playing = False
        state.ui.status_line = "Stopped"
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
            state.ui.status_line = f"Playing: {track.name}"
        except Exception as exc:  # pragma: no cover
            state.ui.status_line = f"Playback error: {exc}"
