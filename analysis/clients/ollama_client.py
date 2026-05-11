"""Ollama client implementation for mission analysis."""

import json
from pathlib import Path
from urllib import error, request

from analysis.clients.base import BaseAIClient, ProviderRequestError


class OllamaClient(BaseAIClient):
    """Ollama client using the local generate API."""

    DEFAULT_API_URL = "http://127.0.0.1:11434"

    def __init__(
        self,
        api_key: str,
        model: str,
        api_url: str,
        prompts_dir: Path,
        user_prompt_template: str | None = None,
        system_prompt_template: str | None = None,
    ):
        resolved_api_url = (api_url or self.DEFAULT_API_URL).strip()
        super().__init__(
            api_key,
            model,
            resolved_api_url,
            prompts_dir,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        )

    def analyze(self, text: str) -> dict:
        user_prompt = self._render_user_prompt(text)
        payload = {
            "model": self.model,
            "system": self.system_prompt,
            "prompt": user_prompt,
            "stream": False,
            "options": {"temperature": 0.2},
        }
        body = json.dumps(payload).encode("utf-8")
        http_request = request.Request(
            self._resolve_generate_url(),
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(http_request, timeout=120) as response:
                raw_body = response.read().decode("utf-8")
        except error.HTTPError as exc:
            status_code = getattr(exc, "code", None)
            if status_code == 403:
                raise ProviderRequestError(
                    "Provider 'ollama' rejected the request with status 403. "
                    "Check local Ollama access and API_URL.",
                    upstream_status_code=status_code,
                ) from exc
            raise ProviderRequestError(
                f"Provider 'ollama' request failed with status {status_code or 'unknown'}.",
                upstream_status_code=status_code,
            ) from exc
        except TimeoutError as exc:
            raise ProviderRequestError("Provider 'ollama' request timed out.") from exc
        except error.URLError as exc:
            raise ProviderRequestError("Could not connect to provider 'ollama'. Check API_URL.") from exc

        try:
            data = json.loads(raw_body)
        except json.JSONDecodeError as exc:
            raise ProviderRequestError("Provider 'ollama' returned invalid JSON.") from exc

        result = ""
        if isinstance(data, dict):
            result = str(data.get("response") or "")

        return {
            "provider": "ollama",
            "system_prompt": self.system_prompt,
            "user_prompt": user_prompt,
            "result": result,
            "model": self.model,
            "api_url": self.api_url,
            "prompt_version": self.prompt_version,
            "raw": data,
        }

    def _resolve_generate_url(self) -> str:
        base_url = self.api_url.rstrip("/")
        if base_url.endswith("/api/generate"):
            return base_url
        return f"{base_url}/api/generate"
