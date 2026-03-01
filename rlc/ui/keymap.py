from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyAction:
    name: str


KEY_ACTIONS = {
    ord("q"): KeyAction("quit"),
    ord("j"): KeyAction("down"),
    ord("k"): KeyAction("up"),
    ord("l"): KeyAction("play_selected"),
    ord(" "): KeyAction("toggle_pause"),
    ord("n"): KeyAction("search_next"),
    ord("p"): KeyAction("search_prev"),
    ord(":"): KeyAction("command_mode"),
    ord("s"): KeyAction("stop"),
}
