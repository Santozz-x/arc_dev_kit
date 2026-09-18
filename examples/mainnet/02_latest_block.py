"""
Example 02 — Read the latest block on Arc Mainnet.

Read-only — safe to run with no private key and no funds.

Run:
    python examples/mainnet/02_latest_block.py
"""

from arc_devkit import Arc


def main():
    arc = Arc.mainnet()

    block = arc.latest_block()

    print(f"Block number:   #{block['number']:,}")
    print(f"Block hash:     {block['hash'].hex()}")
    print(f"Timestamp:      {block['timestamp']}")
    print(f"Transactions:   {len(block['transactions'])}")
    print(f"Gas used:       {block['gasUsed']:,} / {block['gasLimit']:,}")


if __name__ == "__main__":
    main()
