"""Persist OpenAI model and API key chosen in the overlay (BYOK)."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

from src.utils.config_loader import APP_DATA_DIR

log = logging.getLogger("mewgent.llm_user_store")

_USER_FILE = "openai_user_settings.json"


def user_llm_settings_path() -> Path:
    d = APP_DATA_DIR / "data"
    d.mkdir(parents=True, exist_ok=True)
    return d / _USER_FILE


@dataclass
class UserLlm:
    model: str | None = None
    api_key: str | None = None


def load_user_llm() -> UserLlm:
    path = user_llm_settings_path()
    if not path.exists():
        return UserLlm()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            return UserLlm()
        model = data.get("model")
        key = data.get("api_key")
        return UserLlm(
            model=model if isinstance(model, str) and model.strip() else None,
            api_key=key if isinstance(key, str) and key.strip() else None,
        )
    except Exception:
        log.warning(
            "Could not read %s — ignoring user LLM settings", path, exc_info=True
        )
        return UserLlm()


def save_user_llm(user: UserLlm) -> None:
    path = user_llm_settings_path()
    payload: dict[str, str] = {}
    if user.model and user.model.strip():
        payload["model"] = user.model.strip()
    if user.api_key and user.api_key.strip():
        payload["api_key"] = user.api_key.strip()
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
