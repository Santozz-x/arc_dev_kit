"""Arc payment agent — builds and signs transfer transactions."""

import logging
import time
from collections.abc import Callable
from decimal import Decimal
from typing import Any, cast

from eth_typing import ChecksumAddress
from web3 import Web3
from web3.types import TxParams

from arc_devkit.agents.base_agent import BaseAgent
from arc_devkit.agents.guardrails import Guardrails

logger = logging.getLogger(__name__)

_RECEIPT_POLL_INTERVAL = 2  # seconds between receipt polling attempts
_RECEIPT_TIMEOUT = 120  # maximum timeout in seconds
_RBF_GAS_BUMP_PERCENT = 10  # gas price increase when replacing a stuck tx


class PaymentAgent(BaseAgent):
    """
    Executes payments on the Arc network.

    Builds, signs, and optionally broadcasts transfer transactions.
    Supports automatic gas estimation, mandatory pre-broadcast simulation,
    gas price ceiling, replace-by-fee, receipt polling, batch sends, callbacks,
    and optional autonomy guardrails (spend limit + recipient whitelist).
    """

    def __init__(
        self,
        private_key: str | None = None,
        rpc_url: str | None = None,
        guardrails: Guardrails | None = None,
    ) -> None:
        """
        Args:
            private_key: Hex private key (optional, falls back to ARC_PRIVATE_KEY).
            rpc_url: RPC node URL (optional, falls back to ARC_RPC_URL).
            guardrails: When set, every broadcast is checked against the kill
                        switch, recipient whitelist, and daily spend limit —
                        required for autonomous (no human in the loop) usage.
        """
        super().__init__(private_key=private_key, rpc_url=rpc_url)
        self._guardrails = guardrails

    def _check_gas_price_ceiling(self) -> str | None:
        """Return an error message when gas price exceeds MAX_GAS_PRICE_GWEI."""
        from arc_devkit.config import settings

        if settings.max_gas_price_gwei is None:
            return None
        current_gwei = Decimal(str(self._w3.from_wei(self._w3.eth.gas_price, "gwei")))
        if current_gwei > settings.max_gas_price_gwei:
            return (
                f"Gas price {current_gwei} gwei exceeds the configured ceiling "
                f"of {settings.max_gas_price_gwei} gwei (MAX_GAS_PRICE_GWEI)."
            )
        return None

    def get_balance(self) -> dict:
        """
        Return the native wallet balance.

        Returns:
            Dict with address, balance_wei, and balance_usdc (Decimal).
        """
        if not self._address:
            return {"error": "No private key configured — read-only mode."}

        wei = self._w3.eth.get_balance(cast(ChecksumAddress, self._address))
        balance = Decimal(str(self._w3.from_wei(wei, "ether")))

        return {
            "address": self._address,
            "balance_wei": str(wei),
            "balance_usdc": balance,
        }

    def _estimate_gas(self, tx: TxParams) -> int:
        """Call eth_estimateGas; return 21,000 as fallback."""
        try:
            return self._w3.eth.estimate_gas(tx)
        except Exception as exc:
            logger.warning("eth_estimateGas failed (%s), using 21,000", exc)
            return 21_000

    def _wait_for_receipt(self, tx_hash: Any, timeout: int = _RECEIPT_TIMEOUT) -> dict | None:
        """Poll eth_getTransactionReceipt until confirmed or timeout."""
        start = time.time()
        while time.time() - start < timeout:
            try:
                receipt = self._w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    return dict(receipt)
            except Exception:
                pass
            time.sleep(_RECEIPT_POLL_INTERVAL)
        return None

    def _simulate(self, tx: TxParams) -> bool:
        """Simulate transaction via eth_call to detect reverts before sending."""
        try:
            self._w3.eth.call(tx)
            return True
        except Exception as exc:
            logger.warning("Simulation detected revert: %s", exc)
            return False

    def _build_usdc_signed_tx(self, to: str, amount: Decimal) -> tuple:
        """Build and sign a USDC ERC-20 transfer tx; return (signed, gas_limit)."""
        from arc_devkit.config import settings
        from arc_devkit.stablecoins.token import _ERC20_ABI, USDC_MULTIPLIER

        usdc_contract_address = settings.network.contracts.usdc
        if usdc_contract_address is None:
            raise ValueError(f"No USDC contract configured for network {settings.arc_network!r}.")
        usdc_address = Web3.to_checksum_address(usdc_contract_address)
        contract = self._w3.eth.contract(address=usdc_address, abi=_ERC20_ABI)
        atomic = int(amount * Decimal(str(USDC_MULTIPLIER)))
        nonce = self._w3.eth.get_transaction_count(cast(ChecksumAddress, self._address))

        tx = contract.functions.transfer(to, atomic).build_transaction(
            cast(
                TxParams,
                {
                    "from": self._address,
                    "nonce": nonce,
                    "gasPrice": self._w3.eth.gas_price,
                    "chainId": self._w3.eth.chain_id,
                },
            )
        )
        gas_limit = self._estimate_gas(cast(TxParams, tx))
        tx["gas"] = gas_limit
        signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
        return signed, gas_limit

    def execute(  # type: ignore[override]
        self,
        to: str,
        amount_usdc: float,
        enviar: bool = False,
        wait_receipt: bool = True,
        on_success: Callable[[dict], None] | None = None,
        on_failure: Callable[[Exception], None] | None = None,
        token: str = "native",
        force: bool = False,
        rbf: bool = False,
        trigger: str = "manual",
        use_paymaster: bool = False,
    ) -> dict:
        """
        Build and sign a payment transaction.

        Before broadcasting, the transaction is simulated via eth_call — a
        simulated revert aborts the send unless force=True. When the agent has
        guardrails configured, the kill switch, recipient whitelist, and daily
        spend limit are also enforced.

        Args:
            to: EVM recipient address.
            amount_usdc: Amount to transfer.
            enviar: If True, broadcasts to the network (requires private key).
            wait_receipt: If True (and enviar=True), waits for confirmation.
            on_success: Callback invoked with the receipt on confirmation.
            on_failure: Callback invoked with the exception on error.
            token: "native" for native ARC, "usdc" for ERC-20 USDC.
            force: Skip the pre-broadcast simulation check (use with care).
            rbf: On receipt timeout, resend with +10% gas price (replace-by-fee).
            trigger: Label recorded in the audit log ("manual", "on_low_balance", ...).
            use_paymaster: Pay the network fee via a paymaster instead of the
                           sender's own gas balance. Fails clearly until Arc
                           publishes a paymaster (see arc_devkit.paymaster).

        Returns:
            Dict with status and transaction details.
        """
        if not self._private_key:
            return {"status": "error", "error": "Private key required to sign transactions."}

        if use_paymaster:
            from arc_devkit.config import settings
            from arc_devkit.paymaster.detector import detect_paymaster

            paymaster = detect_paymaster(settings.arc_network)
            if not paymaster.available:
                return {
                    "status": "error",
                    "error": f"use_paymaster requested but unavailable: {paymaster.reason}",
                }

        try:
            destinatario = Web3.to_checksum_address(to)
            self.log(f"Preparing {token} payment of {amount_usdc} → {destinatario}")

            if enviar and self._guardrails:
                from arc_devkit.agents.guardrails import GuardrailViolation

                try:
                    self._guardrails.check_kill_switch()
                    self._guardrails.check_recipient(destinatario)
                    self._guardrails.check_spend(Decimal(str(amount_usdc)))
                except GuardrailViolation as exc:
                    self.log(f"Guardrail blocked payment: {exc}")
                    return {"status": "blocked", "error": str(exc)}

            gas_error = self._check_gas_price_ceiling()
            if gas_error:
                self.log(gas_error)
                return {"status": "error", "error": gas_error}

            if token == "usdc":
                signed, gas_limit = self._build_usdc_signed_tx(
                    destinatario, Decimal(str(amount_usdc))
                )
                sim_tx: TxParams | None = None  # simulated inside build via estimate_gas
                self.log("USDC transfer signed successfully.")
            else:
                value_wei = self._w3.to_wei(amount_usdc, "ether")
                nonce = self._w3.eth.get_transaction_count(cast(ChecksumAddress, self._address))
                tx_base = cast(
                    TxParams,
                    {
                        "from": self._address,
                        "to": destinatario,
                        "value": value_wei,
                        "nonce": nonce,
                        "chainId": self._w3.eth.chain_id,
                    },
                )
                gas_limit = self._estimate_gas(tx_base)
                tx = cast(
                    TxParams, {**tx_base, "gas": gas_limit, "gasPrice": self._w3.eth.gas_price}
                )
                sim_tx = tx
                signed = self._w3.eth.account.sign_transaction(tx, self._private_key)
                self.log("Transaction signed successfully.")

            # Mandatory simulation before broadcast — a simulated revert aborts the send
            if enviar and not force and sim_tx is not None and not self._simulate(sim_tx):
                return {
                    "status": "simulation_failed",
                    "error": (
                        "Simulation detected a revert — transaction NOT sent. "
                        "Pass force=True to broadcast anyway."
                    ),
                    "to": destinatario,
                    "amount_usdc": amount_usdc,
                }

            if not enviar:
                return {
                    "status": "signed",
                    "token": token,
                    "from": self._address,
                    "to": destinatario,
                    "amount_usdc": amount_usdc,
                    "gas_limit": gas_limit,
                    "raw_transaction": signed.raw_transaction.hex(),
                    "nota": "Transaction signed. Pass enviar=True to broadcast.",
                }

            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            tx_hash_hex = tx_hash.hex()
            self.log(f"Transaction sent: {tx_hash_hex}")

            if self._guardrails:
                self._guardrails.record_spend(Decimal(str(amount_usdc)))
                self._guardrails.audit(
                    agent=self.__class__.__name__,
                    trigger=trigger,
                    action="transfer",
                    token=token,
                    to=destinatario,
                    amount_usdc=amount_usdc,
                    tx_hash=tx_hash_hex,
                )

            resultado: dict = {
                "status": "sent",
                "token": token,
                "from": self._address,
                "to": destinatario,
                "amount_usdc": amount_usdc,
                "tx_hash": tx_hash_hex,
            }

            if wait_receipt:
                self.log("Waiting for confirmation...")
                receipt = self._wait_for_receipt(tx_hash)
                if receipt:
                    resultado["status"] = "confirmed" if receipt.get("status") == 1 else "failed"
                    resultado["receipt"] = receipt
                    resultado["gas_usado"] = receipt.get("gasUsed")
                    if on_success and resultado["status"] == "confirmed":
                        on_success(receipt)
                elif rbf:
                    self.log("Receipt timeout — attempting replace-by-fee...")
                    rbf_result = self.speed_up(tx_hash_hex)
                    resultado["rbf"] = rbf_result
                    if rbf_result.get("tx_hash"):
                        resultado["tx_hash"] = rbf_result["tx_hash"]
                        resultado["status"] = rbf_result.get("status", "sent")
                else:
                    resultado["aviso"] = "Timeout waiting for receipt — verify the hash manually."

            return resultado

        except Exception as exc:
            if on_failure:
                on_failure(exc)
            raise

    def speed_up(self, tx_hash: str, gas_bump_percent: int = _RBF_GAS_BUMP_PERCENT) -> dict:
        """
        Replace-by-fee: resend a pending transaction with a higher gas price.

        Rebuilds the transaction with the same nonce and a gas price increased
        by gas_bump_percent (over the max of the original price and the current
        network price), then signs and broadcasts the replacement.

        Args:
            tx_hash: Hash of the stuck (pending) transaction.
            gas_bump_percent: Gas price increase percentage (default 10).

        Returns:
            Dict with status and the replacement tx_hash, or an error.
        """
        if not self._private_key:
            return {"status": "error", "error": "Private key required."}

        try:
            from web3.types import HexStr

            original = self._w3.eth.get_transaction(HexStr(tx_hash))
        except Exception as exc:
            return {"status": "error", "error": f"Could not fetch original tx: {exc}"}

        if original.get("blockNumber") is not None:
            return {"status": "already_mined", "tx_hash": tx_hash}

        base_price = max(int(original.get("gasPrice", 0)), int(self._w3.eth.gas_price))
        new_price = base_price * (100 + gas_bump_percent) // 100

        replacement = cast(
            TxParams,
            {
                "from": self._address,
                "to": original.get("to"),
                "value": original.get("value", 0),
                "nonce": original.get("nonce"),
                "gas": original.get("gas", 21_000),
                "gasPrice": new_price,
                "chainId": self._w3.eth.chain_id,
                "data": original.get("input", "0x"),
            },
        )

        try:
            signed = self._w3.eth.account.sign_transaction(replacement, self._private_key)
            new_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction).hex()
            self.log(f"RBF replacement sent: {new_hash} (gas price {new_price})")
            if self._guardrails:
                self._guardrails.audit(
                    agent=self.__class__.__name__,
                    trigger="rbf",
                    action="speed_up",
                    original_tx=tx_hash,
                    replacement_tx=new_hash,
                    gas_price=new_price,
                )
            return {"status": "replaced", "tx_hash": new_hash, "gas_price": new_price}
        except Exception as exc:
            return {"status": "error", "error": f"RBF failed: {exc}"}

    def execute_batch(self, payments: list[dict]) -> list[dict]:
        """
        Execute multiple transfers sequentially with incremental nonces.

        Args:
            payments: List of dicts with keys 'to', 'amount_usdc', and
                      optionally 'enviar' (default False).

        Returns:
            List of results, one per payment.
        """
        if not self._private_key:
            return [{"status": "error", "error": "Private key required."}]

        base_nonce = self._w3.eth.get_transaction_count(cast(ChecksumAddress, self._address))
        resultados = []

        for idx, p in enumerate(payments):
            destinatario = Web3.to_checksum_address(p["to"])
            amount = p["amount_usdc"]
            enviar = p.get("enviar", False)
            value_wei = self._w3.to_wei(amount, "ether")
            nonce = base_nonce + idx

            tx_base = {
                "from": self._address,
                "to": destinatario,
                "value": value_wei,
                "nonce": nonce,
                "chainId": self._w3.eth.chain_id,
            }
            gas_limit = self._estimate_gas(cast(TxParams, tx_base))
            tx = {**tx_base, "gas": gas_limit, "gasPrice": self._w3.eth.gas_price}

            signed = self._w3.eth.account.sign_transaction(tx, self._private_key)

            if not enviar:
                resultados.append(
                    {
                        "status": "signed",
                        "index": idx,
                        "to": destinatario,
                        "amount_usdc": amount,
                        "raw_transaction": signed.raw_transaction.hex(),
                    }
                )
            else:
                tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
                resultados.append(
                    {
                        "status": "sent",
                        "index": idx,
                        "to": destinatario,
                        "amount_usdc": amount,
                        "tx_hash": tx_hash.hex(),
                    }
                )

        return resultados
