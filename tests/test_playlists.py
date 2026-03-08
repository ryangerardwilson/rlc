from pathlib import Path

from rlc.library.scanner import list_playlists, scan_playlist_tracks
from rlc.state import AppState
from rlc.ui.curses_app import (
    _restore_selection,
    _create_playlist,
    _current_download_dir,
    _normalize_playlist_name,
    _open_rename_prompt,
    _rename_selected_playlist,
)


def test_list_playlists_returns_immediate_directories_sorted(tmp_path: Path) -> None:
    (tmp_path / "zeta").mkdir()
    (tmp_path / "Alpha").mkdir()
    (tmp_path / "readme.txt").write_text("x", encoding="utf-8")

    got = list_playlists(tmp_path)

    assert [path.name for path in got] == ["Alpha", "zeta"]


def test_scan_playlist_tracks_scans_audio_files_recursively(tmp_path: Path) -> None:
    playlist = tmp_path / "mix"
    playlist.mkdir()
    (playlist / "a.mp3").write_text("x", encoding="utf-8")
    nested = playlist / "disc2"
    nested.mkdir()
    (nested / "b.flac").write_text("x", encoding="utf-8")
    (nested / "note.txt").write_text("x", encoding="utf-8")

    got = scan_playlist_tracks(playlist)

    assert sorted(path.name for path in got) == ["a.mp3", "b.flac"]


def test_normalize_playlist_name_rejects_invalid_values() -> None:
    assert _normalize_playlist_name("  ") is None
    assert _normalize_playlist_name("a/b") is None
    assert _normalize_playlist_name("..") is None
    assert _normalize_playlist_name("  \"Road Trip\"  ") == "Road Trip"


def test_create_playlist_creates_new_directory(tmp_path: Path) -> None:
    ok, message, created = _create_playlist(tmp_path, "Road Trip")
    assert ok is True
    assert message == "Created playlist: Road Trip"
    assert created == tmp_path / "Road Trip"
    assert created.is_dir()


def test_current_download_dir_requires_playlist_view() -> None:
    state = AppState()
    state.ui.playlists_root = Path("/tmp/root")
    state.ui.current_dir = Path("/tmp/root/one")
    state.ui.in_playlist_view = False

    assert _current_download_dir(state) is None

    state.ui.in_playlist_view = True
    assert _current_download_dir(state) == Path("/tmp/root/one")


def test_rename_selected_playlist(tmp_path: Path) -> None:
    root = tmp_path / "music"
    playlist = root / "Old"
    playlist.mkdir(parents=True)

    state = AppState()
    state.ui.playlists_root = root
    playlists = [playlist]
    ok, message, renamed = _rename_selected_playlist(state, playlists, "New")

    assert ok is True
    assert message == "Renamed playlist: Old -> New"
    assert renamed == root / "New"
    assert renamed.is_dir()


def test_open_rename_prompt_prefills_selected_playlist_name(tmp_path: Path) -> None:
    one = tmp_path / "One"
    one.mkdir()
    two = tmp_path / "Two"
    two.mkdir()
    playlists = [one, two]

    state = AppState()
    state.ui.selected_index = 1
    ok = _open_rename_prompt(state, playlists)

    assert ok is True
    assert state.ui.command_mode is True
    assert state.ui.command_prefix == ":name> "
    assert state.ui.command_buffer == "Two"
    assert state.ui.command_cursor == 3
    assert state.ui.command_intent == "rename_playlist"


def test_restore_selection_prefers_currently_playing_track(tmp_path: Path) -> None:
    state = AppState()
    a = tmp_path / "a.mp3"
    b = tmp_path / "b.mp3"
    c = tmp_path / "c.mp3"
    tracks = [a, b, c]
    state.playback.now_playing_path = b
    state.ui.selected_index = 0

    _restore_selection(state, tracks, preferred=state.playback.now_playing_path, fallback=a)

    assert state.ui.selected_index == 1
