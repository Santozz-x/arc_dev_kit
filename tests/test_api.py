"""Unit tests for the REST API endpoints."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """FastAPI test client with no external dependencies."""
    from arc_devkit.api.main import app

    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------------


def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


# ---------------------------------------------------------------------------
# POST /copilot/ask
# ---------------------------------------------------------------------------


def test_copilot_ask_retorna_resposta(client, mock_anthropic):
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        resp = client.post("/copilot/ask", json={"prompt": "What is Arc?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert data["model"] == "claude-sonnet-4-6"


def test_copilot_ask_prompt_vazio_retorna_422(client):
    resp = client.post("/copilot/ask", json={"prompt": "ab"})
    assert resp.status_code == 422  # min_length=3 fails with 2 chars


# ---------------------------------------------------------------------------
# POST /agents/wallet
# ---------------------------------------------------------------------------


def test_create_wallet_retorna_address_e_chave(client):
    resp = client.post("/agents/wallet")
    assert resp.status_code == 200
    data = resp.json()
    assert data["address"].startswith("0x")
    assert len(data["address"]) == 42
    assert data["private_key"].startswith("0x")


# ---------------------------------------------------------------------------
# GET /agents/balance/{address}
# ---------------------------------------------------------------------------


def test_get_balance_retorna_saldo(client, mock_web3):
    mock_web3.eth.get_balance.return_value = 1_000_000_000_000_000_000
    mock_web3.from_wei.return_value = Decimal("1.0")

    with patch("arc_devkit.core.wallet.get_web3", return_value=mock_web3):
        resp = client.get("/agents/balance/0x" + "a" * 40)

    assert resp.status_code == 200
    data = resp.json()
    assert "balance_usdc" in data
    assert "address" in data


def test_get_balance_endereco_invalido_retorna_400(client):
    resp = client.get("/agents/balance/nao_e_um_endereco")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /agents/block
# ---------------------------------------------------------------------------


def test_get_block_retorna_numero_e_chain(client, mock_web3):
    # get_web3 is imported lazily inside the route → patch at the source
    mock_web3.eth.block_number = 12_345
    mock_web3.eth.chain_id = 7_777_777

    resp = client.get("/agents/block")

    assert resp.status_code == 200
    data = resp.json()
    assert data["block_number"] == mock_web3.eth.block_number
    assert data["chain_id"] == mock_web3.eth.chain_id


# ---------------------------------------------------------------------------
# GET /debug/estimate
# ---------------------------------------------------------------------------


def test_estimate_gas_retorna_custo(client, mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        resp = client.get("/debug/estimate", params={"to": "0x" + "b" * 40, "amount": 5.0})

    assert resp.status_code == 200
    data = resp.json()
    assert "gas_limit" in data
    assert "custo_usdc" in data
    assert data["gas_limit"] == 21_000


def test_estimate_gas_sem_to_retorna_422(client):
    resp = client.get("/debug/estimate", params={"amount": 5.0})
    assert resp.status_code == 422


def test_estimate_gas_bad_address_returns_400(client):
    with patch("arc_devkit.core.gas.estimate_transfer", side_effect=Exception("bad addr")):
        resp = client.get("/debug/estimate", params={"to": "bad", "amount": 1.0})
    assert resp.status_code == 400


def test_debug_analyze_returns_result(client, mock_anthropic):
    tx_hash = "0x" + "a" * 64
    with patch(
        "arc_devkit.debugger.tx_analyzer.TxAnalyzer.analyze",
        return_value={
            "hash": tx_hash,
            "status": "success",
            "summary": "OK",
            "custo_usdc": "0",
            "revert_reason": None,
            "decoded_input": None,
            "error": None,
            "suggestion": "",
            "raw_data": {},
        },
    ):
        resp = client.get(f"/debug/{tx_hash}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"


def test_copilot_ask_500_on_exception(client, mock_anthropic):
    with patch("arc_devkit.copilot.agent.DevCopilot.ask", side_effect=Exception("AI down")):
        resp = client.post("/copilot/ask", json={"prompt": "Will this fail?"})
    assert resp.status_code == 500


def test_copilot_ask_stream_returns_sse(client, mock_anthropic):
    """SSE streaming endpoint returns text/event-stream content."""
    stream_ctx = MagicMock()
    stream_ctx.__enter__ = lambda s: stream_ctx
    stream_ctx.__exit__ = MagicMock(return_value=False)
    stream_ctx.text_stream = iter(["Hello", " Arc"])
    mock_anthropic.messages.stream.return_value = stream_ctx

    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic",
        return_value=mock_anthropic,
    ):
        resp = client.post("/copilot/ask/stream", json={"prompt": "Stream this please"})

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers["content-type"]
    body = resp.text
    assert "token" in body
    assert "done" in body


# ---------------------------------------------------------------------------
# POST /agents/payment
# ---------------------------------------------------------------------------


def test_payment_signed_no_broadcast(client, mock_web3):
    mock_web3.eth.get_transaction_count.return_value = 0
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.eth.chain_id = 7_777_777
    mock_web3.to_wei.return_value = 1_000_000_000_000_000_000

    signed_mock = MagicMock()
    signed_mock.raw_transaction = b"\x01\x02\x03"
    mock_web3.eth.account.sign_transaction.return_value = signed_mock

    with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
        resp = client.post(
            "/agents/payment",
            json={
                "to": "0x" + "b" * 40,
                "amount_usdc": 1.0,
                "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                "enviar": False,
            },
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "signed"


# ---------------------------------------------------------------------------
# /agents error paths
# ---------------------------------------------------------------------------


def test_create_wallet_500_on_exception(client):
    with patch("arc_devkit.core.wallet.create_wallet", side_effect=Exception("keygen failed")):
        resp = client.post("/agents/wallet")
    assert resp.status_code == 500


def test_payment_execute_error_returns_400(client):
    """When execute() returns status=error, the route raises 400."""
    with patch(
        "arc_devkit.agents.payment_agent.PaymentAgent.execute",
        return_value={"status": "error", "error": "no private key configured"},
    ):
        resp = client.post(
            "/agents/payment",
            json={
                "to": "0x" + "b" * 40,
                "amount_usdc": 1.0,
                "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                "enviar": False,
            },
        )
    assert resp.status_code == 400


def test_payment_500_on_unexpected_exception(client, mock_web3):
    with patch(
        "arc_devkit.agents.payment_agent.PaymentAgent.execute", side_effect=Exception("boom")
    ):
        resp = client.post(
            "/agents/payment",
            json={
                "to": "0x" + "b" * 40,
                "amount_usdc": 1.0,
                "private_key": "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80",
                "enviar": False,
            },
        )
    assert resp.status_code == 500


def test_get_block_503_on_rpc_error(client):
    with patch("arc_devkit.core.connection.get_web3", side_effect=Exception("RPC down")):
        resp = client.get("/agents/block")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# gas.estimate_transfer with from_address
# ---------------------------------------------------------------------------


def test_estimate_gas_with_from_address(client, mock_web3):
    mock_web3.eth.gas_price = 1_000_000_000
    mock_web3.from_wei.return_value = "0.000021"
    mock_web3.eth.estimate_gas.return_value = 25_000
    mock_web3.to_wei.return_value = 1_000_000_000_000_000_000

    with patch("arc_devkit.core.gas.get_web3", return_value=mock_web3):
        resp = client.get(
            "/debug/estimate",
            params={"to": "0x" + "b" * 40, "amount": 1.0, "from_address": "0x" + "c" * 40},
        )

    assert resp.status_code == 200
    data = resp.json()
    assert data["gas_limit"] == 25_000
