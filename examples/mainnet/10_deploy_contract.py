"""
Example 10 — Deploy a contract on Arc Mainnet.

╔══════════════════════════════════════════════════════════════════════╗
║  WARNING: THIS EXAMPLE USES REAL FUNDS ON ARC MAINNET.                ║
║  Deploying a contract spends real USDC for gas and is IRREVERSIBLE —  ║
║  the deployed contract's code and address are permanent. Test on Arc  ║
║  Testnet first, and audit any contract before deploying it to real    ║
║  users' funds.                                                        ║
╚══════════════════════════════════════════════════════════════════════╝

Compiles and deploys contracts/Greeter.sol, a trivial example contract, via
ContractDeployer.deploy_from_source() — solc compiles the real bytecode on
your machine, nothing is hand-crafted or guessed. For your own contracts,
point contract_name/source_path at your own .sol file.

Requires: pip install py-solc-x (downloads the solc compiler on first run).
Does NOT run automatically — requires ARC_PRIVATE_KEY and an explicit
CONFIRM=yes environment variable.

Run (after reading the warning above):
    CONFIRM=yes ARC_PRIVATE_KEY=0x... python examples/mainnet/10_deploy_contract.py
"""

import os
from pathlib import Path

from arc_devkit.config import settings
from arc_devkit.deploy.deployer import ContractDeployer

_SOURCE = Path(__file__).parent / "contracts" / "Greeter.sol"


def main():
    if os.environ.get("CONFIRM") != "yes":
        print("Refusing to run — this deploys a contract with real funds on Arc Mainnet.")
        print("Re-run with CONFIRM=yes once you understand the cost and irreversibility.")
        return

    private_key = os.environ.get("ARC_PRIVATE_KEY")
    if not private_key:
        print("ARC_PRIVATE_KEY is required to deploy.")
        return

    print(f"Network: Arc {settings.arc_network.capitalize()}")
    print(f"Compiling and deploying {_SOURCE.name}...")

    deployer = ContractDeployer(private_key=private_key)
    result = deployer.deploy_from_source(
        source_path=_SOURCE,
        contract_name="Greeter",
        constructor_args=["Hello from Arc DevKit"],
    )

    print(f"Contract address: {result.contract_address}")
    print(f"Tx hash:           {result.tx_hash}")
    print(f"Gas used:          {result.gas_used:,}")
    print(f"Explorer:          {settings.network.explorer_url}/address/{result.contract_address}")


if __name__ == "__main__":
    main()
