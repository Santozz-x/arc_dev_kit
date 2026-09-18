"""Arc network health check — shared by `arcdevkit doctor`/`arc doctor` and Arc.health_check()."""

import logging
import time
from dataclasses import dataclass, field

from web3 import Web3

from arc_devkit.networks import NetworkProfile

logger = logging.getLogger(__name__)


@dataclass
class HealthReport:
    """Result of a network health check — read-only, never signs or sends anything."""

    network: str
    rpc_url: str | None
    rpc_ok: bool = False
    rpc_error: str | None = None
    latency_ms: float | None = None
    expected_chain_id: int | None = None
    rpc_chain_id: int | None = None
    chain_id_match: bool = False
    latest_block: int | None = None
    usdc_contract_ok: bool = False
    explorer_configured: bool = False
    checks: list[tuple[str, bool]] = field(default_factory=list)

    @property
    def ready(self) -> bool:
        return all(ok for _, ok in self.checks)


def run_health_check(profile: NetworkProfile, w3: Web3 | None = None) -> HealthReport:
    """
    Run a read-only health check against `profile` (never signs or sends).

    Checks: RPC reachability, chain ID match (RPC-reported vs. the profile's
    expected chain ID), latest block, latency, and that the USDC contract
    address actually has code deployed on-chain (eth_getCode).
    """
    report = HealthReport(
        network=profile.name,
        rpc_url=profile.rpc_url,
        expected_chain_id=profile.chain_id,
    )

    if w3 is None:
        if not profile.rpc_url:
            report.rpc_error = "No RPC URL configured for this network."
            report.checks = [
                ("RPC reachable", False),
                ("Chain ID matches", False),
                ("USDC contract deployed", False),
                ("Explorer configured", profile.explorer_url is not None),
            ]
            return report
        w3 = Web3(Web3.HTTPProvider(profile.rpc_url, request_kwargs={"timeout": 10}))

    try:
        start = time.perf_counter()
        report.rpc_chain_id = w3.eth.chain_id
        report.latency_ms = round((time.perf_counter() - start) * 1000, 1)
        report.rpc_ok = True
        report.latest_block = w3.eth.block_number
        report.chain_id_match = (
            profile.chain_id is not None and report.rpc_chain_id == profile.chain_id
        )
    except Exception as exc:
        report.rpc_error = str(exc)
        logger.warning("Health check RPC call failed for %s: %s", profile.name, exc)

    if report.rpc_ok and profile.contracts.usdc:
        try:
            code = w3.eth.get_code(Web3.to_checksum_address(profile.contracts.usdc))
            report.usdc_contract_ok = len(code) > 0
        except Exception as exc:
            logger.warning("Health check USDC contract lookup failed: %s", exc)

    report.explorer_configured = profile.explorer_url is not None

    report.checks = [
        ("RPC reachable", report.rpc_ok),
        ("Chain ID matches", report.chain_id_match),
        ("USDC contract deployed", report.usdc_contract_ok),
        ("Explorer configured", report.explorer_configured),
    ]
    return report
