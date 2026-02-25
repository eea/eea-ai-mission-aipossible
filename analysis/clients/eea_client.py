"""EEAClient module for interacting with the Chat Completions API via OpenAI."""

from pathlib import Path

from openai import OpenAI

from analysis.clients.base import BaseAIClient


class EEAClient(BaseAIClient):
    """EEA client using the Chat Completions API (SDK)."""

    def __init__(self, api_key: str, model: str, api_url: str, prompts_dir: Path):
        super().__init__(api_key, model, api_url, prompts_dir)
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url or None)

    def analyze(self, text: str) -> dict:
        user_prompt = self._render_user_prompt(text)
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
        )
        data = response.model_dump()
        result = ""
        try:
            result = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            result = ""

        return {
            "provider": "eea",
            "system_prompt": self.system_prompt,
            "user_prompt": user_prompt,
            "result": result,
            "model": self.model,
            "api_url": self.api_url,
            "prompt_version": self.prompt_version,
            "raw": data,
        }
