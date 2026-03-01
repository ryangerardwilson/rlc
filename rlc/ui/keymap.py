from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class KeyAction:
    name: str


KEY_ACTIONS = {
    ord("q"): KeyAction("quit"),
    ord("j"): KeyAction("down"),
    ord("k"): KeyAction("up"),
    ord("s"): KeyAction("stop"),
    10: KeyAction("play_selected"),  # Enter
}
