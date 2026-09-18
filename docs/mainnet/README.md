# Arc Mainnet Documentation

Arc DevKit is an open-source developer toolkit for building, debugging, and interacting with applications on **Arc Mainnet** — Circle's EVM-compatible Layer 1 blockchain, launched 2026-09-16, with USDC as the native gas token. Arc Testnet remains fully supported for development.

## Start here

- **[GETTING_STARTED.md](GETTING_STARTED.md)** — install, configure, and run your first mainnet read in under five minutes.
- **[NETWORK_CONFIG.md](NETWORK_CONFIG.md)** — chain IDs, RPC/WS URLs, explorers, and every contract address, each with its official source.
- **[SECURITY.md](SECURITY.md)** — read this before sending your first real transaction.

## Reference

| Doc | Covers |
|---|---|
| [USDC.md](USDC.md) | USDC's dual native/ERC-20 interface, balances, transfers, allowance |
| [TRANSACTIONS.md](TRANSACTIONS.md) | Reading, sending, and waiting for transactions |
| [GAS_AND_FEES.md](GAS_AND_FEES.md) | Fee quoting, gas estimation, Arc's fee model |
| [SMART_CONTRACTS.md](SMART_CONTRACTS.md) | Loading ABIs, calling/sending, deploying, decoding events |
| [WALLETS.md](WALLETS.md) | Key management, signing, hardware/PQ signer roadmap |
| [TRANSACTION_DEBUGGER.md](TRANSACTION_DEBUGGER.md) | AI-assisted transaction diagnosis |
| [CLI.md](CLI.md) | Every `arc`/`arcdevkit` command, mainnet vs. testnet behavior |
| [MIGRATION_FROM_TESTNET.md](MIGRATION_FROM_TESTNET.md) | Moving an existing testnet integration to mainnet |

## How this documentation was produced

- **[MIGRATION_AUDIT.md](MIGRATION_AUDIT.md)** — the full audit of every testnet assumption in the codebase (Part A) and the sourced, verified official Arc Mainnet configuration (Part B) that this entire migration is built on.
- **[MAINNET_IMPLEMENTATION_PLAN.md](MAINNET_IMPLEMENTATION_PLAN.md)** — the 12-phase plan executed to add mainnet support.
- **[ARC_DEVKIT_ARCHITECTURE.md](ARC_DEVKIT_ARCHITECTURE.md)** — how the SDK is organized and what changed.
- **[MAINNET_MIGRATION_REPORT.md](MAINNET_MIGRATION_REPORT.md)** — the final report: what was built, what was validated live against mainnet, and what is explicitly **not** validated yet.

## Quickstart

```bash
pip install arc-devkit
cp .env.example .env   # fill in ANTHROPIC_API_KEY
```

```python
from arc_devkit import Arc

arc = Arc.mainnet()
print(arc.latest_block()["number"])

tx = arc.get_transaction("0x...")
report = arc.debug_transaction("0x...")
```

No manual RPC, chain ID, or contract address lookup required — see [NETWORK_CONFIG.md](NETWORK_CONFIG.md) for what's pre-configured and where each value came from.
