"""Helpers for reading repo configuration from environment variables."""

import os
from pathlib import Path


def _resolve_config_path() -> Path:
    repo_root = Path(__file__).resolve().parent
    default_api_path = repo_root / ".env.api"
    legacy_default_path = repo_root / ".env"
    configured = os.getenv("MISSION_CONFIG_FILE")
    if not configured:
        if default_api_path.exists():
            return default_api_path
        return legacy_default_path
    configured_path = Path(configured)
    if configured_path.is_absolute():
        return configured_path
    return (repo_root / configured_path).resolve()


def _read_env_file_value(key: str) -> str | None:
    env_path = _resolve_config_path()
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


def get_str_setting(key: str, default: str = "", aliases: tuple[str, ...] = ()) -> str:
    for candidate in (key, *aliases):
        value = os.getenv(candidate)
        if value is None:
            value = _read_env_file_value(candidate)
        if value is not None:
            return value.strip()
    return default


def get_bool_setting(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        value = _read_env_file_value(key)
    if value is None:
        return default
    normalized = value.strip().lower()
    return normalized in {"1", "true", "yes", "y", "on"}
