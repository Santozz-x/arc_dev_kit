# Gas and Fees on Arc

## Fees are always in USDC

Arc's "Stable Fee Design" means gas is denominated in USDC regardless of what you're transferring — a native USDC send and an ERC-20 USDC transfer both cost USDC, not a separate gas token. There is no ETH-equivalent to hold separately.

## Quoting a fee

```python
from arc_devkit.core.gas import quote_fee

fee = quote_fee(to="0xRecipient...", amount=10.0, token="native")   # or "usdc"
print(fee["gas_limit"], fee["gas_price_gwei"], fee["fee_usdc"])
print(fee["paymaster_available"])  # always False today — see below
```

CLI equivalent:

```bash
arcdevkit fees quote 0xRecipient... 10.0 --token native
arcdevkit fees quote 0xRecipient... 10.0 --token usdc
```

`quote_fee()` resolves the USDC ERC-20 contract from the active network's config (`settings.network.contracts.usdc`) automatically — no address to pass.

## Gas estimation

```python
from arc_devkit.core.gas import estimate_transfer

est = estimate_transfer(to="0xRecipient...", amount_usdc=10.0, from_address="0xYour...")
print(est["gas_limit"], est["custo_usdc"])
```

## Arc's fee rules to know

Source: [docs.arc.io/arc/references/evm-compatibility](https://docs.arc.io/arc/references/evm-compatibility), verified 2026-09-18.

- **Minimum base fee: 20 Gwei.** Transactions priced below this are silently dropped from the mempool — if a transaction never confirms and never reverts, check your gas price first.
- **Base fee goes to the block beneficiary, not burned** — a departure from Ethereum's EIP-1559 model. This doesn't change how you estimate fees, but it's a meaningful economic difference if you're reasoning about Arc's fee market.
- A `MAX_GAS_PRICE_GWEI` ceiling is available as a safety rail — set it in `.env` and `PaymentAgent`/CLI sends will refuse to broadcast above it.

## Paymasters (Account Abstraction)

`detect_paymaster()` always reports `available=False` today — no Arc paymaster contract or bundler endpoint has been published. `PaymentAgent.execute(..., use_paymaster=True)` fails clearly rather than pretending to sponsor the fee. `arc_devkit.paymaster.user_operation` implements the standard ERC-4337 `UserOperation` shape so it's ready to use once Arc publishes AA infrastructure — nothing to change on your end when that happens beyond removing the `available=False` gate.
