from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class UIState:
    selected_index: int = 0
    should_quit: bool = False
    status_line: str = "Ready"
    show_shortcuts: bool = False
    playlist_mode: bool = False
    single_track_mode: bool = False
    command_mode: bool = False
    command_prefix: str = ":"
    command_buffer: str = ""
    download_in_progress: bool = False
    search_query: str = ""
    search_results: list[int] = field(default_factory=list)
    search_cursor: int = -1
    search_is_fuzzy: bool = False
    search_mode_label: str = "Search"


@dataclass(slots=True)
class PlaybackState:
    now_playing: str | None = None
    is_playing: bool = False
    is_paused: bool = False
    suppress_autonext_once: bool = False
    spectrum_levels: list[float] = field(default_factory=lambda: [0.0] * 24)
    spectrum_peaks: list[float] = field(default_factory=lambda: [0.0] * 24)


@dataclass(slots=True)
class AppState:
    ui: UIState = field(default_factory=UIState)
    playback: PlaybackState = field(default_factory=PlaybackState)
