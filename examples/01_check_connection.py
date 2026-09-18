"""
Example 01 — Check connection to the Arc testnet.

Run:
    python examples/01_check_connection.py

Requires:
    ARC_RPC_URL in .env (e.g. https://rpc.testnet.arc.io)
"""

from arc_devkit.core.connection import check_connection, get_web3


def main():
    print("Checking connection to Arc testnet...\n")

    if not check_connection():
        print("Connection failed. Check ARC_RPC_URL in .env.")
        return

    w3 = get_web3()

    block = w3.eth.block_number
    chain_id = w3.eth.chain_id
    gas_price_gwei = w3.from_wei(w3.eth.gas_price, "gwei")

    print("Connected!")
    print(f"  Current block:  #{block:,}")
    print(f"  Chain ID:       {chain_id}")
    print(f"  Gas price:      {gas_price_gwei} gwei")


if __name__ == "__main__":
    main()
