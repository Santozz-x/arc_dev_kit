"""
Example 07 — Read from a deployed contract on Arc Mainnet.

Uses Multicall3 (https://www.multicall3.com), a standard contract deployed
at the same address on virtually every EVM chain including Arc — see
docs/mainnet/MIGRATION_AUDIT.md Part B.7 for the verified address.

Read-only — safe to run, no private key needed.

Run:
    python examples/mainnet/07_contract_read.py
"""

from arc_devkit import Arc

_MULTICALL3_ABI = [
    {
        "inputs": [],
        "name": "getBlockNumber",
        "outputs": [{"name": "blockNumber", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "getChainId",
        "outputs": [{"name": "chainid", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def main():
    arc = Arc.mainnet()
    multicall3 = arc.contract(arc.network.contracts.multicall3, _MULTICALL3_ABI)

    block_number = multicall3.call("getBlockNumber")
    chain_id = multicall3.call("getChainId")

    print(f"Multicall3 address: {multicall3.address}")
    print(f"Block number (via contract call): #{block_number:,}")
    print(f"Chain ID (via contract call):      {chain_id}")


if __name__ == "__main__":
    main()
