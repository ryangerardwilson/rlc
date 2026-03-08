from rlc.state import AppState
from rlc.ui.curses_app import _handle_key


def test_quit_works_while_shortcuts_overlay_is_open() -> None:
    state = AppState()
    state.ui.show_shortcuts = True

    _handle_key(ord("q"), state, [], None, None)  # type: ignore[arg-type]

    assert state.ui.should_quit is True
