"""Unit tests for the Copilot read-only tools and the agentic loop."""

from unittest.mock import MagicMock, patch

import pytest
from anthropic.types import TextBlock, ToolUseBlock

from arc_devkit.copilot.tools import (
    MAX_RESULT_CHARS,
    TOOL_DEFINITIONS,
    execute_tool,
    sanitize_tool_result,
)

_VALID_ADDRESS = "0x" + "b" * 40


# ---------------------------------------------------------------------------
# Tool registry and sanitization
# ---------------------------------------------------------------------------


def test_tool_definitions_have_required_fields():
    names = {t["name"] for t in TOOL_DEFINITIONS}
    assert {"get_balance", "get_block_info", "estimate_gas", "debug_transaction"} <= names
    for tool in TOOL_DEFINITIONS:
        assert tool["description"]
        assert "input_schema" in tool


def test_unknown_tool_returns_error():
    result, is_error = execute_tool("rm_rf_root", {})
    assert is_error is True
    assert "Unknown tool" in result


def test_sanitize_truncates_and_marks_untrusted():
    result = sanitize_tool_result({"data": "x" * (MAX_RESULT_CHARS * 2)})
    assert "[truncated]" in result
    assert "UNTRUSTED" in result


def test_sanitize_small_payload_keeps_content():
    result = sanitize_tool_result({"balance": "42"})
    assert '"balance": "42"' in result
    assert "UNTRUSTED" in result


def test_execute_get_block_info(mock_web3):
    result, is_error = execute_tool("get_block_info", {})
    assert is_error is False
    assert "block_number" in result


def test_execute_get_balance_invalid_address_is_error():
    result, is_error = execute_tool("get_balance", {"address": "not-an-address"})
    assert is_error is True
    assert "Tool error" in result


def test_execute_debug_transaction_invalid_hash_is_error():
    result, is_error = execute_tool("debug_transaction", {"tx_hash": "0x123"})
    assert is_error is True


# ---------------------------------------------------------------------------
# New Sprint 5 tools
# ---------------------------------------------------------------------------


def test_execute_get_fee_quote(mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"
    result, is_error = execute_tool(
        "get_fee_quote", {"to": _VALID_ADDRESS, "amount": 5.0, "token": "native"}
    )
    assert is_error is False
    assert "fee_usdc" in result


def test_execute_get_fee_quote_invalid_address_is_error():
    result, is_error = execute_tool("get_fee_quote", {"to": "bad", "amount": 1.0})
    assert is_error is True


def test_execute_get_bridge_status_not_found(tmp_path):
    with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
        result, is_error = execute_tool("get_bridge_status", {"transfer_id": "nope"})
    assert is_error is False
    assert '"found": false' in result


def test_execute_get_bridge_status_found(tmp_path):
    from decimal import Decimal

    from arc_devkit.bridge.models import BridgeTransfer
    from arc_devkit.bridge.store import save_transfer

    transfer = BridgeTransfer(
        id="abc",
        source_chain_id=1,
        dest_chain_id=2,
        sender="0x" + "a" * 40,
        recipient=_VALID_ADDRESS,
        amount_usdc=Decimal("5"),
    )
    save_transfer(transfer, store_dir=tmp_path)

    with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
        result, is_error = execute_tool("get_bridge_status", {"transfer_id": "abc"})
    assert is_error is False
    assert '"found": true' in result


def test_execute_get_agent_reputation_invalid_address_is_error():
    result, is_error = execute_tool(
        "get_agent_reputation",
        {"agent_id": 1, "identity_registry": "bad", "reputation_registry": "bad"},
    )
    assert is_error is True


def test_execute_get_agent_reputation_not_found(mock_web3):
    with patch("arc_devkit.agents.identity.AgentRegistry.get_reputation", return_value=None):
        result, is_error = execute_tool(
            "get_agent_reputation",
            {
                "agent_id": 1,
                "identity_registry": _VALID_ADDRESS,
                "reputation_registry": _VALID_ADDRESS,
            },
        )
    assert is_error is False
    assert '"found": false' in result


def test_execute_search_arc_docs_not_configured():
    result, is_error = execute_tool("search_arc_docs", {"query": "fees"})
    assert is_error is False
    assert '"available": false' in result
    assert "not configured" in result.lower()


def test_execute_search_arc_docs_configured_returns_matches():
    mock_settings = MagicMock()
    mock_settings.arc_llms_txt_url = "https://example.test/llms.txt"

    mock_response = MagicMock()
    mock_response.text = "Fees on Arc are paid in USDC.\n\nSomething unrelated."
    mock_response.raise_for_status.return_value = None

    with (
        patch("arc_devkit.config.settings", mock_settings),
        patch("httpx.get", return_value=mock_response),
    ):
        result, is_error = execute_tool("search_arc_docs", {"query": "fees"})

    assert is_error is False
    assert '"available": true' in result
    assert "USDC" in result


# ---------------------------------------------------------------------------
# Agentic loop (DevCopilot.run_agent)
# ---------------------------------------------------------------------------


def _make_text_message(text: str) -> MagicMock:
    msg = MagicMock()
    msg.stop_reason = "end_turn"
    msg.content = [TextBlock(type="text", text=text)]
    return msg


def _make_tool_use_message(name: str, tool_input: dict) -> MagicMock:
    msg = MagicMock()
    msg.stop_reason = "tool_use"
    msg.content = [ToolUseBlock(type="tool_use", id="toolu_01", name=name, input=tool_input)]
    return msg


def test_run_agent_offline_returns_mock():
    from arc_devkit.copilot.agent import DevCopilot

    copilot = DevCopilot(offline=True)
    result = copilot.run_agent("what is my balance?")
    assert "Offline mode" in result["response"]
    assert result["tool_calls"] == []


def test_run_agent_without_tools_returns_direct_answer(mock_anthropic):
    mock_anthropic.messages.create.return_value = _make_text_message("Direct answer.")

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent("hello")

    assert result["response"] == "Direct answer."
    assert result["iterations"] == 1
    assert result["tool_calls"] == []


def test_run_agent_executes_tool_then_answers(mock_anthropic, mock_web3):
    mock_anthropic.messages.create.side_effect = [
        _make_tool_use_message("get_block_info", {}),
        _make_text_message("The current block is 89432."),
    ]

    tool_calls_seen: list[tuple[str, dict]] = []

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent(
            "what's the current block?",
            on_tool_call=lambda name, args: tool_calls_seen.append((name, args)),
        )

    assert result["iterations"] == 2
    assert len(result["tool_calls"]) == 1
    assert result["tool_calls"][0]["name"] == "get_block_info"
    assert tool_calls_seen == [("get_block_info", {})]
    assert "89432" in result["response"]

    # Second API call must include the tool result as a user message
    second_call = mock_anthropic.messages.create.call_args_list[1]
    messages = second_call.kwargs["messages"]
    assert messages[-1]["role"] == "user"
    assert messages[-1]["content"][0]["type"] == "tool_result"


def test_run_agent_circuit_breaker_stops_loop(mock_anthropic, mock_web3):
    # Model keeps asking for tools forever — the loop must stop at the limit
    mock_anthropic.messages.create.return_value = _make_tool_use_message("get_block_info", {})

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent("loop forever", max_iterations=3)

    assert result["iterations"] == 3
    assert len(result["tool_calls"]) == 3
    assert "circuit breaker" in result["response"]


def test_run_agent_tool_error_is_reported_to_model(mock_anthropic):
    mock_anthropic.messages.create.side_effect = [
        _make_tool_use_message("get_balance", {"address": "invalid"}),
        _make_text_message("That address is invalid."),
    ]

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        from arc_devkit.copilot.agent import DevCopilot

        result = DevCopilot().run_agent("check balance of 'invalid'")

    assert result["tool_calls"][0]["is_error"] is True
    assert result["response"] == "That address is invalid."


def test_run_agent_raises_on_non_anthropic_provider():
    """Tool-use mode is Anthropic-only today — other providers fail clearly."""
    import dataclasses

    from arc_devkit.config import settings as real_settings

    fake_settings = dataclasses.replace(
        real_settings, copilot_provider="ollama", ollama_model="llama3.2"
    )

    with patch("arc_devkit.config.settings", fake_settings):
        from arc_devkit.copilot.agent import DevCopilot

        copilot = DevCopilot()
        with pytest.raises(NotImplementedError, match="anthropic"):
            copilot.run_agent("what is my balance?")
