"""Utility functions for loading environment variables from a file."""

from pathlib import Path


def load_env_file(path: Path) -> dict[str, str]:
    """
    Load environment variables from a file.

    Args:
        path (Path): Path to the environment file.

    Returns:
        dict[str, str]: Dictionary of environment variable key-value pairs.
    """
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip("'").strip('"')
    return values
