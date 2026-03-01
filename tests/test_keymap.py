from rlc.ui.keymap import KEY_ACTIONS


def test_quit_keymap_present() -> None:
    assert ord("q") in KEY_ACTIONS
    assert KEY_ACTIONS[ord("q")].name == "quit"
