# CLI Reference — Mainnet Behavior

Two entry points, same underlying commands: `arc` (flat, direct commands) and `arcdevkit` (grouped subcommands). Both default to **Arc Mainnet** unless `ARC_NETWORK=testnet` is set.

## Network-aware commands

```bash
arc status          # or: arcdevkit status
```

Shows the active network by name, with a visual distinction — **red accent and an explicit "⚠ Real funds — mainnet" line** when connected to mainnet, cyan/no warning on testnet. Chain ID, current block, and gas price come from the live RPC, never hardcoded.

```bash
arc doctor           # or: arcdevkit doctor
```

Full health check — RPC reachability, chain ID match (RPC-reported vs. expected), latest block, latency, whether the USDC contract actually has code deployed (`eth_getCode`, not just "is an address configured"), and whether an explorer URL is set. Exits non-zero if anything fails, so it's CI-friendly:

```
Arc DevKit Doctor

Network:       Arc Mainnet
RPC:           OK https://rpc.mainnet.arc.io
Chain ID:      OK expected 5042, RPC reports 5042
Latest block:  21514192
Latency:       191.6 ms
USDC contract: OK
Explorer:      OK https://explorer.arc.io

Status: READY
```

```bash
arcdevkit network list                 # both networks, config-at-a-glance
arcdevkit network show mainnet         # full contract address table
arcdevkit network show testnet
arcdevkit network check-mainnet        # dry-run: fails if any mainnet field is a placeholder
```

## Sending real funds — the confirmation gate

```bash
arc send 0xRecipient... 1.0 --broadcast
```

On mainnet, this prints:

```
Network: ARC MAINNET
WARNING: This transaction uses real funds.
  Sending 1.0 ARC to 0xRecipient...

Broadcast this transaction on Arc Mainnet? [y/N]:
```

and aborts (exit code 1) unless you confirm or pass `--yes` / `-y`. **Testnet never prompts** — it's assumed to be a safe development flow. The same gate applies to `arcdevkit bridge send` (CCTP cross-chain transfers), since those are even harder to reverse than a same-chain send.

```bash
arc send 0xRecipient... 1.0 --broadcast --yes    # for scripts/automation
```

## Everything else

Every other command (`copilot ask`, `agent wallet create`, `debug tx`, `portfolio analyze`, `fees quote`, `contracts`, `oracle price`, `privacy`, `mcp serve`) works identically on both networks — they all read the active network from `settings.network`/`settings.arc_network`, resolved once at startup from `ARC_NETWORK`.

## Known limitation

There is currently **no per-command `--network` override flag** (e.g. `arc --network testnet status`) — switching networks requires changing `ARC_NETWORK` in `.env` (or the shell environment) before invoking the CLI. This is tracked as a follow-up; see [MAINNET_MIGRATION_REPORT.md](MAINNET_MIGRATION_REPORT.md) Known Limitations.
