# RPC Migration Guide — `rpc.arc.io` → `arc-testnet.drpc.org` (historical, pre-v0.2)

> **Looking for the Arc Mainnet migration guide?** This page documents an old,
> unrelated pre-v0.2 testnet RPC change. For moving from testnet to mainnet
> (or updating from the now-superseded `arc-testnet.drpc.org` testnet default
> to Circle's current official `https://rpc.testnet.arc.io`), see
> [`docs/mainnet/MIGRATION_FROM_TESTNET.md`](mainnet/MIGRATION_FROM_TESTNET.md)
> and [`docs/mainnet/NETWORK_CONFIG.md`](mainnet/NETWORK_CONFIG.md) instead.

This note documents the breaking change in how you connect to the Arc testnet.

## What changed

| | Old (pre-v0.2) | New (v0.2+) |
|---|---|---|
| **RPC URL** | `https://rpc.arc.io` | `https://arc-testnet.drpc.org` |
| **Chain ID** | `12345` (placeholder) | `5042002` |
| **Gas token** | ETH-like | USDC (6 decimals) |

The old endpoint `rpc.arc.io` is no longer reachable. All Arc DevKit versions from
v0.2 onwards target the dRPC-hosted testnet endpoint.

## Steps to migrate

### 1. Update your `.env`

```bash
# Before
ARC_RPC_URL=https://rpc.arc.io
ARC_CHAIN_ID=12345

# After
ARC_RPC_URL=https://arc-testnet.drpc.org
ARC_CHAIN_ID=5042002
```

Run the interactive wizard to regenerate from scratch:

```bash
arc init
```

### 2. Re-verify connectivity

```bash
arc status
```

Expected output:

```
╭─ Arc Testnet ──────────────────────╮
│ Status        ✓ connected           │
│ Network       Arc Testnet           │
│ Chain ID      5042002               │
│ Current block #<latest>             │
│ Gas price     <n> gwei              │
╰─────────────────────────────────────╯
```

### 3. Update hardcoded chain IDs

If your code hardcodes `12345` anywhere, replace with `5042002`:

```python
# Before
tx = {"chainId": 12345, ...}

# After
tx = {"chainId": 5042002, ...}

# Best practice — read from config
from arc_devkit.config import settings
tx = {"chainId": settings.arc_chain_id, ...}
```

### 4. Gas token change

On the new testnet USDC is the gas token (6 decimal precision).
Arc DevKit handles this internally — `PaymentAgent` and `USDCToken` both
use 6 decimals for USDC. No action needed unless you calculate gas costs manually.

## Multiple RPC fallbacks

Arc DevKit supports comma-separated fallback URLs:

```env
ARC_RPC_URL=https://arc-testnet.drpc.org,https://backup-rpc.example.com
```

The `BaseAgent` will automatically retry on the next URL if the primary fails.
