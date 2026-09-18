"""Unit tests for arc_devkit.health.run_health_check."""

from unittest.mock import MagicMock

from arc_devkit.health import run_health_check
from arc_devkit.networks import ContractAddresses, NetworkProfile

_PROFILE = NetworkProfile(
    name="fake",
    chain_id=999,
    rpc_url="https://fake.example.com",
    explorer_url="https://explorer.example.com",
    contracts=ContractAddresses(usdc="0x" + "1" * 40, eurc=None, cctp_token_messenger=None),
)


def _mock_w3(chain_id=999, block=100, code=b"\x60\x80"):
    w3 = MagicMock()
    w3.eth.chain_id = chain_id
    w3.eth.block_number = block
    w3.eth.get_code.return_value = code
    return w3


class TestRunHealthCheck:
    def test_fully_healthy(self):
        report = run_health_check(_PROFILE, w3=_mock_w3())
        assert report.rpc_ok is True
        assert report.chain_id_match is True
        assert report.usdc_contract_ok is True
        assert report.explorer_configured is True
        assert report.ready is True

    def test_chain_id_mismatch(self):
        report = run_health_check(_PROFILE, w3=_mock_w3(chain_id=1))
        assert report.rpc_ok is True
        assert report.chain_id_match is False
        assert report.ready is False

    def test_usdc_contract_not_deployed(self):
        report = run_health_check(_PROFILE, w3=_mock_w3(code=b""))
        assert report.usdc_contract_ok is False
        assert report.ready is False

    def test_rpc_error_marks_not_ready(self):
        w3 = MagicMock()
        w3.eth.chain_id.__class__ = property  # force AttributeError-like failure
        broken_w3 = MagicMock()
        broken_w3.eth = MagicMock()
        type(broken_w3.eth).chain_id = property(lambda self: (_ for _ in ()).throw(ConnectionError))
        report = run_health_check(_PROFILE, w3=broken_w3)
        assert report.rpc_ok is False
        assert report.ready is False
        assert report.rpc_error is not None

    def test_no_rpc_url_configured(self):
        no_rpc_profile = NetworkProfile(
            name="no-rpc",
            chain_id=None,
            rpc_url=None,
            explorer_url=None,
            contracts=ContractAddresses(usdc=None, eurc=None, cctp_token_messenger=None),
        )
        report = run_health_check(no_rpc_profile)
        assert report.rpc_ok is False
        assert report.ready is False
        assert "No RPC URL" in (report.rpc_error or "")

    def test_explorer_not_configured(self):
        no_explorer = NetworkProfile(
            name="fake2",
            chain_id=999,
            rpc_url="https://fake.example.com",
            explorer_url=None,
            contracts=ContractAddresses(usdc="0x" + "1" * 40, eurc=None, cctp_token_messenger=None),
        )
        report = run_health_check(no_explorer, w3=_mock_w3())
        assert report.explorer_configured is False
        assert report.ready is False
