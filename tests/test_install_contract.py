import os
import subprocess
import tempfile
from pathlib import Path


INSTALLER = Path(__file__).resolve().parents[1] / "install.sh"


def _write_executable(path: Path, body: str) -> None:
    path.write_text(body, encoding="utf-8")
    path.chmod(0o755)


def test_installer_version_flag_without_argument_prints_latest_release() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bin_dir = tmp_path / "bin"
        bin_dir.mkdir()

        _write_executable(
            bin_dir / "curl",
            "#!/usr/bin/bash\n"
            "if [[ \"$1\" == \"-fsSL\" && \"$2\" == \"https://api.github.com/repos/ryangerardwilson/rlc/releases/latest\" ]]; then\n"
            "  printf '%s\n' '{\"tag_name\":\"v0.1.3\"}'\n"
            "  exit 0\n"
            "fi\n"
            "echo unexpected curl call >&2\n"
            "exit 1\n",
        )

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"

        result = subprocess.run(
            ["/usr/bin/bash", str(INSTALLER), "-v"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )

        assert result.stdout == "0.1.3\n"
        assert result.stderr == ""


def test_upgrade_same_version_uses_rlc_v_and_exits_cleanly() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        bin_dir = tmp_path / "bin"
        home_dir = tmp_path / "home"
        bin_dir.mkdir()
        home_dir.mkdir()

        _write_executable(
            bin_dir / "curl",
            "#!/usr/bin/bash\n"
            "if [[ \"$1\" == \"-fsSL\" && \"$2\" == \"https://api.github.com/repos/ryangerardwilson/rlc/releases/latest\" ]]; then\n"
            "  printf '%s\n' '{\"tag_name\":\"v0.1.3\"}'\n"
            "  exit 0\n"
            "fi\n"
            "echo unexpected curl call >&2\n"
            "exit 1\n",
        )
        _write_executable(
            bin_dir / "rlc",
            "#!/usr/bin/bash\n"
            "if [[ \"$1\" == \"-v\" ]]; then\n"
            "  printf '0.1.3\\n'\n"
            "  exit 0\n"
            "fi\n"
            "echo unexpected rlc invocation >&2\n"
            "exit 1\n",
        )

        env = os.environ.copy()
        env["PATH"] = f"{bin_dir}:{env['PATH']}"
        env["HOME"] = str(home_dir)

        result = subprocess.run(
            ["/usr/bin/bash", str(INSTALLER), "-u"],
            capture_output=True,
            text=True,
            env=env,
            check=True,
        )

        assert result.stdout == ""
        assert result.stderr == ""
