from rlc.state import AppState


def test_default_state() -> None:
    state = AppState()
    assert state.ui.selected_index == 0
    assert state.ui.command_intent is None
    assert state.playback.now_playing is None
    assert state.playback.is_playing is False
