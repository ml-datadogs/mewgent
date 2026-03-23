"""Tests for config YAML merge and defaults (isolated temp settings.yaml)."""

from __future__ import annotations

import pytest

from src.utils import config_loader
from src.utils.config_loader import load_config


@pytest.fixture
def config_dir(monkeypatch: pytest.MonkeyPatch, tmp_path):
    monkeypatch.setattr(config_loader, "CONFIG_DIR", tmp_path)
    return tmp_path


def test_missing_settings_yaml_uses_defaults(config_dir):
    cfg = load_config()
    assert cfg.logging.level == "INFO"
    assert cfg.logging.file == "mewgent.log"
    assert cfg.save_file.enabled is True
    assert cfg.save_file.poll_interval_ms == 2000
    assert cfg.save_file.path == ""
    assert cfg.llm.enabled is False
    assert cfg.llm.model == "gpt-4o-mini"
    assert cfg.hotkey.toggle == "Ctrl+Shift+M"
    assert cfg.update.check_url == ""
    assert cfg.database.path == "data/mewgent.db"


def test_partial_logging_rest_defaults(config_dir):
    (config_dir / "settings.yaml").write_text(
        "logging:\n  level: DEBUG\n",
        encoding="utf-8",
    )
    cfg = load_config()
    assert cfg.logging.level == "DEBUG"
    assert cfg.logging.file == "mewgent.log"


def test_partial_save_file_rest_defaults(config_dir):
    (config_dir / "settings.yaml").write_text(
        "save_file:\n  poll_interval_ms: 500\n",
        encoding="utf-8",
    )
    cfg = load_config()
    assert cfg.save_file.poll_interval_ms == 500
    assert cfg.save_file.enabled is True
    assert cfg.save_file.path == ""


def test_empty_yaml_file_uses_defaults(config_dir):
    (config_dir / "settings.yaml").write_text("", encoding="utf-8")
    cfg = load_config()
    assert cfg.logging.level == "INFO"
