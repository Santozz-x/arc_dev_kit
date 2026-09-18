# Transaction Debugger

`TxAnalyzer` (and the `arc.debug_transaction()` facade method) combines on-chain data with Claude to explain what a transaction did, in plain language — including decoded revert reasons.

## Usage

```python
from arc_devkit import Arc

arc = Arc.mainnet()
report = arc.debug_transaction("0x...")

print(report["network"])         # "Arc Mainnet" or "Arc Testnet" — resolved from chain ID
print(report["status"])          # "success" or "reverted"
print(report["custo_usdc"])      # gas cost in USDC
print(report["revert_reason"])   # decoded reason, if reverted
print(report["summary"])         # AI-generated explanation
```

Or the lower-level API directly:

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()  # uses ARC_RPC_URL from .env
result = analyzer.analyze("0x...", abi=my_abi)  # abi enables input/custom-error decoding
```

CLI:

```bash
arcdevkit debug tx 0x...
arcdevkit debug batch 0xHash1... 0xHash2...
arcdevkit debug compare 0xHash1... 0xHash2...
```

## What it decodes

- Standard `require(condition, "message")` reverts (`Error(string)`)
- Solidity panics (`Panic(uint256)`) — overflow, division by zero, out-of-bounds array access, etc., translated to plain English
- Custom errors, when you pass the contract's ABI
- Unknown selectors — reported as raw hex rather than silently failing

## Every report is labeled by network

`report["network"]` is resolved from the RPC's reported chain ID against `arc_devkit.networks.NETWORKS`, not assumed. A mainnet transaction is always reported as `"Arc Mainnet"`, never generically as "Arc" or, worse, mislabeled testnet — this was a real bug before the mainnet migration (the AI prompt used to hardcode "testnet" regardless of the actual network).

## Arc-specific behavior the debugger accounts for

The AI analysis prompt includes Arc's EVM deviations (minimum 20 Gwei base fee, `SELFDESTRUCT` reverting on certain targets, no blob transaction support, etc. — see [TRANSACTIONS.md](TRANSACTIONS.md)) so explanations don't assume vanilla Ethereum behavior for a revert that's actually Arc-specific.

## `debug_traceTransaction` support

`trace_transaction()` calls `debug_traceTransaction` and returns `supported=False` with a clear message if the RPC has the `debug_*` namespace disabled — **this is the expected outcome on Circle's default RPC for both mainnet and testnet**, since the official RPC reference lists only State/Transactions/Blocks/Gas/Subscriptions methods, with no `debug_*` mentioned (unconfirmed either way from an official source — see [MIGRATION_AUDIT.md](MIGRATION_AUDIT.md) B.12/B.14). Third-party providers (e.g. Chainstack) advertise `debug_*`/`trace_*` support as a paid add-on; if you need call traces, use a provider that offers it and pass its RPC via `rpc_url=`.
