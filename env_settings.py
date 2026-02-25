"""Helpers for reading repo configuration from environment variables."""

import os
from pathlib import Path


def _read_env_file_value(key: str) -> str | None:
    env_path = Path(__file__).resolve().parent / ".env"
    if not env_path.exists():
        return None
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        env_key, value = line.split("=", 1)
        if env_key.strip() == key:
            return value.strip().strip("'").strip('"')
    return None


def get_bool_setting(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        value = _read_env_file_value(key)
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}
