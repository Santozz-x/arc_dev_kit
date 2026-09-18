"""
Example 04 — Read USDC via both interfaces on Arc Mainnet: native vs. ERC-20.

USDC on Arc has a dual interface (see docs/mainnet/USDC.md):
  - Native (like ETH): 18 decimals, read via eth_getBalance — arc.get_balance()
  - ERC-20 (precompile at 0x3600...0000): 6 decimals, read via balanceOf() —
    arc.usdc.balance()
Both represent the SAME underlying funds. This example prints both so you can
see they track the same balance at different decimal scales — never mix them.

Read-only — safe to run with any public address, no private key needed.

Run:
    python examples/mainnet/04_usdc_balance.py 0xYourAddress...
"""

import sys

from arc_devkit import Arc


def main():
    address = sys.argv[1] if len(sys.argv) > 1 else "0x0000000000000000000000000000000000000000"

    arc = Arc.mainnet()

    native = arc.get_balance(address)
    erc20 = arc.usdc.balance(address)

    print(f"Address: {address}")
    print(f"Native USDC (18 decimals, gas token): {native} USDC")
    print(f"ERC-20 USDC (6 decimals, balanceOf):   {erc20} USDC")
    print(f"USDC contract address: {arc.usdc.contract_address}")


if __name__ == "__main__":
    main()
