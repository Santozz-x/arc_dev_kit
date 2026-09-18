"""Unit tests for the Sprint 6 CLI commands: network check-mainnet, oracle, privacy."""

from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.cli.main import app

runner = CliRunner()


class TestNetworkCheckMainnet:
    def test_ready_by_default(self):
        """Arc Mainnet config is fully filled in (see networks.py) — ready out of the box."""
        result = runner.invoke(app, ["network", "check-mainnet"])
        assert result.exit_code == 0
        assert "Ready" in result.stdout

    def test_not_ready_exits_nonzero(self):
        from arc_devkit.networks import ContractAddresses, NetworkProfile

        incomplete_profile = NetworkProfile(
            name="mainnet",
            chain_id=None,
            rpc_url=None,
            explorer_url=None,
            contracts=ContractAddresses(usdc=None, eurc=None, cctp_token_messenger=None),
        )
        with patch("arc_devkit.networks.get_network", return_value=incomplete_profile):
            result = runner.invoke(app, ["network", "check-mainnet"])
        assert result.exit_code == 1
        assert "missing" in result.stdout.lower()

    def test_ready_when_all_fields_configured(self):
        from arc_devkit.networks import ContractAddresses, NetworkProfile

        fake_profile = NetworkProfile(
            name="mainnet",
            chain_id=1,
            rpc_url="https://mainnet.example.com",
            explorer_url="https://explorer.example.com",
            contracts=ContractAddresses(
                usdc="0x" + "1" * 40,
                eurc="0x" + "2" * 40,
                cctp_token_messenger="0x" + "3" * 40,
                gateway="0x" + "4" * 40,
                cctp_message_transmitter="0x" + "5" * 40,
                gateway_wallet="0x" + "6" * 40,
                gateway_minter="0x" + "7" * 40,
            ),
        )
        with patch("arc_devkit.networks.get_network", return_value=fake_profile):
            result = runner.invoke(app, ["network", "check-mainnet"])
        assert result.exit_code == 0
        assert "Ready" in result.stdout


class TestOraclePrice:
    def test_price_success(self, mock_web3):
        from decimal import Decimal

        from arc_devkit.oracle.price_feed import PriceData

        data = PriceData(
            description="ETH / USD", price=Decimal("2500.5"), decimals=8, updated_at=1, round_id=1
        )
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch("arc_devkit.oracle.price_feed.PriceOracle.latest_price", return_value=data),
        ):
            result = runner.invoke(app, ["oracle", "price", "0x" + "1" * 40])
        assert result.exit_code == 0
        assert "2500.5" in result.stdout

    def test_price_error_exits_nonzero(self, mock_web3):
        with (
            patch("arc_devkit.core.connection.get_web3", return_value=mock_web3),
            patch(
                "arc_devkit.oracle.price_feed.PriceOracle.latest_price",
                side_effect=Exception("bad feed"),
            ),
        ):
            result = runner.invoke(app, ["oracle", "price", "0x" + "1" * 40])
        assert result.exit_code == 1


class TestPrivacyCLI:
    def test_generate_view_key_exits_zero(self):
        result = runner.invoke(app, ["privacy", "generate-view-key"])
        assert result.exit_code == 0
        assert "Public key" in result.stdout

    def test_encrypt_produces_payload(self):
        from arc_devkit.privacy.view_key import generate_view_keypair

        viewer = generate_view_keypair()
        result = runner.invoke(app, ["privacy", "encrypt", viewer.public_key_bytes.hex(), "hello"])
        assert result.exit_code == 0
        assert "Encrypted payload" in result.stdout
