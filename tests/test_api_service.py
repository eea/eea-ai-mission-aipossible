from pathlib import Path
import re
import zipfile

from api.models import AnalysisRunRequest
from analysis.analyzer import BatchRunStats
from api.service import (
    REPO_ROOT,
    _build_client,
    build_excel_export_workbook,
    build_run_download_archive,
    start_run,
)


def test_analysis_run_request_defaults_timestamped_output_dir_true():
    request = AnalysisRunRequest()
    assert request.max_items is None


def test_build_client_uses_provider_default_prompts_dir(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_load_env_file(path: Path) -> dict[str, str]:
        if path.name == ".env.eea":
            return {
                "MODEL": "env-model",
                "API_URL": "https://api.example.com",
                "prompt_directory": "analysis/prompts",
            }
        if path.name == ".env.eea.keys":
            return {"API_KEY": "env-key"}
        return {}

    def _fake_get_client(provider: str, api_key: str, model: str, api_url: str, prompts_dir: Path):
        captured["provider"] = provider
        captured["api_key"] = api_key
        captured["model"] = model
        captured["api_url"] = api_url
        captured["prompts_dir"] = prompts_dir
        return object()

    monkeypatch.setattr("api.service.load_env_file", _fake_load_env_file)
    monkeypatch.setattr("api.service.get_client", _fake_get_client)
    monkeypatch.setattr("api.service.get_default_provider", lambda: "eea")
    monkeypatch.setattr("api.service.get_default_model_override", lambda: "")
    monkeypatch.setattr("api.service.get_default_api_key_override", lambda: "")

    _build_client()

    assert captured["provider"] == "eea"
    assert captured["model"] == "env-model"
    assert captured["api_url"] == "https://api.example.com"
    assert captured["api_key"] == "env-key"
    assert captured["prompts_dir"] == (REPO_ROOT / "analysis/prompts").resolve()


def test_build_client_raises_when_api_key_missing(monkeypatch):
    def _fake_load_env_file(path: Path) -> dict[str, str]:
        if path.name == ".env.eea":
            return {"MODEL": "env-model", "API_URL": "https://api.example.com", "prompt_directory": "analysis/prompts"}
        if path.name == ".env.eea.keys":
            return {}
        return {}

    monkeypatch.setattr("api.service.load_env_file", _fake_load_env_file)
    monkeypatch.setattr("api.service.get_default_provider", lambda: "eea")
    monkeypatch.setattr("api.service.get_default_model_override", lambda: "")
    monkeypatch.setattr("api.service.get_default_api_key_override", lambda: "")

    try:
        _build_client()
    except ValueError as exc:
        assert "Missing API key for provider 'eea'" in str(exc)
        assert ".env.eea.keys" in str(exc)
    else:
        raise AssertionError("Expected ValueError for missing provider API key.")


def test_start_run_creates_timestamped_subfolder(monkeypatch, tmp_path):
    class _StubClient:
        model = "stub-model"

    captured: dict[str, object] = {}

    def _fake_run_batch(input_dir, output_dir, client, max_items, verbose, overwrite, dry_run):
        captured["input_dir"] = input_dir
        captured["output_dir"] = output_dir
        return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

    monkeypatch.setattr("api.service._build_client", lambda: (_StubClient(), "mock"))
    monkeypatch.setattr("api.service.run_batch", _fake_run_batch)
    pages_dir = tmp_path / "pages"
    output_root_dir = tmp_path / "analysis"
    pages_dir.mkdir(parents=True)
    output_root_dir.mkdir(parents=True)
    monkeypatch.setattr("api.service.get_default_input_dir", lambda: str(pages_dir))
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(output_root_dir))

    response = start_run(
        AnalysisRunRequest()
    )

    assert response.warnings == []
    actual_output_dir = Path(response.output_dir)
    assert actual_output_dir.parent == (tmp_path / "analysis")
    assert re.match(r"^\d{8}_\d{6}$", actual_output_dir.name)
    assert response.run_id == actual_output_dir.name
    assert captured["output_dir"] == actual_output_dir


def test_build_run_download_archive_creates_zip(tmp_path):
    run_id = "20260227_133000"
    output_root = tmp_path / "analysis"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "file.json").write_text('{"a": 1}', encoding="utf-8")

    archive_path, temp_dir = build_run_download_archive(run_id=run_id, output_root=str(output_root))

    assert archive_path.exists()
    assert archive_path.name == f"{run_id}.zip"
    with zipfile.ZipFile(archive_path) as zip_file:
        assert "file.json" in zip_file.namelist()


def test_build_run_download_archive_rejects_invalid_run_id(tmp_path):
    output_root = tmp_path / "analysis"
    output_root.mkdir()

    try:
        build_run_download_archive(run_id="bad/id", output_root=str(output_root))
    except ValueError as exc:
        assert "Invalid run id" in str(exc)
    else:
        raise AssertionError("Expected ValueError for invalid run id")


def test_build_excel_export_workbook_for_run_id(monkeypatch, tmp_path):
    run_id = "20260227_133000"
    output_root = tmp_path / "analysis"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "file.json").write_text(
        '{"url":"https://example.com","title":"Example","answers":{"Q1":"A1"}}',
        encoding="utf-8",
    )

    export_root = tmp_path / "exports"
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(output_root))
    monkeypatch.setattr("api.service.get_default_export_dir", lambda: str(export_root))
    workbook_path = build_excel_export_workbook(run_id=run_id)

    assert workbook_path.exists()
    assert workbook_path.name == f"analysis_{run_id}.xlsx"
    assert workbook_path.parent.name == run_id


def test_start_run_uses_configured_default_dirs(monkeypatch, tmp_path):
    class _StubClient:
        model = "stub-model"

    captured: dict[str, object] = {}
    default_input = tmp_path / "default_pages"
    default_output = tmp_path / "default_analysis"
    default_input.mkdir(parents=True)
    default_output.mkdir(parents=True)

    def _fake_run_batch(input_dir, output_dir, client, max_items, verbose, overwrite, dry_run):
        captured["input_dir"] = input_dir
        captured["output_dir"] = output_dir
        return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

    monkeypatch.setattr("api.service._build_client", lambda: (_StubClient(), "mock"))
    monkeypatch.setattr("api.service.run_batch", _fake_run_batch)
    monkeypatch.setattr("api.service.get_default_input_dir", lambda: str(default_input))
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(default_output))

    response = start_run(
        AnalysisRunRequest()
    )

    actual_output_dir = Path(response.output_dir)
    assert actual_output_dir.parent == default_output
    assert captured["input_dir"] == default_input
    assert captured["output_dir"] == actual_output_dir


def test_start_run_fails_when_configured_dirs_missing(monkeypatch, tmp_path):
    class _StubClient:
        model = "stub-model"

    missing_input = tmp_path / "missing_pages"
    missing_output = tmp_path / "missing_analysis"

    monkeypatch.setattr("api.service._build_client", lambda: (_StubClient(), "mock"))
    monkeypatch.setattr("api.service.get_default_input_dir", lambda: str(missing_input))
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(missing_output))

    try:
        start_run(AnalysisRunRequest())
    except FileNotFoundError as exc:
        message = str(exc)
        assert "Input directory not found" in message or "Output directory not found" in message
    else:
        raise AssertionError("Expected FileNotFoundError when configured directories are missing.")
