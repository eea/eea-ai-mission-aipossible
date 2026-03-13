import zipfile

from fastapi.testclient import TestClient

from api.app import app


client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert "analysis_output_dir" in payload


def test_run_endpoint_uses_service(monkeypatch):
    def _fake_start_run(_request):
        return {
            "processed": 1,
            "skipped": 0,
            "total_elapsed_seconds": 1.5,
            "total_elapsed_minutes": 0.025,
            "provider": "eea",
            "model": "stub",
            "run_id": "20260227_120000",
            "output_dir": "data/analysis",
            "items": [
                {
                    "page_file": "data/pages/page.json",
                    "output_file": "data/analysis/result.json",
                    "url": "https://example.com/story",
                    "saved": True,
                    "elapsed_seconds": 1.5,
                }
            ],
        }

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post("/v1/analysis/runs", json={"use_case": "adaptation_stories", "max_items": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["processed"] == 1
    assert payload["items"][0]["saved"] is True
    assert payload["provider"] == "eea"
    assert payload["run_id"] == "20260227_120000"


def test_run_endpoint_accepts_mock_provider(monkeypatch):
    def _fake_start_run(_request):
        return {
            "processed": 0,
            "skipped": 0,
            "total_elapsed_seconds": 0.0,
            "total_elapsed_minutes": 0.0,
            "provider": "mock",
            "model": "mock-model",
            "run_id": "20260227_120000",
            "output_dir": "data/analysis",
            "items": [],
        }

    monkeypatch.setattr("api.app.start_run", _fake_start_run)
    response = client.post("/v1/analysis/runs", json={"use_case": "adaptation_stories", "max_items": 1})

    assert response.status_code == 200
    payload = response.json()
    assert payload["provider"] == "mock"


def test_run_endpoint_accepts_user_prompt_override(monkeypatch):
    captured = {}

    def _fake_start_run(request):
        captured["user_prompt"] = request.user_prompt
        captured["use_case"] = request.use_case
        return {
            "processed": 0,
            "skipped": 0,
            "total_elapsed_seconds": 0.0,
            "total_elapsed_minutes": 0.0,
            "provider": "mock",
            "model": "mock-model",
            "run_id": "20260227_120000",
            "output_dir": "data/analysis",
            "items": [],
        }

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs",
        json={
            "use_case": "adaptation_stories",
            "max_items": 1,
            "user_prompt": "I would like you to analyse the following 3 questions.",
        },
    )

    assert response.status_code == 200
    assert captured["user_prompt"] == "I would like you to analyse the following 3 questions."
    assert captured["use_case"] == "adaptation_stories"


def test_run_endpoint_requires_use_case():
    response = client.post("/v1/analysis/runs", json={"max_items": 1})
    assert response.status_code == 422


def test_run_endpoint_invalid_use_case_maps_to_400(monkeypatch):
    def _fake_start_run(_request):
        raise ValueError("Unknown use_case: bad_case")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post("/v1/analysis/runs", json={"use_case": "bad_case", "max_items": 1})
    assert response.status_code == 400
    assert "Unknown use_case" in response.json()["detail"]


def test_run_endpoint_rejects_unknown_provider():
    response = client.post("/v1/analysis/runs", json={"provider": "invalid-provider", "use_case": "adaptation_stories", "max_items": 1})
    assert response.status_code == 422


def test_run_endpoint_rejects_removed_parameters():
    response = client.post(
        "/v1/analysis/runs",
        json={
            "provider": "mock",
            "model": "gpt-4o",
            "api_key": "secret",
            "quiet": True,
            "file": "data/pages/a.json",
            "use_case": "adaptation_stories",
        },
    )
    assert response.status_code == 422


def test_run_endpoint_returns_404_when_configured_dirs_missing(monkeypatch):
    def _fake_start_run(_request):
        raise FileNotFoundError("Input directory not found: C:/missing/pages")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)
    response = client.post("/v1/analysis/runs", json={"use_case": "adaptation_stories", "max_items": 1})

    assert response.status_code == 404
    assert "Input directory not found" in response.json()["detail"]


def test_run_endpoint_returns_400_when_provider_key_missing(monkeypatch):
    def _fake_start_run(_request):
        raise ValueError("Missing API key for provider 'eea'. Set API_API_KEY in .env.api.")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)
    response = client.post("/v1/analysis/runs", json={"use_case": "adaptation_stories", "max_items": 1})

    assert response.status_code == 400
    assert "Missing API key for provider 'eea'" in response.json()["detail"]


def test_run_endpoint_returns_500_for_use_case_configuration_error(monkeypatch):
    from api.service import UseCaseConfigurationError

    def _fake_start_run(_request):
        raise UseCaseConfigurationError("Use-case config file not found")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)
    response = client.post("/v1/analysis/runs", json={"use_case": "adaptation_stories", "max_items": 1})

    assert response.status_code == 500
    assert "Use-case config file not found" in response.json()["detail"]


def test_run_endpoint_maps_provider_request_error(monkeypatch):
    from api.service import ProviderRequestError

    def _fake_start_run(_request):
        raise ProviderRequestError("Provider 'eea' rejected the request with status 403.")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)
    response = client.post("/v1/analysis/runs", json={"use_case": "adaptation_stories", "max_items": 1})

    assert response.status_code == 502
    assert "Provider 'eea' rejected the request with status 403." in response.json()["detail"]


def test_upload_prompt_endpoint_uses_service(monkeypatch):
    captured = {}

    def _fake_start_run(request):
        captured["user_prompt"] = request.user_prompt
        captured["max_items"] = request.max_items
        captured["use_case"] = request.use_case
        return {
            "processed": 0,
            "skipped": 0,
            "total_elapsed_seconds": 0.0,
            "total_elapsed_minutes": 0.0,
            "provider": "mock",
            "model": "mock-model",
            "run_id": "20260227_120000",
            "output_dir": "data/analysis",
            "items": [],
        }

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"I would like you to analyse the following 3 questions.", "text/plain")},
        data={"use_case": "adaptation_stories", "max_items": "2"},
    )

    assert response.status_code == 200
    assert captured["user_prompt"] == "I would like you to analyse the following 3 questions."
    assert captured["max_items"] == 2
    assert captured["use_case"] == "adaptation_stories"


def test_upload_prompt_endpoint_rejects_non_txt_file(monkeypatch):
    def _fake_start_run(_request):
        raise AssertionError("start_run should not be called")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.md", b"test", "text/markdown")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Only .txt prompt files are supported"


def test_upload_prompt_endpoint_requires_prompt_file():
    response = client.post("/v1/analysis/runs/upload-prompt", data={"use_case": "adaptation_stories", "max_items": "1"})
    assert response.status_code == 422


def test_upload_prompt_endpoint_requires_use_case():
    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"I would like you to analyse the following 3 questions.", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_prompt_endpoint_rejects_invalid_utf8(monkeypatch):
    def _fake_start_run(_request):
        raise AssertionError("start_run should not be called")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"\xff\xfe\xfa", "text/plain")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Prompt file must be UTF-8 text"


def test_upload_prompt_endpoint_rejects_empty_prompt(monkeypatch):
    def _fake_start_run(_request):
        raise AssertionError("start_run should not be called")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"   \n\t ", "text/plain")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "Prompt file is empty"


def test_upload_prompt_endpoint_maps_file_not_found(monkeypatch):
    def _fake_start_run(_request):
        raise FileNotFoundError("Input directory not found: C:/missing/pages")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"I would like you to analyse the following 3 questions.", "text/plain")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 404
    assert "Input directory not found" in response.json()["detail"]


def test_upload_prompt_endpoint_maps_value_error(monkeypatch):
    def _fake_start_run(_request):
        raise ValueError("Could not determine question count from user prompt.")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"I would like you to analyse the following 3 questions.", "text/plain")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 400
    assert "Could not determine question count" in response.json()["detail"]


def test_upload_prompt_endpoint_maps_use_case_configuration_error(monkeypatch):
    from api.service import UseCaseConfigurationError

    def _fake_start_run(_request):
        raise UseCaseConfigurationError("Use-case config file not found")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"I would like you to analyse the following 3 questions.", "text/plain")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 500
    assert "Use-case config file not found" in response.json()["detail"]


def test_upload_prompt_endpoint_maps_provider_request_error(monkeypatch):
    from api.service import ProviderRequestError

    def _fake_start_run(_request):
        raise ProviderRequestError("Provider 'eea' rejected the request with status 403.")

    monkeypatch.setattr("api.app.start_run", _fake_start_run)

    response = client.post(
        "/v1/analysis/runs/upload-prompt",
        files={"prompt_file": ("prompt.txt", b"I would like you to analyse the following 3 questions.", "text/plain")},
        data={"use_case": "adaptation_stories"},
    )

    assert response.status_code == 502
    assert "Provider 'eea' rejected the request with status 403." in response.json()["detail"]


def test_download_run_archive_endpoint(tmp_path, monkeypatch):
    run_id = "20260227_123456"
    run_dir = tmp_path / run_id
    run_dir.mkdir()
    (run_dir / "result.json").write_text('{"ok": true}', encoding="utf-8")

    def _fake_build_run_download_archive(run_id: str):
        archive = tmp_path / f"{run_id}.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(run_dir / "result.json", arcname="result.json")
        return archive, tmp_path

    monkeypatch.setattr("api.app.build_run_download_archive", _fake_build_run_download_archive)

    response = client.get(f"/v1/analysis/runs/{run_id}/download")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert f'filename="{run_id}.zip"' in response.headers["content-disposition"]


def test_download_run_archive_endpoint_invalid_run_id(monkeypatch):
    def _fake_build_run_download_archive(run_id: str):
        raise ValueError("Invalid run id")

    monkeypatch.setattr("api.app.build_run_download_archive", _fake_build_run_download_archive)

    response = client.get("/v1/analysis/runs/bad!id/download")
    assert response.status_code == 400


def test_download_excel_export_endpoint(tmp_path, monkeypatch):
    workbook = tmp_path / "analysis.xlsx"
    workbook.write_bytes(b"dummy")

    def _fake_build_excel_export_workbook(run_id: str):
        return workbook

    monkeypatch.setattr("api.app.build_excel_export_workbook", _fake_build_excel_export_workbook)

    response = client.get("/v1/analysis/export/excel", params={"run_id": "20260227_123456"})
    assert response.status_code == 200
    assert response.headers["content-type"].startswith(
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
    assert 'filename="analysis.xlsx"' in response.headers["content-disposition"]


def test_download_excel_export_endpoint_invalid_run_id(monkeypatch):
    def _fake_build_excel_export_workbook(run_id: str):
        raise ValueError("Invalid run id")

    monkeypatch.setattr("api.app.build_excel_export_workbook", _fake_build_excel_export_workbook)

    response = client.get("/v1/analysis/export/excel", params={"run_id": "bad!id"})
    assert response.status_code == 400


def test_download_excel_export_endpoint_requires_run_id():
    response = client.get("/v1/analysis/export/excel")
    assert response.status_code == 422
