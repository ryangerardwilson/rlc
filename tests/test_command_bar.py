from rlc.ui.curses_app import _parse_download_command


def test_parse_download_command_with_mp3_name() -> None:
    got = _parse_download_command("stand_by_me.mp3 https://youtu.be/abc")
    assert got == ("stand_by_me.mp3", "https://youtu.be/abc")


def test_parse_download_command_appends_mp3() -> None:
    got = _parse_download_command("stand_by_me https://youtu.be/abc")
    assert got == ("stand_by_me.mp3", "https://youtu.be/abc")


def test_parse_download_command_rejects_missing_url() -> None:
    assert _parse_download_command("stand_by_me.mp3") is None


def test_parse_download_command_rejects_path_name() -> None:
    assert _parse_download_command("foo/bar.mp3 https://youtu.be/abc") is None
