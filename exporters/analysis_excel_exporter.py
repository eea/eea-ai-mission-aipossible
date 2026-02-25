"""Exporter for analysis JSON files to a single Excel workbook."""

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Font


def export_analysis_to_excel(
    input_dir: Path,
    output_path: Path,
    overwrite: bool = False,
    verbose: bool = True,
    dry_run: bool = False,
) -> None:
    """Export analysis JSON files to a single Excel workbook.

    Args:
        input_dir: Directory containing analysis JSON files.
        output_path: Excel file path to write.
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

    rows = []
    answer_keys: set[str] = set()
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source_file"] = path.name  # Add the filename as a new field
        answers = data.get("answers")
        if isinstance(answers, dict):
            answer_keys.update(str(key) for key in answers.keys())
        rows.append(data)

    ordered_answer_keys = sorted(answer_keys)
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if sheet is None:
        raise RuntimeError("Failed to create Excel worksheet.")
    sheet.title = "Analysis"
    sheet.append(["url", "title", "source_file", *ordered_answer_keys])
    header_font = Font(bold=True)
    for cell in sheet[1]:
        cell.font = header_font

    for data in rows:
        answers = data.get("answers")
        if not isinstance(answers, dict):
            answers = {}
        row_values = [
            data.get("url", ""),
            data.get("title", ""),
            data.get("source_file", ""),
        ]
        for key in ordered_answer_keys:
            value = answers.get(key, "")
            row_values.append("" if value is None else str(value))
        sheet.append(row_values)

    workbook.save(output_path)
    if verbose:
        print(f"saved: {output_path.name} ({len(rows)} items)")
