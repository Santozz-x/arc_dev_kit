"""LLM provider abstraction for Dev Copilot — selects a backend via COPILOT_PROVIDER."""

from arc_devkit.copilot.providers.anthropic_provider import AnthropicProvider
from arc_devkit.copilot.providers.base import ChatMessage, LLMProvider

SUPPORTED_PROVIDERS = ("anthropic", "gemini", "openai", "ollama")


def get_provider(name: str | None = None) -> LLMProvider:
    """
    Return the LLMProvider for `name` (defaults to settings.copilot_provider).

    Never guesses a model name for gemini/openai/ollama — GEMINI_MODEL/
    OPENAI_MODEL/OLLAMA_MODEL must be set explicitly in .env when using those
    providers, since a hardcoded default could silently point at a
    deprecated or non-existent model.
    """
    from arc_devkit.config import settings

    provider_name = (name or settings.copilot_provider).strip().lower()

    if provider_name == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key, model=settings.anthropic_model)

    if provider_name == "gemini":
        if not settings.gemini_api_key:
            raise ValueError("GEMINI_API_KEY is not set — required for COPILOT_PROVIDER=gemini.")
        if not settings.gemini_model:
            raise ValueError(
                "GEMINI_MODEL is not set — required for COPILOT_PROVIDER=gemini. "
                "No default is guessed; set it explicitly (e.g. a current Gemini model "
                "name from https://ai.google.dev/gemini-api/docs/models)."
            )
        try:
            from arc_devkit.copilot.providers.gemini_provider import GeminiProvider
        except ImportError as exc:
            raise ImportError(
                "google-genai is required for COPILOT_PROVIDER=gemini. "
                "Install it with: pip install arc-devkit[gemini]"
            ) from exc
        return GeminiProvider(api_key=settings.gemini_api_key, model=settings.gemini_model)

    if provider_name == "openai":
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is not set — required for COPILOT_PROVIDER=openai.")
        if not settings.openai_model:
            raise ValueError(
                "OPENAI_MODEL is not set — required for COPILOT_PROVIDER=openai. "
                "No default is guessed; set it explicitly (e.g. a current model name "
                "from https://platform.openai.com/docs/models)."
            )
        try:
            from arc_devkit.copilot.providers.openai_provider import OpenAIProvider
        except ImportError as exc:
            raise ImportError(
                "openai is required for COPILOT_PROVIDER=openai. "
                "Install it with: pip install arc-devkit[openai]"
            ) from exc
        return OpenAIProvider(api_key=settings.openai_api_key, model=settings.openai_model)

    if provider_name == "ollama":
        if not settings.ollama_model:
            raise ValueError(
                "OLLAMA_MODEL is not set — required for COPILOT_PROVIDER=ollama "
                "(e.g. a model you've already pulled with `ollama pull <model>`)."
            )
        from arc_devkit.copilot.providers.ollama_provider import OllamaProvider

        return OllamaProvider(base_url=settings.ollama_base_url, model=settings.ollama_model)

    raise ValueError(
        f"Unknown COPILOT_PROVIDER {provider_name!r}. Supported: {', '.join(SUPPORTED_PROVIDERS)}."
    )


__all__ = ["ChatMessage", "LLMProvider", "SUPPORTED_PROVIDERS", "get_provider"]
