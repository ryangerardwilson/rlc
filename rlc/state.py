from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class UIState:
    selected_index: int = 0
    should_quit: bool = False
    status_line: str = "Ready"
    show_shortcuts: bool = False
    single_track_mode: bool = False
    command_mode: bool = False
    command_prefix: str = ":"
    command_buffer: str = ""
    command_cursor: int = 0
    command_intent: str | None = None
    download_in_progress: bool = False
    search_query: str = ""
    search_results: list[int] = field(default_factory=list)
    search_cursor: int = -1
    search_is_fuzzy: bool = False
    search_mode_label: str = "Search"
    pending_seek_delta: float = 0.0
    pending_seek_deadline: float = 0.0
    last_pause_toggle_at: float = 0.0
    playlists_root: Path | None = None
    current_dir: Path | None = None
    in_playlist_view: bool = False


@dataclass(slots=True)
class PlaybackState:
    now_playing: str | None = None
    now_playing_path: Path | None = None
    is_playing: bool = False
    is_paused: bool = False
    suppress_autonext_once: bool = False
    elapsed_seconds: float = 0.0
    duration_seconds: float | None = None
    spectrum_levels: list[float] = field(default_factory=lambda: [0.0] * 24)
    spectrum_peaks: list[float] = field(default_factory=lambda: [0.0] * 24)


@dataclass(slots=True)
class AppState:
    ui: UIState = field(default_factory=UIState)
    playback: PlaybackState = field(default_factory=PlaybackState)
