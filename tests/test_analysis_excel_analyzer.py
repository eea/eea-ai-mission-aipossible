import json
from pathlib import Path

import pytest
from openpyxl import Workbook

from analysis.excel_analyzer import run_batch


class DummyClient:
    model = "dummy-model"

    def analyze(self, text: str) -> dict:
        return {
            "provider": "mock",
            "system_prompt": "system",
            "user_prompt": f"user:{text}",
            "prompt_version": "v1",
            "result": '{"answers":{"Answer 1":"ok"}}',
        }


def _write_workbook(path: Path) -> None:
    workbook = Workbook()
    sheet = workbook.active
    assert sheet is not None
    sheet.title = "Sheet1"
    sheet["A1"] = "col7_Please explain"
    sheet["A2"] = "Row 2 value"
    sheet["A3"] = "Row 3 value"
    workbook.save(path)


def test_excel_analyzer_writes_one_json_per_row_with_metadata(tmp_path: Path) -> None:
    input_file = tmp_path / "source.xlsx"
    output_dir = tmp_path / "analysis"
    _write_workbook(input_file)

    stats = run_batch(
        input_file=input_file,
        sheet_name="Sheet1",
        column_name="col7_Please explain",
        header_row=1,
        output_dir=output_dir,
        client=DummyClient(),
        use_case="question_2_1_1_column_7",
        source_type="excel",
        source_path=str(input_file),
        verbose=False,
    )

    assert stats.processed == 2
    files = sorted(output_dir.glob("*.json"))
    assert len(files) == 2

    payload = json.loads(files[0].read_text(encoding="utf-8"))
    assert payload["source"]["use_case"] == "question_2_1_1_column_7"
    assert payload["source"]["source_type"] == "excel"
    assert payload["source"]["source_path"] == str(input_file)
    assert payload["source"]["sheet_name"] == "Sheet1"
    assert payload["source"]["column_name"] == "col7_Please explain"
    assert "row_index" in payload["source"]
    assert payload["answers"]["Answer 1"] == "ok"


def test_excel_analyzer_raises_when_sheet_missing(tmp_path: Path) -> None:
    input_file = tmp_path / "source.xlsx"
    _write_workbook(input_file)
    with pytest.raises(ValueError, match="Sheet not found"):
        run_batch(
            input_file=input_file,
            sheet_name="Missing",
            column_name="col7_Please explain",
            header_row=1,
            output_dir=tmp_path / "analysis",
            client=DummyClient(),
            verbose=False,
        )


def test_excel_analyzer_raises_when_column_missing(tmp_path: Path) -> None:
    input_file = tmp_path / "source.xlsx"
    _write_workbook(input_file)
    with pytest.raises(ValueError, match="Column header not found"):
        run_batch(
            input_file=input_file,
            sheet_name="Sheet1",
            column_name="missing_column",
            header_row=1,
            output_dir=tmp_path / "analysis",
            client=DummyClient(),
            verbose=False,
        )


def test_excel_analyzer_honors_max_items(tmp_path: Path) -> None:
    input_file = tmp_path / "source.xlsx"
    output_dir = tmp_path / "analysis"
    _write_workbook(input_file)

    stats = run_batch(
        input_file=input_file,
        sheet_name="Sheet1",
        column_name="col7_Please explain",
        header_row=1,
        output_dir=output_dir,
        client=DummyClient(),
        max_items=1,
        verbose=False,
    )

    assert stats.processed == 1
    assert len(list(output_dir.glob("*.json"))) == 1
