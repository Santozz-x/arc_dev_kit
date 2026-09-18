# Getting Started on Arc Mainnet

## Install

```bash
pip install arc-devkit
```

Requires Python 3.11+.

## Configure

```bash
cp .env.example .env
```

Fill in `ANTHROPIC_API_KEY` (required by `arc_devkit.config` at import time — get one at [console.anthropic.com](https://console.anthropic.com)). Everything else is optional:

- `ARC_NETWORK` — `mainnet` (the SDK default, no need to set it) or `testnet`.
- `ARC_RPC_URL` / `ARC_CHAIN_ID` — only set these to override the network's official default (e.g. to use your own Alchemy/QuickNode endpoint). Leave blank to use Circle's default RPC.
- `ARC_PRIVATE_KEY` — only needed to sign and send transactions. **Never commit this.**

## Your first read

```python
from arc_devkit import Arc

arc = Arc.mainnet()

print(arc.network.name, arc.network.chain_id)   # mainnet 5042
print(arc.latest_block()["number"])
print(arc.get_balance("0xYourAddress..."))       # native USDC balance (18 decimals)
```

This makes a real, read-only call to `https://rpc.mainnet.arc.io` — no private key, no funds, no risk.

## Check the CLI works

```bash
arcdevkit status
arcdevkit doctor
```

`doctor` runs a full health check: RPC reachability, chain ID match, latest block, latency, and that the USDC contract actually has code deployed on-chain — see [CLI.md](CLI.md).

## Developing safely — use testnet

Point everything at Arc Testnet while you build, by setting one variable:

```dotenv
ARC_NETWORK=testnet
```

Get free test USDC from the official faucet: [faucet.circle.com](https://faucet.circle.com) (select "Arc Testnet"). Every example in [`examples/mainnet/`](../../examples/mainnet/) works identically against testnet — just swap `Arc.mainnet()` for `Arc.testnet()`.

## Your first transaction (mainnet, real funds)

Only do this once you've tested the equivalent flow on testnet. See [SECURITY.md](SECURITY.md) first.

```bash
arc send 0xRecipient... 1.0 --broadcast
```

The CLI will print `Network: ARC MAINNET` and `WARNING: This transaction uses real funds.` and ask you to confirm before broadcasting. Pass `--yes` to skip the prompt in scripts/automation once you've verified the flow works.

## Next steps

- [NETWORK_CONFIG.md](NETWORK_CONFIG.md) — full network reference
- [USDC.md](USDC.md) — USDC's native vs. ERC-20 interface
- [TRANSACTION_DEBUGGER.md](TRANSACTION_DEBUGGER.md) — AI-assisted debugging
- [`examples/mainnet/`](../../examples/mainnet/) — 10 runnable scripts, from read-only to contract deployment
