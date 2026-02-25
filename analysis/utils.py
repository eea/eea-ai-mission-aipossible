"""Utility functions for mission scraper analysis."""

import hashlib
import json
from pathlib import Path
from typing import Any, cast


def load_page_json(path: Path) -> dict[str, Any]:
    """Load a page JSON payload from disk."""
    data = json.loads(path.read_text(encoding="utf-8"))
    return cast(dict[str, Any], data)


def normalize_text(text: Any | None) -> str:
    """Normalize text for prompting or storage."""
    if text is None:
        return ""
    return " ".join(str(text).split())


def build_prompt(page: dict) -> str:
    """Build a prompt from a page payload."""
    parts = [
        normalize_text(page.get("title")),
        normalize_text(page.get("subtitle")),
        normalize_text(page.get("document_description")),
    ]
    section_texts = []
    for section in page.get("sections", []):
        title = normalize_text(section.get("section_title"))
        content = normalize_text(section.get("content"))
        if title:
            section_texts.append(title)
        if content:
            section_texts.append(content)
    parts.extend(section_texts)
    return "\n".join([part for part in parts if part])


def _strip_code_fences(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            for index in range(len(lines) - 1, 0, -1):
                if lines[index].startswith("```"):
                    return "\n".join(lines[1:index]).strip()
    return stripped


def parse_answers(result: str) -> dict[str, str] | None:
    """Parse a JSON string containing answers and return a dictionary of answers, or None if parsing fails."""
    if not result:
        return None
    cleaned = _strip_code_fences(result)
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    answers = data.get("answers")
    if not isinstance(answers, dict):
        return None
    return {str(key): "" if value is None else str(value) for key, value in answers.items()}


def output_path_for_url(output_dir: Path, url: str) -> Path:
    """Compute output path for a page URL."""
    filename = hashlib.sha256(url.encode("utf-8")).hexdigest() + ".json"
    return output_dir / filename
