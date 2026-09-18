"""Unit tests for arc_devkit.cli.flat — arc CLI commands."""

import json
from decimal import Decimal
from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.cli.flat import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# arc status
# ---------------------------------------------------------------------------


class TestStatus:
    def test_connected_rich_output(self, mock_web3):
        mock_web3.is_connected.return_value = True
        mock_web3.eth.block_number = 42
        mock_web3.eth.chain_id = 5042002
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.from_wei.return_value = "0.000000001"

        with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
            result = runner.invoke(app, ["status"])

        assert result.exit_code == 0

    def test_connected_json(self, mock_web3):
        mock_web3.is_connected.return_value = True
        mock_web3.eth.block_number = 99
        mock_web3.eth.chain_id = 5042002
        mock_web3.eth.gas_price = 1_000_000_000
        mock_web3.from_wei.return_value = "0.001"

        with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
            result = runner.invoke(app, ["status", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["connected"] is True
        assert data["block_number"] == 99

    def test_not_connected(self, mock_web3):
        mock_web3.is_connected.return_value = False

        with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
            result = runner.invoke(app, ["status"])

        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# arc balance
# ---------------------------------------------------------------------------


class TestBalance:
    def test_balance_json(self, mock_web3):
        address = "0x" + "a" * 40
        mock_web3.eth.get_balance.return_value = 5_000_000_000_000_000_000
        mock_web3.from_wei.return_value = Decimal("5.0")
        mock_web3.eth.get_transaction_count.return_value = 3

        with patch("arc_devkit.core.connection.get_web3", return_value=mock_web3):
            result = runner.invoke(app, ["balance", address, "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["address"] == address.lower() or data["address"].lower() == address.lower()
        assert "balance_arc" in data
        assert data["nonce"] == 3

    def test_balance_invalid_address(self):
        result = runner.invoke(app, ["balance", "not-an-address"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# arc gas
# ---------------------------------------------------------------------------


class TestGas:
    def test_gas_estimate_json(self, mock_web3):
        dest = "0x" + "b" * 40
        with patch(
            "arc_devkit.core.gas.estimate_transfer",
            return_value={
                "to": dest,
                "gas_limit": 21_000,
                "gas_price_gwei": "1",
                "custo_usdc": "0.000021",
            },
        ):
            result = runner.invoke(app, ["gas", dest, "1.0", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["gas_limit"] == 21_000

    def test_gas_invalid_to_address(self):
        result = runner.invoke(app, ["gas", "bad", "1.0"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# arc ask
# ---------------------------------------------------------------------------


class TestAsk:
    def test_ask_returns_response(self, mock_anthropic):
        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="Some answer"):
            result = runner.invoke(app, ["ask", "What is Arc?", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "response" in data

    def test_ask_raw_mode(self, mock_anthropic):
        with patch("arc_devkit.copilot.agent.DevCopilot.ask", return_value="Raw answer"):
            result = runner.invoke(app, ["ask", "Hello?", "--raw"])

        assert result.exit_code == 0
        assert "Raw answer" in result.output


# ---------------------------------------------------------------------------
# arc wallet
# ---------------------------------------------------------------------------


class TestWallet:
    def test_wallet_create_json(self):
        with patch(
            "arc_devkit.core.wallet.create_wallet",
            return_value={"address": "0x" + "a" * 40, "private_key": "0x" + "b" * 64},
        ):
            result = runner.invoke(app, ["wallet", "create", "--json"])

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "address" in data
        assert "private_key" in data

    def test_wallet_balance_json(self, mock_web3):
        addr = "0x" + "a" * 40
        with patch(
            "arc_devkit.core.wallet.get_balance",
            return_value={"address": addr, "balance_wei": 0, "balance_usdc": Decimal("0")},
        ):
            result = runner.invoke(app, ["wallet", "balance", addr, "--json"])

        assert result.exit_code == 0

    def test_wallet_balance_invalid_address(self):
        result = runner.invoke(app, ["wallet", "balance", "not-valid"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# arc config
# ---------------------------------------------------------------------------


class TestConfig:
    def test_config_set_and_get(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)

        # set
        result = runner.invoke(app, ["config", "set", "LOG_LEVEL", "DEBUG"])
        assert result.exit_code == 0

        # get
        import os

        os.environ["LOG_LEVEL"] = "DEBUG"
        result = runner.invoke(app, ["config", "get", "LOG_LEVEL"])
        assert result.exit_code == 0

    def test_config_list(self, tmp_path, monkeypatch):
        env_file = tmp_path / ".env"
        env_file.write_text("ARC_RPC_URL=https://rpc.testnet.arc.io\nLOG_LEVEL=INFO\n")
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code == 0
        assert "ARC_RPC_URL" in result.output

    def test_config_get_missing_key(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        import os

        os.environ.pop("NONEXISTENT_KEY_XYZ", None)
        result = runner.invoke(app, ["config", "get", "NONEXISTENT_KEY_XYZ"])
        assert result.exit_code != 0

    def test_config_list_no_env_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["config", "list"])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# arc history
# ---------------------------------------------------------------------------


class TestHistory:
    def test_history_no_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr("arc_devkit.cli.flat._HISTORY_FILE", tmp_path / "history.json")
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0
        assert "No history" in result.output

    def test_history_json_output(self, tmp_path, monkeypatch):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [{"type": "debug", "tx_hash": "0x" + "a" * 64, "timestamp": "2026-06-21T10:00:00"}]
            )
        )
        monkeypatch.setattr("arc_devkit.cli.flat._HISTORY_FILE", history_file)
        result = runner.invoke(app, ["history", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["type"] == "debug"

    def test_history_table_output(self, tmp_path, monkeypatch):
        history_file = tmp_path / "history.json"
        history_file.write_text(
            json.dumps(
                [
                    {
                        "type": "portfolio",
                        "address": "0x" + "a" * 40,
                        "timestamp": "2026-06-21T10:00:00",
                    }
                ]
            )
        )
        monkeypatch.setattr("arc_devkit.cli.flat._HISTORY_FILE", history_file)
        result = runner.invoke(app, ["history"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# arc debug (with revert and abi fields)
# ---------------------------------------------------------------------------


class TestDebugCommand:
    def test_debug_shows_revert_reason(self, mock_anthropic):
        tx_hash = "0x" + "a" * 64
        with patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "hash": tx_hash,
                "status": "reverted",
                "summary": "TX reverted",
                "custo_usdc": "0.001",
                "revert_reason": 'require failed: "Insufficient balance"',
                "decoded_input": None,
                "error": "reverted",
                "suggestion": "",
                "raw_data": {},
            }
            result = runner.invoke(app, ["debug", tx_hash])

        assert result.exit_code == 0
        assert "Insufficient balance" in result.output

    def test_debug_shows_decoded_input(self, mock_anthropic):
        tx_hash = "0x" + "b" * 64
        with patch("arc_devkit.debugger.tx_analyzer.TxAnalyzer.analyze") as mock_analyze:
            mock_analyze.return_value = {
                "hash": tx_hash,
                "status": "success",
                "summary": "OK",
                "custo_usdc": "0.0001",
                "revert_reason": None,
                "decoded_input": {
                    "function": "transfer",
                    "args": {"to": "0xf...", "amount": "100"},
                },
                "error": None,
                "suggestion": "",
                "raw_data": {},
            }
            result = runner.invoke(app, ["debug", tx_hash])

        assert result.exit_code == 0
        assert "transfer" in result.output


# ---------------------------------------------------------------------------
# arc portfolio
# ---------------------------------------------------------------------------


class TestPortfolioCLICommands:
    def test_analyze_rich_output(self):
        from arc_devkit.analytics.portfolio import PortfolioSnapshot

        address = "0x" + "a" * 40
        snap = PortfolioSnapshot(
            address=address,
            native_balance=Decimal("1.5"),
            usdc_balance=None,
            nonce=7,
            recent_txs=[],
            blocks_scanned=100,
            blocks_from=900,
            blocks_to=1000,
            activity_score="low",
        )

        with (
            patch("arc_devkit.analytics.portfolio.PortfolioAnalyzer.analyze", return_value=snap),
            patch("arc_devkit.cli.flat._save_history"),
        ):
            result = runner.invoke(app, ["portfolio", "analyze", address, "--no-ai"])

        assert result.exit_code == 0
        assert "low" in result.output.lower() or "inactive" in result.output.lower()

    def test_report_invalid_json_file(self, tmp_path):
        bad_file = tmp_path / "wallets.json"
        bad_file.write_text("not valid json")
        result = runner.invoke(app, ["portfolio", "report", str(bad_file)])
        assert result.exit_code != 0

    def test_report_empty_wallet_list(self, tmp_path):
        f = tmp_path / "wallets.json"
        f.write_text("[]")
        result = runner.invoke(app, ["portfolio", "report", str(f)])
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# arc send
# ---------------------------------------------------------------------------


class TestSendCommand:
    _PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    def test_send_native_signed_json(self, mock_web3, monkeypatch):
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        signed_result = {
            "status": "signed",
            "token": "native",
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount_usdc": 1.0,
            "gas_limit": 21_000,
            "raw_transaction": "0xdeadbeef",
            "nota": "Transaction signed.",
        }
        with patch(
            "arc_devkit.agents.payment_agent.PaymentAgent.execute", return_value=signed_result
        ):
            result = runner.invoke(
                app,
                ["send", "0x" + "b" * 40, "1.0", "--token", "native", "--json"],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "signed"
        assert data["token"] == "native"

    def test_send_usdc_signed_json(self, mock_web3, monkeypatch):
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        signed_result = {
            "status": "signed",
            "token": "usdc",
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount_usdc": 5.0,
            "gas_limit": 65_000,
            "raw_transaction": "0xcafebabe",
            "nota": "USDC transfer signed.",
        }
        with patch(
            "arc_devkit.agents.payment_agent.PaymentAgent.execute", return_value=signed_result
        ):
            result = runner.invoke(
                app,
                ["send", "0x" + "b" * 40, "5.0", "--token", "usdc", "--json"],
            )

        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["status"] == "signed"
        assert data["token"] == "usdc"

    def test_send_table_output(self, mock_web3, monkeypatch):
        """Rich table output when --json is not passed."""
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        signed_result = {
            "status": "signed",
            "token": "native",
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount_usdc": 2.0,
            "gas_limit": 21_000,
            "raw_transaction": "0xdeadbeef01020304050607080910111213",
            "nota": "Transaction signed.",
        }
        with patch(
            "arc_devkit.agents.payment_agent.PaymentAgent.execute", return_value=signed_result
        ):
            result = runner.invoke(app, ["send", "0x" + "b" * 40, "2.0"])

        assert result.exit_code == 0
        assert "signed" in result.output.lower() or "payment" in result.output.lower()

    def test_send_with_tx_hash_displayed(self, mock_web3, monkeypatch):
        """When result contains tx_hash and aviso, they appear in the table."""
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        sent_result = {
            "status": "sent",
            "token": "usdc",
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount_usdc": 3.0,
            "tx_hash": "0x" + "de" * 32,
            "aviso": "Timeout waiting for receipt.",
        }
        with patch(
            "arc_devkit.agents.payment_agent.PaymentAgent.execute", return_value=sent_result
        ):
            result = runner.invoke(app, ["send", "0x" + "b" * 40, "3.0", "--token", "usdc"])

        assert result.exit_code == 0

    def test_send_no_key_exits(self, monkeypatch):
        monkeypatch.delenv("ARC_PRIVATE_KEY", raising=False)
        result = runner.invoke(app, ["send", "0x" + "b" * 40, "1.0"])
        assert result.exit_code != 0


class TestSendMainnetSafety:
    """`--broadcast` on mainnet requires confirmation unless --yes is passed.

    settings is a module-level singleton resolved once at import time, so
    ARC_NETWORK env changes after import don't reach it — these tests patch
    arc_devkit.config.settings directly (flat.py re-reads it via a local
    `from arc_devkit.config import settings` inside send()).
    """

    _PRIVKEY = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"

    @staticmethod
    def _settings_for(network: str):
        import dataclasses

        from arc_devkit.config import settings as real_settings

        return dataclasses.replace(real_settings, arc_network=network)

    def test_broadcast_on_mainnet_without_yes_prompts_and_aborts_on_no(
        self, mock_web3, monkeypatch
    ):
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        with (
            patch("arc_devkit.config.settings", self._settings_for("mainnet")),
            patch("arc_devkit.agents.payment_agent.PaymentAgent.execute") as mock_execute,
        ):
            result = runner.invoke(
                app,
                ["send", "0x" + "b" * 40, "1.0", "--broadcast"],
                input="n\n",
            )

        assert result.exit_code == 1
        assert "MAINNET" in result.output
        assert "real funds" in result.output.lower()
        mock_execute.assert_not_called()

    def test_broadcast_on_mainnet_with_yes_flag_skips_prompt(self, mock_web3, monkeypatch):
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        sent_result = {
            "status": "sent",
            "token": "native",
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount_usdc": 1.0,
            "tx_hash": "0x" + "aa" * 32,
        }
        with (
            patch("arc_devkit.config.settings", self._settings_for("mainnet")),
            patch("arc_devkit.agents.payment_agent.PaymentAgent.execute", return_value=sent_result),
        ):
            result = runner.invoke(app, ["send", "0x" + "b" * 40, "1.0", "--broadcast", "--yes"])

        assert result.exit_code == 0

    def test_broadcast_on_testnet_does_not_prompt(self, mock_web3, monkeypatch):
        monkeypatch.setenv("ARC_PRIVATE_KEY", self._PRIVKEY)

        sent_result = {
            "status": "sent",
            "token": "native",
            "from": "0x" + "a" * 40,
            "to": "0x" + "b" * 40,
            "amount_usdc": 1.0,
            "tx_hash": "0x" + "bb" * 32,
        }
        with (
            patch("arc_devkit.config.settings", self._settings_for("testnet")),
            patch("arc_devkit.agents.payment_agent.PaymentAgent.execute", return_value=sent_result),
        ):
            result = runner.invoke(app, ["send", "0x" + "b" * 40, "1.0", "--broadcast"])

        assert result.exit_code == 0
