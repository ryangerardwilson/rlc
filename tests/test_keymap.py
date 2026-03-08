from rlc.ui.keymap import KEY_ACTIONS


def test_quit_keymap_present() -> None:
    assert ord("q") in KEY_ACTIONS
    assert KEY_ACTIONS[ord("q")].name == "quit"


def test_playlist_navigation_keymap_present() -> None:
    assert KEY_ACTIONS[ord("l")].name == "play_selected"
    assert KEY_ACTIONS[ord("h")].name == "go_parent"
    assert KEY_ACTIONS[ord(",")].name == "leader_mode"
    assert KEY_ACTIONS[ord("n")].name == "new_playlist_mode"
