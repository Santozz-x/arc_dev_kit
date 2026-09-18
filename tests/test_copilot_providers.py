"""Unit tests for arc_devkit.copilot.providers — the multi-LLM abstraction.

All tests mock the underlying SDK/HTTP calls — none make a real network
call to Anthropic, Google, OpenAI, or a local Ollama server.
"""

import dataclasses
from unittest.mock import MagicMock, patch

import pytest

from arc_devkit.copilot.providers.base import ChatMessage

# ---------------------------------------------------------------------------
# get_provider() factory — selection and validation
# ---------------------------------------------------------------------------


class TestGetProvider:
    def test_defaults_to_anthropic(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider
        from arc_devkit.copilot.providers.anthropic_provider import AnthropicProvider

        with patch(
            "arc_devkit.config.settings",
            dataclasses.replace(settings, copilot_provider="anthropic"),
        ):
            provider = get_provider()
        assert isinstance(provider, AnthropicProvider)
        assert provider.model == settings.anthropic_model

    def test_explicit_name_overrides_settings(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider
        from arc_devkit.copilot.providers.anthropic_provider import AnthropicProvider

        with patch("arc_devkit.config.settings", settings):
            provider = get_provider("anthropic")
        assert isinstance(provider, AnthropicProvider)

    def test_gemini_without_api_key_raises(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider

        fake = dataclasses.replace(
            settings, copilot_provider="gemini", gemini_api_key=None, gemini_model="gemini-x"
        )
        with (
            patch("arc_devkit.config.settings", fake),
            pytest.raises(ValueError, match="GEMINI_API_KEY"),
        ):
            get_provider()

    def test_gemini_without_model_raises(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider

        fake = dataclasses.replace(
            settings, copilot_provider="gemini", gemini_api_key="fake-key", gemini_model=None
        )
        with (
            patch("arc_devkit.config.settings", fake),
            pytest.raises(ValueError, match="GEMINI_MODEL"),
        ):
            get_provider()

    def test_openai_without_api_key_raises(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider

        fake = dataclasses.replace(
            settings, copilot_provider="openai", openai_api_key=None, openai_model="gpt-x"
        )
        with (
            patch("arc_devkit.config.settings", fake),
            pytest.raises(ValueError, match="OPENAI_API_KEY"),
        ):
            get_provider()

    def test_ollama_without_model_raises(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider

        fake = dataclasses.replace(settings, copilot_provider="ollama", ollama_model=None)
        with (
            patch("arc_devkit.config.settings", fake),
            pytest.raises(ValueError, match="OLLAMA_MODEL"),
        ):
            get_provider()

    def test_unknown_provider_raises(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider

        fake = dataclasses.replace(settings, copilot_provider="not-a-real-provider")
        with patch("arc_devkit.config.settings", fake), pytest.raises(ValueError, match="Unknown"):
            get_provider()

    def test_gemini_constructs_when_configured(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider
        from arc_devkit.copilot.providers.gemini_provider import GeminiProvider

        fake = dataclasses.replace(
            settings, copilot_provider="gemini", gemini_api_key="fake-key", gemini_model="gemini-x"
        )
        with (
            patch("arc_devkit.config.settings", fake),
            patch("google.genai.Client") as MockClient,
        ):
            provider = get_provider()
        assert isinstance(provider, GeminiProvider)
        assert provider.model == "gemini-x"
        MockClient.assert_called_once_with(api_key="fake-key")

    def test_openai_constructs_when_configured(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider
        from arc_devkit.copilot.providers.openai_provider import OpenAIProvider

        fake = dataclasses.replace(
            settings, copilot_provider="openai", openai_api_key="fake-key", openai_model="gpt-x"
        )
        with (
            patch("arc_devkit.config.settings", fake),
            patch("openai.OpenAI") as MockClient,
        ):
            provider = get_provider()
        assert isinstance(provider, OpenAIProvider)
        assert provider.model == "gpt-x"
        MockClient.assert_called_once_with(api_key="fake-key")

    def test_ollama_constructs_when_configured(self):
        from arc_devkit.config import settings
        from arc_devkit.copilot.providers import get_provider
        from arc_devkit.copilot.providers.ollama_provider import OllamaProvider

        fake = dataclasses.replace(
            settings,
            copilot_provider="ollama",
            ollama_model="llama3.2",
            ollama_base_url="http://localhost:11434",
        )
        with patch("arc_devkit.config.settings", fake):
            provider = get_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider.model == "llama3.2"


# ---------------------------------------------------------------------------
# AnthropicProvider
# ---------------------------------------------------------------------------


class TestAnthropicProvider:
    def test_ask_returns_text(self):
        from anthropic.types import TextBlock

        from arc_devkit.copilot.providers.anthropic_provider import AnthropicProvider

        with patch(
            "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic"
        ) as MockAnthropic:
            instance = MagicMock()
            instance.messages.create.return_value = MagicMock(
                content=[TextBlock(type="text", text="Hi there")]
            )
            MockAnthropic.return_value = instance

            provider = AnthropicProvider(api_key="sk-test", model="claude-x")
            result = provider.ask("system prompt", [ChatMessage(role="user", content="hello")], 100)

        assert result == "Hi there"

    def test_supports_tools_is_true(self):
        from arc_devkit.copilot.providers.anthropic_provider import AnthropicProvider

        with patch("arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic"):
            provider = AnthropicProvider(api_key="sk-test", model="claude-x")
        assert provider.supports_tools is True


# ---------------------------------------------------------------------------
# GeminiProvider
# ---------------------------------------------------------------------------


class TestGeminiProvider:
    def test_ask_returns_text(self):
        from arc_devkit.copilot.providers.gemini_provider import GeminiProvider

        with patch("google.genai.Client") as MockClient:
            instance = MagicMock()
            instance.models.generate_content.return_value = MagicMock(text="Gemini says hi")
            MockClient.return_value = instance

            provider = GeminiProvider(api_key="fake-key", model="gemini-x")
            result = provider.ask("system prompt", [ChatMessage(role="user", content="hello")], 100)

        assert result == "Gemini says hi"

    def test_ask_stream_yields_chunks(self):
        from arc_devkit.copilot.providers.gemini_provider import GeminiProvider

        with patch("google.genai.Client") as MockClient:
            instance = MagicMock()
            chunk1 = MagicMock(text="Hello")
            chunk2 = MagicMock(text=" world")
            instance.models.generate_content_stream.return_value = [chunk1, chunk2]
            MockClient.return_value = instance

            provider = GeminiProvider(api_key="fake-key", model="gemini-x")
            chunks = list(
                provider.ask_stream("system prompt", [ChatMessage(role="user", content="hi")], 100)
            )

        assert chunks == ["Hello", " world"]

    def test_supports_tools_defaults_false(self):
        from arc_devkit.copilot.providers.gemini_provider import GeminiProvider

        with patch("google.genai.Client"):
            provider = GeminiProvider(api_key="fake-key", model="gemini-x")
        assert provider.supports_tools is False


# ---------------------------------------------------------------------------
# OpenAIProvider
# ---------------------------------------------------------------------------


class TestOpenAIProvider:
    def test_ask_returns_text(self):
        from arc_devkit.copilot.providers.openai_provider import OpenAIProvider

        with patch("openai.OpenAI") as MockClient:
            instance = MagicMock()
            message = MagicMock(content="GPT says hi")
            instance.chat.completions.create.return_value = MagicMock(
                choices=[MagicMock(message=message)]
            )
            MockClient.return_value = instance

            provider = OpenAIProvider(api_key="fake-key", model="gpt-x")
            result = provider.ask("system prompt", [ChatMessage(role="user", content="hello")], 100)

        assert result == "GPT says hi"

    def test_ask_stream_yields_chunks(self):
        from arc_devkit.copilot.providers.openai_provider import OpenAIProvider

        with patch("openai.OpenAI") as MockClient:
            instance = MagicMock()
            chunk1 = MagicMock(choices=[MagicMock(delta=MagicMock(content="Hello"))])
            chunk2 = MagicMock(choices=[MagicMock(delta=MagicMock(content=" world"))])
            instance.chat.completions.create.return_value = [chunk1, chunk2]
            MockClient.return_value = instance

            provider = OpenAIProvider(api_key="fake-key", model="gpt-x")
            chunks = list(
                provider.ask_stream("system prompt", [ChatMessage(role="user", content="hi")], 100)
            )

        assert chunks == ["Hello", " world"]


# ---------------------------------------------------------------------------
# OllamaProvider
# ---------------------------------------------------------------------------


class TestOllamaProvider:
    def test_ask_returns_text(self):
        from arc_devkit.copilot.providers.ollama_provider import OllamaProvider

        with patch("arc_devkit.copilot.providers.ollama_provider.httpx.post") as mock_post:
            mock_post.return_value = MagicMock(
                json=lambda: {"message": {"content": "Ollama says hi"}},
                raise_for_status=lambda: None,
            )

            provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2")
            result = provider.ask("system prompt", [ChatMessage(role="user", content="hello")], 100)

        assert result == "Ollama says hi"
        mock_post.assert_called_once()

    def test_ask_stream_yields_chunks(self):
        import json as _json

        from arc_devkit.copilot.providers.ollama_provider import OllamaProvider

        lines = [
            _json.dumps({"message": {"content": "Hello"}, "done": False}),
            _json.dumps({"message": {"content": " world"}, "done": True}),
        ]

        mock_response = MagicMock()
        mock_response.iter_lines.return_value = lines
        mock_response.raise_for_status = lambda: None
        mock_response.__enter__ = lambda self: mock_response
        mock_response.__exit__ = lambda self, *a: None

        with patch(
            "arc_devkit.copilot.providers.ollama_provider.httpx.stream", return_value=mock_response
        ):
            provider = OllamaProvider(base_url="http://localhost:11434", model="llama3.2")
            chunks = list(
                provider.ask_stream("system prompt", [ChatMessage(role="user", content="hi")], 100)
            )

        assert chunks == ["Hello", " world"]
