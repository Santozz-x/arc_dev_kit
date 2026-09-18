"""Unit tests for `arcdevkit bridge send|status|resume`."""

from decimal import Decimal
from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.bridge.models import BridgeStatus, BridgeTransfer
from arc_devkit.cli.main import app
from arc_devkit.networks import ContractAddresses, NetworkProfile

runner = CliRunner()

_KEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
_TO = "0x" + "b" * 40

# CCTP addresses are now published for testnet/mainnet (see networks.py) — this
# fake profile simulates a network where they still aren't, to keep covering
# CCTPBridge's "not published" guard.
_UNPUBLISHED_PROFILE = NetworkProfile(
    name="unpublished-fake",
    chain_id=999,
    rpc_url="https://fake.example.com",
    explorer_url=None,
    contracts=ContractAddresses(usdc=None, eurc=None, cctp_token_messenger=None),
)


class TestBridgeSend:
    def test_send_fails_clearly_when_no_cctp_contract(self, mock_web3):
        """CCTPBridge must fail with a clear message when a network has no published CCTP contract."""
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.bridge.cctp.get_network", return_value=_UNPUBLISHED_PROFILE),
        ):
            result = runner.invoke(
                app,
                [
                    "bridge",
                    "send",
                    _TO,
                    "5.0",
                    "--dest-domain",
                    "0",
                    "--dest-chain-id",
                    "1",
                    "--key",
                    _KEY,
                ],
            )

        assert result.exit_code == 1
        assert "CCTP TokenMessenger" in result.stdout

    def test_send_without_key_fails(self, mock_web3, monkeypatch):
        monkeypatch.delenv("ARC_PRIVATE_KEY", raising=False)
        with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
            result = runner.invoke(
                app,
                ["bridge", "send", _TO, "5.0", "--dest-domain", "0", "--dest-chain-id", "1"],
            )
        assert result.exit_code == 1
        assert "private key" in result.stdout.lower()


class TestBridgeStatus:
    def test_status_unknown_transfer_fails(self, tmp_path):
        with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
            result = runner.invoke(app, ["bridge", "status", "nope"])
        assert result.exit_code == 1

    def test_status_known_transfer_shows_fields(self, tmp_path):
        from arc_devkit.bridge.store import save_transfer

        transfer = BridgeTransfer(
            id="abc123",
            source_chain_id=5042002,
            dest_chain_id=1,
            sender="0x" + "a" * 40,
            recipient=_TO,
            amount_usdc=Decimal("5"),
            status=BridgeStatus.BURNED,
            burn_tx_hash="0x" + "ee" * 32,
        )
        save_transfer(transfer, store_dir=tmp_path)

        with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
            result = runner.invoke(app, ["bridge", "status", "abc123"])

        assert result.exit_code == 0
        assert "burned" in result.stdout.lower()


class TestBridgeResume:
    def test_resume_unknown_transfer_fails(self, tmp_path):
        with patch("arc_devkit.bridge.store._STORE_DIR", tmp_path):
            result = runner.invoke(app, ["bridge", "resume", "nope"])
        assert result.exit_code == 1

    def test_resume_fails_clearly_when_no_cctp_contract(self, tmp_path, mock_web3):
        from arc_devkit.bridge.store import save_transfer

        transfer = BridgeTransfer(
            id="abc123",
            source_chain_id=5042002,
            dest_chain_id=1,
            sender="0x" + "a" * 40,
            recipient=_TO,
            amount_usdc=Decimal("5"),
            status=BridgeStatus.BURNED,
        )
        save_transfer(transfer, store_dir=tmp_path)

        with (
            patch("arc_devkit.bridge.store._STORE_DIR", tmp_path),
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.bridge.cctp.get_network", return_value=_UNPUBLISHED_PROFILE),
        ):
            result = runner.invoke(app, ["bridge", "resume", "abc123", "--key", _KEY])

        assert result.exit_code == 1
        assert "CCTP TokenMessenger" in result.stdout
