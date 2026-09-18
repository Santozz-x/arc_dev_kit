"""
Shared fixtures for all tests.

Environment variables are set BEFORE any arc_devkit import to avoid
EnvironmentError from config.py at load time.
"""

import os

# Set test environment variables before any package import.
# Unit tests default to the testnet profile explicitly (matching the RPC/chain
# ID below) — the SDK's own default network is mainnet (see arc_devkit.networks
# .DEFAULT_NETWORK), but unit tests should be deterministic regardless of that
# default, and most fixtures/mocks below predate mainnet support.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test-key-for-tests-only")
os.environ.setdefault("ARC_NETWORK", "testnet")
os.environ.setdefault("ARC_RPC_URL", "https://rpc.testnet.arc.io")
os.environ.setdefault("ARC_CHAIN_ID", "5042002")
os.environ.setdefault("LOG_LEVEL", "WARNING")  # reduce noise during tests

from unittest.mock import MagicMock, patch  # noqa: E402

import pytest  # noqa: E402
from anthropic.types import TextBlock  # noqa: E402


def pytest_collection_modifyitems(config, items):
    """Skip @pytest.mark.integration tests unless -m integration is passed."""
    if config.getoption("-m", default="") == "integration":
        return
    skip_integration = pytest.mark.skip(reason="integration test — use -m integration to run")
    for item in items:
        if item.get_closest_marker("integration"):
            item.add_marker(skip_integration)


@pytest.fixture
def mock_web3():
    """
    Full web3.py client mock for unit tests.

    Removes the need for a real Arc testnet connection,
    allowing tests to run without network access.
    """
    with patch("arc_devkit.core.connection.Web3") as MockWeb3:
        # Simulate a connected instance
        instance = MagicMock()
        instance.is_connected.return_value = True
        instance.eth.block_number = 89_432
        instance.eth.chain_id = 7_777_777
        instance.eth.gas_price = 1_000_000_000  # 1 gwei
        instance.from_wei.return_value = "0.001"

        MockWeb3.return_value = instance
        MockWeb3.HTTPProvider = MagicMock()

        yield instance


@pytest.fixture
def mock_anthropic():
    """
    Anthropic client mock to avoid real API calls.

    Replaces anthropic.Anthropic with a MagicMock that returns a
    simulated response without consuming API credits.
    """
    with patch(
        "arc_devkit.copilot.providers.anthropic_provider.anthropic.Anthropic"
    ) as MockAnthropic:
        instance = MagicMock()

        # Simulate real response structure with a proper TextBlock instance
        content = TextBlock(type="text", text="Simulated Dev Copilot response for tests.")

        message = MagicMock()
        message.content = [content]

        instance.messages.create.return_value = message
        MockAnthropic.return_value = instance

        yield instance
