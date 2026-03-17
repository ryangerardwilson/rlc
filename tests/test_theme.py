from rlc.ui import theme


class _FakeScreen:
    def __init__(self) -> None:
        self.calls: list[tuple[str, int]] = []

    def bkgd(self, ch: str, attr: int) -> None:
        self.calls.append((ch, attr))


def test_theme_uses_terminal_default_attributes(monkeypatch) -> None:
    lifecycle_calls: list[str] = []

    monkeypatch.setattr(theme.curses, "has_colors", lambda: True)
    monkeypatch.setattr(theme.curses, "start_color", lambda: lifecycle_calls.append("start_color"))
    monkeypatch.setattr(theme.curses, "use_default_colors", lambda: lifecycle_calls.append("use_default_colors"))

    screen = _FakeScreen()

    theme.init_theme(screen)

    assert lifecycle_calls == ["start_color", "use_default_colors"]
    assert screen.calls == [(" ", theme.attr_base())]
    assert theme.attr_base() == theme.curses.A_NORMAL
    assert theme.attr_dim() == theme.curses.A_NORMAL
    assert theme.attr_bright() == theme.curses.A_BOLD
    assert theme.attr_selected() == theme.curses.A_BOLD | theme.curses.A_REVERSE
