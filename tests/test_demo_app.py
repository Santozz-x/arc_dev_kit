"""Unit tests for the read-only Mainnet Demo API (arc_devkit.api.demo_app).

All tests mock arc_devkit.api.demo_app._arc — no real network calls.
"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

_TX_HASH = "0x" + "ab" * 32
_USDC_ADDRESS = "0x3600000000000000000000000000000000000000"
_TRANSFER_TOPIC = "ddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


@pytest.fixture
def client():
    from arc_devkit.api.demo_app import app

    return TestClient(app)


def _mock_arc():
    """A MagicMock standing in for the module-level `_arc` Arc instance."""
    arc = MagicMock()
    arc.network.name = "mainnet"
    arc.network.explorer_url = "https://explorer.arc.io"
    arc.network.rpc_url = "https://rpc.mainnet.arc.io"
    return arc


# ---------------------------------------------------------------------------
# GET /demo/status
# ---------------------------------------------------------------------------


def test_status_ok(client):
    arc = _mock_arc()
    arc.health_check.return_value = {
        "network": "mainnet",
        "ready": True,
        "rpc_ok": True,
        "rpc_error": None,
        "latency_ms": 120.0,
        "expected_chain_id": 5042,
        "rpc_chain_id": 5042,
        "chain_id_match": True,
        "latest_block": 100,
        "usdc_contract_ok": True,
        "explorer_configured": True,
    }
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["ready"] is True
    assert data["network"] == "mainnet"
    assert data["explorer_url"] == "https://explorer.arc.io"


def test_status_rpc_unreachable_returns_503(client):
    arc = _mock_arc()
    arc.health_check.side_effect = ConnectionError("no route to host")
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/status")
    assert resp.status_code == 503
    assert "RPC unreachable" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# GET /demo/block/latest
# ---------------------------------------------------------------------------


def test_latest_block_ok(client):
    arc = _mock_arc()
    arc.latest_block.return_value = {
        "number": 21_500_000,
        "hash": b"\xab" * 32,
        "timestamp": 1_789_000_000,
        "transactions": [1, 2, 3],
        "gasUsed": 500_000,
        "gasLimit": 30_000_000,
    }
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/block/latest")
    assert resp.status_code == 200
    data = resp.json()
    assert data["number"] == 21_500_000
    assert data["hash"] == "0x" + "ab" * 32
    assert data["tx_count"] == 3


def test_latest_block_rpc_unreachable_returns_503(client):
    arc = _mock_arc()
    arc.latest_block.side_effect = TimeoutError("timed out")
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/block/latest")
    assert resp.status_code == 503


# ---------------------------------------------------------------------------
# GET /demo/tx/find
# ---------------------------------------------------------------------------


def test_find_tx_ok(client):
    arc = _mock_arc()
    arc.w3.eth.block_number = 100
    block_with_tx = {"transactions": [{"hash": b"\xcd" * 32}]}
    arc.w3.eth.get_block.return_value = block_with_tx
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/tx/find?scan_blocks=5")
    assert resp.status_code == 200
    assert resp.json()["tx_hash"] == "0x" + "cd" * 32


def test_find_tx_none_found_returns_404(client):
    arc = _mock_arc()
    arc.w3.eth.block_number = 100
    arc.w3.eth.get_block.return_value = {"transactions": []}
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/tx/find?scan_blocks=3")
    assert resp.status_code == 404


def test_find_tx_rejects_excessive_scan_range(client):
    arc = _mock_arc()
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/tx/find?scan_blocks=999999")
    assert resp.status_code == 400


# ---------------------------------------------------------------------------
# GET /demo/tx/{tx_hash}
# ---------------------------------------------------------------------------


def test_tx_invalid_hash_returns_400(client):
    resp = client.get("/demo/tx/not-a-hash")
    assert resp.status_code == 400


def test_tx_ok_success_status(client):
    arc = _mock_arc()
    arc.get_transaction.return_value = {
        "value": 10**18,
        "gasPrice": 1_000_000_000,
        "from": "0x" + "1" * 40,
        "to": "0x" + "2" * 40,
    }
    arc.get_transaction_receipt.return_value = {"status": 1, "gasUsed": 21_000, "logs": []}
    arc.debug_transaction.return_value = {
        "network": "Arc Mainnet",
        "status": "success",
        "custo_usdc": "0.000021",
        "revert_reason": None,
        "summary": "Status: success | Gas used: 21000 | Cost: 0.000021 USDC",
    }
    arc.w3.from_wei.side_effect = lambda wei, unit: str(wei / 10**18)

    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get(f"/demo/tx/{_TX_HASH}")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["hash"] == _TX_HASH
    assert data["debug_analysis"]["status"] == "success"
    # debug_transaction() is always called with use_ai=False on this public endpoint
    arc.debug_transaction.assert_called_once()
    assert arc.debug_transaction.call_args.kwargs.get("use_ai") is False


def test_tx_decodes_usdc_transfer_log(client):
    arc = _mock_arc()
    arc.get_transaction.return_value = {
        "value": 0,
        "gasPrice": 1_000_000_000,
        "from": "0x" + "1" * 40,
        "to": _USDC_ADDRESS,
    }
    from_topic = b"\x00" * 12 + bytes.fromhex("11" * 20)
    to_topic = b"\x00" * 12 + bytes.fromhex("22" * 20)
    amount_atomic = 5_000_000  # 5.0 USDC at 6 decimals
    log = {
        "address": _USDC_ADDRESS,
        "topics": [bytes.fromhex(_TRANSFER_TOPIC), from_topic, to_topic],
        "data": amount_atomic.to_bytes(32, "big"),
    }
    arc.get_transaction_receipt.return_value = {"status": 1, "gasUsed": 55_000, "logs": [log]}
    arc.debug_transaction.return_value = {
        "network": "Arc Mainnet",
        "status": "success",
        "custo_usdc": "0.000055",
        "revert_reason": None,
        "summary": "ok",
    }
    arc.w3.from_wei.side_effect = lambda wei, unit: str(wei / 10**18)

    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get(f"/demo/tx/{_TX_HASH}")

    assert resp.status_code == 200
    transfers = resp.json()["usdc_erc20_transfers_decoded"]
    assert len(transfers) == 1
    assert transfers[0]["amount_usdc"] == "5"
    assert transfers[0]["from"] == "0x" + "11" * 20
    assert transfers[0]["to"] == "0x" + "22" * 20


def test_tx_reverted_status(client):
    arc = _mock_arc()
    arc.get_transaction.return_value = {
        "value": 0,
        "gasPrice": 1_000_000_000,
        "from": "0x" + "1" * 40,
        "to": "0x" + "2" * 40,
    }
    arc.get_transaction_receipt.return_value = {"status": 0, "gasUsed": 30_000, "logs": []}
    arc.debug_transaction.return_value = {
        "network": "Arc Mainnet",
        "status": "reverted",
        "custo_usdc": "0.00003",
        "revert_reason": 'require failed: "insufficient balance"',
        "summary": "reverted",
    }
    arc.w3.from_wei.side_effect = lambda wei, unit: str(wei / 10**18)

    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get(f"/demo/tx/{_TX_HASH}")

    assert resp.status_code == 200
    assert resp.json()["status"] == "reverted"


def test_tx_rpc_error_returns_502(client):
    arc = _mock_arc()
    arc.get_transaction.side_effect = ConnectionError("RPC down")
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get(f"/demo/tx/{_TX_HASH}")
    assert resp.status_code == 502


# ---------------------------------------------------------------------------
# CORS / security headers
# ---------------------------------------------------------------------------


def test_response_has_security_headers(client):
    arc = _mock_arc()
    arc.health_check.return_value = {
        "network": "mainnet",
        "ready": True,
        "rpc_ok": True,
        "rpc_error": None,
        "latency_ms": 1.0,
        "expected_chain_id": 5042,
        "rpc_chain_id": 5042,
        "chain_id_match": True,
        "latest_block": 1,
        "usdc_contract_ok": True,
        "explorer_configured": True,
    }
    with patch("arc_devkit.api.demo_app._arc", arc):
        resp = client.get("/demo/status")
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in resp.headers
