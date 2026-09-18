"""Unit tests for arc_devkit.config — ARC_NETWORK profile fallback."""

import dataclasses as _dataclasses
from unittest.mock import patch

import pytest

from arc_devkit.config import _load_settings
from arc_devkit.networks import get_network


def _clear_network_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test-key")
    monkeypatch.delenv("ARC_NETWORK", raising=False)
    monkeypatch.delenv("ARC_RPC_URL", raising=False)
    monkeypatch.delenv("ARC_CHAIN_ID", raising=False)


class TestNetworkFallback:
    def test_default_network_is_mainnet_when_unset(self, monkeypatch):
        """Arc Mainnet is the SDK's default network — see arc_devkit.networks.DEFAULT_NETWORK."""
        _clear_network_env(monkeypatch)

        settings = _load_settings()

        assert settings.arc_network == "mainnet"
        assert settings.arc_rpc_url == "https://rpc.mainnet.arc.io"
        assert settings.arc_chain_id == 5042
        assert settings.network.name == "mainnet"

    def test_testnet_still_fully_supported_when_selected_explicitly(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "testnet")

        settings = _load_settings()

        assert settings.arc_network == "testnet"
        assert settings.arc_rpc_url == "https://rpc.testnet.arc.io"
        assert settings.arc_chain_id == 5042002
        assert settings.network.name == "testnet"

    def test_explicit_rpc_url_overrides_network_profile(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "testnet")
        monkeypatch.setenv("ARC_RPC_URL", "https://custom-rpc.example.com")

        settings = _load_settings()

        assert settings.arc_rpc_url == "https://custom-rpc.example.com"

    def test_explicit_chain_id_overrides_network_profile(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_RPC_URL", "https://rpc.testnet.arc.io")
        monkeypatch.setenv("ARC_CHAIN_ID", "999999")

        settings = _load_settings()

        assert settings.arc_chain_id == 999999

    def test_mainnet_without_explicit_rpc_uses_official_default(self, monkeypatch):
        """Mainnet now has a published default RPC — no ARC_RPC_URL required to use it."""
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "mainnet")

        settings = _load_settings()

        assert settings.arc_rpc_url == "https://rpc.mainnet.arc.io"
        assert settings.arc_chain_id == 5042

    def test_network_without_chain_id_and_no_override_raises(self, monkeypatch):
        """config.py must never silently fall back to another network's chain ID."""
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "mainnet")

        fake_profile = get_network("mainnet")
        broken_profile = _dataclasses.replace(fake_profile, chain_id=None)

        with patch("arc_devkit.config.get_network", return_value=broken_profile):
            with pytest.raises(OSError, match="ARC_CHAIN_ID"):
                _load_settings()

    def test_mainnet_with_explicit_rpc_and_chain_id_works(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "mainnet")
        monkeypatch.setenv("ARC_RPC_URL", "https://mainnet-rpc.example.com")
        monkeypatch.setenv("ARC_CHAIN_ID", "1234567")

        settings = _load_settings()

        assert settings.arc_network == "mainnet"
        assert settings.arc_rpc_url == "https://mainnet-rpc.example.com"
        assert settings.arc_chain_id == 1234567

    def test_unknown_network_raises(self, monkeypatch):
        _clear_network_env(monkeypatch)
        monkeypatch.setenv("ARC_NETWORK", "not-a-real-network")
        monkeypatch.setenv("ARC_RPC_URL", "https://rpc.testnet.arc.io")

        with pytest.raises(OSError, match="Unknown Arc network"):
            _load_settings()
