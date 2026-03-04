"""Mock AI client implementation for local testing without API calls."""

from pathlib import Path

from analysis.clients.base import BaseAIClient


class MockClient(BaseAIClient):
    """Deterministic mock provider that never calls external services."""

    def __init__(self, api_key: str, model: str, api_url: str, prompts_dir: Path):
        resolved_model = model or "mock-model"
        super().__init__(api_key, resolved_model, api_url, prompts_dir)

    def analyze(self, text: str) -> dict:
        user_prompt = self._render_user_prompt(text)
        snippet = (text or "").strip().replace("\r", " ").replace("\n", " ")
        snippet = snippet[:300]
        result = (
            "Q1: Mock analysis response for API/local testing.\n"
            "Q2: This output is deterministic and uses no external tokens.\n"
            f"Q3: Input snippet: {snippet}"
        )

        return {
            "provider": "mock",
            "system_prompt": self.system_prompt,
            "user_prompt": user_prompt,
            "result": result,
            "model": self.model,
            "api_url": self.api_url,
            "prompt_version": self.prompt_version,
            "raw": {"mode": "mock"},
        }
