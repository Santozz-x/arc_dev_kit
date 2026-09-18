"""Arc — a single-entry-point facade over arc-devkit's existing modules.

This is an additive convenience layer, not a rewrite: every method below
delegates to the same classes/functions already used elsewhere in the SDK
(TxAnalyzer, USDCToken, contracts.loader, core.wallet, health.run_health_check).
Existing per-module imports (`from arc_devkit.debugger import TxAnalyzer`, ...)
keep working unchanged — Arc just gives a simpler starting point:

    from arc_devkit import Arc

    arc = Arc.mainnet()
    balance = arc.get_balance("0x...")          # native USDC gas balance (18 decimals)
    tx = arc.get_transaction("0x...")
    receipt = arc.wait_for_transaction("0x...")
    report = arc.debug_transaction("0x...")
    usdc_balance = arc.usdc.balance("0x...")    # ERC-20 USDC view (6 decimals)
"""

import logging
from decimal import Decimal
from typing import Any

from web3 import Web3
from web3.middleware import ExtraDataToPOAMiddleware

from arc_devkit.networks import NetworkProfile, get_network

logger = logging.getLogger(__name__)


class ArcContract:
    """Thin wrapper returned by Arc.contract() — bound to one address/ABI/w3."""

    def __init__(self, w3: Web3, address: str, abi: list[dict]) -> None:
        self._w3 = w3
        self.address = Web3.to_checksum_address(address)
        self.abi = abi

    def call(self, function_name: str, *args: Any) -> Any:
        """Call a read-only (view/pure) contract function."""
        from arc_devkit.contracts.loader import call_view

        return call_view(self.abi, self.address, function_name, *args, w3=self._w3)

    def send(self, function_name: str, *args: Any, private_key: str, gas: int = 200_000) -> str:
        """Sign and broadcast a state-changing contract call. Returns the tx hash."""
        from arc_devkit.contracts.loader import send_tx

        return send_tx(
            self.abi, self.address, function_name, private_key, *args, gas=gas, w3=self._w3
        )


class Arc:
    """
    Single entry point for reading and interacting with an Arc network.

    Construct via Arc.mainnet() / Arc.testnet() / Arc(network=...) rather than
    directly, unless you're passing a fully custom NetworkProfile.
    """

    def __init__(
        self,
        network: str | NetworkProfile = "mainnet",
        rpc_url: str | None = None,
    ) -> None:
        """
        Args:
            network: "mainnet", "testnet", or a NetworkProfile.
            rpc_url: Override the network's default RPC (e.g. a private/paid
                     provider — Alchemy, QuickNode, self-hosted). Required for
                     networks with no published default RPC.
        """
        self.network: NetworkProfile = (
            network if isinstance(network, NetworkProfile) else get_network(network)
        )
        resolved_rpc = rpc_url or self.network.rpc_url
        if not resolved_rpc:
            raise ValueError(
                f"No RPC URL configured for Arc {self.network.name!r} — pass rpc_url= explicitly."
            )
        self._w3 = Web3(Web3.HTTPProvider(resolved_rpc, request_kwargs={"timeout": 15}))
        self._w3.middleware_onion.inject(ExtraDataToPOAMiddleware, layer=0)
        self._usdc: Any = None

    @classmethod
    def mainnet(cls, rpc_url: str | None = None) -> "Arc":
        """Arc(network="mainnet", rpc_url=rpc_url) — Circle's default RPC unless overridden."""
        return cls(network="mainnet", rpc_url=rpc_url)

    @classmethod
    def testnet(cls, rpc_url: str | None = None) -> "Arc":
        """Arc(network="testnet", rpc_url=rpc_url) — Circle's default RPC unless overridden."""
        return cls(network="testnet", rpc_url=rpc_url)

    @property
    def w3(self) -> Web3:
        """The underlying web3.py instance, for anything this facade doesn't cover."""
        return self._w3

    @property
    def usdc(self) -> Any:
        """A USDCToken bound to this network's connection (ERC-20 view, 6 decimals)."""
        if self._usdc is None:
            from arc_devkit.stablecoins.token import USDCToken

            if not self.network.contracts.usdc:
                raise ValueError(f"No USDC contract address configured for {self.network.name!r}.")
            self._usdc = USDCToken(contract_address=self.network.contracts.usdc, w3=self._w3)
        return self._usdc

    # ------------------------------------------------------------------
    # Reads
    # ------------------------------------------------------------------

    def get_balance(self, address: str) -> Decimal:
        """Native USDC gas balance of `address` (18 decimals — see stablecoins.token module docs)."""
        checksum = Web3.to_checksum_address(address)
        wei = self._w3.eth.get_balance(checksum)
        return Decimal(str(self._w3.from_wei(wei, "ether")))

    def get_transaction(self, tx_hash: str) -> dict:
        """Raw transaction data (eth_getTransactionByHash)."""
        from arc_devkit.core.validation import validate_tx_hash

        return dict(self._w3.eth.get_transaction(validate_tx_hash(tx_hash)))  # type: ignore[arg-type]

    def get_transaction_receipt(self, tx_hash: str) -> dict:
        """Raw transaction receipt (eth_getTransactionReceipt)."""
        from arc_devkit.core.validation import validate_tx_hash

        return dict(self._w3.eth.get_transaction_receipt(validate_tx_hash(tx_hash)))  # type: ignore[arg-type]

    def wait_for_transaction(self, tx_hash: str, timeout: int = 120) -> dict:
        """Block until the transaction is mined (or timeout) and return its receipt."""
        from arc_devkit.core.validation import validate_tx_hash

        receipt = self._w3.eth.wait_for_transaction_receipt(
            validate_tx_hash(tx_hash),  # type: ignore[arg-type]
            timeout=timeout,
        )
        return dict(receipt)

    def latest_block(self) -> dict:
        """The most recent block."""
        return dict(self._w3.eth.get_block("latest"))

    def get_block(self, block_identifier: int | str = "latest") -> dict:
        """A block by number, hash, or tag ("latest", "pending", ...)."""
        return dict(self._w3.eth.get_block(block_identifier))  # type: ignore[arg-type]

    def debug_transaction(
        self, tx_hash: str, abi: list[dict] | None = None, use_ai: bool = True
    ) -> dict:
        """Full diagnosis of a transaction — delegates to debugger.TxAnalyzer."""
        from arc_devkit.debugger.tx_analyzer import TxAnalyzer

        return TxAnalyzer(w3=self._w3).analyze(tx_hash, abi=abi, use_ai=use_ai)

    def contract(self, address: str, abi: list[dict]) -> ArcContract:
        """A contract bound to this connection — contract.call(...) / contract.send(...)."""
        return ArcContract(self._w3, address, abi)

    def health_check(self) -> dict:
        """RPC reachability, chain ID match, latest block, latency, USDC contract presence."""
        from arc_devkit.health import run_health_check

        report = run_health_check(self.network, w3=self._w3)
        return {
            "network": report.network,
            "ready": report.ready,
            "rpc_ok": report.rpc_ok,
            "rpc_error": report.rpc_error,
            "latency_ms": report.latency_ms,
            "expected_chain_id": report.expected_chain_id,
            "rpc_chain_id": report.rpc_chain_id,
            "chain_id_match": report.chain_id_match,
            "latest_block": report.latest_block,
            "usdc_contract_ok": report.usdc_contract_ok,
            "explorer_configured": report.explorer_configured,
        }
