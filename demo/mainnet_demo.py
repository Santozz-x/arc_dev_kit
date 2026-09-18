#!/usr/bin/env python3
"""
Arc DevKit — Arc Mainnet Live Demo (read-only, public data only)

Built for the Arc Microgrants application: proves that `arc-devkit` can be
installed from PyPI and used, as-is, to read real data from Arc Mainnet.

What this script does, using ONLY arc_devkit.Arc (no raw RPC calls, no
custom web3 wiring):
  1. Connects to Arc Mainnet via Arc.mainnet().
  2. Runs Arc.health_check() and checks the RPC-reported chain ID against
     the SDK's own network configuration (arc_devkit.networks).
  3. Reads the latest block and its timestamp.
  4. Reads a real, already-confirmed transaction — either the hash you pass,
     or the first transaction found scanning back a limited number of
     recent blocks (never fabricated, never truncated).
  5. Prints its full hash, status, block, USDC cost, and explorer link,
     distinguishing the native USDC gas balance (18 decimals) from the
     ERC-20 USDC view (6 decimals) — and decodes any USDC ERC-20 Transfer
     log found in the receipt to show both scales side by side.
  6. Runs arc.debug_transaction(tx_hash, use_ai=False) — the same debugger
     used by `arcdevkit debug tx`, with the AI summary explicitly disabled
     so this demo never depends on an AI provider or API key.

What this script deliberately does NOT do:
  - It never imports arc_devkit.config, so no .env (personal or otherwise)
    is ever loaded — the process needs no ANTHROPIC_API_KEY, no
    ARC_PRIVATE_KEY, nothing.
  - It never constructs a wallet, signs anything, or broadcasts a
    transaction — every call here is a read.
  - It never deploys a contract.

Usage:
    python demo/mainnet_demo.py                        # auto-find a recent tx
    python demo/mainnet_demo.py 0xTX_HASH...            # use a specific tx
    python demo/mainnet_demo.py --scan-blocks 100        # widen the auto-search
    python demo/mainnet_demo.py --rpc-url https://...    # use your own RPC
    python demo/mainnet_demo.py --json out.json          # also save structured results

Exit codes: 0 on success, 1 on any RPC/network failure or if no transaction
could be found — always with a clear message on stderr, never a silent
fallback to fake data.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

# Only import from the public arc_devkit package — this is exactly what a
# `pip install arc-devkit` user gets, nothing added, nothing patched.
from arc_devkit import Arc
from arc_devkit.networks import NATIVE_USDC_DECIMALS, USDC_ERC20_ADDRESS

_TRANSFER_TOPIC = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"


def _hex0x(value: Any) -> str:
    """Normalize bytes/HexBytes/str into a lowercase '0x...' string."""
    if isinstance(value, (bytes, bytearray)):
        return "0x" + value.hex()
    if hasattr(value, "hex") and not isinstance(value, str):
        h = value.hex()
        return h if h.startswith("0x") else "0x" + h
    return str(value)


def _hr(title: str) -> None:
    print(f"\n--- {title} " + "-" * max(1, 60 - len(title)))


def _fail(message: str) -> None:
    print(f"[ERROR] {message}", file=sys.stderr)
    sys.exit(1)


def find_recent_tx_hash(arc: Arc, scan_blocks: int) -> str | None:
    """Scan back from the latest block for the first real transaction found."""
    latest = arc.w3.eth.block_number
    lowest = max(latest - scan_blocks + 1, 0)
    for block_number in range(latest, lowest - 1, -1):
        block = arc.w3.eth.get_block(block_number, full_transactions=True)
        txs = block.get("transactions", [])
        if txs:
            return _hex0x(txs[0]["hash"])
    return None


def decode_usdc_transfer_logs(receipt: dict) -> list[dict]:
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Arc DevKit — Arc Mainnet live demo (read-only, public data only)."
    )
    parser.add_argument(
        "tx_hash",
        nargs="?",
        default=None,
        help="Transaction hash to inspect (0x + 64 hex chars). If omitted, the script "
        "scans recent blocks for one.",
    )
    parser.add_argument(
        "--scan-blocks",
        type=int,
        default=30,
        help="How many recent blocks to scan for a transaction when tx_hash is omitted "
        "(default: 30).",
    )
    parser.add_argument(
        "--rpc-url",
        default=None,
        help="Override the RPC endpoint (still Arc Mainnet's chain ID/contracts). "
        "Defaults to Circle's official https://rpc.mainnet.arc.io.",
    )
    parser.add_argument(
        "--json",
        metavar="PATH",
        default=None,
        help="Also write the full structured results to this JSON file.",
    )
    args = parser.parse_args()

    result: dict[str, Any] = {"generated_at_utc": datetime.now(UTC).isoformat()}

    print("=" * 70)
    print("Arc DevKit — Arc Mainnet Live Demo")
    print("Read-only. Public data only. No wallet, no signing, no .env loaded.")
    print("=" * 70)

    try:
        arc = Arc.mainnet(rpc_url=args.rpc_url)
    except Exception as exc:  # noqa: BLE001
        _fail(f"Could not construct the Arc Mainnet client: {exc}")
        return

    print(f"\nSDK network config : {arc.network.name}")
    print(f"Expected chain ID  : {arc.network.chain_id}")
    print(f"RPC endpoint       : {args.rpc_url or arc.network.rpc_url}")
    print(f"Explorer           : {arc.network.explorer_url}")
    result["network"] = {
        "name": arc.network.name,
        "expected_chain_id": arc.network.chain_id,
        "rpc_url": args.rpc_url or arc.network.rpc_url,
        "explorer_url": arc.network.explorer_url,
    }

    # ------------------------------------------------------------------
    # 1. Health check — reuses arc_devkit.health.run_health_check()
    # ------------------------------------------------------------------
    _hr("1. Health check (arc.health_check())")
    try:
        health = arc.health_check()
    except Exception as exc:  # noqa: BLE001
        _fail(f"RPC unreachable while running health_check(): {exc}")
        return

    for key in (
        "rpc_ok",
        "rpc_chain_id",
        "expected_chain_id",
        "chain_id_match",
        "latency_ms",
        "usdc_contract_ok",
        "explorer_configured",
        "ready",
    ):
        print(f"  {key:20s}: {health[key]}")
    result["health_check"] = health

    if not health["rpc_ok"]:
        _fail(f"RPC not reachable: {health['rpc_error']}")
        return
    if not health["chain_id_match"]:
        _fail(
            "Chain ID mismatch — RPC reported "
            f"{health['rpc_chain_id']}, arc_devkit.networks expects "
            f"{health['expected_chain_id']}. Refusing to continue."
        )
        return
    print("  -> RPC-reported chain ID matches arc_devkit.networks config: CONFIRMED")

    # ------------------------------------------------------------------
    # 2. Latest block — arc.latest_block()
    # ------------------------------------------------------------------
    _hr("2. Latest block (arc.latest_block())")
    try:
        block = arc.latest_block()
    except Exception as exc:  # noqa: BLE001
        _fail(f"Could not fetch the latest block: {exc}")
        return

    block_number = block["number"]
    block_hash = _hex0x(block["hash"])
    block_ts = datetime.fromtimestamp(block["timestamp"], tz=UTC)
    tx_count = len(block.get("transactions", []))
    print(f"  Number    : #{block_number:,}")
    print(f"  Hash      : {block_hash}")
    print(f"  Timestamp : {block_ts.isoformat()} (unix {block['timestamp']})")
    print(f"  Tx count  : {tx_count}")
    result["latest_block"] = {
        "number": block_number,
        "hash": block_hash,
        "timestamp_unix": block["timestamp"],
        "timestamp_utc": block_ts.isoformat(),
        "tx_count": tx_count,
    }

    # ------------------------------------------------------------------
    # 3. Pick a transaction — provided hash, or scan recent blocks
    # ------------------------------------------------------------------
    tx_hash = args.tx_hash
    if tx_hash:
        _hr("3. Using the provided transaction hash")
        print(f"  {tx_hash}")
        result["tx_source"] = "provided"
    else:
        _hr(f"3. Scanning the last {args.scan_blocks} blocks for a confirmed transaction")
        tx_hash = find_recent_tx_hash(arc, args.scan_blocks)
        if not tx_hash:
            _fail(
                f"No transactions found in the last {args.scan_blocks} blocks. "
                "Try a larger --scan-blocks value, or pass a tx hash explicitly."
            )
            return
        print(f"  Found: {tx_hash}")
        result["tx_source"] = f"scanned last {args.scan_blocks} blocks"

    # ------------------------------------------------------------------
    # 4. Transaction details — arc.get_transaction() / get_transaction_receipt()
    # ------------------------------------------------------------------
    _hr("4. Transaction (arc.get_transaction() / get_transaction_receipt())")
    try:
        tx = arc.get_transaction(tx_hash)
        receipt = arc.get_transaction_receipt(tx_hash)
    except Exception as exc:  # noqa: BLE001
        _fail(f"Could not fetch transaction {tx_hash}: {exc}")
        return

    status = "success" if receipt.get("status") == 1 else "reverted"
    value_native = Decimal(str(arc.w3.from_wei(tx.get("value", 0), "ether")))
    gas_cost_native = Decimal(
        str(arc.w3.from_wei(receipt.get("gasUsed", 0) * tx.get("gasPrice", 0), "ether"))
    )
    explorer_link = f"{arc.network.explorer_url}/tx/{tx_hash}"

    print(f"  Hash                              : {tx_hash}")
    print(f"  Status                            : {status}")
    print(f"  Block                             : #{receipt.get('blockNumber'):,}")
    print(f"  From                              : {tx.get('from')}")
    print(f"  To                                : {tx.get('to')}")
    print(f"  Value  (native USDC, {NATIVE_USDC_DECIMALS} decimals) : {value_native} USDC")
    print(f"  Gas used                          : {receipt.get('gasUsed'):,}")
    print(f"  Gas cost (native USDC, {NATIVE_USDC_DECIMALS} decimals): {gas_cost_native} USDC")
    print(f"  Explorer                          : {explorer_link}")

    transfers = decode_usdc_transfer_logs(receipt)
    if transfers:
        print(
            f"\n  Decoded {len(transfers)} USDC ERC-20 Transfer log(s) "
            f"(contract {USDC_ERC20_ADDRESS}, 6 decimals — a separate view of the"
        )
        print("  same underlying USDC balance shown above at 18 decimals natively):")
        for t in transfers:
            print(f"    {t['from']} -> {t['to']}: {t['amount_usdc']} USDC (6 decimals)")
    else:
        print(
            "\n  No USDC ERC-20 Transfer log in this receipt — the native/ERC-20 "
            "decimal split above still applies to any USDC balance on Arc "
            f"(native = 18 decimals, ERC-20 view at {USDC_ERC20_ADDRESS} = 6 decimals)."
        )

    result["transaction"] = {
        "hash": tx_hash,
        "status": status,
        "block": receipt.get("blockNumber"),
        "from": tx.get("from"),
        "to": tx.get("to"),
        "value_native_usdc": str(value_native),
        "gas_used": receipt.get("gasUsed"),
        "gas_cost_native_usdc": str(gas_cost_native),
        "explorer_url": explorer_link,
        "usdc_erc20_transfers_decoded": transfers,
    }

    # ------------------------------------------------------------------
    # 5. Debugger analysis — arc.debug_transaction(tx_hash, use_ai=False)
    # ------------------------------------------------------------------
    _hr("5. Debugger analysis (arc.debug_transaction(tx_hash, use_ai=False))")
    try:
        report = arc.debug_transaction(tx_hash, use_ai=False)
    except Exception as exc:  # noqa: BLE001
        _fail(f"debug_transaction() failed: {exc}")
        return

    print(f"  Network       : {report['network']}")
    print(f"  Status        : {report['status']}")
    print(f"  Cost (USDC)   : {report['custo_usdc']}")
    print(f"  Revert reason : {report['revert_reason']}")
    print(f"  Summary       : {report['summary']}")
    result["debug_transaction"] = report

    print("\n" + "=" * 70)
    print("Done. Every value above was read live from Arc Mainnet via arc-devkit.")
    print(f"Verify independently: {explorer_link}")
    print("=" * 70)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, default=str)
        print(f"\nStructured results written to: {args.json}")


if __name__ == "__main__":
    main()
