import re
import zipfile
from pathlib import Path

from analysis.analyzer import BatchRunStats
from api.models import AnalysisRunRequest
from api.service import (
    REPO_ROOT,
    UseCaseConfig,
    UseCaseConfigurationError,
    _build_client,
    _resolve_use_case,
    build_excel_export_workbook,
    build_run_download_archive,
    get_default_export_dir,
    get_default_output_dir,
    get_default_provider,
    start_run,
)


def test_analysis_run_request_defaults_timestamped_output_dir_true():
    request = AnalysisRunRequest(use_case="adaptation_stories")
    assert request.use_case == "adaptation_stories"
    assert request.max_items is None
    assert request.user_prompt is None


def test_resolve_use_case_for_pages(monkeypatch):
    monkeypatch.setattr(
        "api.service._load_use_case_presets",
        lambda: {
            "adaptation_stories": {
                "source_type": "pages",
                "source_path": "data/pages",
                "system_prompt_path": "analysis/prompts/system_prompt.txt",
                "user_prompt_path": "analysis/prompts/user_prompt.txt",
            }
        },
    )

    config = _resolve_use_case("adaptation_stories")
    assert config.source_type == "pages"
    assert config.name == "adaptation_stories"
    assert config.source_path == (REPO_ROOT / "data/pages").resolve()
    assert config.system_prompt_path == (REPO_ROOT / "analysis/prompts/system_prompt.txt").resolve()
    assert config.user_prompt_path == (REPO_ROOT / "analysis/prompts/user_prompt.txt").resolve()


def test_resolve_use_case_for_excel(monkeypatch):
    monkeypatch.setattr(
        "api.service._load_use_case_presets",
        lambda: {
            "question_2_1_1_column_7": {
                "source_type": "excel",
                "source_path": "data/data_sources/2_1_1.xlsx",
                "system_prompt_path": "analysis/prompts/system_prompt.txt",
                "user_prompt_path": "analysis/prompts/user_prompt.txt",
                "sheet_name": "Sheet1",
                "column_name": "col7_Please explain",
                "header_row": 2,
            }
        },
    )

    config = _resolve_use_case("question_2_1_1_column_7")
    assert config.source_type == "excel"
    assert config.sheet_name == "Sheet1"
    assert config.column_name == "col7_Please explain"
    assert config.header_row == 2


def test_resolve_use_case_raises_for_unknown(monkeypatch):
    monkeypatch.setattr("api.service._load_use_case_presets", lambda: {})
    try:
        _resolve_use_case("missing_use_case")
    except ValueError as exc:
        assert "Unknown use_case" in str(exc)
    else:
        raise AssertionError("Expected ValueError for unknown use_case")


def test_resolve_use_case_raises_for_invalid_excel_config(monkeypatch):
    monkeypatch.setattr(
        "api.service._load_use_case_presets",
        lambda: {
            "question_2_1_1_column_7": {
                "source_type": "excel",
                "source_path": "data/data_sources/2_1_1.xlsx",
            }
        },
    )
    try:
        _resolve_use_case("question_2_1_1_column_7")
    except UseCaseConfigurationError as exc:
        assert "system_prompt_path" in str(exc)
    else:
        raise AssertionError("Expected UseCaseConfigurationError for invalid excel preset")


def test_api_defaults_prefer_short_env_keys(monkeypatch):
    values = {
        "OUTPUT_DIR": "short-output",
        "EXPORT_DIR": "short-export",
        "PROVIDER": "openai",
    }

    monkeypatch.setattr(
        "api.service.get_str_setting",
        lambda key, default="", aliases=(): values.get(key, default),
    )

    assert get_default_output_dir() == "short-output"
    assert get_default_export_dir() == "short-export"
    assert get_default_provider() == "openai"


def test_api_defaults_fall_back_to_legacy_api_keys(monkeypatch):
    values = {
        "API_OUTPUT_DIR": "legacy-output",
        "API_EXPORT_DIR": "legacy-export",
        "API_PROVIDER": "mock",
    }

    def _fake_get_str_setting(key: str, default: str = "", aliases: tuple[str, ...] = ()) -> str:
        for candidate in (key, *aliases):
            if candidate in values:
                return values[candidate]
        return default

    monkeypatch.setattr("api.service.get_str_setting", _fake_get_str_setting)

    assert get_default_output_dir() == "legacy-output"
    assert get_default_export_dir() == "legacy-export"
    assert get_default_provider() == "mock"


def test_build_client_uses_provider_default_prompts_dir(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_load_env_file(path: Path) -> dict[str, str]:
        if path.name == ".env.eea":
            return {
                "MODEL": "env-model",
                "API_URL": "https://api.example.com",
            }
        if path.name == ".env.eea.keys":
            return {"API_KEY": "env-key"}
        return {}

    def _fake_get_client(
        provider: str,
        api_key: str,
        model: str,
        api_url: str,
        prompts_dir: Path,
        user_prompt_template: str | None = None,
        system_prompt_template: str | None = None,
    ):
        captured["provider"] = provider
        captured["api_key"] = api_key
        captured["model"] = model
        captured["api_url"] = api_url
        captured["prompts_dir"] = prompts_dir
        captured["user_prompt_template"] = user_prompt_template
        captured["system_prompt_template"] = system_prompt_template
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
    assert captured["user_prompt_template"] is None
    assert captured["system_prompt_template"] is None


def test_build_client_passes_user_prompt_override(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_load_env_file(path: Path) -> dict[str, str]:
        if path.name == ".env.mock":
            return {"MODEL": "mock-model", "API_URL": ""}
        if path.name == ".env.mock.keys":
            return {}
        return {}

    def _fake_get_client(
        provider: str,
        api_key: str,
        model: str,
        api_url: str,
        prompts_dir: Path,
        user_prompt_template: str | None = None,
        system_prompt_template: str | None = None,
    ):
        captured["provider"] = provider
        captured["user_prompt_template"] = user_prompt_template
        captured["system_prompt_template"] = system_prompt_template
        return object()

    monkeypatch.setattr("api.service.load_env_file", _fake_load_env_file)
    monkeypatch.setattr("api.service.get_client", _fake_get_client)
    monkeypatch.setattr("api.service.get_default_provider", lambda: "mock")
    monkeypatch.setattr("api.service.get_default_model_override", lambda: "")
    monkeypatch.setattr("api.service.get_default_api_key_override", lambda: "")

    _build_client(user_prompt_override="  I would like you to analyse the following 3 questions.  ")

    assert captured["provider"] == "mock"
    assert captured["user_prompt_template"] == "I would like you to analyse the following 3 questions."
    assert captured["system_prompt_template"] is None


def test_build_client_passes_system_prompt_override(monkeypatch):
    captured: dict[str, object] = {}

    def _fake_load_env_file(path: Path) -> dict[str, str]:
        if path.name == ".env.mock":
            return {"MODEL": "mock-model", "API_URL": ""}
        if path.name == ".env.mock.keys":
            return {}
        return {}

    def _fake_get_client(
        provider: str,
        api_key: str,
        model: str,
        api_url: str,
        prompts_dir: Path,
        user_prompt_template: str | None = None,
        system_prompt_template: str | None = None,
    ):
        captured["provider"] = provider
        captured["system_prompt_template"] = system_prompt_template
        return object()

    monkeypatch.setattr("api.service.load_env_file", _fake_load_env_file)
    monkeypatch.setattr("api.service.get_client", _fake_get_client)
    monkeypatch.setattr("api.service.get_default_provider", lambda: "mock")
    monkeypatch.setattr("api.service.get_default_model_override", lambda: "")
    monkeypatch.setattr("api.service.get_default_api_key_override", lambda: "")

    _build_client(system_prompt_override="  You are a strict extractor.  ")
    assert captured["provider"] == "mock"
    assert captured["system_prompt_template"] == "You are a strict extractor."


def test_build_client_raises_when_api_key_missing(monkeypatch):
    def _fake_load_env_file(path: Path) -> dict[str, str]:
        if path.name == ".env.eea":
            return {"MODEL": "env-model", "API_URL": "https://api.example.com"}
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

    def _fake_run_batch(input_dir, output_dir, client, max_items, verbose, overwrite, dry_run, **kwargs):
        captured["input_dir"] = input_dir
        captured["output_dir"] = output_dir
        return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

    monkeypatch.setattr(
        "api.service._build_client",
        lambda user_prompt_override=None, system_prompt_override=None: (_StubClient(), "mock"),
    )
    monkeypatch.setattr("api.service.run_pages_batch", _fake_run_batch)
    pages_dir = tmp_path / "pages"
    output_root_dir = tmp_path / "analysis"
    pages_dir.mkdir(parents=True)
    output_root_dir.mkdir(parents=True)
    monkeypatch.setattr(
        "api.service._resolve_use_case",
        lambda use_case: UseCaseConfig(
            name=use_case,
            source_type="pages",
            source_path=pages_dir,
            system_prompt_path=REPO_ROOT / "analysis/prompts/system_prompt.txt",
            user_prompt_path=REPO_ROOT / "analysis/prompts/user_prompt.txt",
        ),
    )
    monkeypatch.setattr("api.service._load_system_prompt_override", lambda config: "system prompt")
    monkeypatch.setattr("api.service._load_user_prompt_override", lambda config: "user prompt")
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(output_root_dir))

    response = start_run(AnalysisRunRequest(use_case="adaptation_stories"))

    assert response.warnings == []
    actual_output_dir = Path(response.output_dir)
    assert actual_output_dir.parent == (tmp_path / "analysis")
    assert re.match(r"^\d{8}_\d{6}$", actual_output_dir.name)
    assert response.run_id == actual_output_dir.name
    assert captured["output_dir"] == actual_output_dir


def test_start_run_passes_user_prompt_override_to_build_client(monkeypatch, tmp_path):
    class _StubClient:
        model = "stub-model"

    captured: dict[str, object] = {}

    def _fake_build_client(user_prompt_override=None, system_prompt_override=None):
        captured["user_prompt_override"] = user_prompt_override
        captured["system_prompt_override"] = system_prompt_override
        return _StubClient(), "mock"

    def _fake_run_batch(input_dir, output_dir, client, max_items, verbose, overwrite, dry_run, **kwargs):
        return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

    pages_dir = tmp_path / "pages"
    output_root_dir = tmp_path / "analysis"
    pages_dir.mkdir(parents=True)
    output_root_dir.mkdir(parents=True)

    monkeypatch.setattr("api.service._build_client", _fake_build_client)
    monkeypatch.setattr("api.service.run_pages_batch", _fake_run_batch)
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(output_root_dir))
    monkeypatch.setattr(
        "api.service._resolve_use_case",
        lambda use_case: UseCaseConfig(
            name=use_case,
            source_type="pages",
            source_path=pages_dir,
            system_prompt_path=REPO_ROOT / "analysis/prompts/system_prompt.txt",
            user_prompt_path=REPO_ROOT / "analysis/prompts/user_prompt.txt",
        ),
    )
    monkeypatch.setattr("api.service._load_system_prompt_override", lambda config: "system prompt")
    monkeypatch.setattr("api.service._load_user_prompt_override", lambda config: "user prompt")

    start_run(
        AnalysisRunRequest(
            use_case="adaptation_stories", user_prompt="I would like you to analyse the following 2 questions."
        )
    )

    assert captured["user_prompt_override"] == "I would like you to analyse the following 2 questions."


def test_build_run_download_archive_creates_zip(tmp_path):
    run_id = "20260227_133000"
    output_root = tmp_path / "analysis"
    run_dir = output_root / run_id
    run_dir.mkdir(parents=True)
    (run_dir / "file.json").write_text('{"a": 1}', encoding="utf-8")

    archive_path, _temp_dir = build_run_download_archive(run_id=run_id, output_root=str(output_root))

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

    def _fake_run_batch(input_dir, output_dir, client, max_items, verbose, overwrite, dry_run, **kwargs):
        captured["input_dir"] = input_dir
        captured["output_dir"] = output_dir
        return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

    monkeypatch.setattr(
        "api.service._build_client",
        lambda user_prompt_override=None, system_prompt_override=None: (_StubClient(), "mock"),
    )
    monkeypatch.setattr("api.service.run_pages_batch", _fake_run_batch)
    monkeypatch.setattr(
        "api.service._resolve_use_case",
        lambda use_case: UseCaseConfig(
            name=use_case,
            source_type="pages",
            source_path=default_input,
            system_prompt_path=REPO_ROOT / "analysis/prompts/system_prompt.txt",
            user_prompt_path=REPO_ROOT / "analysis/prompts/user_prompt.txt",
        ),
    )
    monkeypatch.setattr("api.service._load_system_prompt_override", lambda config: "system prompt")
    monkeypatch.setattr("api.service._load_user_prompt_override", lambda config: "user prompt")
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(default_output))

    response = start_run(AnalysisRunRequest(use_case="adaptation_stories"))

    actual_output_dir = Path(response.output_dir)
    assert actual_output_dir.parent == default_output
    assert captured["input_dir"] == default_input
    assert captured["output_dir"] == actual_output_dir


def test_start_run_fails_when_configured_dirs_missing(monkeypatch, tmp_path):
    class _StubClient:
        model = "stub-model"

    missing_input = tmp_path / "missing_pages"
    missing_output = tmp_path / "missing_analysis"

    monkeypatch.setattr(
        "api.service._build_client",
        lambda user_prompt_override=None, system_prompt_override=None: (_StubClient(), "mock"),
    )
    monkeypatch.setattr(
        "api.service._resolve_use_case",
        lambda use_case: UseCaseConfig(
            name=use_case,
            source_type="pages",
            source_path=missing_input,
            system_prompt_path=REPO_ROOT / "analysis/prompts/system_prompt.txt",
            user_prompt_path=REPO_ROOT / "analysis/prompts/user_prompt.txt",
        ),
    )
    monkeypatch.setattr("api.service._load_system_prompt_override", lambda config: "system prompt")
    monkeypatch.setattr("api.service._load_user_prompt_override", lambda config: "user prompt")
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(missing_output))

    try:
        start_run(AnalysisRunRequest(use_case="adaptation_stories"))
    except FileNotFoundError as exc:
        message = str(exc)
        assert "Input directory not found" in message or "Output directory not found" in message
    else:
        raise AssertionError("Expected FileNotFoundError when configured directories are missing.")


def test_start_run_routes_to_excel_use_case(monkeypatch, tmp_path):
    class _StubClient:
        model = "stub-model"

    captured: dict[str, object] = {}
    input_file = tmp_path / "source.xlsx"
    input_file.write_bytes(b"x")
    output_root = tmp_path / "analysis"
    output_root.mkdir(parents=True)

    def _fake_run_excel_batch(**kwargs):
        captured.update(kwargs)
        return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

    monkeypatch.setattr(
        "api.service._build_client",
        lambda user_prompt_override=None, system_prompt_override=None: (_StubClient(), "mock"),
    )
    monkeypatch.setattr(
        "api.service._resolve_use_case",
        lambda use_case: UseCaseConfig(
            name=use_case,
            source_type="excel",
            source_path=input_file,
            system_prompt_path=REPO_ROOT / "analysis/prompts/system_prompt.txt",
            user_prompt_path=REPO_ROOT / "analysis/prompts/user_prompt.txt",
            sheet_name="Sheet1",
            column_name="colA",
            header_row=1,
        ),
    )
    monkeypatch.setattr("api.service._load_system_prompt_override", lambda config: "system prompt")
    monkeypatch.setattr("api.service._load_user_prompt_override", lambda config: "user prompt")
    monkeypatch.setattr("api.service.run_excel_batch", _fake_run_excel_batch)
    monkeypatch.setattr("api.service.get_default_output_dir", lambda: str(output_root))

    start_run(AnalysisRunRequest(use_case="question_2_1_1_column_7"))

    assert captured["input_file"] == input_file
    assert captured["sheet_name"] == "Sheet1"
    assert captured["column_name"] == "colA"
