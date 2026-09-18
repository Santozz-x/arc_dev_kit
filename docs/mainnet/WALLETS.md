# Wallets and Signing

## Creating a wallet

```python
from arc_devkit.core.wallet import create_wallet

wallet = create_wallet()
print(wallet["address"])       # checksummed EVM address
print(wallet["private_key"])   # 0x-prefixed hex — shown once, store it securely
```

```bash
arc wallet create
```

The private key is generated locally and never transmitted anywhere — Arc DevKit does not phone home. It is your responsibility to store it securely once printed.

## Key resolution order

Every agent/facade that signs transactions resolves the private key the same way: **explicit argument → `ARC_PRIVATE_KEY` env var → OS keyring → read-only mode** (no signing capability, reads still work).

```python
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key="0x...")        # explicit
agent = PaymentAgent()                            # falls back to ARC_PRIVATE_KEY / keyring
```

## Never do this

- **Never** hardcode a private key in source code.
- **Never** commit `.env` (it's in `.gitignore` by default — verify before your first commit).
- **Never** log a private key. Arc DevKit's logging never includes private keys or raw signed transactions containing them; keep any custom logging you add to the same standard.
- **Never** reuse a mainnet key for testnet development, or vice versa — keep them fully separate so a testnet mistake can't touch real funds.

## Mainnet vs. testnet keys

Since Arc DevKit now defaults to mainnet, it's easy to accidentally sign a real transaction while intending to test. Two independent safety nets exist:

1. **CLI confirmation** — `arc send --broadcast` and `arcdevkit bridge send` print `Network: ARC MAINNET` / `WARNING: This transaction uses real funds.` and require interactive confirmation (or `--yes`) before broadcasting on mainnet. Testnet does not prompt.
2. **`config.py` chain ID validation** — `ARC_CHAIN_ID` is never silently defaulted to another network's value; if it can't be resolved, `Settings` raises at startup rather than guessing.

See [SECURITY.md](SECURITY.md) for the full list of protections.

## Pluggable signers (roadmap)

`arc_devkit.core.signer` defines a `Signer` ABC (`address` property + `sign_transaction()`). `LocalKeySigner` — wrapping `eth_account`, the same path every agent already uses — is fully functional today. `LedgerSigner`, `TrezorSigner`, and `MLDSASigner` (post-quantum) are explicit stubs that raise `NotImplementedError`: they require vendor SDKs or an Arc-published PQ scheme that don't exist yet. Do not treat their presence in the codebase as working hardware-wallet or PQ support — this is groundwork, not a shipped feature.

## Guardrails for autonomous agents

If an agent signs without a human confirming each transaction, configure `Guardrails` — daily USDC spend limit, recipient whitelist, and a kill switch:

```python
from arc_devkit.agents.guardrails import Guardrails
from arc_devkit.agents.payment_agent import PaymentAgent

guardrails = Guardrails(max_spend_per_day_usdc=Decimal("100"), allowed_recipients=["0x..."])
agent = PaymentAgent(private_key=KEY, guardrails=guardrails)
```

**By default, guardrails are not configured** (`MAX_SPEND_PER_DAY_USDC` and `AGENT_ALLOWED_RECIPIENTS` are empty in `.env.example`) — an unguarded agent has no spend limit and no recipient restriction. Configure this explicitly for any agent that runs unattended against mainnet.
