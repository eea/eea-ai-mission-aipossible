"""Base module for AI client interfaces."""

import hashlib
from pathlib import Path


class BaseAIClient:
    """Base interface for AI clients."""

    def __init__(self, api_key: str, model: str, api_url: str, prompts_dir: Path):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.prompts_dir = prompts_dir
        self.system_prompt = self._load_prompt("system_prompt.txt")
        self.user_prompt_template = self._load_prompt("user_prompt.txt")
        self.response_format = self._load_optional_prompt("response_format.txt")
        self.prompt_version = self._compute_prompt_version()

    def analyze(self, text: str) -> dict:
        """
        Analyze the given text and return the analysis results as a dictionary.

        Args:
            text (str): The text to be analyzed.

        Returns:
            dict: A dictionary containing the results of the analysis.

        Raises:
            NotImplementedError: If the method is not implemented in a subclass.
        """
        raise NotImplementedError

    def get_model(self) -> str:
        """Return the model name."""
        return self.model

    def _load_prompt(self, name: str) -> str:
        prompt_path = self.prompts_dir / name
        return prompt_path.read_text(encoding="utf-8").strip()

    def _load_optional_prompt(self, name: str) -> str:
        prompt_path = self.prompts_dir / name
        if not prompt_path.exists():
            return ""
        return prompt_path.read_text(encoding="utf-8").strip()

    def _render_user_prompt(self, text: str) -> str:
        prompt = self.user_prompt_template.replace("{INSERT SCRAPED TEXT HERE}", text or "")
        if self.response_format:
            return f"{prompt}\n\n{self.response_format}"
        return prompt

    def _compute_prompt_version(self) -> str:
        combined = f"{self.system_prompt}\n{self.user_prompt_template}\n{self.response_format}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
