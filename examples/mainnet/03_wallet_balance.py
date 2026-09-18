"""
Example 03 — Check a wallet's native USDC balance on Arc Mainnet.

USDC is Arc's native gas token, read the same way ETH would be on any other
EVM chain (eth_getBalance) — but at 18 decimals, not the 6 decimals of the
ERC-20 view (see 04_usdc_balance.py for that).

Read-only — safe to run with any public address, no private key needed.

Run:
    python examples/mainnet/03_wallet_balance.py 0xYourAddress...
"""

import sys

from arc_devkit import Arc


def main():
    address = sys.argv[1] if len(sys.argv) > 1 else "0x0000000000000000000000000000000000000000"

    arc = Arc.mainnet()
    balance = arc.get_balance(address)

    print(f"Address: {address}")
    print(f"Native USDC balance (gas token, 18 decimals): {balance} USDC")


if __name__ == "__main__":
    main()
