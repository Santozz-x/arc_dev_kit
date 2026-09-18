# USDC on Arc

USDC is structural to Arc, not just another token — it's the network's gas currency. It has a **dual interface**: the same underlying balance is visible both as Arc's native coin (like ETH on Ethereum) and as a standard ERC-20 token. Understanding this split is the single most important USDC-specific fact for building on Arc.

## The dual interface

| Interface | Decimals | How to read it | Used for |
|---|---|---|---|
| **Native** | 18 | `eth_getBalance` | Gas payment, `msg.value`, native sends |
| **ERC-20** | 6 | `balanceOf()` at `0x3600...0000` | `approve`/`transferFrom`/existing ERC-20 tooling |

Both are views onto the **same funds**, kept in sync by a precompiled contract — there is no wrapper token, no bridging between the two. **Never mix the two decimal scales**: reading a native balance and treating it as a 6-decimal ERC-20 amount (or vice versa) will misreport the balance by a factor of 10¹².

Source: [docs.arc.io/arc/references/contract-addresses](https://docs.arc.io/arc/references/contract-addresses), [docs.arc.io/arc/references/evm-compatibility](https://docs.arc.io/arc/references/evm-compatibility) — verified 2026-09-18.

## Reading balances

```python
from arc_devkit import Arc

arc = Arc.mainnet()

native = arc.get_balance("0xAddress...")     # 18 decimals — the gas balance
erc20 = arc.usdc.balance("0xAddress...")     # 6 decimals — the ERC-20 view
```

Or without the facade:

```python
from arc_devkit.stablecoins.token import USDCToken, native_usdc_balance

native = native_usdc_balance("0xAddress...")   # 18 decimals
erc20 = USDCToken().balance("0xAddress...")    # 6 decimals, defaults to the
                                                # official USDC ERC-20 address
```

## Transfers, approvals, allowance

`USDCToken` (in `arc_devkit.stablecoins.token`, or via `arc.usdc`) covers the standard ERC-20 surface:

```python
from arc_devkit.stablecoins.token import USDCToken
from decimal import Decimal

usdc = USDCToken()  # defaults to the real USDC contract — no address needed

usdc.balance("0xAddress...")
usdc.transfer(to="0xRecipient...", amount=Decimal("10"), private_key=PRIVATE_KEY)
usdc.approve(spender="0xSpender...", amount=Decimal("100"), private_key=PRIVATE_KEY)
usdc.allowance(owner="0xOwner...", spender="0xSpender...")
usdc.transfer_from(owner="0xOwner...", to="0xTo...", amount=Decimal("5"), private_key=SPENDER_KEY)
```

All amounts are `Decimal`, never `float` (see [Key Conventions](../../CLAUDE.md#key-conventions)). `USDCToken()` with no arguments now resolves to `arc_devkit.networks.USDC_ERC20_ADDRESS` (`0x3600...0000`, identical on mainnet and testnet) — earlier versions defaulted to a zero-address placeholder; that has been removed.

## EURC

Same pattern, but `EURCToken` requires an explicit contract address (it has no shared cross-network address like USDC):

```python
from arc_devkit.stablecoins.token import EURCToken
from arc_devkit.config import settings

eurc = EURCToken(contract_address=settings.network.contracts.eurc)
```

## Fee currency

Gas on Arc is always denominated in USDC, whether you're sending native USDC or an ERC-20 transfer — see [GAS_AND_FEES.md](GAS_AND_FEES.md).
