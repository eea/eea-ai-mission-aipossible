"""Base module for AI client interfaces."""

import hashlib
import json
import re
from pathlib import Path


class ProviderRequestError(RuntimeError):
    """Raised when an upstream AI provider request fails."""

    def __init__(self, detail: str, upstream_status_code: int | None = None):
        super().__init__(detail)
        self.detail = detail
        self.upstream_status_code = upstream_status_code


class BaseAIClient:
    """Base interface for AI clients."""

    TEXT_PLACEHOLDER = "{INSERT SCRAPED TEXT HERE}"
    LEGACY_TEXT_PLACEHOLDER = "{ROW_TEXT}"

    def __init__(
        self,
        api_key: str,
        model: str,
        api_url: str,
        prompts_dir: Path,
        user_prompt_template: str | None = None,
        system_prompt_template: str | None = None,
    ):
        self.api_key = api_key
        self.model = model
        self.api_url = api_url
        self.prompts_dir = prompts_dir
        loaded_system_prompt = system_prompt_template
        if loaded_system_prompt is None:
            loaded_system_prompt = self._load_prompt("system_prompt.txt")
        self.system_prompt = loaded_system_prompt.strip()
        if user_prompt_template is None:
            raise ValueError("user_prompt_template is required but was not provided.")
        self.user_prompt_template = self._ensure_text_to_analyse_block(user_prompt_template.strip())
        question_count = self._extract_question_count_from_user_prompt(self.user_prompt_template)
        self.response_format = self._generate_response_format(question_count)
        self.prompt_version = self._compute_prompt_version()

    def analyze(self, text: str) -> dict:
        """Analyze the given text and return the analysis results as a dictionary.

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

    def _render_user_prompt(self, text: str) -> str:
        prompt = self.user_prompt_template.replace(self.TEXT_PLACEHOLDER, text or "")
        if self.response_format:
            return f"{prompt}\n\n{self.response_format}"
        return prompt

    @classmethod
    def _ensure_text_to_analyse_block(cls, prompt: str) -> str:
        normalized_prompt = prompt.replace(cls.LEGACY_TEXT_PLACEHOLDER, cls.TEXT_PLACEHOLDER)
        if cls.TEXT_PLACEHOLDER in normalized_prompt:
            return normalized_prompt
        block = "Response text:\n<<<\n{INSERT SCRAPED TEXT HERE}\n>>>"
        if not normalized_prompt.strip():
            return block
        return f"{block}\n\n{normalized_prompt.lstrip()}"

    def _extract_question_count_from_user_prompt(self, prompt: str) -> int:
        normalized_prompt = prompt.lower()
        patterns = (
            r"\bfollowing\s+([a-z][a-z-]*|\d+)\s+questions?\b",
            r"\b([a-z][a-z-]*|\d+)\s+questions?\s+below\b",
        )
        match = None
        for pattern in patterns:
            match = re.search(pattern, normalized_prompt)
            if match:
                break
        if not match:
            raise ValueError(
                "Could not determine question count from user prompt. "
                "Include a sentence such as "
                "'I would like you to analyse the following 10 questions.' "
                "or 'Answer the 10 questions below.'"
            )

        token = match.group(1)
        if token.isdigit():
            count = int(token)
        else:
            count = self._number_word_to_int(token)

        if count <= 0:
            raise ValueError(
                f"Invalid question count '{token}' in user prompt. " "Question count must be a positive integer."
            )
        return count

    @staticmethod
    def _number_word_to_int(token: str) -> int:
        ones = {
            "one": 1,
            "two": 2,
            "three": 3,
            "four": 4,
            "five": 5,
            "six": 6,
            "seven": 7,
            "eight": 8,
            "nine": 9,
            "ten": 10,
            "eleven": 11,
            "twelve": 12,
            "thirteen": 13,
            "fourteen": 14,
            "fifteen": 15,
            "sixteen": 16,
            "seventeen": 17,
            "eighteen": 18,
            "nineteen": 19,
        }
        tens = {
            "twenty": 20,
            "thirty": 30,
            "forty": 40,
            "fifty": 50,
            "sixty": 60,
            "seventy": 70,
            "eighty": 80,
            "ninety": 90,
        }
        if token in ones:
            return ones[token]
        if token in tens:
            return tens[token]
        if "-" in token:
            parts = token.split("-", 1)
            if len(parts) == 2 and parts[0] in tens and parts[1] in ones:
                return tens[parts[0]] + ones[parts[1]]
        raise ValueError(
            f"Unsupported number word '{token}' in user prompt. " "Use digits (e.g. 10) or English number words."
        )

    def _generate_response_format(self, question_count: int) -> str:
        schema = {"answers": {f"Answer {index}": "" for index in range(1, question_count + 1)}}
        schema_json = json.dumps(schema, indent=2, ensure_ascii=False)
        return (
            "Return ONLY valid JSON. Use this exact schema with string values:\n\n"
            f"{schema_json}\n\n"
            "Rules:\n"
            "- Do not include any text outside the JSON.\n"
            "- Keep the keys exactly as shown.\n"
            "- Each value must be a string.\n"
            '- Use "" when the answer is missing.'
        )

    def _compute_prompt_version(self) -> str:
        combined = f"{self.system_prompt}\n{self.user_prompt_template}\n{self.response_format}"
        return hashlib.sha256(combined.encode("utf-8")).hexdigest()
