"""Exporter for scraped pages to JSONL format."""

import json
from pathlib import Path

from env_settings import get_bool_setting

def export_pages_to_jsonl(
    input_dir: Path,
    output_path: Path,
    overwrite: bool = False,
    verbose: bool = True,
    dry_run: bool = False,
) -> None:
    """Export scraped page JSON files to a single JSONL file.

    Args:
        input_dir: Directory containing page JSON files.
        output_path: JSONL file path to write.
        overwrite: If True, overwrite existing output.
        verbose: If True, print progress messages.
        dry_run: If True, simulate the export without writing outputs.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    files = sorted(input_dir.glob("*.json"))

    if output_path.exists() and not overwrite:
        if verbose:
            print(f"skip: {output_path.name}")
        return

    if dry_run:
        if verbose:
            print(f"would save: {output_path.name} ({len(files)} items)")
        return

    ensure_ascii = get_bool_setting("JSON_ENSURE_ASCII", default=False)
    with output_path.open("w", encoding="utf-8") as handle:
        for path in files:
            data = json.loads(path.read_text(encoding="utf-8"))
            handle.write(json.dumps(data, ensure_ascii=ensure_ascii))
            handle.write("\n")

    if verbose:
        print(f"saved: {output_path.name} ({len(files)} items)")
