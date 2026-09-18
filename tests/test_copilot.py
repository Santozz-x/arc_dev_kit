"""Tests for the arc_devkit.copilot.agent module."""

from unittest.mock import MagicMock, patch


def test_ask_retorna_string_nao_vazia(mock_anthropic):
    """DevCopilot.ask() must return a non-empty string."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        response = copilot.ask("What is the Arc blockchain?")

    assert isinstance(response, str)
    assert len(response) > 0


def test_ask_envia_system_prompt(mock_anthropic):
    """DevCopilot.ask() must include the system prompt in every call."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Test question")

    # Verify that messages.create was called with 'system'
    call = mock_anthropic.messages.create.call_args
    assert call is not None

    kwargs = call.kwargs
    assert "system" in kwargs, "The 'system' parameter must be present in the call"
    assert "Arc" in kwargs["system"], "The system prompt must mention the Arc blockchain"


def test_ask_usa_modelo_correto(mock_anthropic):
    """DevCopilot.ask() must use the claude-sonnet-4-6 model."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("Model test")

    call = mock_anthropic.messages.create.call_args
    assert call.kwargs.get("model") == "claude-sonnet-4-6"


def test_ask_respeita_max_tokens(mock_anthropic):
    """DevCopilot.ask() must send max_tokens in the request."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("max_tokens test")

    call = mock_anthropic.messages.create.call_args
    assert "max_tokens" in call.kwargs
    assert call.kwargs["max_tokens"] == DevCopilot.MAX_TOKENS


def test_ask_envia_prompt_do_usuario(mock_anthropic):
    """DevCopilot.ask() must send the user prompt in the messages list."""
    test_prompt = "How do I create a wallet on the Arc testnet?"

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask(test_prompt)

    call = mock_anthropic.messages.create.call_args
    messages = call.kwargs.get("messages", [])
    assert len(messages) == 1
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == test_prompt


def test_extra_context_injected_in_system_prompt(mock_anthropic):
    """extra_context is appended to the system prompt."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot(extra_context="Use only Solidity 0.8.x")
        copilot.ask("Test")

    call = mock_anthropic.messages.create.call_args
    assert "Use only Solidity 0.8.x" in call.kwargs["system"]


def test_model_property_alias(mock_anthropic):
    """MODEL property returns same value as .model attribute."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
    assert copilot.MODEL == copilot.model


def test_ask_cache_hit_skips_api_call(mock_anthropic):
    """Second identical ask returns cached response without calling the API."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        r1 = copilot.ask("What is Arc?")
        r2 = copilot.ask("What is Arc?")  # should hit cache

    assert r1 == r2
    # API called only once despite two asks
    assert mock_anthropic.messages.create.call_count == 1


def test_ask_stream_yields_chunks(mock_anthropic):
    """ask_stream yields each text chunk from the stream."""
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = lambda s: stream_ctx
    stream_ctx.__exit__ = MagicMock(return_value=False)
    stream_ctx.text_stream = iter(["Hello", " world", "!"])
    mock_anthropic.messages.stream.return_value = stream_ctx

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        chunks = list(copilot.ask_stream("Hi?"))

    assert chunks == ["Hello", " world", "!"]


def test_clear_history_empties_list(mock_anthropic):
    """clear_history() removes all messages from the conversation."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("First question")
        assert len(copilot.history) > 0
        copilot.clear_history()
        assert copilot.history == []


def test_count_tokens_returns_int(mock_anthropic):
    """count_tokens() calls the API and returns token count."""
    mock_anthropic.messages.count_tokens.return_value = MagicMock(input_tokens=37)

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        count = copilot.count_tokens("How many tokens is this?")

    assert count == 37


def test_history_property_returns_copy(mock_anthropic):
    """history property returns a copy so external mutation doesn't affect state."""
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        copilot.ask("First message")
        h = copilot.history
        h.clear()  # mutate the returned copy

    # Internal history must be unaffected
    assert len(copilot.history) > 0
