# Migrating an Existing Integration from Testnet to Mainnet

If you built against Arc DevKit before v0.9.0, here's what changed and what you need to do.

## 1. The default network changed

**Before:** `ARC_NETWORK` defaulted to `testnet`.
**Now:** `ARC_NETWORK` defaults to `mainnet`.

If your `.env` doesn't set `ARC_NETWORK` explicitly, your application now points at **real Arc Mainnet** instead of testnet the moment you upgrade. This is the one intentional breaking change in this release.

**Action:** if you want to keep developing against testnet, set explicitly:

```dotenv
ARC_NETWORK=testnet
```

## 2. RPC URLs are now pre-configured — you can delete your override

**Before:** `ARC_RPC_URL` was effectively required (testnet had a default, `https://arc-testnet.drpc.org`; mainnet had none).
**Now:** both networks have an official default (`rpc.mainnet.arc.io` / `rpc.testnet.arc.io`). `ARC_RPC_URL` is now optional — only set it to use a different provider.

**Action:** if your `.env` has `ARC_RPC_URL=https://arc-testnet.drpc.org`, you can remove it (the new official testnet default is `https://rpc.testnet.arc.io` — the old dRPC-branded URL may still resolve, but isn't the one this SDK defaults to anymore). If you deliberately want a specific provider, keep your override — explicit `ARC_RPC_URL` always wins.

## 3. `ARC_CHAIN_ID` is now optional — and never silently wrong

**Before:** if `ARC_CHAIN_ID` was unset and the network profile had no chain ID, `config.py` silently fell back to `5042002` (testnet's chain ID) — a latent bug where a misconfigured mainnet setup could resolve to the wrong chain ID without any error.
**Now:** `ARC_CHAIN_ID` is optional (both networks have real defaults: `5042` mainnet, `5042002` testnet) and the silent fallback is gone — if it genuinely can't be resolved, startup raises `OSError` instead of guessing.

**Action:** you can remove `ARC_CHAIN_ID` from your `.env` unless you're overriding it for a custom RPC.

## 4. USDC contract address — no more zero-address placeholder

**Before:** `USDCToken()` defaulted to `0x000...000` (Circle hadn't published a real address yet).
**Now:** `USDCToken()` defaults to `0x3600000000000000000000000000000000000000` — the real, official USDC ERC-20 address, identical on both networks.

**Action:** if you were passing a placeholder or workaround address explicitly, you can remove it and let the default resolve.

## 5. USDC has two balances now — native and ERC-20

New in this release: USDC is Arc's native gas token (18 decimals) *and* has an ERC-20 view (6 decimals) at the address above. If you were only ever reading the ERC-20 balance via `USDCToken.balance()`, nothing changes for you. If you want the native/gas balance, use the new `native_usdc_balance()` (or `arc.get_balance()` via the facade) — see [USDC.md](USDC.md).

## 6. New: the `Arc` facade

Optional, fully additive — every existing per-module import (`from arc_devkit.debugger import TxAnalyzer`, etc.) still works unchanged. `from arc_devkit import Arc` is a new, simpler entry point if you want it:

```python
from arc_devkit import Arc

arc = Arc.mainnet()  # or Arc.testnet()
```

## 7. New CLI safety prompts on mainnet

`arc send --broadcast` and `arcdevkit bridge send` now print a warning and ask for confirmation when the active network is mainnet (pass `--yes` to skip in scripts). This did not exist before — if you have automation that calls these commands non-interactively against mainnet, add `--yes`.

## 8. `arcdevkit doctor` / `arc doctor` is new

A one-command health check — see [CLI.md](CLI.md).

## Nothing else changed

Every other module — `TxAnalyzer`, `EventListener`, `ContractDeployer`, `contracts.loader`, `AgentRegistry`/`JobRegistry`, `PriceOracle`, `privacy.view_key` — is unchanged and network-agnostic by design; it already worked correctly against whatever network you pointed it at, and continues to.
