"""Utility helpers for pre-analysis runs."""

import hashlib
import json
from pathlib import Path
from typing import Any


def normalize_text(value: Any | None) -> str:
    """Normalize cell text for prompting."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def truncate_text(text: str, max_chars: int) -> tuple[str, bool, int]:
    """Return truncated text, whether truncation occurred, and original length."""
    original_length = len(text)
    if original_length <= max_chars:
        return text, False, original_length
    return text[:max_chars], True, original_length


def output_path_for_row(output_dir: Path, key: str) -> Path:
    """Compute output path for a row using a stable hash key."""
    filename = hashlib.sha256(key.encode("utf-8")).hexdigest() + ".json"
    return output_dir / filename


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            for index in range(len(lines) - 1, 0, -1):
                if lines[index].startswith("```"):
                    return "\n".join(lines[1:index]).strip()
    return stripped


def parse_pattern(result: str) -> dict[str, Any] | None:
    """Parse a JSON string containing pattern data."""
    if not result:
        return None
    cleaned = _strip_code_fences(result)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data
