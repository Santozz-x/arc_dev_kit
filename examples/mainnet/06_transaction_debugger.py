"""
Example 06 — AI-assisted transaction debugging on Arc Mainnet.

Fetches full transaction + receipt data and asks Claude (via DevCopilot) to
explain what happened, in plain language — including any revert reason.

Read-only (never signs or sends anything) — safe to run with any real tx
hash. Requires ANTHROPIC_API_KEY for the AI summary (pass use_ai=False to
skip it and only inspect raw on-chain data).

Run:
    python examples/mainnet/06_transaction_debugger.py 0xYourTxHash...
"""

import sys

from arc_devkit import Arc


def main():
    if len(sys.argv) < 2:
        print("Usage: python examples/mainnet/06_transaction_debugger.py 0xTxHash...")
        return

    tx_hash = sys.argv[1]
    arc = Arc.mainnet()

    report = arc.debug_transaction(tx_hash)

    print(f"Network:  {report['network']}")
    print(f"Status:   {report['status']}")
    print(f"Cost:     {report['custo_usdc']} USDC")
    if report["revert_reason"]:
        print(f"Revert:   {report['revert_reason']}")
    print("\nAI summary:")
    print(report["summary"])


if __name__ == "__main__":
    main()
