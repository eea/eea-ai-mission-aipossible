"""Factory for creating API clients based on provider."""

from pathlib import Path

from analysis.clients.eea_client import EEAClient
from analysis.clients.mock_client import MockClient
from analysis.clients.openai_client import OpenAIClient


def get_client(provider: str, api_key: str, model: str, api_url: str, prompts_dir: Path):
    """
    Create and return an API client instance based on the provider.

    Args:
        provider (str): The name of the provider ('openai', 'eea', or 'mock').
        api_key (str): The API key for authentication.
        model (str): The model name to use.
        api_url (str): The API endpoint URL.
        prompts_dir (Path): Directory containing prompt files.

    Returns:
        An instance of OpenAIClient, EEAClient, or MockClient.

    Raises:
        ValueError: If the provider is unknown.
    """
    key = (provider or "").lower()
    if key == "openai":
        return OpenAIClient(api_key=api_key, model=model, api_url=api_url, prompts_dir=prompts_dir)
    if key == "eea":
        return EEAClient(api_key=api_key, model=model, api_url=api_url, prompts_dir=prompts_dir)
    if key == "mock":
        return MockClient(api_key=api_key, model=model, api_url=api_url, prompts_dir=prompts_dir)
    raise ValueError(f"Unknown provider: {provider}")
