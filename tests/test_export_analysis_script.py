from pathlib import Path

from scripts import export_analysis


def test_main_passes_default_paths(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_export_analysis_to_md(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(export_analysis, "export_analysis_to_md", _fake_export_analysis_to_md)
    monkeypatch.setattr(
        "sys.argv",
        ["prog", "--input", "data/analysis", "--output", "data/exports"],
    )

    result = export_analysis.main()

    assert result == 0
    assert captured["input_dir"] == Path("data/analysis")
    assert captured["output_dir"] == Path("data/exports")
    assert captured["combine"] is False
    assert captured["include_header"] is True


def test_main_supports_run_id(monkeypatch, tmp_path):
    captured: dict[str, object] = {}
    run_id = "20260227_143015"
    input_root = tmp_path / "analysis"
    (input_root / run_id).mkdir(parents=True)
    output_root = tmp_path / "exports"

    def _fake_export_analysis_to_md(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(export_analysis, "export_analysis_to_md", _fake_export_analysis_to_md)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--input",
            str(input_root),
            "--run-id",
            run_id,
            "--output",
            str(output_root),
            "--combine",
        ],
    )

    result = export_analysis.main()

    assert result == 0
    assert captured["input_dir"] == input_root / run_id
    assert captured["output_dir"] == output_root / run_id
    assert captured["combine"] is True
