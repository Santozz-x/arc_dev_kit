"""
Example 09 — Send a native USDC payment on Arc Mainnet via PaymentAgent.

╔══════════════════════════════════════════════════════════════════════╗
║  WARNING: THIS EXAMPLE USES REAL FUNDS ON ARC MAINNET.                ║
║  Broadcasting the transaction below spends real (native, 18-decimal)  ║
║  USDC. Double-check the recipient and amount before confirming.       ║
║  Test the equivalent flow on Arc Testnet first.                       ║
╚══════════════════════════════════════════════════════════════════════╝

PaymentAgent.execute() simulates the transaction (eth_call) before
broadcasting, and aborts automatically if the simulation would revert.
Does NOT run automatically — requires ARC_PRIVATE_KEY and an explicit
CONFIRM=yes environment variable.

Run (after reading the warning above):
    CONFIRM=yes ARC_PRIVATE_KEY=0x... python examples/mainnet/09_send_transaction.py 0xRecipient... 1.0
"""

import os
import sys

from arc_devkit.agents.payment_agent import PaymentAgent
from arc_devkit.config import settings


def main():
    if len(sys.argv) < 3:
        print("Usage: python examples/mainnet/09_send_transaction.py 0xRecipient... <amount_usdc>")
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
    amount_usdc = float(sys.argv[2])

    print(f"Network: Arc {settings.arc_network.capitalize()}")
    print(f"Sending: {amount_usdc} USDC (native) to {recipient}")

    agent = PaymentAgent(private_key=private_key)
    result = agent.execute(
        to=recipient,
        amount_usdc=amount_usdc,
        enviar=True,  # broadcast — set to False to only sign and inspect first
        wait_receipt=True,
    )

    print(f"Status:  {result['status']}")
    if result.get("tx_hash"):
        print(f"Tx hash: {result['tx_hash']}")


if __name__ == "__main__":
    main()
