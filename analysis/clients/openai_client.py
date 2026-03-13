"""OpenAI client implementation for mission analysis."""

from pathlib import Path
from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

from analysis.clients.base import BaseAIClient, ProviderRequestError


class OpenAIClient(BaseAIClient):
    """OpenAI client using the Responses API (SDK)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        api_url: str,
        prompts_dir: Path,
        user_prompt_template: str | None = None,
        system_prompt_template: str | None = None,
    ):
        super().__init__(
            api_key,
            model,
            api_url,
            prompts_dir,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        )
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_url or None)

    def analyze(self, text: str) -> dict:
        user_prompt = self._render_user_prompt(text)
        try:
            response = self.client.responses.create(
                model=self.model,
                input=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.2,
            )
        except APIStatusError as exc:
            status_code = getattr(exc, "status_code", None)
            if status_code == 403:
                raise ProviderRequestError(
                    "Provider 'openai' rejected the request with status 403. "
                    "Check API key, model access, and API_URL.",
                    upstream_status_code=status_code,
                ) from exc
            raise ProviderRequestError(
                f"Provider 'openai' request failed with status {status_code or 'unknown'}.",
                upstream_status_code=status_code,
            ) from exc
        except APITimeoutError as exc:
            raise ProviderRequestError("Provider 'openai' request timed out.") from exc
        except APIConnectionError as exc:
            raise ProviderRequestError("Could not connect to provider 'openai'. Check API_URL.") from exc
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
