import os

from scripts import run_analysis_api


def test_main_sets_config_and_dir_overrides(monkeypatch, tmp_path):
    captured: dict[str, object] = {}
    config_file = tmp_path / ".env.api"
    config_file.write_text(
        (
            "OUTPUT_DIR=data/analysis\n"
            "EXPORT_DIR=data/exports\n"
            "PROVIDER=mock\n"
            "API_MODEL=mock-model\n"
        ),
        encoding="utf-8",
    )

    def _fake_run(app, host, port, reload):
        captured["app"] = app
        captured["host"] = host
        captured["port"] = port
        captured["reload"] = reload

    monkeypatch.setattr(run_analysis_api, "_is_port_in_use", lambda host, port: False)
    monkeypatch.setattr("uvicorn.run", _fake_run)
    monkeypatch.setattr(
        "sys.argv",
        [
            "prog",
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
            "--config-file",
            str(config_file),
            "--output-dir",
            "data/analysis_custom",
            "--export-dir",
            "data/exports_custom",
            "--provider",
            "openai",
            "--model",
            "gpt-4o-mini",
            "--api-key",
            "key-123",
        ],
    )

    result = run_analysis_api.main()

    assert result == 0
    assert captured["app"] == "api.app:app"
    assert captured["host"] == "127.0.0.1"
    assert captured["port"] == 8000
    assert captured["reload"] is False
    assert os.environ["MISSION_CONFIG_FILE"] == str(config_file)
    assert os.environ["OUTPUT_DIR"] == "data/analysis_custom"
    assert os.environ["EXPORT_DIR"] == "data/exports_custom"
    assert os.environ["PROVIDER"] == "openai"
    assert os.environ["API_MODEL"] == "gpt-4o-mini"
    assert os.environ["API_API_KEY"] == "key-123"


def test_main_errors_when_default_env_api_missing(monkeypatch):
    monkeypatch.setattr(run_analysis_api, "_is_port_in_use", lambda host, port: False)
    monkeypatch.setattr("sys.argv", ["prog", "--host", "127.0.0.1", "--port", "8000"])

    original_exists = run_analysis_api.Path.exists

    def _fake_exists(path_obj):
        if path_obj.name == ".env.api":
            return False
        return original_exists(path_obj)

    monkeypatch.setattr(run_analysis_api.Path, "exists", _fake_exists)

    try:
        run_analysis_api.main()
    except SystemExit as exc:
        assert "Config file not found" in str(exc)
        assert ".env.api" in str(exc)
    else:
        raise AssertionError("Expected SystemExit when .env.api is missing.")
