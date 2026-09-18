"""Registry of Arc network profiles and per-network contract addresses.

All values below come from Circle's official Arc documentation
(https://docs.arc.io/arc/references/rpc-endpoints and
https://docs.arc.io/arc/references/contract-addresses), verified byte-for-byte
against the raw page content on 2026-09-18 — see docs/mainnet/MIGRATION_AUDIT.md
Part B for the full sourcing. Arc Mainnet launched 2026-09-16.
"""

from dataclasses import dataclass

# USDC's ERC-20 interface address — identical on mainnet and testnet. This is
# a fixed precompile: USDC is also Arc's *native* gas token (18 decimals,
# read via eth_getBalance), and this address exposes a synchronized 6-decimal
# ERC-20 view of the same underlying balance for compatibility with existing
# tooling. Never treat the two balances as interchangeable without converting
# — see arc_devkit.stablecoins.token for the native vs. ERC-20 split.
USDC_ERC20_ADDRESS = "0x3600000000000000000000000000000000000000"

# Native USDC gas token decimals (distinct from the 6-decimal ERC-20 view above).
NATIVE_USDC_DECIMALS = 18


@dataclass(frozen=True)
class ContractAddresses:
    """Known contract addresses for a given Arc network.

    usdc is always USDC_ERC20_ADDRESS (identical on both networks) — kept as
    a field rather than a bare constant so callers only ever need to read
    settings.network.contracts.usdc, never import the constant directly.
    """

    usdc: str | None
    eurc: str | None
    cctp_token_messenger: str | None
    # Deprecated alias — pre-mainnet callers used a single "gateway" field
    # before Gateway Wallet/Minter were published separately. Kept for
    # backward compatibility; new code should use gateway_wallet/gateway_minter.
    gateway: str | None = None
    cctp_message_transmitter: str | None = None
    cctp_token_minter: str | None = None
    cctp_message: str | None = None
    cctp_domain: int | None = None
    gateway_wallet: str | None = None
    gateway_minter: str | None = None
    multicall3: str | None = None
    permit2: str | None = None


@dataclass(frozen=True)
class NetworkProfile:
    """A named Arc network profile: chain ID, RPC, explorer, and contracts."""

    name: str
    chain_id: int | None
    rpc_url: str | None
    explorer_url: str | None
    contracts: ContractAddresses
    ws_rpc_url: str | None = None
    native_currency_symbol: str = "USDC"
    native_currency_decimals: int = NATIVE_USDC_DECIMALS


DEFAULT_NETWORK = "mainnet"

NETWORKS: dict[str, NetworkProfile] = {
    "mainnet": NetworkProfile(
        name="mainnet",
        chain_id=5042,
        rpc_url="https://rpc.mainnet.arc.io",
        ws_rpc_url=None,  # Circle's primary mainnet RPC is HTTP-only.
        explorer_url="https://explorer.arc.io",
        contracts=ContractAddresses(
            usdc=USDC_ERC20_ADDRESS,
            eurc="0xbEf5f6d51CB62b58e6A8f77868681825C6fe21c1",
            cctp_token_messenger="0x28b5a0e9C621a5BadaA536219b3a228C8168cf5d",
            cctp_message_transmitter="0x81D40F21F12A8F0E3252Bccb954D722d4c464B64",
            cctp_token_minter="0xfd78EE919681417d192449715b2594ab58f5D002",
            cctp_message="0xec546b6B005471ECf012e5aF77FBeC07e0FD8f78",
            cctp_domain=26,
            gateway_wallet="0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE",
            gateway_minter="0x2222222d7164433c4C09B0b0D809a9b52C04C205",
            multicall3="0xcA11bde05977b3631167028862bE2a173976CA11",
            permit2="0x000000000022D473030F116dDEE9F6B43aC78BA3",
            gateway="0x77777777Dcc4d5A8B6E418Fd04D8997ef11000eE",
        ),
    ),
    "testnet": NetworkProfile(
        name="testnet",
        chain_id=5042002,
        rpc_url="https://rpc.testnet.arc.io",
        ws_rpc_url="wss://rpc.testnet.arc.io",
        explorer_url="https://explorer.testnet.arc.io",
        contracts=ContractAddresses(
            usdc=USDC_ERC20_ADDRESS,
            eurc="0x89B50855Aa3bE2F677cD6303Cec089B5F319D72a",
            cctp_token_messenger="0x8FE6B999Dc680CcFDD5Bf7EB0974218be2542DAA",
            cctp_message_transmitter="0xE737e5cEBEEBa77EFE34D4aa090756590b1CE275",
            cctp_token_minter="0xb43db544E2c27092c107639Ad201b3dEfAbcF192",
            cctp_message="0xbaC0179bB358A8936169a63408C8481D582390C4",
            cctp_domain=26,
            gateway_wallet="0x0077777d7EBA4688BDeF3E311b846F25870A19B9",
            gateway_minter="0x0022222ABE238Cc2C7Bb1f21003F0a260052475B",
            multicall3="0xcA11bde05977b3631167028862bE2a173976CA11",
            permit2="0x000000000022D473030F116dDEE9F6B43aC78BA3",
            gateway="0x0077777d7EBA4688BDeF3E311b846F25870A19B9",
        ),
    ),
}


def get_network(name: str) -> NetworkProfile:
    """Return the network profile for `name`, raising ValueError if unknown."""
    try:
        return NETWORKS[name]
    except KeyError:
        known = ", ".join(sorted(NETWORKS))
        raise ValueError(f"Unknown Arc network {name!r}. Known networks: {known}.") from None
