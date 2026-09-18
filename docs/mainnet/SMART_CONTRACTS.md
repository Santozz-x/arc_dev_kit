# Smart Contracts on Arc

Arc is fully EVM-compatible — Solidity, Hardhat, Foundry, and standard ABI/bytecode workflows work unmodified. Arc DevKit's contract tooling is network-agnostic by design: nothing below needed to change for mainnet support beyond the network config itself (see [NETWORK_CONFIG.md](NETWORK_CONFIG.md)).

## Quick path — the `Arc` facade

```python
from arc_devkit import Arc

arc = Arc.mainnet()
contract = arc.contract(address="0x...", abi=abi)

balance = contract.call("balanceOf", "0xAddress...")           # read
tx_hash = contract.send("transfer", "0xTo...", 100, private_key=KEY)  # write
```

See [`examples/mainnet/07_contract_read.py`](../../examples/mainnet/07_contract_read.py) for a live example reading Multicall3 (`arc.network.contracts.multicall3`).

## Lower-level API

```python
from arc_devkit.contracts.loader import load_abi, call_view, send_tx, decode_events

abi = load_abi("MyContract.json")

result = call_view(abi, "0xContract...", "balanceOf", "0xAddress...")
tx_hash = send_tx(abi, "0xContract...", "transfer", PRIVATE_KEY, "0xTo...", 100)

events = decode_events(abi, receipt, "Transfer")
```

## Deploying

```python
from arc_devkit.deploy.deployer import ContractDeployer

deployer = ContractDeployer(private_key=PRIVATE_KEY)

# From pre-compiled ABI + bytecode (Hardhat/Foundry output)
result = deployer.deploy(abi=abi, bytecode=bytecode)

# Or compile Solidity source directly (requires `pip install py-solc-x`)
result = deployer.deploy_from_source("MyContract.sol", "MyContract", constructor_args=[...])

print(result.contract_address, result.tx_hash, result.gas_used)
```

See [`examples/mainnet/10_deploy_contract.py`](../../examples/mainnet/10_deploy_contract.py) — it compiles and deploys a real minimal contract, gated behind `CONFIRM=yes` since deployment is irreversible and costs real gas on mainnet.

## Standard contracts already deployed on Arc

Several well-known EVM standard contracts are deployed at their usual addresses on both Arc networks (same as most EVM chains) — see the full table in [NETWORK_CONFIG.md](NETWORK_CONFIG.md):

- **Multicall3** (`0xcA11bde0...`) — batch read calls
- **CREATE2 Factory** (Arachnid, `0x4e59b448...`) — deterministic deployment
- **Permit2** (`0x00000000...`) — signature-based approvals

## Events

```python
from arc_devkit.events.listener import EventListener

listener = EventListener(contract_address="0x...", abi=abi)
listener.on("Transfer", lambda event: print(event))
listener.start_polling(interval=5)  # blocking
```

`EventListener` polls `eth_getLogs` — no Arc-specific behavior, works identically on mainnet and testnet.

## Mainnet safety

Every write in this document (`send_tx`, `contract.send()`, `ContractDeployer.deploy*`) moves real funds and, for deployment, is irreversible once broadcast. See [SECURITY.md](SECURITY.md) before running any of these against mainnet with a funded key.
