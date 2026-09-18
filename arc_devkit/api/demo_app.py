"""Arc DevKit — Mainnet Demo API.

A minimal, standalone, read-only FastAPI app that backs the "Mainnet Demo"
page on the Arc DevKit website (website/app/demo). It exists as a separate
app from arc_devkit.api.main on purpose:

  - It exposes ONLY read-only Arc Mainnet data (health check, latest block,
    transaction lookup + debugger analysis) — never the payment, bridge,
    agent-identity, or Copilot endpoints that the main API serves.
  - It deliberately never imports arc_devkit.config, so it needs no
    ANTHROPIC_API_KEY, no ARC_PRIVATE_KEY — nothing beyond the two optional
    env vars documented below. This keeps the public demo deployment's
    credential surface at zero.
  - Every on-chain read goes through arc_devkit.Arc, the same facade class
    documented and shipped in the PyPI package — this service is a thin
    HTTP wrapper around it, not a reimplementation.

It never signs, sends, or deploys anything, and it never lets a caller pick
an arbitrary RPC URL — the operator sets DEMO_RPC_URL once (or leaves it
unset to use Circle's official Arc Mainnet RPC), and that's the only RPC
this service will ever talk to.

Run locally:
    uvicorn arc_devkit.api.demo_app:app --reload --port 8010

Env vars (all optional):
    DEMO_ALLOWED_ORIGINS   Comma-separated CORS origins allowed to call this
                           API (default: http://localhost:3000).
    DEMO_RPC_URL           Override the Arc Mainnet RPC this service talks
                           to (default: Circle's official
                           https://rpc.mainnet.arc.io, via arc_devkit.Arc).
"""

from __future__ import annotations

import logging
import os
import time
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from arc_devkit import Arc, __version__
from arc_devkit.api.rate_limit import limiter
from arc_devkit.core.validation import ValidationError, validate_block_range, validate_tx_hash
from arc_devkit.networks import NATIVE_USDC_DECIMALS, USDC_ERC20_ADDRESS

logger = logging.getLogger(__name__)

_MAX_SCAN_BLOCKS = 200
_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _allowed_origins() -> list[str]:
    raw = os.getenv("DEMO_ALLOWED_ORIGINS", "").strip()
    if raw:
        return [o.strip() for o in raw.split(",") if o.strip()]
    return ["http://localhost:3000"]


def _hex0x(value: Any) -> str:
    """Normalize bytes/HexBytes/str into a lowercase '0x...' string."""
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    if hasattr(value, "hex") and not isinstance(value, str):
        h = str(value.hex())
        return h if h.startswith("0x") else "0x" + h
    return str(value)


def _decode_usdc_transfers(receipt: dict) -> list[dict]:
    """Best-effort decode of any USDC ERC-20 Transfer(address,address,uint256) log."""
    transfers = []
    for log in receipt.get("logs", []):
        try:
            if _hex0x(log["address"]).lower() != USDC_ERC20_ADDRESS.lower():
                continue
            topics = log.get("topics", [])
            if not topics or _hex0x(topics[0]).lower() != _TRANSFER_TOPIC:
                continue
            from_addr = "0x" + _hex0x(topics[1])[-40:]
            to_addr = "0x" + _hex0x(topics[2])[-40:]
            data = log["data"]
            data_bytes = (
                data if isinstance(data, (bytes, bytearray)) else bytes.fromhex(_hex0x(data)[2:])
            )
            amount_atomic = int.from_bytes(data_bytes, "big")
            amount = Decimal(amount_atomic) / Decimal(10**6)
            transfers.append({"from": from_addr, "to": to_addr, "amount_usdc": str(amount)})
        except Exception:  # noqa: BLE001 - best-effort decoding, never fatal
            continue
    return transfers


def _find_recent_tx_hash(arc: Arc, scan_blocks: int) -> str | None:
    latest = arc.w3.eth.block_number
    lowest = max(latest - scan_blocks + 1, 0)
    for block_number in range(latest, lowest - 1, -1):
        block = arc.w3.eth.get_block(block_number, full_transactions=True)
        txs = block.get("transactions", [])
        if txs:
            return _hex0x(txs[0]["hash"])  # type: ignore[call-overload]
    return None


app = FastAPI(
    title="Arc DevKit — Mainnet Demo API",
    description=(
        "Read-only public endpoints backing the Arc Mainnet live demo on the "
        "Arc DevKit website. Every response is built on arc_devkit.Arc — the "
        "same facade class shipped in the `arc-devkit` PyPI package."
    ),
    version=__version__,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins(),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_and_logging(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    start = time.time()
    response = await call_next(request)
    latency_ms = int((time.time() - start) * 1000)
    response.headers["X-Request-ID"] = request_id
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    logger.info(
        "request_id=%s method=%s path=%s status=%d latency_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        latency_ms,
    )
    return response


# Constructing Arc() never makes a network call (Web3/HTTPProvider is lazy),
# so it's safe to build once at import time and reuse across requests.
_rpc_override = os.getenv("DEMO_RPC_URL", "").strip() or None
_arc = Arc.mainnet(rpc_url=_rpc_override)


@app.get("/demo/status", tags=["Demo"])
@limiter.limit("30/minute")
async def demo_status(request: Request) -> dict:
    """Live health check against Arc Mainnet — wraps Arc.health_check()."""
    try:
        health = _arc.health_check()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"RPC unreachable: {exc}") from exc
    return {
        "queried_at_utc": datetime.now(UTC).isoformat(),
        "network": _arc.network.name,
        "explorer_url": _arc.network.explorer_url,
        "rpc_url": _rpc_override or _arc.network.rpc_url,
        **health,
    }


@app.get("/demo/block/latest", tags=["Demo"])
@limiter.limit("30/minute")
async def demo_latest_block(request: Request) -> dict:
    """The most recent Arc Mainnet block — wraps Arc.latest_block()."""
    try:
        block = _arc.latest_block()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"RPC unreachable: {exc}") from exc
    return {
        "queried_at_utc": datetime.now(UTC).isoformat(),
        "number": block["number"],
        "hash": _hex0x(block["hash"]),
        "timestamp_unix": block["timestamp"],
        "timestamp_utc": datetime.fromtimestamp(block["timestamp"], tz=UTC).isoformat(),
        "tx_count": len(block.get("transactions", [])),
        "gas_used": block.get("gasUsed"),
        "gas_limit": block.get("gasLimit"),
    }


@app.get("/demo/tx/find", tags=["Demo"])
@limiter.limit("10/minute")
async def demo_find_tx(request: Request, scan_blocks: int = 30) -> dict:
    """Scan back from the latest block for the first confirmed transaction found."""
    try:
        scan_blocks = validate_block_range(scan_blocks, max_blocks=_MAX_SCAN_BLOCKS)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    try:
        tx_hash = _find_recent_tx_hash(_arc, scan_blocks)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"RPC unreachable: {exc}") from exc
    if not tx_hash:
        raise HTTPException(
            status_code=404,
            detail=f"No transactions found in the last {scan_blocks} blocks.",
        )
    return {
        "queried_at_utc": datetime.now(UTC).isoformat(),
        "tx_hash": tx_hash,
        "scanned_blocks": scan_blocks,
    }


@app.get("/demo/tx/{tx_hash}", tags=["Demo"])
@limiter.limit("20/minute")
async def demo_tx(request: Request, tx_hash: str) -> dict:
    """
    Full read-only diagnosis of one transaction — get_transaction() +
    get_transaction_receipt() + debug_transaction(use_ai=False). The AI
    summary is always disabled on this public endpoint: this service
    carries no AI provider credentials by design.
    """
    try:
        tx_hash = validate_tx_hash(tx_hash)
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        tx = _arc.get_transaction(tx_hash)
        receipt = _arc.get_transaction_receipt(tx_hash)
        report = _arc.debug_transaction(tx_hash, use_ai=False)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=502, detail=f"Could not fetch transaction {tx_hash}: {exc}"
        ) from exc

    status = "success" if receipt.get("status") == 1 else "reverted"
    value_native = Decimal(str(_arc.w3.from_wei(tx.get("value", 0), "ether")))
    gas_cost_native = Decimal(
        str(_arc.w3.from_wei(receipt.get("gasUsed", 0) * tx.get("gasPrice", 0), "ether"))
    )

    return {
        "queried_at_utc": datetime.now(UTC).isoformat(),
        "hash": tx_hash,
        "status": status,
        "block": receipt.get("blockNumber"),
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value_native_usdc": str(value_native),
        "native_usdc_decimals": NATIVE_USDC_DECIMALS,
        "gas_used": receipt.get("gasUsed"),
        "gas_cost_native_usdc": str(gas_cost_native),
        "explorer_url": f"{_arc.network.explorer_url}/tx/{tx_hash}",
        "usdc_erc20_contract": USDC_ERC20_ADDRESS,
        "usdc_erc20_transfers_decoded": _decode_usdc_transfers(receipt),
        "debug_analysis": {
            "network": report["network"],
            "status": report["status"],
            "custo_usdc": report["custo_usdc"],
            "revert_reason": report["revert_reason"],
            "summary": report["summary"],
        },
    }
