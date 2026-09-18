"""
Example 01 — Connect to Arc Mainnet.

Read-only — safe to run with no private key and no funds.

Run:
    python examples/mainnet/01_connect.py

Requires:
    ANTHROPIC_API_KEY in .env (required by arc_devkit.config at import time,
    even though this example itself never calls Claude)
"""

from arc_devkit import Arc


def main():
    arc = Arc.mainnet()  # Arc.testnet() for development — same API either way

    print(f"Network:    {arc.network.name}")
    print(f"Chain ID:   {arc.network.chain_id}")
    print(f"RPC:        {arc.network.rpc_url}")
    print(f"Explorer:   {arc.network.explorer_url}")
    print(
        f"Gas token:  {arc.network.native_currency_symbol} ({arc.network.native_currency_decimals} decimals)"
    )


if __name__ == "__main__":
    main()
