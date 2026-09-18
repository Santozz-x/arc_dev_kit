"""CCTP (Cross-Chain Transfer Protocol) bridge: burn → attestation → mint.

Arc is assigned CCTP domain 26, and Circle has published TokenMessengerV2 /
MessageTransmitterV2 / TokenMinterV2 / MessageV2 addresses for both networks
(see arc_devkit.networks — contracts.cctp_token_messenger etc., sourced from
docs.arc.io/arc/references/contract-addresses, verified 2026-09-18).

The ABI below targets CCTP V2's depositForBurn signature (TokenMessengerV2),
which differs from V1 by adding destinationCaller/maxFee/minFinalityThreshold
parameters. destinationCaller defaults to the zero bytes32 (anyone may call
receiveMessage on the destination), maxFee defaults to 0, and
minFinalityThreshold defaults to 2000 (CCTP V2 "standard" finality — pass
1000 for "fast" finality if the destination domain supports it).

IMPORTANT — NOT VALIDATED: this V2 signature matches Circle's publicly
documented CCTP V2 interface (developers.circle.com), but has NOT been
exercised against a live Arc CCTP V2 contract from this SDK. Test
start_transfer()/mint() end-to-end on Arc Testnet with small amounts before
relying on this against real mainnet funds.

KNOWN ISSUE — attestation API: Circle's public Iris API
(https://iris-api.circle.com mainnet, https://iris-api-sandbox.circle.com
sandbox/testnet) is the standard CCTP attestation endpoint, but as of
2026-09-18 there is an open, unresolved public report that it does not
return attestations for Arc Testnet's domain 26:
https://github.com/circlefin/evm-cctp-contracts/issues/110 — verify current
status before relying on fetch_attestation() in production. No default is
set for CCTP_ATTESTATION_API_URL precisely to avoid masking this.
"""

import logging
import time
import uuid
from decimal import Decimal

import httpx
from web3 import Web3

from arc_devkit.agents.guardrails import Guardrails, GuardrailViolation
from arc_devkit.bridge.models import BridgeStatus, BridgeTransfer
from arc_devkit.bridge.store import save_transfer
from arc_devkit.networks import NetworkProfile, get_network

logger = logging.getLogger(__name__)

_RECEIPT_POLL_INTERVAL = 2
_RECEIPT_TIMEOUT = 120
_ATTESTATION_POLL_INTERVAL = 5
_ATTESTATION_TIMEOUT = 300

# CCTP V2 depositForBurn defaults: "standard" finality (~13-19 min on most
# chains; pass 1000 for "fast" finality where the destination domain
# supports it), no destination-caller restriction, no max fee cap.
CCTP_STANDARD_FINALITY_THRESHOLD = 2000
CCTP_FAST_FINALITY_THRESHOLD = 1000
_ZERO_BYTES32 = b"\x00" * 32

# Minimal ABI for Circle's CCTP TokenMessenger + MessageTransmitter (public,
# chain-agnostic standard — see github.com/circlefin/evm-cctp-contracts).
_TOKEN_MESSENGER_ABI = [
    {
        "inputs": [
            {"name": "amount", "type": "uint256"},
            {"name": "destinationDomain", "type": "uint32"},
            {"name": "mintRecipient", "type": "bytes32"},
            {"name": "burnToken", "type": "address"},
            {"name": "destinationCaller", "type": "bytes32"},
            {"name": "maxFee", "type": "uint256"},
            {"name": "minFinalityThreshold", "type": "uint32"},
        ],
        "name": "depositForBurn",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "anonymous": False,
        "inputs": [{"indexed": False, "name": "message", "type": "bytes"}],
        "name": "MessageSent",
        "type": "event",
    },
]

_MESSAGE_TRANSMITTER_ABI = [
    {
        "inputs": [
            {"name": "message", "type": "bytes"},
            {"name": "attestation", "type": "bytes"},
        ],
        "name": "receiveMessage",
        "outputs": [{"name": "success", "type": "bool"}],
        "stateMutability": "nonpayable",
        "type": "function",
    },
]


class CCTPBridge:
    """Burns USDC on Arc and mints on a destination EVM chain via CCTP."""

    def __init__(
        self,
        w3: Web3,
        network: str | NetworkProfile = "testnet",
        attestation_api_url: str | None = None,
        guardrails: Guardrails | None = None,
    ) -> None:
        profile = network if isinstance(network, NetworkProfile) else get_network(network)
        if profile.contracts.cctp_token_messenger is None:
            raise ValueError(
                f"No CCTP TokenMessenger address published for Arc {profile.name!r} yet "
                "(see arc_devkit.networks.NETWORKS) — bridging is unavailable until "
                "Arc/Circle publish it."
            )

        from arc_devkit.config import settings

        self._w3 = w3
        self._profile = profile
        self._guardrails = guardrails
        self._attestation_api_url = attestation_api_url or settings.cctp_attestation_api_url

        self._token_messenger = w3.eth.contract(
            address=Web3.to_checksum_address(profile.contracts.cctp_token_messenger),
            abi=_TOKEN_MESSENGER_ABI,
        )

    def _wait_for_receipt(self, tx_hash) -> dict | None:
        start = time.time()
        while time.time() - start < _RECEIPT_TIMEOUT:
            try:
                receipt = self._w3.eth.get_transaction_receipt(tx_hash)
                if receipt is not None:
                    return dict(receipt)
            except Exception:
                pass
            time.sleep(_RECEIPT_POLL_INTERVAL)
        return None

    def start_transfer(
        self,
        amount_usdc: Decimal,
        recipient: str,
        destination_domain: int,
        dest_chain_id: int,
        private_key: str,
        max_fee_usdc: Decimal = Decimal("0"),
        min_finality_threshold: int = CCTP_STANDARD_FINALITY_THRESHOLD,
        destination_caller: bytes = _ZERO_BYTES32,
    ) -> BridgeTransfer:
        """
        Burn USDC on Arc to start a CCTP V2 cross-chain transfer.

        Args:
            amount_usdc: Amount to bridge.
            recipient: Recipient address on the destination chain.
            destination_domain: CCTP domain id of the destination chain
                                 (Circle-assigned — see developers.circle.com;
                                 not looked up automatically).
            dest_chain_id: EVM chain id of the destination chain (for the record).
            private_key: Sender's Arc private key.
            max_fee_usdc: Maximum fee the sender is willing to pay for a fast
                          transfer (0 = standard finality only, no fee cap needed).
            min_finality_threshold: CCTP_STANDARD_FINALITY_THRESHOLD (default)
                                     or CCTP_FAST_FINALITY_THRESHOLD.
            destination_caller: Restrict who may call receiveMessage() on the
                                 destination (zero bytes32 = anyone may call it).

        Returns:
            BridgeTransfer with status BURNED (success) or FAILED.
        """
        from eth_account import Account

        from arc_devkit.core.validation import validate_address
        from arc_devkit.stablecoins.token import USDC_MULTIPLIER

        sender = Account.from_key(private_key).address
        try:
            recipient_cs = validate_address(recipient)
        except Exception as exc:
            transfer = BridgeTransfer(
                id=str(uuid.uuid4()),
                source_chain_id=self._w3.eth.chain_id,
                dest_chain_id=dest_chain_id,
                sender=sender,
                recipient=recipient,
                amount_usdc=amount_usdc,
                status=BridgeStatus.FAILED,
                error=str(exc),
            )
            save_transfer(transfer)
            return transfer

        transfer = BridgeTransfer(
            id=str(uuid.uuid4()),
            source_chain_id=self._w3.eth.chain_id,
            dest_chain_id=dest_chain_id,
            sender=sender,
            recipient=recipient_cs,
            amount_usdc=amount_usdc,
        )

        if self._guardrails:
            try:
                self._guardrails.check_kill_switch()
                self._guardrails.check_recipient(recipient_cs)
                self._guardrails.check_spend(amount_usdc)
            except GuardrailViolation as exc:
                transfer.status = BridgeStatus.FAILED
                transfer.error = f"Guardrail blocked bridge transfer: {exc}"
                save_transfer(transfer)
                return transfer

        try:
            if self._profile.contracts.usdc is None:
                raise ValueError(f"No USDC contract configured for network {self._profile.name!r}.")
            atomic = int(amount_usdc * USDC_MULTIPLIER)
            max_fee_atomic = int(max_fee_usdc * USDC_MULTIPLIER)
            mint_recipient = Web3.to_bytes(hexstr=recipient_cs).rjust(32, b"\x00")
            burn_token = Web3.to_checksum_address(self._profile.contracts.usdc)

            tx = self._token_messenger.functions.depositForBurn(
                atomic,
                destination_domain,
                mint_recipient,
                burn_token,
                destination_caller,
                max_fee_atomic,
                min_finality_threshold,
            ).build_transaction(
                {
                    "from": sender,
                    "nonce": self._w3.eth.get_transaction_count(sender),
                    "gas": 200_000,
                    "gasPrice": self._w3.eth.gas_price,
                    "chainId": self._w3.eth.chain_id,
                }
            )
            signed = self._w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = self._w3.eth.send_raw_transaction(signed.raw_transaction)
            transfer.burn_tx_hash = tx_hash.hex()

            receipt = self._wait_for_receipt(tx_hash)
            if not receipt or receipt.get("status") != 1:
                transfer.status = BridgeStatus.FAILED
                transfer.error = "Burn transaction failed or timed out."
                save_transfer(transfer)
                return transfer

            logs = self._token_messenger.events.MessageSent().process_receipt(receipt)
            if logs:
                message_bytes = logs[0]["args"]["message"]
                transfer.message_bytes = "0x" + message_bytes.hex()
                transfer.message_hash = Web3.keccak(message_bytes).hex()

            transfer.status = BridgeStatus.BURNED

            if self._guardrails:
                self._guardrails.record_spend(amount_usdc)
                self._guardrails.audit(
                    agent="CCTPBridge",
                    trigger="manual",
                    action="bridge_burn",
                    to=recipient_cs,
                    amount_usdc=str(amount_usdc),
                    tx_hash=transfer.burn_tx_hash,
                )
        except Exception as exc:
            transfer.status = BridgeStatus.FAILED
            transfer.error = str(exc)

        save_transfer(transfer)
        return transfer

    def fetch_attestation(self, transfer: BridgeTransfer) -> BridgeTransfer:
        """Poll Circle's attestation API for the burn message's attestation."""
        if not self._attestation_api_url:
            transfer.status = BridgeStatus.FAILED
            transfer.error = (
                "No CCTP attestation API URL configured (set CCTP_ATTESTATION_API_URL) — "
                "Circle's endpoint for Arc isn't published yet."
            )
            save_transfer(transfer)
            return transfer

        if not transfer.message_hash:
            transfer.status = BridgeStatus.FAILED
            transfer.error = "No message hash available — the burn transaction did not confirm."
            save_transfer(transfer)
            return transfer

        transfer.status = BridgeStatus.PENDING_ATTESTATION
        save_transfer(transfer)

        deadline = time.time() + _ATTESTATION_TIMEOUT
        url = f"{self._attestation_api_url.rstrip('/')}/attestations/{transfer.message_hash}"
        while time.time() < deadline:
            try:
                resp = httpx.get(url, timeout=10.0)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("status") == "complete":
                        transfer.attestation = data.get("attestation")
                        transfer.status = BridgeStatus.ATTESTED
                        save_transfer(transfer)
                        return transfer
            except Exception as exc:
                logger.debug("Attestation poll failed: %s", exc)
            time.sleep(_ATTESTATION_POLL_INTERVAL)

        transfer.status = BridgeStatus.FAILED
        transfer.error = "Attestation polling timed out."
        save_transfer(transfer)
        return transfer

    def mint(
        self,
        transfer: BridgeTransfer,
        dest_w3: Web3,
        message_transmitter_address: str,
        private_key: str,
    ) -> BridgeTransfer:
        """Complete the transfer by calling receiveMessage on the destination chain."""
        if transfer.status != BridgeStatus.ATTESTED or not transfer.attestation:
            transfer.status = BridgeStatus.FAILED
            transfer.error = "Cannot mint before the transfer is attested."
            save_transfer(transfer)
            return transfer

        from eth_account import Account

        from arc_devkit.core.validation import validate_address

        try:
            transmitter_address = validate_address(message_transmitter_address)
        except Exception as exc:
            transfer.status = BridgeStatus.FAILED
            transfer.error = str(exc)
            save_transfer(transfer)
            return transfer

        sender = Account.from_key(private_key).address
        contract = dest_w3.eth.contract(
            address=transmitter_address,
            abi=_MESSAGE_TRANSMITTER_ABI,
        )

        transfer.status = BridgeStatus.PENDING_MINT
        save_transfer(transfer)

        try:
            message = bytes.fromhex(transfer.message_bytes.removeprefix("0x"))
            attestation = bytes.fromhex(transfer.attestation.removeprefix("0x"))

            tx = contract.functions.receiveMessage(message, attestation).build_transaction(
                {
                    "from": sender,
                    "nonce": dest_w3.eth.get_transaction_count(sender),
                    "gas": 200_000,
                    "gasPrice": dest_w3.eth.gas_price,
                    "chainId": dest_w3.eth.chain_id,
                }
            )
            signed = dest_w3.eth.account.sign_transaction(tx, private_key)
            tx_hash = dest_w3.eth.send_raw_transaction(signed.raw_transaction)
            transfer.mint_tx_hash = tx_hash.hex()
            transfer.status = BridgeStatus.COMPLETE
        except Exception as exc:
            transfer.status = BridgeStatus.FAILED
            transfer.error = str(exc)

        save_transfer(transfer)
        return transfer

    def resume(
        self,
        transfer: BridgeTransfer,
        dest_w3: Web3 | None = None,
        message_transmitter_address: str | None = None,
        private_key: str | None = None,
    ) -> BridgeTransfer:
        """
        Resume a transfer from its last known status — the error-recovery entrypoint.

        BURNED → fetch_attestation(); ATTESTED → mint() (requires destination
        chain args); anything else (COMPLETE/FAILED/pending burn) is returned
        unchanged.
        """
        if transfer.status == BridgeStatus.BURNED:
            return self.fetch_attestation(transfer)
        if transfer.status == BridgeStatus.ATTESTED:
            if not (dest_w3 is not None and message_transmitter_address and private_key):
                transfer.error = (
                    "Resuming from ATTESTED requires dest_w3, "
                    "message_transmitter_address, and private_key."
                )
                save_transfer(transfer)
                return transfer
            return self.mint(transfer, dest_w3, message_transmitter_address, private_key)
        return transfer
