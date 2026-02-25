"""OpenAI client implementation for mission analysis."""

from pathlib import Path
from openai import OpenAI

from analysis.clients.base import BaseAIClient


class OpenAIClient(BaseAIClient):
    """OpenAI client using the Responses API (SDK)."""

    def __init__(self, api_key: str, model: str, api_url: str, prompts_dir: Path):
        super().__init__(api_key, model, api_url, prompts_dir)
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url or None)

    def analyze(self, text: str) -> dict:
        user_prompt = self._render_user_prompt(text)
        response = self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        result = getattr(response, "output_text", "") or ""
        data = response.model_dump()

        return {
            "provider": "openai",
            "system_prompt": self.system_prompt,
            "user_prompt": user_prompt,
            "result": result,
            "model": self.model,
            "api_url": self.api_url,
            "prompt_version": self.prompt_version,
            "raw": data,
        }
