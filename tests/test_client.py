"""Unit tests for arc_devkit.client.Arc — the single-entry-point facade."""

from unittest.mock import MagicMock, patch

import pytest

from arc_devkit import Arc
from arc_devkit.networks import ContractAddresses, NetworkProfile

_FAKE_PROFILE = NetworkProfile(
    name="fake",
    chain_id=999,
    rpc_url="https://fake.example.com",
    explorer_url="https://explorer.example.com",
    contracts=ContractAddresses(usdc="0x" + "1" * 40, eurc=None, cctp_token_messenger=None),
)

_NO_RPC_PROFILE = NetworkProfile(
    name="no-rpc-fake",
    chain_id=999,
    rpc_url=None,
    explorer_url=None,
    contracts=ContractAddresses(usdc=None, eurc=None, cctp_token_messenger=None),
)


def _make_arc(profile: NetworkProfile = _FAKE_PROFILE) -> Arc:
    with patch("arc_devkit.client.Web3") as MockWeb3:
        instance = MagicMock()
        MockWeb3.return_value = instance
        MockWeb3.HTTPProvider = MagicMock()
        MockWeb3.to_checksum_address = staticmethod(lambda a: a)
        arc = Arc(network=profile)
    return arc


class TestConstruction:
    def test_mainnet_classmethod(self):
        arc = Arc.mainnet()
        assert arc.network.name == "mainnet"
        assert arc.network.chain_id == 5042

    def test_testnet_classmethod(self):
        arc = Arc.testnet()
        assert arc.network.name == "testnet"
        assert arc.network.chain_id == 5042002

    def test_custom_rpc_override(self):
        arc = Arc.mainnet(rpc_url="https://custom.example.com")
        assert arc.network.name == "mainnet"  # profile unchanged, only the connection differs

    def test_raises_without_rpc_url(self):
        with pytest.raises(ValueError, match="No RPC URL"):
            Arc(network=_NO_RPC_PROFILE)


class TestReads:
    def test_get_balance_converts_from_wei(self):
        arc = _make_arc()
        arc._w3.eth.get_balance.return_value = 1_000_000_000_000_000_000
        arc._w3.from_wei.return_value = "1"
        from decimal import Decimal

        assert arc.get_balance("0x" + "a" * 40) == Decimal("1")

    def test_latest_block_delegates_to_w3(self):
        arc = _make_arc()
        arc._w3.eth.get_block.return_value = {"number": 42}
        assert arc.latest_block() == {"number": 42}
        arc._w3.eth.get_block.assert_called_with("latest")

    def test_get_block_with_identifier(self):
        arc = _make_arc()
        arc._w3.eth.get_block.return_value = {"number": 7}
        assert arc.get_block(7) == {"number": 7}

    def test_get_transaction_validates_hash(self):
        arc = _make_arc()
        with pytest.raises(Exception):
            arc.get_transaction("not-a-hash")


class TestUsdc:
    def test_usdc_property_constructs_token(self):
        arc = _make_arc()
        with patch("arc_devkit.stablecoins.token.USDCToken") as MockToken:
            instance = MagicMock()
            MockToken.return_value = instance
            token = arc.usdc
            assert token is instance
            # Cached on second access — constructed only once.
            assert arc.usdc is instance
            MockToken.assert_called_once()

    def test_usdc_raises_when_no_address_configured(self):
        no_usdc_profile = NetworkProfile(
            name="no-usdc-fake",
            chain_id=999,
            rpc_url="https://fake.example.com",
            explorer_url=None,
            contracts=ContractAddresses(usdc=None, eurc=None, cctp_token_messenger=None),
        )
        arc = _make_arc(no_usdc_profile)
        with pytest.raises(ValueError, match="No USDC contract"):
            _ = arc.usdc


class TestContract:
    def test_contract_call_delegates_to_call_view(self):
        arc = _make_arc()
        abi = [{"name": "balanceOf", "type": "function"}]
        with patch("arc_devkit.contracts.loader.call_view", return_value=123) as mock_call:
            contract = arc.contract("0x" + "b" * 40, abi)
            result = contract.call("balanceOf", "0x" + "c" * 40)
        assert result == 123
        mock_call.assert_called_once()

    def test_contract_send_delegates_to_send_tx(self):
        arc = _make_arc()
        abi = [{"name": "transfer", "type": "function"}]
        with patch("arc_devkit.contracts.loader.send_tx", return_value="0xhash") as mock_send:
            contract = arc.contract("0x" + "b" * 40, abi)
            result = contract.send("transfer", "0x" + "c" * 40, 1, private_key="0xkey")
        assert result == "0xhash"
        mock_send.assert_called_once()


class TestHealthCheck:
    def test_health_check_delegates_to_run_health_check(self):
        arc = _make_arc()
        from arc_devkit.health import HealthReport

        fake_report = HealthReport(network="fake", rpc_url="https://fake.example.com")
        fake_report.checks = [("RPC reachable", True)]
        with patch("arc_devkit.health.run_health_check", return_value=fake_report):
            result = arc.health_check()
        assert result["network"] == "fake"
        assert result["ready"] is True


class TestDebugTransaction:
    def test_debug_transaction_delegates_to_tx_analyzer(self):
        arc = _make_arc()
        with patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer") as MockAnalyzer:
            instance = MagicMock()
            instance.analyze.return_value = {"status": "success"}
            MockAnalyzer.return_value = instance
            result = arc.debug_transaction("0x" + "1" * 64, use_ai=False)
        assert result == {"status": "success"}
