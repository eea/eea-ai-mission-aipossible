"""Factory for creating API clients based on provider."""

from pathlib import Path

from analysis.clients.eea_client import EEAClient
from analysis.clients.mock_client import MockClient
from analysis.clients.ollama_client import OllamaClient
from analysis.clients.openai_client import OpenAIClient


def get_client(
    provider: str,
    api_key: str,
    model: str,
    api_url: str,
    prompts_dir: Path,
    user_prompt_template: str | None = None,
    system_prompt_template: str | None = None,
):
    """
    Create and return an API client instance based on the provider.

    Args:
        provider (str): The name of the provider ('openai', 'eea', 'ollama', or 'mock').
        api_key (str): The API key for authentication.
        model (str): The model name to use.
        api_url (str): The API endpoint URL.
        prompts_dir (Path): Directory containing prompt files.
        user_prompt_template (str | None): Optional per-run user prompt override.
        system_prompt_template (str | None): Optional per-run system prompt override.

    Returns:
        An instance of OpenAIClient, EEAClient, OllamaClient, or MockClient.

    Raises:
        ValueError: If the provider is unknown.
    """
    key = (provider or "").lower()
    if key == "openai":
        return OpenAIClient(
            api_key=api_key,
            model=model,
            api_url=api_url,
            prompts_dir=prompts_dir,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        )
    if key == "eea":
        return EEAClient(
            api_key=api_key,
            model=model,
            api_url=api_url,
            prompts_dir=prompts_dir,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        )
    if key == "ollama":
        return OllamaClient(
            api_key=api_key,
            model=model,
            api_url=api_url,
            prompts_dir=prompts_dir,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        )
    if key == "mock":
        return MockClient(
            api_key=api_key,
            model=model,
            api_url=api_url,
            prompts_dir=prompts_dir,
            user_prompt_template=user_prompt_template,
            system_prompt_template=system_prompt_template,
        )
    raise ValueError(f"Unknown provider: {provider}")
