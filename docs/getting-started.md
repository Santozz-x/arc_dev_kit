# Getting Started with Arc DevKit

This guide takes you from zero to a working example on Arc in under ten minutes. It defaults to **Arc Mainnet** (the SDK's default network) but every step works identically on **Arc Testnet** — see the callouts below.

> **Current version:** 0.9.0 — All classes and methods documented here reflect the current codebase. Full mainnet reference: [docs/mainnet/](mainnet/README.md).

---

## Prerequisites

| Requirement | Minimum version | Check |
|---|---|---|
| Python | 3.11 | `python --version` |
| pip | 23+ | `pip --version` |

You will also need:

- **Anthropic API key** — required for Dev Copilot ([console.anthropic.com](https://console.anthropic.com))
- **EVM wallet** — any compatible wallet (MetaMask, Rabby, etc.)
- **USDC to pay gas** — on mainnet this is real USDC you fund yourself; for development, use **Arc Testnet** instead and get test USDC from the official faucet: [faucet.circle.com](https://faucet.circle.com) (select "Arc Testnet")

---

## Installation

### Standard install

```bash
pip install arc-devkit
```

### Development install (contributors)

```bash
git clone https://github.com/jeielsantosdev/arc-devkit.git
cd arc-devkit
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\activate         # Windows
pip install -e ".[dev]"
```

---

## Configuration

Create `.env` in the project root (never commit this file):

```bash
cp .env.example .env
```

Fill in the variables:

```dotenv
# Required
ANTHROPIC_API_KEY=sk-ant-...

# Optional — network defaults to mainnet; set testnet for development.
# RPC/chain ID are pre-configured per network (arc_devkit/networks.py) —
# only set ARC_RPC_URL/ARC_CHAIN_ID to override with your own provider.
ARC_NETWORK=testnet                # or mainnet (the SDK default)
ARC_RPC_URL=                       # optional override
ARC_CHAIN_ID=                      # optional override
ARC_PRIVATE_KEY=0x...              # needed only for sending transactions
ANTHROPIC_MODEL=claude-sonnet-4-6  # override the Claude model
LOG_LEVEL=INFO
API_KEY=your-secret-key            # enables X-API-Key auth on the REST API
```

> **Mainnet uses real funds.** If `ARC_NETWORK` is unset or `mainnet`, any transaction you broadcast spends real USDC. Set `ARC_NETWORK=testnet` while developing — see [docs/mainnet/SECURITY.md](mainnet/SECURITY.md).

Add `.env` to `.gitignore`:

```bash
echo ".env" >> .gitignore
```

Alternatively, run the interactive setup wizard:

```bash
arc init
```

---

## Verify the Connection

```bash
arc status
```

Expected output:

```
╭─ Arc Testnet ──────────────────────────╮
│ Status       ✓ connected               │
│ Network      Arc Testnet               │
│ Chain ID     5042002                   │
│ Current block #1,284,931               │
│ Gas price    0.001 gwei                │
╰────────────────────────────────────────╯
```

---

## Example 1 — Read the Blockchain

```python
from arc_devkit.core.connection import get_web3, check_connection

if check_connection():
    print("Connected to Arc testnet!")

w3 = get_web3()
print(f"Block:     #{w3.eth.block_number}")
print(f"Chain ID:  {w3.eth.chain_id}")
print(f"Gas price: {w3.from_wei(w3.eth.gas_price, 'gwei')} gwei")
```

---

## Example 2 — Dev Copilot (blocking and streaming)

`DevCopilot` maintains conversation history across `ask()` calls within the same instance. Call `clear_history()` to reset between topics.

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

# Blocking — waits for the full response
answer = copilot.ask("How do I check a USDC balance on Arc testnet?")
print(answer)

# Follow-up uses conversation history automatically
follow_up = copilot.ask("Show me the same with async web3.py")
print(follow_up)
```

For real-time output in terminals or WebSocket handlers, use the streaming iterator:

```python
for chunk in copilot.ask_stream("Generate a recurring payment contract in Solidity"):
    print(chunk, end="", flush=True)
print()
```

Via CLI:

```bash
arc ask "How does USDC gas work on Arc?"
arc ask "Generate an ERC-20 contract for Arc" --stream
arc ask "What is the Circle Agent Stack?" --json
```

---

## Example 3 — Create a Wallet

```bash
arc wallet create
```

The private key is displayed once. Copy it to `ARC_PRIVATE_KEY` in your `.env` if you plan to send transactions, and fund it via the [Arc Testnet faucet](https://faucet.circle.com) (select "Arc Testnet").

```python
from arc_devkit.core.wallet import create_wallet
wallet = create_wallet()
print(wallet["address"])      # checksummed EVM address
print(wallet["private_key"])  # 0x-prefixed hex — store securely
```

---

## Example 4 — Check Balance

```bash
arc balance 0xYourAddress...
arc balance 0xYourAddress... --json
```

```python
from arc_devkit.core.wallet import get_balance
result = get_balance("0xYourAddress...")
print(result["balance_usdc"])  # Decimal, 18 decimals (native balance)
```

---

## Example 5 — Gas Estimation

Always estimate before sending, especially for contract interactions where the gas limit is not fixed at 21,000.

```bash
arc gas 0xDest... 10.0
arc gas 0xDest... 10.0 --from 0xYourWallet...  # more precise
```

```python
from arc_devkit.core.gas import estimate_transfer
est = estimate_transfer(to="0xDest...", amount_usdc=10.0, from_address="0xYour...")
print(f"Gas limit: {est['gas_limit']}")
print(f"Gas cost:  {est['custo_usdc']} USDC")
```

---

## Example 6 — Send a Payment

`PaymentAgent.execute()` auto-estimates gas via `eth_estimateGas` and optionally polls for the receipt. Pass `wait_receipt=False` if you need the hash immediately and will poll separately.

```python
import os
from arc_devkit.agents.payment_agent import PaymentAgent

agent = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])

# Sign only — inspect the raw transaction before broadcasting
result = agent.execute(to="0xDest...", amount_usdc=5.0)
print(result["status"])         # "signed"
print(result["raw_transaction"])

# Sign and broadcast, wait for confirmation
result = agent.execute(
    to="0xDest...",
    amount_usdc=5.0,
    enviar=True,
    on_success=lambda receipt: print("Confirmed!", receipt["transactionHash"].hex()),
)
print(result["status"])   # "confirmed"
print(result["tx_hash"])
```

`execute_batch()` sends multiple payments in sequence with incrementing nonces, so they don't collide:

```python
payments = [
    {"to": "0xAddr1...", "amount_usdc": 1.0, "enviar": True},
    {"to": "0xAddr2...", "amount_usdc": 2.5, "enviar": True},
]
results = agent.execute_batch(payments)
for r in results:
    print(r["status"], r.get("tx_hash"))
```

---

## Example 7 — Monitor Multiple Wallets

`MonitorAgent` polls all watched addresses on the same interval. The `min_change_wei` threshold silences noise from dust-level fluctuations. State persists across restarts when `state_file` is set, so the agent resumes from known balances rather than treating the first poll as a baseline.

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

agent = MonitorAgent(
    watched_addresses=["0xWallet1...", "0xWallet2..."],
    interval_seconds=10,
    min_change_wei=10**15,          # ignore changes below 0.001 ARC
    state_file="~/.arc_devkit/monitor_state.json",
)

def on_change(event: dict):
    print(f"[{event['address'][:10]}] {event['tipo']}: {event['diferenca_wei']} wei")

agent.execute(callback=on_change)
```

---

## Example 8 — USDC Token Interactions

```python
from decimal import Decimal
from arc_devkit.usdc import USDCToken

usdc = USDCToken(contract_address="0xUSDCOnArc...")

balance = usdc.balance("0xYourWallet...")
print(f"USDC balance: {balance}")   # Decimal with 6 decimal places

tx_hash = usdc.transfer(
    to="0xRecipient...",
    amount=Decimal("5.50"),
    private_key="0xYourKey...",
)
print(f"Transfer tx: {tx_hash}")

allowance = usdc.allowance(owner="0xOwner...", spender="0xSpender...")
print(f"Allowance: {allowance} USDC")
```

---

## Example 9 — Generic Contract Calls

```python
from arc_devkit.contracts import load_abi, call_view, send_tx, decode_events

abi = load_abi("MyToken.json")  # list or {"abi": [...]}

# Read-only call — no gas
total = call_view(abi, "0xContract...", "totalSupply")
print(total)

# State-changing call
tx_hash = send_tx(
    abi, "0xContract...", "mint",
    private_key="0x...",
    "0xRecipient...", 1000,   # function args
)
```

---

## Example 10 — Debug a Transaction

```bash
arc debug 0xTxHash...
arc debug 0xTxHash... --json
arcdevkit debug tx 0xTxHash...
```

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

result = TxAnalyzer().analyze("0xTxHash...")
print(result["status"])      # "success" or "reverted"
print(result["custo_usdc"])  # gas cost as Decimal string
print(result["resumo"])      # AI-generated diagnosis (Markdown)
```

---

## Example 11 — REST API

Start the server:

```bash
uvicorn arc_devkit.api.main:app --reload
```

All endpoints require `X-API-Key` when `API_KEY` is set in the environment. Without `API_KEY`, authentication is disabled (useful for local development).

```bash
# Copilot — blocking
curl -X POST http://localhost:8000/copilot/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"prompt": "What is the Arc Agent Stack?"}'

# Copilot — SSE streaming
curl -N http://localhost:8000/copilot/ask/stream \
  -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"prompt": "Generate a Solidity vault contract"}'

# Health check — includes RPC latency
curl http://localhost:8000/health
```

---

## CLI Config Management

```bash
# Interactive setup wizard
arc init

# Read / write individual variables
arc config get ARC_RPC_URL
arc config set LOG_LEVEL DEBUG
arc config list

# View history of CLI operations (saved to ~/.arc_devkit/history.json)
arc history
arc history --limit 5 --json
```

---

## Troubleshooting

### `OSError: Required variables not configured: ANTHROPIC_API_KEY`

```bash
cp .env.example .env
# fill in ANTHROPIC_API_KEY and ARC_RPC_URL
```

Or use the wizard: `arc init`

### Connection failure on `arc status`

```bash
curl -X POST https://rpc.testnet.arc.io \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"eth_blockNumber","params":[],"id":1}'
```

### `AuthenticationError` from Dev Copilot

```bash
echo $ANTHROPIC_API_KEY   # must start with sk-ant-
```

### `ModuleNotFoundError: No module named 'arc_devkit'`

```bash
pip install -e ".[dev]"   # development mode
# or
pip install arc-devkit    # standard install
```

---

## Next Steps

- [Dev Copilot](modules/dev-copilot.md) — conversation history, streaming, token counting
- [Agent Starter Kit](modules/agent-starter-kit.md) — PaymentAgent, MonitorAgent, USDC, Contracts
- [Tx Debugger](modules/tx-debugger.md) — transaction analysis with AI
- [CLI Guide](cli-guide.md) — complete command reference for both `arc` and `arcdevkit`
