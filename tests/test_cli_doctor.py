"""Unit tests for `arc doctor` / `arcdevkit doctor`."""

from unittest.mock import patch

from typer.testing import CliRunner

from arc_devkit.health import HealthReport

runner = CliRunner()


def _ready_report(network: str = "testnet") -> HealthReport:
    report = HealthReport(
        network=network,
        rpc_url="https://rpc.testnet.arc.io",
        rpc_ok=True,
        latency_ms=42.0,
        expected_chain_id=5042002,
        rpc_chain_id=5042002,
        chain_id_match=True,
        latest_block=100,
        usdc_contract_ok=True,
        explorer_configured=True,
    )
    report.checks = [
        ("RPC reachable", True),
        ("Chain ID matches", True),
        ("USDC contract deployed", True),
        ("Explorer configured", True),
    ]
    return report


def _not_ready_report() -> HealthReport:
    report = HealthReport(network="testnet", rpc_url=None, rpc_error="No RPC URL configured.")
    report.checks = [
        ("RPC reachable", False),
        ("Chain ID matches", False),
        ("USDC contract deployed", False),
        ("Explorer configured", False),
    ]
    return report


class TestFlatDoctor:
    def test_ready_exits_zero(self):
        from arc_devkit.cli.flat import app

        with patch("arc_devkit.health.run_health_check", return_value=_ready_report()):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "READY" in result.stdout

    def test_not_ready_exits_nonzero(self):
        from arc_devkit.cli.flat import app

        with patch("arc_devkit.health.run_health_check", return_value=_not_ready_report()):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 1
        assert "NOT READY" in result.stdout


class TestGroupedDoctor:
    def test_ready_exits_zero(self):
        from arc_devkit.cli.main import app

        with patch("arc_devkit.health.run_health_check", return_value=_ready_report()):
            result = runner.invoke(app, ["doctor"])
        assert result.exit_code == 0
        assert "READY" in result.stdout
