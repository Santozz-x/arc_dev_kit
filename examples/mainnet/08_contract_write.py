"""
Example 08 — Write to a contract on Arc Mainnet (state-changing call).

╔══════════════════════════════════════════════════════════════════════╗
║  WARNING: THIS EXAMPLE USES REAL FUNDS ON ARC MAINNET.                ║
║  Broadcasting the transaction below spends real USDC (for gas) and    ║
║  moves real ERC-20 USDC. Double-check the recipient and amount.       ║
║  Test the equivalent flow on Arc Testnet first (Arc.testnet()).       ║
╚══════════════════════════════════════════════════════════════════════╝

Calls transfer() on the USDC ERC-20 contract via arc.contract(...).send(...).
Does NOT run automatically — requires ARC_PRIVATE_KEY and an explicit
CONFIRM=yes environment variable, so it can never fire by accident.

Run (after reading the warning above):
    CONFIRM=yes ARC_PRIVATE_KEY=0x... python examples/mainnet/08_contract_write.py 0xRecipient... 1.0
"""

import os
import sys
from decimal import Decimal

from arc_devkit import Arc

_ERC20_TRANSFER_ABI = [
    {
        "constant": False,
        "inputs": [
            {"name": "_to", "type": "address"},
            {"name": "_value", "type": "uint256"},
        ],
        "name": "transfer",
        "outputs": [{"name": "", "type": "bool"}],
        "type": "function",
    },
]


def main():
    if len(sys.argv) < 3:
        print("Usage: python examples/mainnet/08_contract_write.py 0xRecipient... <amount_usdc>")
        return

    if os.environ.get("CONFIRM") != "yes":
        print("Refusing to run — this sends real funds on Arc Mainnet.")
        print("Re-run with CONFIRM=yes once you've verified the recipient and amount.")
        return

    private_key = os.environ.get("ARC_PRIVATE_KEY")
    if not private_key:
        print("ARC_PRIVATE_KEY is required to sign this transaction.")
        return

    recipient = sys.argv[1]
    amount_usdc = Decimal(sys.argv[2])
    atomic_amount = int(amount_usdc * Decimal(10**6))  # USDC ERC-20 uses 6 decimals

    arc = Arc.mainnet()
    usdc_contract = arc.contract(arc.network.contracts.usdc, _ERC20_TRANSFER_ABI)

    print(f"Network:   {arc.network.name}")
    print(f"Sending:   {amount_usdc} USDC to {recipient}")
    tx_hash = usdc_contract.send("transfer", recipient, atomic_amount, private_key=private_key)
    print(f"Tx hash:   {tx_hash}")
    print(f"Explorer:  {arc.network.explorer_url}/tx/{tx_hash}")


if __name__ == "__main__":
    main()
