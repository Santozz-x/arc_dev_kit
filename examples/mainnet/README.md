# Arc Mainnet Examples

Runnable examples against **Arc Mainnet** (real network, real funds). Each script defaults to `Arc.mainnet()` — swap for `Arc.testnet()` to run the same flow safely against Arc Testnet instead.

| # | Script | Touches real funds? |
|---|---|---|
| 01 | [`01_connect.py`](01_connect.py) | No — read-only |
| 02 | [`02_latest_block.py`](02_latest_block.py) | No — read-only |
| 03 | [`03_wallet_balance.py`](03_wallet_balance.py) | No — read-only |
| 04 | [`04_usdc_balance.py`](04_usdc_balance.py) | No — read-only |
| 05 | [`05_transaction.py`](05_transaction.py) | No — read-only |
| 06 | [`06_transaction_debugger.py`](06_transaction_debugger.py) | No — read-only (calls Claude for the AI summary) |
| 07 | [`07_contract_read.py`](07_contract_read.py) | No — read-only |
| 08 | [`08_contract_write.py`](08_contract_write.py) | **Yes** — requires `CONFIRM=yes` + `ARC_PRIVATE_KEY` |
| 09 | [`09_send_transaction.py`](09_send_transaction.py) | **Yes** — requires `CONFIRM=yes` + `ARC_PRIVATE_KEY` |
| 10 | [`10_deploy_contract.py`](10_deploy_contract.py) | **Yes** — requires `CONFIRM=yes` + `ARC_PRIVATE_KEY` (and `pip install py-solc-x`) |

Examples 01–07 were validated live against Arc Mainnet on 2026-09-18 (real chain ID, real blocks, a real transaction, and a real Multicall3 contract call). Examples 08–10 are **not** run automatically by anything in this repo — they require you to set `CONFIRM=yes` explicitly, precisely so a mistaken `python examples/mainnet/09_send_transaction.py` can never move real funds by accident.

Set `ANTHROPIC_API_KEY` in your `.env` before running any of these (required at import time even for examples that don't call Claude directly).
