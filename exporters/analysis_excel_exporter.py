"""Exporter for analysis JSON files to a single Excel workbook."""

import json
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Font

from analysis.utils import parse_answers


def _load_rows(files: list[Path]) -> tuple[list[dict], list[str], str | None, str | None]:
    rows = []
    answer_keys: set[str] = set()
    row_identifier_column_name: str | None = None
    summary_column_name: str | None = None
    for path in files:
        data = json.loads(path.read_text(encoding="utf-8"))
        data["source_file"] = path.name  # Add the filename as a new field
        answers = data.get("answers")
        if not isinstance(answers, dict):
            parsed = parse_answers(str(data.get("ai_result") or ""))
            if isinstance(parsed, dict):
                answers = parsed
                data["answers"] = parsed
        if isinstance(answers, dict):
            answer_keys.update(str(key) for key in answers.keys())
        source = data.get("source") or {}
        if row_identifier_column_name is None:
            row_identifier_column_name = source.get("row_identifier_column") or None
        if summary_column_name is None:
            summary_column_name = source.get("column_name") or None
        rows.append(data)

    ordered_answer_keys = sorted(answer_keys)
    if not ordered_answer_keys:
        ordered_answer_keys = [f"Answer {index}" for index in range(1, 11)]
    return rows, ordered_answer_keys, row_identifier_column_name, summary_column_name


def _write_data_rows(
    sheet,
    rows: list[dict],
    ordered_answer_keys: list[str],
    row_identifier_column_name: str | None,
    summary_column_name: str | None,
) -> None:
    for data in rows:
        answers = data.get("answers")
        if not isinstance(answers, dict):
            answers = {}
        row_values = [
            data.get("url", ""),
            data.get("title", ""),
            data.get("source_file", ""),
        ]
        if row_identifier_column_name:
            identifier = (data.get("source") or {}).get("row_identifier")
            row_values.append("" if identifier is None else str(identifier))
        if summary_column_name:
            summary_value = data.get("summary")
            row_values.append("" if summary_value is None else str(summary_value))
        for key in ordered_answer_keys:
            value = answers.get(key, "")
            row_values.append("" if value is None else str(value))
        sheet.append(row_values)


def _apply_wrap_text(sheet) -> None:
    wrapped_alignment = Alignment(wrap_text=True, vertical="top")
    for row in sheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrapped_alignment


def _build_workbook_with_header(
    row_identifier_column_name: str | None,
    summary_column_name: str | None,
    ordered_answer_keys: list[str],
    header_bold: bool,
):
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    if sheet is None:
        raise RuntimeError("Failed to create Excel worksheet.")
    sheet.title = "Analysis"
    extra_cols = [row_identifier_column_name] if row_identifier_column_name else []
    summary_cols = [summary_column_name] if summary_column_name else []
    sheet.append(["url", "title", "source_file", *extra_cols, *summary_cols, *ordered_answer_keys])
    header_font = Font(bold=header_bold)
    for cell in sheet[1]:
        cell.font = header_font
    return workbook, sheet


def _apply_auto_width(sheet) -> None:
    for column in sheet.columns:
        max_length = 0
        for cell in column:
            value = "" if cell.value is None else str(cell.value)
            if len(value) > max_length:
                max_length = len(value)
        adjusted = min(max(max_length + 2, 10), 100)
        sheet.column_dimensions[column[0].column_letter].width = adjusted


def export_analysis_to_excel(
    input_dir: Path,
    output_path: Path,
    overwrite: bool = False,
    verbose: bool = True,
    dry_run: bool = False,
    header_bold: bool = True,
    auto_width: bool = True,
    wrap_text: bool = True,
    freeze_panes: str | None = "A2",
) -> None:
    """Export analysis JSON files to a single Excel workbook.

    Args:
        input_dir: Directory containing analysis JSON files.
        output_path: Excel file path to write.
        overwrite: If True, overwrite existing output.
        verbose: If True, print progress messages.
        dry_run: If True, simulate the export without writing outputs.
        header_bold: If True, apply bold style to header row.
        auto_width: If True, auto-size column widths based on cell content.
        wrap_text: If True, enable wrapped text for body cells.
        freeze_panes: Excel freeze panes reference (e.g. "A2"), or None to disable.

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

    rows, ordered_answer_keys, row_identifier_column_name, summary_column_name = _load_rows(files)
    workbook, sheet = _build_workbook_with_header(
        row_identifier_column_name, summary_column_name, ordered_answer_keys, header_bold
    )
    _write_data_rows(sheet, rows, ordered_answer_keys, row_identifier_column_name, summary_column_name)

    if freeze_panes:
        sheet.freeze_panes = freeze_panes

    if wrap_text:
        _apply_wrap_text(sheet)

    if auto_width:
        _apply_auto_width(sheet)

    workbook.save(output_path)
    if verbose:
        print(f"saved: {output_path.name} ({len(rows)} items)")
