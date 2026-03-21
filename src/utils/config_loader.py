from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("mewgent.config")

if getattr(sys, "frozen", False):
    PROJECT_ROOT = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    APP_DATA_DIR = Path(sys.executable).parent
else:
    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    APP_DATA_DIR = PROJECT_ROOT
CONFIG_DIR = PROJECT_ROOT / "config"


@dataclass
class DatabaseConfig:
    path: str = "data/mewgent.db"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "mewgent.log"


@dataclass
class SaveFileConfig:
    enabled: bool = True
    path: str = ""
    poll_interval_ms: int = 2000


@dataclass
class LLMConfig:
    enabled: bool = False
    model: str = "gpt-4o-mini"
    mock: bool = False


@dataclass
class HotkeyConfig:
    toggle: str = "Ctrl+Shift+M"


@dataclass
class UpdateConfig:
    check_url: str = ""


@dataclass
class AppConfig:
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    save_file: SaveFileConfig = field(default_factory=SaveFileConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    hotkey: HotkeyConfig = field(default_factory=HotkeyConfig)
    update: UpdateConfig = field(default_factory=UpdateConfig)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        log.warning("Config file not found: %s — using defaults", path)
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def load_config() -> AppConfig:
    settings_raw = _load_yaml(CONFIG_DIR / "settings.yaml")

    app = AppConfig(
        database=DatabaseConfig(**settings_raw.get("database", {})),
        logging=LoggingConfig(**settings_raw.get("logging", {})),
        save_file=SaveFileConfig(**settings_raw.get("save_file", {})),
        llm=LLMConfig(**settings_raw.get("llm", {})),
        hotkey=HotkeyConfig(**settings_raw.get("hotkey", {})),
        update=UpdateConfig(**settings_raw.get("update", {})),
    )

    log.info("Config loaded from %s", CONFIG_DIR)
    return app
