from __future__ import annotations

from pathlib import Path

from rlc.config import build_app_config, default_config_path, load_user_config, save_user_config


def test_default_config_path_uses_xdg(monkeypatch) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", "/tmp/xdg")
    assert default_config_path() == Path("/tmp/xdg/rlc/config.json")


def test_build_app_config_prefers_cli_music_dir(tmp_path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text('{"music_dir": "/tmp/from-config", "fps": 40}', encoding="utf-8")

    app_cfg = build_app_config(
        cli_music_dir="/tmp/from-cli",
        cli_fps=None,
        config_path=cfg,
    )

    assert app_cfg.music_dir == Path("/tmp/from-cli")
    assert app_cfg.fps == 40


def test_build_app_config_defaults_when_file_missing(tmp_path) -> None:
    app_cfg = build_app_config(
        cli_music_dir=None,
        cli_fps=None,
        config_path=tmp_path / "missing.json",
    )

    assert app_cfg.music_dir == Path("~/Music").expanduser().resolve()
    assert app_cfg.fps == 20


def test_save_user_config_writes_music_dir(tmp_path) -> None:
    cfg = tmp_path / "config.json"
    save_user_config(cfg, music_dir="/tmp/music")
    loaded = load_user_config(cfg)
    assert loaded.music_dir == "/tmp/music"


def test_save_user_config_preserves_existing_values(tmp_path) -> None:
    cfg = tmp_path / "config.json"
    cfg.write_text('{"music_dir": "/tmp/music", "fps": 20}', encoding="utf-8")
    save_user_config(cfg, music_dir="/tmp/new-music")
    loaded = load_user_config(cfg)
    assert loaded.music_dir == "/tmp/new-music"
    assert loaded.fps == 20
