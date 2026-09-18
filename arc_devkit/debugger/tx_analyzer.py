"""Arc transaction analyzer — combines RPC data with Claude AI analysis."""

import logging
from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from web3 import Web3
from web3.types import HexStr, TxParams

from arc_devkit.core.connection import get_web3
from arc_devkit.networks import NETWORKS

logger = logging.getLogger(__name__)


def _network_label(w3: Web3) -> str:
    """Best-effort network name for a chain ID, so reports never confuse mainnet/testnet."""
    try:
        chain_id = w3.eth.chain_id
    except Exception:
        return "unknown"
    for profile in NETWORKS.values():
        if profile.chain_id == chain_id:
            return f"Arc {profile.name.capitalize()}"
    return f"unknown (chain_id={chain_id})"


# Solidity revert selectors
_REVERT_SELECTOR = bytes.fromhex("08c379a0")  # Error(string)
_PANIC_SELECTOR = bytes.fromhex("4e487b71")  # Panic(uint256)

_PANIC_CODES: dict[int, str] = {
    0x00: "Generic compiler-inserted panic",
    0x01: "Assertion failed (assert())",
    0x11: "Arithmetic overflow or underflow",
    0x12: "Division or modulo by zero",
    0x21: "Invalid enum value",
    0x22: "Corrupted storage byte array",
    0x31: "pop() called on empty array",
    0x32: "Array index out of bounds",
    0x41: "Out of memory (new allocation too large)",
    0x51: "Call to zero-initialized function variable",
}

_ANALYSIS_PROMPT = """\
Analyze this Arc blockchain transaction and respond in English.

Transaction data:
{data}

Answer in structured format:
1. **What the transaction did** — describe in plain language
2. **Status** — success or failure, with reason if error
3. **Cost in USDC** — gas consumed converted to USDC
4. **Suggestion** — if error occurred, how to fix it; if success, any possible optimization
"""


# ---------------------------------------------------------------------------
# Revert decoding helpers (module-level, reusable)
# ---------------------------------------------------------------------------


def _extract_revert_bytes(exc: Exception) -> bytes | None:
    """Extract raw revert bytes from a web3 ContractLogicError or similar."""
    # web3 >= 7: ContractLogicError has a .data attribute
    data = getattr(exc, "data", None)
    if data is None:
        args = getattr(exc, "args", ())
        data = args[0] if args else None

    if isinstance(data, str) and data.startswith("0x"):
        try:
            return bytes.fromhex(data[2:])
        except ValueError:
            pass
    if isinstance(data, (bytes, bytearray)):
        return bytes(data)
    return None


def decode_revert_bytes(data: bytes, abi: list[dict] | None = None) -> str:
    """
    Decode raw revert bytes into a human-readable message.

    Handles:
    - Standard ``require(condition, "message")`` → Error(string)
    - Solidity panic codes                       → Panic(uint256)
    - Custom errors from ABI (if provided)
    - Unknown selectors                          → raw hex fallback

    Args:
        data: Raw revert data bytes (without 0x prefix).
        abi: Optional contract ABI to decode custom errors.

    Returns:
        Human-readable revert reason string.
    """
    if len(data) < 4:
        return f"empty revert (data: 0x{data.hex()})" if data else "empty revert"

    selector = data[:4]

    # Standard Error(string)
    if selector == _REVERT_SELECTOR:
        try:
            from eth_abi import decode as abi_decode

            (message,) = abi_decode(["string"], data[4:])
            return f'require failed: "{message}"'
        except Exception:
            pass

    # Panic(uint256)
    if selector == _PANIC_SELECTOR:
        try:
            from eth_abi import decode as abi_decode

            (code,) = abi_decode(["uint256"], data[4:])
            msg = _PANIC_CODES.get(code, f"unknown panic code 0x{code:02x}")
            return f"Panic(0x{code:02x}): {msg}"
        except Exception:
            pass

    # Custom error from ABI
    if abi:
        selector_hex = selector.hex()
        for entry in abi:
            if entry.get("type") != "error":
                continue
            inputs = entry.get("inputs", [])
            fn_sig = f"{entry['name']}({','.join(i['type'] for i in inputs)})"
            entry_selector = Web3.keccak(text=fn_sig)[:4].hex()
            if entry_selector == selector_hex:
                try:
                    from eth_abi import decode as abi_decode

                    types = [i["type"] for i in inputs]
                    if types:
                        args = abi_decode(types, data[4:])
                        args_str = ", ".join(str(a) for a in args)
                        return f"custom error: {entry['name']}({args_str})"
                    return f"custom error: {entry['name']}()"
                except Exception:
                    return f"custom error: {entry['name']} (selector 0x{selector_hex})"

    return f"unknown revert (selector 0x{selector.hex()}, data 0x{data.hex()})"


# ---------------------------------------------------------------------------
# TxAnalyzer
# ---------------------------------------------------------------------------


class TxAnalyzer:
    """
    Analyze Arc transactions: fetches data via RPC and generates AI diagnosis.

    Combines eth_getTransaction + eth_getTransactionReceipt with DevCopilot to
    produce a natural-language analysis report. Optionally decodes revert reasons
    and input calldata when an ABI is provided.

    Example:
        analyzer = TxAnalyzer()
        result = analyzer.analyze("0xTxHash...")

        # With ABI for richer decoding
        abi = load_abi("MyContract.json")
        result = analyzer.analyze("0xTxHash...", abi=abi)

        # Batch analysis
        results = analyzer.analyze_batch(["0xHash1...", "0xHash2..."])
    """

    def __init__(self, w3: Web3 | None = None, rpc_url: str | None = None) -> None:
        if w3:
            self._w3 = w3
        elif rpc_url:
            from web3.middleware import ExtraDataToPOAMiddleware

            _w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 10}))
            _w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
            self._w3 = _w3
        else:
            self._w3 = get_web3()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        tx_hash: str,
        abi: list[dict] | None = None,
        use_ai: bool = True,
    ) -> dict:
        """
        Analyze a transaction and return a complete diagnosis.

        Args:
            tx_hash: Transaction hash (0x... format).
            abi: Optional contract ABI for decoding input data and custom errors.
            use_ai: When False, skip the DevCopilot natural-language summary and
                    return only on-chain data (used by Copilot tools to avoid
                    recursive AI calls).

        Returns:
            Dict with: hash, status, summary, custo_usdc, revert_reason,
            decoded_input, error, and raw_data.

        Raises:
            ValidationError: If tx_hash is not 0x + 64 hex chars.
        """
        from arc_devkit.core.validation import validate_tx_hash

        tx_hash = validate_tx_hash(tx_hash)
        logger.info("Analyzing transaction: %s", tx_hash)

        try:
            tx = self._w3.eth.get_transaction(HexStr(tx_hash))
            receipt = self._w3.eth.get_transaction_receipt(HexStr(tx_hash))
        except Exception as exc:
            logger.error("Error fetching transaction %s: %s", tx_hash, exc)
            return {
                "hash": tx_hash,
                "network": _network_label(self._w3),
                "status": "error",
                "summary": f"Could not fetch transaction: {exc}",
                "custo_usdc": "0",
                "revert_reason": None,
                "decoded_input": None,
                "error": str(exc),
                "suggestion": "Check that the hash is correct and the RPC is reachable.",
                "raw_data": None,
            }

        gas_used = receipt.get("gasUsed", 0)
        gas_price = tx.get("gasPrice", 0)
        cost_wei = gas_used * gas_price
        cost_decimal = Decimal(str(self._w3.from_wei(cost_wei, "ether")))

        status_str = "success" if receipt.get("status") == 1 else "reverted"

        # Revert reason (only for failed txs)
        revert_reason: str | None = None
        if status_str == "reverted":
            revert_reason = self._decode_revert_reason(tx, receipt, abi)
            logger.info("Revert reason for %s: %s", tx_hash[:16], revert_reason)

        # Input decoding (only when ABI is provided)
        decoded_input: dict | None = None
        if abi:
            decoded_input = self._decode_input(tx, abi)

        data_summary = {
            "hash": tx_hash,
            "from": tx.get("from"),
            "to": tx.get("to"),
            "value_wei": str(tx.get("value", 0)),
            "gas_limit": tx.get("gas"),
            "gas_used": gas_used,
            "status": status_str,
            "revert_reason": revert_reason,
            "decoded_input": decoded_input,
            "estimated_cost_usdc": str(cost_decimal),
            "block": receipt.get("blockNumber"),
            "logs_count": len(receipt.get("logs", [])),
        }

        logger.debug("Data collected: %s", data_summary)

        summary = f"Status: {status_str} | Gas used: {gas_used} | Cost: {cost_decimal} USDC"
        if revert_reason:
            summary += f" | Revert: {revert_reason}"

        if use_ai:
            try:
                from arc_devkit.copilot.agent import DevCopilot

                copilot = DevCopilot()
                prompt = _ANALYSIS_PROMPT.format(data=data_summary)
                summary = copilot.ask(prompt)
            except Exception as exc:
                logger.warning("AI analysis unavailable: %s", exc)

        return {
            "hash": tx_hash,
            "network": _network_label(self._w3),
            "status": status_str,
            "summary": summary,
            "custo_usdc": str(cost_decimal),
            "revert_reason": revert_reason,
            "decoded_input": decoded_input,
            "error": None if status_str == "success" else (revert_reason or "Transaction reverted"),
            "suggestion": "",
            "raw_data": data_summary,
        }

    def trace_transaction(self, tx_hash: str, tracer: str = "callTracer") -> dict:
        """
        Fetch an internal-call trace via debug_traceTransaction, if the connected
        RPC supports it.

        Most public RPC endpoints (including Circle's default Arc RPC, on
        both mainnet and testnet) disable the non-standard debug_* namespace — this returns a clear,
        structured "not supported" result instead of raising.

        Args:
            tx_hash: Transaction hash (0x... format).
            tracer: Trace type understood by the node (default "callTracer").

        Returns:
            Dict with hash, supported (bool), trace (raw result or None), and
            error (explanation when unsupported).
        """
        from arc_devkit.core.validation import validate_tx_hash

        tx_hash = validate_tx_hash(tx_hash)
        try:
            result = self._w3.manager.request_blocking(
                "debug_traceTransaction",  # type: ignore[arg-type]
                [tx_hash, {"tracer": tracer}],
            )
            return {"hash": tx_hash, "supported": True, "trace": result, "error": None}
        except Exception as exc:
            logger.info("debug_traceTransaction unavailable for %s: %s", tx_hash[:16], exc)
            return {
                "hash": tx_hash,
                "supported": False,
                "trace": None,
                "error": (
                    f"debug_traceTransaction is not available on this RPC: {exc}. "
                    "Most public endpoints disable the debug_* namespace — try an "
                    "archive node or a self-hosted node with debug APIs enabled."
                ),
            }

    def analyze_batch(
        self,
        tx_hashes: list[str],
        abi: list[dict] | None = None,
        *,
        on_progress: Callable[[int, int, str], None] | None = None,
    ) -> list[dict]:
        """
        Analyze multiple transactions sequentially.

        Args:
            tx_hashes: List of transaction hashes to analyze.
            abi: Optional contract ABI applied to all transactions.
            on_progress: Optional callback(current, total, tx_hash) for progress updates.

        Returns:
            List of analysis dicts in the same order as tx_hashes.
        """
        results: list[dict] = []
        total = len(tx_hashes)

        for i, tx_hash in enumerate(tx_hashes, start=1):
            if on_progress:
                on_progress(i, total, tx_hash)
            result = self.analyze(tx_hash.strip(), abi=abi)
            results.append(result)

        logger.info("Batch analysis complete: %d transactions", total)
        return results

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _decode_revert_reason(
        self,
        tx: Any,
        receipt: Any,
        abi: list[dict] | None,
    ) -> str | None:
        """Replay the failed call with eth_call to extract the revert reason."""
        try:
            call_params = {
                "from": tx.get("from"),
                "to": tx.get("to"),
                "data": tx.get("input", "0x"),
                "value": tx.get("value", 0),
            }
            block_number = receipt.get("blockNumber")

            try:
                self._w3.eth.call(cast(TxParams, call_params), block_number)
                # If call succeeds, state changed between tx and replay — no reason
                return "Transaction reverted (state-dependent; reason unavailable on replay)"
            except Exception as exc:
                revert_bytes = _extract_revert_bytes(exc)
                if revert_bytes:
                    return decode_revert_bytes(revert_bytes, abi)
                # Fallback: try to extract from exception message
                msg = str(exc)
                if "execution reverted" in msg.lower():
                    return msg
                return f"reverted (could not decode reason: {msg})"

        except Exception as exc:
            logger.debug("_decode_revert_reason failed: %s", exc)
            return None

    def _decode_input(self, tx: Any, abi: list[dict]) -> dict | None:
        """Decode transaction input calldata using the provided ABI."""
        input_data = tx.get("input") or tx.get("data", "0x")
        if not input_data or input_data in ("0x", b""):
            return None  # plain ETH transfer — no calldata

        try:
            to_addr = tx.get("to")
            if not to_addr:
                return None

            contract = self._w3.eth.contract(
                address=Web3.to_checksum_address(to_addr),
                abi=abi,
            )
            fn_obj, fn_args = contract.decode_function_input(input_data)

            # Normalize non-JSON-serializable values
            normalized: dict = {}
            for k, v in fn_args.items():
                if isinstance(v, bytes):
                    normalized[k] = "0x" + v.hex()
                elif isinstance(v, int):
                    normalized[k] = str(v)
                elif isinstance(v, (list, tuple)):
                    normalized[k] = [
                        (
                            "0x" + x.hex()
                            if isinstance(x, bytes)
                            else str(x)
                            if isinstance(x, int)
                            else x
                        )
                        for x in v
                    ]
                else:
                    normalized[k] = v

            return {"function": fn_obj.fn_name, "args": normalized}

        except Exception as exc:
            logger.debug("_decode_input failed: %s", exc)
            return None
