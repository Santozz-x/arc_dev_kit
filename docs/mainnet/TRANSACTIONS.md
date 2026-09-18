# Transactions on Arc

## Reading

```python
from arc_devkit import Arc

arc = Arc.mainnet()

tx = arc.get_transaction("0x...")
receipt = arc.get_transaction_receipt("0x...")
receipt = arc.wait_for_transaction("0x...", timeout=120)  # blocks until mined
```

These are thin wrappers over standard `eth_getTransactionByHash` / `eth_getTransactionReceipt` / polling — nothing Arc-specific about the read path.

## Sending

The high-level path is `PaymentAgent`, which handles nonce management, gas estimation, mandatory pre-broadcast simulation (aborts on a simulated revert unless `force=True`), and optional receipt polling:

```python
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key=PRIVATE_KEY)

# Sign only — inspect before broadcasting
result = agent.execute(to="0xRecipient...", amount_usdc=5.0)
print(result["raw_transaction"])

# Sign and broadcast (real funds)
result = agent.execute(to="0xRecipient...", amount_usdc=5.0, enviar=True)
print(result["status"], result.get("tx_hash"))
```

`enviar=True` (native USDC) or `token="usdc"` (ERC-20 USDC) — see [USDC.md](USDC.md) for the difference. See [SECURITY.md](SECURITY.md) for the confirmation flow the CLI adds on top of this for mainnet.

## Transaction types

Arc supports Legacy, EIP-1559 (type-2), EIP-2930 (type-1), and EIP-7702 (type-4) transactions. **EIP-4844 blob transactions (type-3) are not supported** — the mempool rejects them. Source: [docs.arc.io/arc/references/evm-compatibility](https://docs.arc.io/arc/references/evm-compatibility), verified 2026-09-18.

## Arc-specific EVM behavior that affects transactions

These are real deviations from vanilla Ethereum, not Arc DevKit quirks (source: same page as above):

- **Minimum base fee: 20 Gwei.** A transaction priced below this is silently dropped from the mempool.
- **Base fee is paid to the block beneficiary, not burned** — unlike Ethereum's EIP-1559 burn model.
- **`SELFDESTRUCT` reverts** when sending value to the zero address, to itself, or to an already-destructed account.
- **Native value transfers revert** to the zero address, a blocklisted sender/recipient, or a precompile recipient.
- `PREVRANDAO` always returns `0` — no on-chain randomness source.

## Replace-by-fee (stuck transactions)

```python
result = agent.speed_up(tx_hash, gas_bump_percent=10)
```

## Batch sends

```python
payments = [
    {"to": "0xAddr1...", "amount_usdc": 1.0, "enviar": True},
    {"to": "0xAddr2...", "amount_usdc": 2.5, "enviar": True},
]
results = agent.execute_batch(payments)
```

Nonces increment automatically so the batch doesn't collide.
