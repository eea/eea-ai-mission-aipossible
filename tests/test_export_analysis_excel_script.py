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


def test_main_supports_run_id_and_disable_flags(monkeypatch, tmp_path):
    captured: dict[str, object] = {}
    run_id = "20260227_143015"
    input_root = tmp_path / "analysis"
    (input_root / run_id).mkdir(parents=True)
    output_root = tmp_path / "exports"

    def _fake_export_analysis_to_excel(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(export_analysis_excel, "export_analysis_to_excel", _fake_export_analysis_to_excel)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--input",
            str(input_root),
            "--run-id",
            run_id,
            "--output",
            str(output_root / "run.xlsx"),
            "--no-header-bold",
            "--no-auto-width",
            "--no-wrap-text",
            "--no-freeze-panes",
        ],
    )

    result = export_analysis_excel.main()

    assert result == 0
    assert captured["input_dir"] == input_root / run_id
    assert captured["output_path"] == output_root / run_id / "run.xlsx"
    assert captured["header_bold"] is False
    assert captured["auto_width"] is False
    assert captured["wrap_text"] is False
    assert captured["freeze_panes"] is None


def test_main_uses_dotenv_output_and_export_defaults(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_export_analysis_to_excel(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(export_analysis_excel, "export_analysis_to_excel", _fake_export_analysis_to_excel)
    monkeypatch.setattr(
        export_analysis_excel,
        "load_env_file",
        lambda path: {"OUTPUT_DIR": "custom-analysis", "EXPORT_DIR": "custom-exports"},
    )
    monkeypatch.setattr("sys.argv", ["prog"])

    result = export_analysis_excel.main()

    assert result == 0
    assert captured["input_dir"] == Path("custom-analysis")
    assert captured["output_path"] == Path("custom-exports") / "analysis.xlsx"
