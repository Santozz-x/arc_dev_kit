"""
Example 05 — Look up a transaction on Arc Mainnet.

Read-only — safe to run with any real tx hash, no private key needed.

Run:
    python examples/mainnet/05_transaction.py 0xYourTxHash...
"""

import sys

from arc_devkit import Arc


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/mainnet/05_transaction.py 0xTxHash...")
        return

    tx_hash = sys.argv[1]
    arc = Arc.mainnet()

    tx = arc.get_transaction(tx_hash)
    receipt = arc.get_transaction_receipt(tx_hash)

    print(f"Hash:        {tx_hash}")
    print(f"From:        {tx['from']}")
    print(f"To:          {tx['to']}")
    print(f"Value (wei): {tx['value']}")
    print(f"Block:       #{tx['blockNumber']}")
    print(f"Status:      {'success' if receipt['status'] == 1 else 'reverted'}")
    print(f"Gas used:    {receipt['gasUsed']:,}")


if __name__ == "__main__":
    main()
