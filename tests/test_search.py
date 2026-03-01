from pathlib import Path

from rlc.state import AppState
from rlc.ui.curses_app import _run_search_command


def test_search_prefers_startswith_over_contains() -> None:
    state = AppState()
    tracks = [
        Path("/tmp/my_stand.mp3"),
        Path("/tmp/stand_by_me.mp3"),
    ]

    _run_search_command(state, tracks, "stand")

    assert state.ui.search_mode_label == "Prefix"
    assert state.ui.search_results
    assert state.ui.search_results[0] == 1


def test_search_uses_contains_before_fuzzy() -> None:
    state = AppState()
    tracks = [
        Path("/tmp/abc_def_song.mp3"),
        Path("/tmp/random.mp3"),
    ]

    _run_search_command(state, tracks, "def")

    assert state.ui.search_mode_label == "Search"
    assert state.ui.search_is_fuzzy is False
    assert state.ui.search_results == [0]


def test_search_uses_fuzzy_when_contains_has_no_match() -> None:
    state = AppState()
    tracks = [Path("/tmp/stand_by_me.mp3"), Path("/tmp/other_song.mp3")]

    _run_search_command(state, tracks, "sbm")

    assert state.ui.search_is_fuzzy is True
    assert state.ui.search_results
    assert state.ui.search_results[0] == 0
