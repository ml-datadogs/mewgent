from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

log = logging.getLogger("mewgent.config")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = PROJECT_ROOT / "config"


@dataclass
class CaptureConfig:
    window_title: str = "Mewgenics"
    interval_ms: int = 1000
    dpi_aware: bool = True


@dataclass
class OcrConfig:
    gpu: bool = True
    languages: list[str] = field(default_factory=lambda: ["en"])


@dataclass
class DatabaseConfig:
    path: str = "data/mewgent.db"


@dataclass
class LoggingConfig:
    level: str = "INFO"
    file: str = "mewgent.log"


@dataclass
class DebugConfig:
    save_screenshots: bool = True
    screenshots_dir: str = "debug_screenshots"


@dataclass
class SaveFileConfig:
    enabled: bool = True
    path: str = ""
    poll_interval_ms: int = 2000


@dataclass
class LLMConfig:
    enabled: bool = False
    model: str = "gpt-4o-mini"


@dataclass
class RegionDef:
    """Definition for a single OCR region.

    Simple regions (cat_name, cat_age, etc.) use ``rect``.
    Stat regions use ``rect_total``, ``rect_base``, ``rect_bonus`` instead.
    """
    rect: list[int] = field(default_factory=list)
    allowlist: str = ""
    preprocess: list[str] = field(default_factory=lambda: ["grayscale", "threshold"])
    icon_file: str = ""
    rect_total: list[int] = field(default_factory=list)
    rect_base: list[int] = field(default_factory=list)
    rect_bonus: list[int] = field(default_factory=list)

    @property
    def is_stat_triple(self) -> bool:
        return bool(self.rect_total)


@dataclass
class SceneTemplateDef:
    file: str
    match_threshold: float = 0.80
    match_region: list[int] = field(default_factory=lambda: [0, 0, 400, 100])


@dataclass
class RegionsConfig:
    game_resolution: list[int] = field(default_factory=lambda: [1920, 1080])
    scene_templates: dict[str, SceneTemplateDef] = field(default_factory=dict)
    regions: dict[str, RegionDef] = field(default_factory=dict)


@dataclass
class AppConfig:
    capture: CaptureConfig = field(default_factory=CaptureConfig)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    debug: DebugConfig = field(default_factory=DebugConfig)
    save_file: SaveFileConfig = field(default_factory=SaveFileConfig)
    llm: LLMConfig = field(default_factory=LLMConfig)
    regions: RegionsConfig = field(default_factory=RegionsConfig)


def _load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        log.warning("Config file not found: %s — using defaults", path)
        return {}
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data or {}


def _build_regions_config(raw: dict[str, Any]) -> RegionsConfig:
    cfg = RegionsConfig()
    cfg.game_resolution = raw.get("game_resolution", cfg.game_resolution)

    for name, tpl in raw.get("scene_templates", {}).items():
        cfg.scene_templates[name] = SceneTemplateDef(**tpl)

    for name, reg in raw.get("regions", {}).items():
        cfg.regions[name] = RegionDef(**reg)

    return cfg


def load_config() -> AppConfig:
    settings_raw = _load_yaml(CONFIG_DIR / "settings.yaml")
    regions_raw = _load_yaml(CONFIG_DIR / "regions.yaml")

    app = AppConfig(
        capture=CaptureConfig(**settings_raw.get("capture", {})),
        ocr=OcrConfig(**settings_raw.get("ocr", {})),
        database=DatabaseConfig(**settings_raw.get("database", {})),
        logging=LoggingConfig(**settings_raw.get("logging", {})),
        debug=DebugConfig(**settings_raw.get("debug", {})),
        save_file=SaveFileConfig(**settings_raw.get("save_file", {})),
        llm=LLMConfig(**settings_raw.get("llm", {})),
        regions=_build_regions_config(regions_raw),
    )

    log.info("Config loaded from %s", CONFIG_DIR)
    return app
