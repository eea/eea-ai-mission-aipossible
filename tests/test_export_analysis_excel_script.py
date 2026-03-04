from pathlib import Path

from scripts import export_analysis_excel


def test_main_passes_default_formatting_options(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_export_analysis_to_excel(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(export_analysis_excel, "export_analysis_to_excel", _fake_export_analysis_to_excel)
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--input", "data/analysis", "--output", "data/exports/analysis.xlsx"],
    )

    result = export_analysis_excel.main()

    assert result == 0
    assert captured["input_dir"] == Path("data/analysis")
    assert captured["output_path"] == Path("data/exports/analysis.xlsx")
    assert captured["header_bold"] is True
    assert captured["auto_width"] is True
    assert captured["wrap_text"] is True
    assert captured["freeze_panes"] == "A2"


def test_main_supports_run_id_and_disable_flags(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_export_analysis_to_excel(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(export_analysis_excel, "export_analysis_to_excel", _fake_export_analysis_to_excel)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--input",
            "data/analysis",
            "--run-id",
            "20260227_143015",
            "--output",
            "data/exports/run.xlsx",
            "--no-header-bold",
            "--no-auto-width",
            "--no-wrap-text",
            "--no-freeze-panes",
        ],
    )

    result = export_analysis_excel.main()

    assert result == 0
    assert captured["input_dir"] == Path("data/analysis") / "20260227_143015"
    assert captured["output_path"] == Path("data/exports/run.xlsx")
    assert captured["header_bold"] is False
    assert captured["auto_width"] is False
    assert captured["wrap_text"] is False
    assert captured["freeze_panes"] is None
