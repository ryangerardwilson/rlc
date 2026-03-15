from io import StringIO
from types import SimpleNamespace
from unittest.mock import patch

from rlc.main import HELP_TEXT, main


def test_help_prints_human_written_text() -> None:
    with patch("sys.stdout", new=StringIO()) as stdout:
        code = main(["-h"])

    assert code == 0
    assert stdout.getvalue() == f"{HELP_TEXT.rstrip()}\n"


def test_version_prints_single_value() -> None:
    with patch("sys.stdout", new=StringIO()) as stdout:
        code = main(["-v"])

    assert code == 0
    assert stdout.getvalue() == "0.0.0\n"


def test_conf_opens_default_config_in_editor() -> None:
    with patch.dict("os.environ", {"XDG_CONFIG_HOME": "/tmp/rlc-test-config", "VISUAL": "nvim"}, clear=False):
        with patch("subprocess.run") as subprocess_run:
            subprocess_run.return_value = SimpleNamespace(returncode=0)
            code = main(["conf"])

    assert code == 0
    assert subprocess_run.call_args.args[0][0] == "nvim"
    assert subprocess_run.call_args.args[0][-1] == "/tmp/rlc-test-config/rlc/config.json"


def test_upgrade_delegates_to_installer_upgrade_mode() -> None:
    results = [
        SimpleNamespace(returncode=0, stdout="0.1.3\n"),
        SimpleNamespace(returncode=0, stdout=""),
    ]

    with patch("subprocess.run", side_effect=results) as subprocess_run:
        code = main(["-u"])

    assert code == 0
    assert subprocess_run.call_args_list[0].args[0][-1] == "-v"
    assert subprocess_run.call_args_list[1].args[0][-1] == "-u"
