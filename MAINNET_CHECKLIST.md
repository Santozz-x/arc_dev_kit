# Arc DevKit — Mainnet Readiness Checklist

> **Historical planning document.** Arc Mainnet launched 2026-09-16 and this
> checklist's items were executed in v0.9.0 — see
> [`docs/mainnet/`](docs/mainnet/README.md) for the current, authoritative
> reference (network config, security, migration guide) and
> [`docs/mainnet/MAINNET_MIGRATION_REPORT.md`](docs/mainnet/MAINNET_MIGRATION_REPORT.md)
> for the full validation status. Kept here, checked off, as a record of what
> this checklist asked for vs. what shipped — not superseding the newer docs.

## 1. Network configuration

- [x] `arc_devkit/networks.py` — `NETWORKS["mainnet"]` filled in with real values:
  - [x] `chain_id` (`5042`)
  - [x] `rpc_url` (`https://rpc.mainnet.arc.io`)
  - [x] `explorer_url` (`https://explorer.arc.io`)
  - [x] `contracts.usdc`
  - [x] `contracts.eurc`
  - [x] `contracts.cctp_token_messenger` + documented CCTP domain ID (26)
  - [x] `contracts.gateway` (now `gateway_wallet`/`gateway_minter`, `gateway` kept as a deprecated alias)
- [x] `arcdevkit network check-mainnet` reports all checks configured (verified live against real mainnet, 2026-09-18)
- [x] Dry-run confirmed: `arcdevkit status`/`arcdevkit doctor` connect successfully with no `ARC_RPC_URL` override, against real mainnet
- [x] **Superseded, deliberately:** the default was flipped from `testnet` to
      `mainnet` in v0.9.0 — a conscious decision (not an oversight), made
      because Arc Mainnet is now live and stable enough to be the SDK's
      primary target, and protected by the new mainnet confirmation prompts
      in the CLI. See `docs/mainnet/MIGRATION_FROM_TESTNET.md`.

## 2. Contract address validation

- [x] Every mainnet address cross-checked against `docs.arc.io` — extracted
      from raw HTML and verified byte-for-byte (not just AI-summarized) — see
      `docs/mainnet/MIGRATION_AUDIT.md` Part B.7
- [x] `arc_devkit/stablecoins/token.py` — the old
      `USDC_ARC_TESTNET_ADDRESS` zero-address placeholder is gone; `core/gas.py`,
      `agents/payment_agent.py`, and `bridge/cctp.py` all resolve USDC from
      the active network's config instead of a hardcoded address
- [ ] `arc_devkit/paymaster/detector.py` — **not updated**, `detect_paymaster()`
      still always returns `available=False`; no Arc paymaster/bundler has
      been published as of 2026-09-18
- [ ] `arc_devkit/agents/identity.py` / `jobs.py` — **not confirmed**; no
      canonical Arc ERC-8004/ERC-8183 registry address was found during this
      migration — these remain bring-your-own-registry

## 3. Guardrails & safety defaults

- [x] Guardrails guidance strengthened — `docs/mainnet/SECURITY.md` and
      `docs/mainnet/WALLETS.md` now state explicitly that guardrails are
      opt-in and empty by default, with a pre-transaction checklist
- [ ] `ENV=production` API behavior — **not re-verified** in this pass (unchanged from prior release)
- [ ] `bandit`/`pip-audit` security sweep — **not run** in this pass; recommended before a production mainnet deployment

## 4. Breaking-change communication

- [x] `CHANGELOG.md` — `[0.9.0]` section documents the mainnet default flip as the release's one breaking change
- [x] `docs/mainnet/NETWORK_CONFIG.md` documents that testnet/mainnet EURC and CCTP/Gateway contract addresses differ (USDC, Multicall3, Permit2, CREATE2 factory, Memo, and Multicall3From are identical on both)
- [x] Versioned as **0.9.0** (MINOR, not MAJOR) — the package is still
      `Development Status :: 3 - Alpha` / pre-1.0, where SemVer 0.x convention
      allows a MINOR bump to carry behavior changes; MAJOR is reserved for the
      1.0 stabilization milestone in section 5 below. This was a deliberate
      choice, not an oversight of this checklist's original "major bump" note.

## 5. Path to v1.0

- [ ] All items above checked for at least one full release cycle on mainnet without a rollback
- [x] `arcdevkit network check-mainnet` green against real mainnet config (verified 2026-09-18; not yet wired into CI against live mainnet)
- [ ] No outstanding "not published yet" placeholders for bridge/paymaster/agent-economy — paymaster and ERC-8004/8183 registries remain unpublished as of 2026-09-18
