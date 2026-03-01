from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyAction:
    name: str


KEY_ACTIONS = {
    ord("q"): KeyAction("quit"),
    ord("?"): KeyAction("toggle_help"),
    ord("j"): KeyAction("down"),
    ord("k"): KeyAction("up"),
    10: KeyAction("move_item_down"),  # Ctrl+j
    11: KeyAction("move_item_up"),  # Ctrl+k
    ord("/"): KeyAction("search_mode"),
    ord("l"): KeyAction("play_selected"),
    ord(" "): KeyAction("toggle_pause"),
    ord("f"): KeyAction("seek_forward"),
    ord("b"): KeyAction("seek_backward"),
    ord("n"): KeyAction("search_next"),
    ord("N"): KeyAction("search_prev"),
    ord("s"): KeyAction("shuffle_playlist"),
    ord(":"): KeyAction("command_mode"),
    ord("x"): KeyAction("stop"),
}
