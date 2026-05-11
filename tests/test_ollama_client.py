import json
from pathlib import Path

import pytest

from analysis.clients.base import ProviderRequestError
from analysis.clients.ollama_client import OllamaClient


def _write_prompts(tmp_path: Path) -> Path:
    prompts_dir = tmp_path / "prompts"
    prompts_dir.mkdir(parents=True)
    (prompts_dir / "system_prompt.txt").write_text("System prompt", encoding="utf-8")
    (prompts_dir / "user_prompt.txt").write_text(
        "I would like you to analyse the following 2 questions.\n\n{INSERT SCRAPED TEXT HERE}",
        encoding="utf-8",
    )
    return prompts_dir


def test_ollama_client_defaults_api_url(tmp_path: Path) -> None:
    prompts_dir = _write_prompts(tmp_path)

    client = OllamaClient(
        api_key="",
        model="llama3.1",
        api_url="",
        prompts_dir=prompts_dir,
        user_prompt_template="I would like you to analyse the following 2 questions.",
    )

    assert client.api_url == "http://127.0.0.1:11434"
    assert client._resolve_generate_url() == "http://127.0.0.1:11434/api/generate"


def test_ollama_client_analyze_returns_response_payload(monkeypatch, tmp_path: Path) -> None:
    prompts_dir = _write_prompts(tmp_path)
    client = OllamaClient(
        api_key="",
        model="llama3.1",
        api_url="http://localhost:11434",
        prompts_dir=prompts_dir,
        user_prompt_template="I would like you to analyse the following 2 questions.",
    )

    captured: dict[str, object] = {}

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return json.dumps({"response": '{"answers":{"Answer 1":"Yes","Answer 2":"No"}}'}).encode("utf-8")

    def _fake_urlopen(http_request, timeout):
        captured["url"] = http_request.full_url
        captured["timeout"] = timeout
        captured["body"] = json.loads(http_request.data.decode("utf-8"))
        return _Response()

    monkeypatch.setattr("analysis.clients.ollama_client.request.urlopen", _fake_urlopen)

    result = client.analyze("sample text")

    assert captured["url"] == "http://localhost:11434/api/generate"
    assert captured["timeout"] == 120
    assert captured["body"]["model"] == "llama3.1"
    assert captured["body"]["stream"] is False
    assert captured["body"]["options"]["temperature"] == 0.2
    assert result["provider"] == "ollama"
    assert result["result"] == '{"answers":{"Answer 1":"Yes","Answer 2":"No"}}'
    assert result["raw"]["response"] == result["result"]


def test_ollama_client_raises_for_invalid_json_response(monkeypatch, tmp_path: Path) -> None:
    prompts_dir = _write_prompts(tmp_path)
    client = OllamaClient(
        api_key="",
        model="llama3.1",
        api_url="http://localhost:11434",
        prompts_dir=prompts_dir,
        user_prompt_template="I would like you to analyse the following 2 questions.",
    )

    class _Response:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def read(self) -> bytes:
            return b"not-json"

    monkeypatch.setattr("analysis.clients.ollama_client.request.urlopen", lambda http_request, timeout: _Response())

    with pytest.raises(ProviderRequestError, match="returned invalid JSON"):
        client.analyze("sample text")
