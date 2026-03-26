from pathlib import Path
import shutil
from uuid import uuid4

import pytest

from api.service import UseCaseConfig
from analysis.analyzer import BatchRunStats
from scripts import run_analysis


TEST_ROOT = Path(__file__).resolve().parents[1] / ".test_tmp_run_analysis"


def _make_scratch_dir() -> Path:
    path = TEST_ROOT / uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    return path


def _cleanup_scratch_dir(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


def test_main_uses_page_use_case_and_absolute_input_override(monkeypatch, capsys):
    temp_path = _make_scratch_dir()
    try:
        captured: dict[str, object] = {}
        source_dir = temp_path / "use_case_pages"
        source_dir.mkdir()
        output_dir = temp_path / "analysis"
        output_dir.mkdir()

        def _fake_get_client(**kwargs):
            captured["client_kwargs"] = kwargs
            return object()

        def _fake_run_batch(**kwargs):
            captured["run_batch_kwargs"] = kwargs
            return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

        monkeypatch.setattr(
            "scripts.run_analysis._resolve_use_case",
            lambda name: UseCaseConfig(
                name=name,
                source_type="pages",
                source_path=temp_path / "configured_pages",
                system_prompt_path=temp_path / "configured_system_prompt.txt",
                user_prompt_path=temp_path / "configured_user_prompt.txt",
            ),
        )
        monkeypatch.setattr("scripts.run_analysis._load_system_prompt_override", lambda config: "system prompt")
        monkeypatch.setattr("scripts.run_analysis._load_user_prompt_override", lambda config: "user prompt")
        monkeypatch.setattr("scripts.run_analysis.load_env_file", lambda path: {})
        monkeypatch.setattr("scripts.run_analysis.get_client", _fake_get_client)
        monkeypatch.setattr("scripts.run_analysis.run_batch", _fake_run_batch)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_analysis.py",
                "--use-case",
                "adaptation_stories",
                "--input",
                str(source_dir),
                "--output",
                str(output_dir),
            ],
        )

        assert run_analysis.main() == 0
        assert captured["client_kwargs"]["system_prompt_template"] == "system prompt"
        assert captured["run_batch_kwargs"]["input_dir"] == source_dir
        actual_output_dir = captured["run_batch_kwargs"]["output_dir"]
        assert actual_output_dir.parent == output_dir
        assert actual_output_dir.name != output_dir.name
        assert captured["run_batch_kwargs"]["use_case"] == "adaptation_stories"
        assert captured["run_batch_kwargs"]["source_type"] == "pages"
        assert captured["run_batch_kwargs"]["source_path"] == str(source_dir)
        assert f"run_id: {actual_output_dir.name}" in capsys.readouterr().out
    finally:
        _cleanup_scratch_dir(temp_path)


def test_main_routes_excel_use_case_and_cli_overrides(monkeypatch):
    temp_path = _make_scratch_dir()
    try:
        captured: dict[str, object] = {}
        output_dir = temp_path / "analysis"
        output_dir.mkdir()
        input_file = temp_path / "override.xlsx"
        input_file.write_bytes(b"")
        prompt_file = temp_path / "override_prompt.txt"
        user_prompt_file = temp_path / "override_user_prompt.txt"
        prompt_file.write_text("override prompt", encoding="utf-8")
        user_prompt_file.write_text(
            "I would like you to analyse the following 2 questions.\n\n{TEXT_TO_ANALYSE}",
            encoding="utf-8",
        )

        def _fake_get_client(**kwargs):
            captured["client_kwargs"] = kwargs
            return object()

        def _fake_run_excel_batch(**kwargs):
            captured["run_excel_kwargs"] = kwargs
            return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

        monkeypatch.setattr(
            "scripts.run_analysis._resolve_use_case",
            lambda name: UseCaseConfig(
                name=name,
                source_type="excel",
                source_path=temp_path / "configured.xlsx",
                system_prompt_path=temp_path / "configured_system_prompt.txt",
                user_prompt_path=temp_path / "configured_user_prompt.txt",
                sheet_name="ConfiguredSheet",
                column_name="ConfiguredColumn",
                header_row=1,
            ),
        )
        monkeypatch.setattr(
            "scripts.run_analysis._load_system_prompt_override",
            lambda config: config.system_prompt_path.read_text(encoding="utf-8"),
        )
        monkeypatch.setattr("scripts.run_analysis.load_env_file", lambda path: {})
        monkeypatch.setattr("scripts.run_analysis.get_client", _fake_get_client)
        monkeypatch.setattr("scripts.run_analysis.run_excel_batch", _fake_run_excel_batch)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_analysis.py",
                "--use-case",
                "question_2_1_1_column_7",
                "--input",
                str(input_file),
                "--system-prompt-file",
                str(prompt_file),
                "--user-prompt-file",
                str(user_prompt_file),
                "--sheet-name",
                "OverrideSheet",
                "--column-name",
                "OverrideColumn",
                "--header-row",
                "3",
                "--output",
                str(output_dir),
            ],
        )

        assert run_analysis.main() == 0
        assert captured["client_kwargs"]["system_prompt_template"] == "override prompt"
        assert captured["client_kwargs"]["user_prompt_template"] == (
            "I would like you to analyse the following 2 questions.\n\n{TEXT_TO_ANALYSE}"
        )
        actual_output_dir = captured["run_excel_kwargs"]["output_dir"]
        assert actual_output_dir.parent == output_dir
        assert actual_output_dir.name != output_dir.name
        assert captured["run_excel_kwargs"]["input_file"] == input_file
        assert captured["run_excel_kwargs"]["sheet_name"] == "OverrideSheet"
        assert captured["run_excel_kwargs"]["column_name"] == "OverrideColumn"
        assert captured["run_excel_kwargs"]["header_row"] == 3
        assert captured["run_excel_kwargs"]["source_path"] == str(input_file)
    finally:
        _cleanup_scratch_dir(temp_path)


def test_main_rejects_relative_input_path(monkeypatch):
    temp_path = _make_scratch_dir()
    try:
        output_dir = temp_path / "analysis"
        output_dir.mkdir()
        monkeypatch.setattr("scripts.run_analysis.load_env_file", lambda path: {})
        monkeypatch.setattr("scripts.run_analysis.get_client", lambda **kwargs: object())
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_analysis.py",
                "--input",
                "data/pages",
                "--output",
                str(output_dir),
            ],
        )

        with pytest.raises(ValueError, match="--input must be an absolute path"):
            run_analysis.main()
    finally:
        _cleanup_scratch_dir(temp_path)


def test_main_accepts_absolute_input_path_without_use_case(monkeypatch):
    temp_path = _make_scratch_dir()
    try:
        captured: dict[str, object] = {}
        input_dir = temp_path / "pages"
        input_dir.mkdir()
        output_dir = temp_path / "analysis"
        output_dir.mkdir()
        user_prompt_file = temp_path / "user_prompt.txt"
        user_prompt_file.write_text(
            "I would like you to analyse the following 3 questions.\n\n{TEXT_TO_ANALYSE}",
            encoding="utf-8",
        )

        def _fake_get_client(**kwargs):
            captured["client_kwargs"] = kwargs
            return object()

        def _fake_run_batch(**kwargs):
            captured["run_batch_kwargs"] = kwargs
            return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

        monkeypatch.setattr("scripts.run_analysis.load_env_file", lambda path: {})
        monkeypatch.setattr("scripts.run_analysis.get_client", _fake_get_client)
        monkeypatch.setattr("scripts.run_analysis.run_batch", _fake_run_batch)
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_analysis.py",
                "--input",
                str(input_dir),
                "--user-prompt-file",
                str(user_prompt_file),
                "--output",
                str(output_dir),
            ],
        )

        assert run_analysis.main() == 0
        assert captured["client_kwargs"]["user_prompt_template"] == (
            "I would like you to analyse the following 3 questions.\n\n{TEXT_TO_ANALYSE}"
        )
        assert captured["run_batch_kwargs"]["input_dir"] == input_dir
        assert captured["run_batch_kwargs"]["source_path"] == str(input_dir)
    finally:
        _cleanup_scratch_dir(temp_path)


def test_main_uses_provider_and_output_defaults_from_dotenv(monkeypatch):
    temp_path = _make_scratch_dir()
    try:
        captured: dict[str, object] = {}
        configured_output = temp_path / "configured-analysis"

        def _fake_load_env_file(path: Path) -> dict[str, str]:
            if path.name == ".env":
                return {
                    "PROVIDER": "mock",
                    "OUTPUT_DIR": str(configured_output),
                }
            if path.name == ".env.mock":
                return {"MODEL": "mock-model", "API_URL": ""}
            if path.name == ".env.mock.keys":
                return {}
            return {}

        def _fake_get_client(**kwargs):
            captured["client_kwargs"] = kwargs
            return object()

        def _fake_run_batch(**kwargs):
            captured["run_batch_kwargs"] = kwargs
            return BatchRunStats(processed=0, skipped=0, total_elapsed_seconds=0.0, items=[])

        monkeypatch.setattr("scripts.run_analysis.load_env_file", _fake_load_env_file)
        monkeypatch.setattr("scripts.run_analysis.get_client", _fake_get_client)
        monkeypatch.setattr("scripts.run_analysis.run_batch", _fake_run_batch)
        monkeypatch.setattr("sys.argv", ["run_analysis.py"])

        assert run_analysis.main() == 0
        assert captured["client_kwargs"]["provider"] == "mock"
        assert captured["run_batch_kwargs"]["output_dir"] == configured_output
    finally:
        _cleanup_scratch_dir(temp_path)


def test_main_raises_for_unknown_use_case(monkeypatch, capsys):
    temp_path = _make_scratch_dir()
    try:
        output_dir = temp_path / "analysis"
        output_dir.mkdir()
        monkeypatch.setattr("scripts.run_analysis.load_env_file", lambda path: {})
        monkeypatch.setattr(
            "scripts.run_analysis._resolve_use_case",
            lambda name: (_ for _ in ()).throw(ValueError("Unknown use_case: bad_case")),
        )
        monkeypatch.setattr(
            "sys.argv",
            [
                "run_analysis.py",
                "--use-case",
                "bad_case",
                "--output",
                str(output_dir),
            ],
        )

        result = run_analysis.main()
        assert result == 1
        assert "Unknown use_case: bad_case" in capsys.readouterr().err
    finally:
        _cleanup_scratch_dir(temp_path)
