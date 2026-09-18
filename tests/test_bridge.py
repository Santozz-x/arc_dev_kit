"""Unit tests for arc_devkit.bridge (CCTP burn → attestation → mint)."""

from decimal import Decimal
from unittest.mock import MagicMock, patch

import pytest

from arc_devkit.bridge.models import BridgeStatus, BridgeTransfer
from arc_devkit.networks import ContractAddresses, NetworkProfile

_FAKE_PROFILE = NetworkProfile(
    name="test-fake",
    chain_id=999,
    rpc_url="https://fake.example.com",
    explorer_url=None,
    contracts=ContractAddresses(
        usdc="0x" + "1" * 40,
        eurc=None,
        cctp_token_messenger="0x" + "2" * 40,
        gateway=None,
    ),
)

_PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_SENDER = "0x" + "a" * 40
_RECIPIENT = "0x" + "b" * 40


# ---------------------------------------------------------------------------
# BridgeTransfer model
# ---------------------------------------------------------------------------


class TestBridgeTransferModel:
    def test_round_trip_to_dict_from_dict(self):
        transfer = BridgeTransfer(
            id="abc",
            source_chain_id=1,
            dest_chain_id=2,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("10.5"),
        )
        restored = BridgeTransfer.from_dict(transfer.to_dict())
        assert restored.id == transfer.id
        assert restored.amount_usdc == Decimal("10.5")
        assert restored.status == BridgeStatus.PENDING_BURN


# ---------------------------------------------------------------------------
# store.py
# ---------------------------------------------------------------------------


class TestBridgeStore:
    def test_save_and_load_transfer(self, tmp_path):
        from arc_devkit.bridge.store import load_transfer, save_transfer

        transfer = BridgeTransfer(
            id="xyz",
            source_chain_id=1,
            dest_chain_id=2,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("5"),
        )
        save_transfer(transfer, store_dir=tmp_path)
        loaded = load_transfer("xyz", store_dir=tmp_path)
        assert loaded is not None
        assert loaded.amount_usdc == Decimal("5")

    def test_load_missing_transfer_returns_none(self, tmp_path):
        from arc_devkit.bridge.store import load_transfer

        assert load_transfer("nope", store_dir=tmp_path) is None

    def test_list_transfers(self, tmp_path):
        from arc_devkit.bridge.store import list_transfers, save_transfer

        for i in range(3):
            save_transfer(
                BridgeTransfer(
                    id=f"id-{i}",
                    source_chain_id=1,
                    dest_chain_id=2,
                    sender=_SENDER,
                    recipient=_RECIPIENT,
                    amount_usdc=Decimal("1"),
                ),
                store_dir=tmp_path,
            )
        transfers = list_transfers(store_dir=tmp_path)
        assert len(transfers) == 3


# ---------------------------------------------------------------------------
# CCTPBridge construction
# ---------------------------------------------------------------------------


_UNPUBLISHED_PROFILE = NetworkProfile(
    name="unpublished-fake",
    chain_id=999,
    rpc_url="https://fake.example.com",
    explorer_url=None,
    contracts=ContractAddresses(usdc=None, eurc=None, cctp_token_messenger=None),
)


class TestCCTPBridgeConstruction:
    def test_raises_when_no_token_messenger_published(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        with pytest.raises(ValueError, match="No CCTP TokenMessenger"):
            CCTPBridge(w3=MagicMock(), network=_UNPUBLISHED_PROFILE)

    def test_constructs_with_fake_profile(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        assert bridge is not None

    def test_constructs_with_real_testnet_profile(self):
        """CCTP addresses are now published — testnet/mainnet construct successfully."""
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network="testnet")
        assert bridge is not None

        bridge = CCTPBridge(w3=MagicMock(), network="mainnet")
        assert bridge is not None


def _mock_bridge_w3(receipt_status: int = 1) -> MagicMock:
    w3 = MagicMock()
    w3.eth.chain_id = 999
    w3.eth.gas_price = 1_000_000_000
    w3.eth.get_transaction_count.return_value = 0
    contract = MagicMock()
    w3.eth.contract.return_value = contract
    contract.functions.depositForBurn.return_value.build_transaction.return_value = {
        "from": "0x...",
        "gas": 200_000,
    }
    signed = MagicMock()
    signed.raw_transaction = b"\xab\xcd"
    w3.eth.account.sign_transaction.return_value = signed
    tx_hash = MagicMock()
    tx_hash.hex.return_value = "0x" + "aa" * 32
    w3.eth.send_raw_transaction.return_value = tx_hash
    w3.eth.get_transaction_receipt.return_value = {"status": receipt_status}

    message_bytes = b"\x01\x02\x03"
    contract.events.MessageSent.return_value.process_receipt.return_value = [
        {"args": {"message": message_bytes}}
    ]
    return w3


# ---------------------------------------------------------------------------
# start_transfer (burn)
# ---------------------------------------------------------------------------


class TestStartTransfer:
    def test_invalid_recipient_returns_failed_not_raise(self):
        """Regression: an invalid recipient must come back as a FAILED transfer,
        not an unhandled ValueError (which would crash the CLI/API)."""
        from arc_devkit.bridge.cctp import CCTPBridge

        w3 = _mock_bridge_w3()
        bridge = CCTPBridge(w3=w3, network=_FAKE_PROFILE)

        with patch("arc_devkit.bridge.cctp.save_transfer"):
            transfer = bridge.start_transfer(
                amount_usdc=Decimal("10"),
                recipient="not-an-address",
                destination_domain=0,
                dest_chain_id=1,
                private_key=_PRIVKEY,
            )

        assert transfer.status == BridgeStatus.FAILED
        assert "Invalid EVM address" in transfer.error
        w3.eth.send_raw_transaction.assert_not_called()

    def test_burn_success_sets_burned_status(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        w3 = _mock_bridge_w3()
        bridge = CCTPBridge(w3=w3, network=_FAKE_PROFILE)

        with patch("arc_devkit.bridge.cctp.save_transfer") as mock_save:
            transfer = bridge.start_transfer(
                amount_usdc=Decimal("10"),
                recipient=_RECIPIENT,
                destination_domain=0,
                dest_chain_id=1,
                private_key=_PRIVKEY,
            )

        assert transfer.status == BridgeStatus.BURNED
        assert transfer.burn_tx_hash is not None
        assert transfer.message_hash is not None
        mock_save.assert_called()

    def test_burn_failure_receipt_sets_failed(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        w3 = _mock_bridge_w3(receipt_status=0)
        bridge = CCTPBridge(w3=w3, network=_FAKE_PROFILE)

        with patch("arc_devkit.bridge.cctp.save_transfer"):
            transfer = bridge.start_transfer(
                amount_usdc=Decimal("10"),
                recipient=_RECIPIENT,
                destination_domain=0,
                dest_chain_id=1,
                private_key=_PRIVKEY,
            )

        assert transfer.status == BridgeStatus.FAILED

    def test_guardrail_violation_blocks_burn(self, tmp_path):
        from arc_devkit.agents.guardrails import Guardrails
        from arc_devkit.bridge.cctp import CCTPBridge

        w3 = _mock_bridge_w3()
        guardrails = Guardrails(allowed_recipients=["0x" + "c" * 40], state_dir=tmp_path)
        bridge = CCTPBridge(w3=w3, network=_FAKE_PROFILE, guardrails=guardrails)

        with patch("arc_devkit.bridge.cctp.save_transfer"):
            transfer = bridge.start_transfer(
                amount_usdc=Decimal("10"),
                recipient=_RECIPIENT,
                destination_domain=0,
                dest_chain_id=1,
                private_key=_PRIVKEY,
            )

        assert transfer.status == BridgeStatus.FAILED
        assert "Guardrail" in transfer.error
        w3.eth.send_raw_transaction.assert_not_called()


# ---------------------------------------------------------------------------
# fetch_attestation
# ---------------------------------------------------------------------------


class TestFetchAttestation:
    def test_no_attestation_url_configured_fails(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE, attestation_api_url=None)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.BURNED,
            message_hash="0x" + "ab" * 32,
        )
        with patch("arc_devkit.bridge.cctp.save_transfer"):
            result = bridge.fetch_attestation(transfer)
        assert result.status == BridgeStatus.FAILED
        assert "attestation API" in result.error

    def test_no_message_hash_fails(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(
            w3=MagicMock(),
            network=_FAKE_PROFILE,
            attestation_api_url="https://fake-attestation.test",
        )
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.BURNED,
        )
        with patch("arc_devkit.bridge.cctp.save_transfer"):
            result = bridge.fetch_attestation(transfer)
        assert result.status == BridgeStatus.FAILED

    def test_successful_attestation(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(
            w3=MagicMock(),
            network=_FAKE_PROFILE,
            attestation_api_url="https://fake-attestation.test",
        )
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.BURNED,
            message_hash="0x" + "ab" * 32,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "status": "complete",
            "attestation": "0x" + "cd" * 32,
        }

        with (
            patch("arc_devkit.bridge.cctp.save_transfer"),
            patch("httpx.get", return_value=mock_response),
        ):
            result = bridge.fetch_attestation(transfer)

        assert result.status == BridgeStatus.ATTESTED
        assert result.attestation == "0x" + "cd" * 32


# ---------------------------------------------------------------------------
# mint
# ---------------------------------------------------------------------------


class TestMint:
    def test_mint_requires_attested_status(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.BURNED,
        )
        with patch("arc_devkit.bridge.cctp.save_transfer"):
            result = bridge.mint(transfer, MagicMock(), "0x" + "d" * 40, _PRIVKEY)
        assert result.status == BridgeStatus.FAILED

    def test_mint_invalid_message_transmitter_returns_failed_not_raise(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.ATTESTED,
            message_bytes="0x010203",
            attestation="0x040506",
        )

        with patch("arc_devkit.bridge.cctp.save_transfer"):
            result = bridge.mint(transfer, MagicMock(), "not-an-address", _PRIVKEY)

        assert result.status == BridgeStatus.FAILED
        assert "Invalid EVM address" in result.error

    def test_mint_success(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.ATTESTED,
            message_bytes="0x010203",
            attestation="0x040506",
        )

        dest_w3 = MagicMock()
        dest_w3.eth.get_transaction_count.return_value = 0
        dest_w3.eth.gas_price = 1
        dest_w3.eth.chain_id = 1
        contract = MagicMock()
        dest_w3.eth.contract.return_value = contract
        contract.functions.receiveMessage.return_value.build_transaction.return_value = {
            "from": "0x...",
            "gas": 200_000,
        }
        signed = MagicMock()
        signed.raw_transaction = b"\x01"
        dest_w3.eth.account.sign_transaction.return_value = signed
        tx_hash = MagicMock()
        tx_hash.hex.return_value = "0x" + "ee" * 32
        dest_w3.eth.send_raw_transaction.return_value = tx_hash

        with patch("arc_devkit.bridge.cctp.save_transfer"):
            result = bridge.mint(transfer, dest_w3, "0x" + "d" * 40, _PRIVKEY)

        assert result.status == BridgeStatus.COMPLETE
        assert result.mint_tx_hash == "0x" + "ee" * 32


# ---------------------------------------------------------------------------
# resume (error recovery dispatch)
# ---------------------------------------------------------------------------


class TestResume:
    def test_resume_from_burned_calls_fetch_attestation(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.BURNED,
        )
        with patch.object(bridge, "fetch_attestation", return_value=transfer) as mock_fa:
            bridge.resume(transfer)
        mock_fa.assert_called_once_with(transfer)

    def test_resume_from_attested_without_dest_args_fails(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.ATTESTED,
        )
        with patch("arc_devkit.bridge.cctp.save_transfer"):
            result = bridge.resume(transfer)
        assert result.error is not None

    def test_resume_from_complete_is_noop(self):
        from arc_devkit.bridge.cctp import CCTPBridge

        bridge = CCTPBridge(w3=MagicMock(), network=_FAKE_PROFILE)
        transfer = BridgeTransfer(
            id="t1",
            source_chain_id=999,
            dest_chain_id=1,
            sender=_SENDER,
            recipient=_RECIPIENT,
            amount_usdc=Decimal("1"),
            status=BridgeStatus.COMPLETE,
        )
        result = bridge.resume(transfer)
        assert result.status == BridgeStatus.COMPLETE
