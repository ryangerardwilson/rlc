from io import StringIO
from unittest.mock import patch

from rlc.main import main


def test_version_prints_single_value() -> None:
    with patch("sys.stdout", new=StringIO()) as stdout:
        code = main(["-v"])

    assert code == 0
    assert stdout.getvalue() == "0.0.0\n"


def test_upgrade_delegates_to_installer_upgrade_mode() -> None:
    fake_response = type("Response", (), {"read": lambda self: b"#!/usr/bin/env bash\n"})()

    class _Context:
        def __enter__(self_inner):
            return fake_response

        def __exit__(self_inner, exc_type, exc, tb):
            return False

    with patch("urllib.request.urlopen", return_value=_Context()):
        with patch("subprocess.run") as subprocess_run:
            subprocess_run.return_value.returncode = 0
            code = main(["-u"])

    assert code == 0
    assert "-u" in subprocess_run.call_args.args[0]
