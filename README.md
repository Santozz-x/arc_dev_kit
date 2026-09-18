# Arc DevKit

[![PyPI version](https://img.shields.io/pypi/v/arc-devkit.svg)](https://pypi.org/project/arc-devkit/)
[![CI](https://github.com/Jeielsantosdev/arc-devkit/actions/workflows/ci.yml/badge.svg)](https://github.com/Jeielsantosdev/arc-devkit/actions)
[![Coverage](https://img.shields.io/badge/coverage-80%25-brightgreen.svg)](https://github.com/Jeielsantosdev/arc-devkit)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![MIT License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Arc Mainnet](https://img.shields.io/badge/arc-mainnet-brightgreen.svg)](https://explorer.arc.io)

**Arc DevKit** is an open-source developer toolkit for building, debugging, and interacting with applications on **Arc Mainnet** — Circle's EVM-compatible Layer 1 with USDC as the gas token and sub-second finality. Arc Testnet is fully supported too.

**link to project**  https://arc-dev-kit-uxun.vercel.app/

It solves the practical friction of building on Arc: network config (chain ID, RPC, explorer, contract addresses — no manual lookup needed), USDC's dual native/ERC-20 interface, PoA middleware, ERC-20 monitoring, async agents, WebSocket streaming, mainnet safety guardrails, and AI-assisted debugging — all packaged and ready to use.

---

## What is Arc?

**Arc** is a Layer 1 blockchain by Circle (creators of USDC), designed for programmable payments and autonomous economic agents. Mainnet launched 2026-09-16.

| Feature | Detail |
|---|---|
| **EVM-compatible** | Solidity/web3.py/ethers.js work without modification |
| **USDC as gas** | No ETH needed — USDC is the native gas token (18 decimals), also exposed as a synchronized ERC-20 view (6 decimals) |
| **Malachite consensus** | Sub-second block finality |
| **Circle Agent Stack** | Native infrastructure for AI economic agents |
| **Mainnet** | Chain ID `5042` — RPC `https://rpc.mainnet.arc.io` — Explorer `https://explorer.arc.io` |
| **Testnet** | Chain ID `5042002` — RPC `https://rpc.testnet.arc.io` — Explorer `https://explorer.testnet.arc.io` |

See [docs/mainnet/NETWORK_CONFIG.md](docs/mainnet/NETWORK_CONFIG.md) for full, sourced network details.

---

## Quickstart

**Requires Python 3.11+**

```bash
pip install arc-devkit
```

```python
from arc_devkit import Arc

arc = Arc.mainnet()  # or Arc.testnet() for development

print(arc.network.name, arc.network.chain_id)
print(arc.latest_block()["number"])

tx = arc.get_transaction("0x...")
report = arc.debug_transaction("0x...")
```

No manual RPC/chain-ID/contract lookup needed — everything above is pre-configured and verified (see [docs/mainnet/MIGRATION_AUDIT.md](docs/mainnet/MIGRATION_AUDIT.md) Part B for sources). Pass `rpc_url=` to `Arc.mainnet()`/`Arc.testnet()` to use your own provider (Alchemy, QuickNode, self-hosted).

### CLI setup

```bash
# 1. Copy example env
cp .env.example .env

# 2. Fill in your keys
#    ANTHROPIC_API_KEY  — from console.anthropic.com
#    ARC_NETWORK        — mainnet (default) or testnet
#    ARC_PRIVATE_KEY    — optional; needed to send transactions

# 3. Guided interactive setup (creates .env from scratch)
arcdevkit init

# 4. Verify connection and network health
arcdevkit status
arcdevkit doctor
```

```
Arc Mainnet
Chain ID:      5042
Current block: #21500000
Gas price:     0.02 gwei

⚠ Real funds — mainnet
```

For development, set `ARC_NETWORK=testnet` in `.env` — see [docs/mainnet/MIGRATION_FROM_TESTNET.md](docs/mainnet/MIGRATION_FROM_TESTNET.md). (A per-command `--network` override flag is not implemented yet — see Known Limitations in the migration report.)

---

## Modules

| Module | Package | What it does |
|---|---|---|
| **Dev Copilot** | `arc_devkit.copilot` | AI assistant (Claude, Gemini, GPT, or Ollama) with Arc context built in |
| **Payment Agent** | `arc_devkit.agents` | Sign and broadcast USDC/native payments |
| **Monitor Agent** | `arc_devkit.agents` | Watch wallets for balance changes and ERC-20 events |
| **Async Monitor** | `arc_devkit.agents` | Async-native monitor for FastAPI / WebSocket use |
| **Tx Debugger** | `arc_devkit.debugger` | Decode reverts, input data, and analyze transactions with AI |
| **Portfolio Analyzer** | `arc_devkit.analytics` | Snapshot balances, scan txs, score activity |
| **USDC Token** | `arc_devkit.usdc` | ERC-20 balance, transfer, approve, allowance |
| **Contracts** | `arc_devkit.contracts` | Call view functions, send transactions, decode events |
| **Event Listener** | `arc_devkit.events` | Poll on-chain logs and trigger callbacks |
| **Contract Deployer** | `arc_devkit.deploy` | Deploy from ABI+bytecode or Solidity source |
| **REST API** | `arc_devkit.api` | FastAPI server with SSE streaming and WebSocket monitor |
| **CLI** | `arc` / `arcdevkit` | Full command-line interface for all modules |

---

## Dev Copilot

AI assistant with Arc blockchain context embedded in the system prompt. Answers questions, generates code, explains Circle ecosystem concepts. Backed by a pluggable LLM provider — **Claude (Anthropic, default), Gemini (Google), GPT (OpenAI), or a local Ollama model** — selected globally via `COPILOT_PROVIDER` in `.env`:

```dotenv
COPILOT_PROVIDER=anthropic   # default — requires ANTHROPIC_API_KEY
# COPILOT_PROVIDER=gemini    # requires pip install arc-devkit[gemini], GEMINI_API_KEY, GEMINI_MODEL
# COPILOT_PROVIDER=openai    # requires pip install arc-devkit[openai], OPENAI_API_KEY, OPENAI_MODEL
# COPILOT_PROVIDER=ollama    # local, no API key — requires OLLAMA_MODEL (already pulled) and a running Ollama server
```

`ask()`, `ask_stream()`, conversation history, response caching, offline mode, and image attachments work identically across all four providers. **Agentic tool-use mode (`run_agent()` / `arc ask --agent`) is Anthropic-only today** — it raises `NotImplementedError` with the other providers, since each has an incompatible tool-calling schema that hasn't been wired up yet. No model name is ever guessed for Gemini/OpenAI/Ollama — you set `GEMINI_MODEL`/`OPENAI_MODEL`/`OLLAMA_MODEL` explicitly, since a hardcoded default could silently point at a deprecated or non-existent model. See [`arc_devkit/copilot/providers/`](arc_devkit/copilot/providers/) for the provider abstraction.

### CLI

```bash
# Ask a question
arcdevkit copilot ask "How do I deploy an ERC-20 contract on Arc testnet?"

# Streaming output (token by token)
arcdevkit copilot ask "Write a USDC payment contract in Solidity" --stream
```

### Python

```python
from arc_devkit.copilot.agent import DevCopilot

copilot = DevCopilot()

# Single question
answer = copilot.ask("What is the gas cost in USDC for a simple transfer on Arc?")
print(answer)

# Streaming
for chunk in copilot.ask_stream("Write a recurring payment agent in Python"):
    print(chunk, end="", flush=True)

# Pass an image (PNG/JPEG/GIF/WebP) as context
answer = copilot.ask("What does this error mean?", image_path="screenshot.png")

# Maintain multi-turn conversation
copilot.ask("What is Circle CCTP?")
copilot.ask("Show me a Python example of a cross-chain USDC transfer")

# Count tokens before calling (free estimate)
tokens = copilot.count_tokens("Explain how Malachite consensus works")
print(f"This prompt uses ~{tokens} tokens")

# Offline mode — returns a static message, no API call (useful in CI/tests)
copilot = DevCopilot(offline=True)
copilot.ask("anything")  # → "[Offline mode] ..."

# Inject custom context (e.g. your contract ABI or project description)
copilot = DevCopilot(extra_context="This project uses a custom USDC vault contract.")
```

**Features:**
- In-memory conversation history per session
- Response cache with 5-minute TTL (MD5 hash of prompt + model)
- Token usage logged on every call
- `offline=True` for CI/test environments without an API key
- Image attachments support (PNG, JPEG, GIF, WebP)
- Model configurable via `ANTHROPIC_MODEL` env var (default: `claude-sonnet-4-6`)

---

## Payment Agent

Signs and broadcasts transactions on Arc. Supports native ARC transfers and USDC ERC-20 transfers.

```python
from arc_devkit.agents.payment_agent import PaymentAgent
import os

agent = PaymentAgent(private_key=os.environ["ARC_PRIVATE_KEY"])

# Send native ARC
result = agent.execute(
    to="0xRecipientAddress",
    amount_usdc=1.5,           # interpreted as native ARC amount
    enviar=True,
    token="native",
)
print(result["tx_hash"])

# Send USDC ERC-20
result = agent.execute(
    to="0xRecipientAddress",
    amount_usdc=10.0,
    enviar=True,
    token="usdc",
)

# Dry run — returns signed tx without broadcasting
result = agent.execute(to="0xAddr", amount_usdc=5.0, enviar=False)
print(result["raw_transaction"])

# Batch payments (sequential, nonce-incremental)
payments = [
    {"to": "0xAddr1", "amount_usdc": 1.0},
    {"to": "0xAddr2", "amount_usdc": 2.0},
    {"to": "0xAddr3", "amount_usdc": 0.5},
]
results = agent.execute_batch(payments, enviar=True)

# Success / failure callbacks
agent.execute(
    to="0xAddr",
    amount_usdc=5.0,
    enviar=True,
    on_success=lambda r: print(f"Confirmed: {r['transactionHash'].hex()}"),
    on_failure=lambda e: print(f"Failed: {e}"),
)
```

**Features:**
- Automatic gas estimation via `eth_estimateGas` (fallback 21 000)
- Waits for receipt by default (120s timeout, configurable)
- Pre-send simulation via `eth_call` to detect reverts before broadcasting
- Batch execution with automatic nonce management
- Multi-RPC fallback (comma-separated `ARC_RPC_URL`)
- Retry on network errors (3 attempts, exponential backoff via tenacity)

---

## Monitor Agent

Watches one or more wallets for balance changes and ERC-20 Transfer events.

```python
from arc_devkit.agents.monitor_agent import MonitorAgent

monitor = MonitorAgent(
    watched_addresses=["0xWallet1", "0xWallet2"],
    interval_seconds=15,
    min_change_wei=10**16,           # only alert on changes ≥ 0.01 ARC
    state_file="monitor_state.json", # persists across restarts
    usdc_contract_address="0xUSDs",  # enable ERC-20 event scanning
    webhook_url="https://myapp.io/hooks/arc",  # optional HTTP webhook
)

def on_event(event):
    if event["event_type"] == "native":
        print(f"[{event['type']}] {event['address']}: {event['change_wei']} wei")
    elif event["event_type"] == "erc20_transfer":
        print(f"[USDC {event['type']}] {event['value_atomic']} atomic units")

# Blocking loop (runs until stop() or KeyboardInterrupt)
monitor.execute(callback=on_event)

# Non-blocking: run in a thread and stop later
import threading
t = threading.Thread(target=monitor.execute, kwargs={"callback": on_event}, daemon=True)
t.start()
# ... later
monitor.stop()
```

**Features:**
- Multiple wallets in one instance
- Minimum threshold to suppress micro-fluctuations
- JSON state file — balance cursor survives restarts
- ERC-20 Transfer event scanning (USDC log monitoring via `eth_getLogs`)
- HTTP webhook: `POST` event payloads to any URL on each alert
- Retry on network errors (tenacity)

---

## Async Monitor Agent (for FastAPI / WebSocket)

Drop-in async version of MonitorAgent. Uses `asyncio.sleep` and `asyncio.to_thread` — never blocks the event loop.

```python
from arc_devkit.agents.async_monitor import AsyncMonitorAgent

monitor = AsyncMonitorAgent(
    watched_address="0xWallet",
    interval_seconds=10,
    min_change_wei=0,
)

# Async execute (await in an async context)
async def run():
    result = await monitor.execute(
        callback=lambda event: print(event),  # sync or async callback
        max_iterations=100,
    )

# Async generator — ideal for WebSocket handlers
async def stream_to_websocket(ws):
    async for event in monitor.event_stream():
        await ws.send_json(event)
```

### WebSocket via REST API

Arc DevKit exposes a WebSocket endpoint out of the box:

```
WS /agents/monitor/{address}?interval=15&min_change_wei=0
```

```javascript
// Browser / frontend
const ws = new WebSocket("ws://localhost:8000/agents/monitor/0xYourWallet");
ws.onmessage = (e) => {
  const event = JSON.parse(e.data);
  if (event.event_type === "native") {
    console.log(`Balance change: ${event.change_wei} wei (${event.type})`);
  } else if (event.event_type === "erc20_transfer") {
    console.log(`USDC ${event.type}: ${event.value_atomic} atomic units`);
  }
  // event_type === "ping" → heartbeat, no action needed
};
```

Each event message contains:

| Field | Description |
|---|---|
| `event_type` | `"native"`, `"erc20_transfer"`, or `"ping"` (heartbeat) |
| `address` | Monitored wallet address |
| `type` | `"credit"` or `"debit"` |
| `balance_wei` | Current balance in wei |
| `change_wei` | Change amount (signed) |
| `tx_hash` | Transaction hash (ERC-20 events only) |

---

## Tx Debugger

Fetches transaction data via RPC, decodes the error/result, and uses the Dev Copilot to generate a plain-language diagnosis.

```bash
# Analyze a transaction
arcdevkit debug tx 0xYourTxHashHere

# Load an ABI to decode input data
arcdevkit debug tx 0xYourTxHash --abi ./MyContract.abi.json

# Batch — analyze a file of hashes (one per line)
arcdevkit debug batch hashes.txt

# View recent operation history
arcdevkit history
```

```python
from arc_devkit.debugger.tx_analyzer import TxAnalyzer

analyzer = TxAnalyzer()
report = analyzer.analyze("0xYourTxHashHere", abi_path="MyContract.abi.json")
print(report)
```

**Example output for a reverted transaction:**

```
Status:     reverted
Error:      ERC20: transfer amount exceeds balance
Gas used:   21,000 / 100,000
Cost:       0.0008 USDC
Diagnosis:  The sender wallet did not have enough USDC balance at the time
            of execution. Call balanceOf() before transfer() to verify.
Suggestion: Add a pre-check or use a try/catch in your contract.
```

**Features:**
- Decodes `require()` string errors and custom Solidity errors
- Decodes input data (function name + arguments) when ABI is provided
- History saved to `~/.arc_devkit/history.json` automatically
- Batch analysis from a file of tx hashes

---

## Portfolio Analyzer

Snapshot a wallet's complete state and activity on Arc, with AI commentary.

```bash
# Analyze a single wallet
arcdevkit portfolio analyze 0xYourWalletAddress

# Show saved balance history
arcdevkit portfolio history 0xYourWalletAddress

# Generate a consolidated report for multiple wallets
arcdevkit portfolio report wallets.json
```

```python
from arc_devkit.analytics.portfolio import PortfolioAnalyzer

analyzer = PortfolioAnalyzer()
snapshot = analyzer.analyze("0xYourWalletAddress", blocks_back=1000)

print(f"Native balance: {snapshot.native_balance} ARC")
print(f"USDC balance:   {snapshot.usdc_balance} USDC")
print(f"Total txs sent: {snapshot.nonce}")
print(f"Activity:       {snapshot.activity_score}")  # high/medium/low/inactive
print(f"Recent txs:     {len(snapshot.recent_txs)}")
```

**Features:**
- Scans recent N blocks for sent/received transactions
- Activity score: `high / medium / low / inactive`
- Balance history snapshots saved to `~/.arc_devkit/portfolio_history/`
- Multi-wallet consolidated report via JSON wallet file

---

## USDC Token

ERC-20 wrapper for the USDC contract on Arc. All amounts use `Decimal` with 6 decimal places.

```python
from arc_devkit.usdc.token import USDCToken
from decimal import Decimal

usdc = USDCToken(contract_address="0xUSDCContractAddress")

# Read
balance = usdc.balance("0xWalletAddress")         # → Decimal("10.500000")
allowance = usdc.allowance("0xOwner", "0xSpender") # → Decimal("100.0")

# Write (requires private key)
tx_hash = usdc.transfer("0xRecipient", Decimal("5.0"), private_key="0xKey")
tx_hash = usdc.approve("0xSpender", Decimal("50.0"), private_key="0xKey")
```

---

## Contracts

Low-level utilities for interacting with any EVM contract on Arc.

```python
from arc_devkit.contracts.loader import load_abi, call_view, send_tx, decode_events

# Load ABI from JSON file (supports {"abi": [...]} or raw [...] format)
abi = load_abi("MyContract.abi.json")

# Read-only call (eth_call)
result = call_view(abi, "0xContractAddress", "totalSupply")
result = call_view(abi, "0xContractAddress", "balanceOf", "0xWallet")

# Send transaction
tx_hash = send_tx(
    abi, "0xContractAddress", "transfer",
    private_key="0xKey",
    "0xRecipient", 1_000_000,  # function args
)

# Decode events from a receipt
events = decode_events(receipt, abi, "Transfer", "0xContractAddress")
for evt in events:
    print(evt["args"])
```

---

## Event Listener

Polls on-chain logs for any event and fires callbacks. No WebSocket RPC required — uses `eth_getLogs`.

```python
from arc_devkit.events.listener import EventListener

listener = EventListener(
    contract_address="0xUSDCAddress",
    abi=erc20_abi,
    from_block="latest",
)

listener.on("Transfer", lambda evt: print(f"Transfer: {evt['args']}"))

# Blocking loop (runs until stop())
listener.start(poll_interval=5)

# Or: single-shot manual poll
events = listener.poll()
```

---

## Contract Deployer

Deploys contracts from pre-compiled ABI+bytecode or directly from a `.sol` source file.

```python
from arc_devkit.deploy.deployer import ContractDeployer

deployer = ContractDeployer(private_key="0xKey")

# Deploy from ABI + bytecode
address = deployer.deploy(
    abi=abi,
    bytecode="0x...",
    constructor_args=[],
)
print(f"Deployed at: {address}")

# Deploy from Solidity source (requires solc / py-solc-x)
address = deployer.deploy_source(
    source_file="MyToken.sol",
    contract_name="MyToken",
    constructor_args=["MyToken", "MTK", 18],
)
```

---

## REST API

Arc DevKit ships a full FastAPI server with Swagger UI, authentication, rate limiting, and real-time streaming.

```bash
# Start
uvicorn arc_devkit.api.main:app --reload

# Swagger UI  →  http://localhost:8000/docs
# ReDoc       →  http://localhost:8000/redoc
```

### Endpoints

| Method | Route | Description |
|---|---|---|
| `POST` | `/copilot/ask` | Ask the Dev Copilot |
| `POST` | `/copilot/ask/stream` | SSE streaming response (token by token) |
| `GET` | `/agents/balance/{address}` | Query wallet balance |
| `POST` | `/agents/wallet` | Create a new wallet |
| `POST` | `/agents/payment` | Execute a payment |
| `GET` | `/agents/block` | Current block number and chain ID |
| `WS` | `/agents/monitor/{address}` | Real-time balance events (WebSocket) |
| `GET` | `/debug/tx/{hash}` | Analyze a transaction |
| `GET` | `/debug/history` | Paginated analysis history |
| `GET` | `/health` | API health + RPC connectivity |

### Authentication

```bash
# Enable API key auth
export API_KEY="your-secret-key"

# Pass in every request
curl -H "X-API-Key: your-secret-key" http://localhost:8000/health

# Without API_KEY set, auth is disabled (local development)
```

### SSE Streaming

```bash
curl -X POST http://localhost:8000/copilot/ask/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "How do I send USDC on Arc?"}' \
  --no-buffer
# Stream: data: {"token": "To "} data: {"token": "send "} ... data: {"done": true}
```

### WebSocket Monitor

```bash
# Using websocat CLI
websocat "ws://localhost:8000/agents/monitor/0xYourWallet?interval=10"
# {"event_type": "ping"}
# {"event_type": "native", "type": "credit", "change_wei": "1000000000000000000", ...}
```

### Docker

```bash
docker compose up
```

The `docker-compose.yml` mounts your `.env` and runs the API on port 8000 with a healthcheck.

---

## CLI Reference

The primary entry point is `arcdevkit`, with commands grouped by domain.

### Setup

```bash
arcdevkit init                              # interactive .env wizard
arcdevkit status                            # check active network connection + block info
arcdevkit doctor                            # health check: RPC, chain ID, USDC contract, explorer
```

### Config — manage `.env`

```bash
arcdevkit config list                       # show all variables
arcdevkit config get ANTHROPIC_API_KEY      # read a specific variable
arcdevkit config set ARC_RPC_URL https://...# write a variable
```

### Copilot — AI assistant

```bash
arcdevkit copilot ask "What is Malachite consensus?"
arcdevkit copilot ask "Write a USDC vault" --stream   # token-by-token streaming
arcdevkit copilot ask "..." --json                    # output as JSON
```

### Agent — wallet & payments

```bash
arcdevkit agent create-wallet               # generate new EVM wallet
arcdevkit agent balance 0xAddress...        # check wallet balance
arcdevkit agent status                      # network info (block, chain ID, gas)
arcdevkit agent pay 0xDest... 5.0           # sign-only (safe default)
arcdevkit agent pay 0xDest... 5.0 --send    # sign and broadcast
arcdevkit agent pay 0xDest... 5.0 --send --key 0xPrivKey...
arcdevkit agent monitor 0xWallet...         # watch balance changes
arcdevkit agent monitor 0xWallet... --interval 5 --max 50
```

### Debug — transaction analysis

```bash
arcdevkit debug tx 0xHash...                # analyze a transaction with AI
arcdevkit debug tx 0xHash... --json
arcdevkit debug estimate 0xDest... 10.0     # estimate gas cost
arcdevkit debug estimate 0xDest... 10.0 --from 0xSender...
arcdevkit debug batch hashes.txt            # analyze multiple txs from a file
arcdevkit debug batch hashes.txt --abi MyContract.json
```

### Portfolio — wallet analytics

```bash
arcdevkit portfolio analyze 0xWallet...     # balances, txs, AI insights
arcdevkit portfolio analyze 0xWallet... --no-ai --blocks 500
arcdevkit portfolio history 0xWallet...     # saved balance snapshots
arcdevkit portfolio report wallets.json     # consolidated multi-wallet report
```

### Codegen — script generation

```bash
arcdevkit codegen "monitor a wallet and alert when balance drops"
arcdevkit codegen "deploy an ERC-20 with a mint function" --out ./scripts
arcdevkit codegen "..." --no-save           # print only, don't save to disk
```

### History — operation log

```bash
arcdevkit history                           # last 10 CLI operations
arcdevkit history --limit 25 --json
```

---

## Project Structure

```
arc_devkit/
├── config.py               # Settings from .env; validates required vars at import
├── core/
│   ├── connection.py       # web3.py + ExtraDataToPOAMiddleware for Arc's validator model
│   ├── wallet.py           # Wallet creation, balance queries
│   └── gas.py              # USDC gas estimation
├── copilot/
│   └── agent.py            # DevCopilot — streaming, history, cache, offline mode, images
├── agents/
│   ├── base_agent.py       # BaseAgent ABC — retry, multi-RPC, wallet resolution
│   ├── async_base.py       # AsyncBaseAgent — async ABC via asyncio.to_thread
│   ├── payment_agent.py    # PaymentAgent — native + USDC payments, batch
│   ├── monitor_agent.py    # MonitorAgent — sync polling + ERC-20 events + webhook
│   └── async_monitor.py    # AsyncMonitorAgent — async loop + event_stream generator
├── debugger/
│   └── tx_analyzer.py      # TxAnalyzer — revert decode, ABI decode, AI analysis
├── analytics/
│   └── portfolio.py        # PortfolioAnalyzer — balance snapshot, tx scan, activity score
├── usdc/
│   └── token.py            # USDCToken — ERC-20 wrapper (balance, transfer, approve)
├── contracts/
│   └── loader.py           # load_abi, call_view, send_tx, decode_events
├── events/
│   └── listener.py         # EventListener — eth_getLogs polling + callbacks
├── deploy/
│   └── deployer.py         # ContractDeployer — ABI+bytecode and .sol source deploy
├── api/
│   ├── main.py             # FastAPI app — CORS, auth, rate limit, logging middleware
│   └── routes/
│       ├── copilot.py      # /copilot — ask, stream (SSE)
│       ├── agents.py       # /agents — wallet, payment, balance, WS monitor
│       └── debugger.py     # /debug — analyze tx, history
└── cli/
    ├── flat.py             # `arc` — flat CLI for quick use
    └── commands/           # `arcdevkit` — grouped subcommands
```

---

## Development

```bash
# Clone and install in editable mode with dev dependencies
git clone https://github.com/Jeielsantosdev/arc-devkit.git
cd arc-devkit
pip install -e ".[dev]"

# Unit tests (no network required)
pytest

# Run a specific test
pytest -k "test_copilot"

# Integration tests (live Arc — mainnet or testnet per ARC_NETWORK — + Anthropic API)
pytest -m integration

# Lint and format
ruff check .
ruff format .

# Type check
mypy arc_devkit/

# Build docs locally
mkdocs serve
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `ANTHROPIC_API_KEY` | Yes | — | Anthropic API key (console.anthropic.com) |
| `ARC_NETWORK` | No | `mainnet` | `mainnet` or `testnet` — selects RPC/chain ID/contract defaults |
| `ARC_RPC_URL` | No | network default | Arc RPC endpoint override, comma-separated for multi-RPC failover |
| `ARC_PRIVATE_KEY` | No | — | Wallet private key — required to send transactions |
| `ANTHROPIC_MODEL` | No | `claude-sonnet-4-6` | Claude model to use |
| `ARC_CHAIN_ID` | No | network default | Arc chain ID override |
| `LOG_LEVEL` | No | `INFO` | Logging level |
| `API_KEY` | No | — | REST API key — if unset, auth is disabled |

---

## CI / CD

| Pipeline | Trigger | What it does |
|---|---|---|
| `ci.yml` | Every push / PR | Lint (ruff) + unit tests on Python 3.11, 3.12, 3.13 + mypy |
| `ci.yml` (integration job) | `main` branch | Runs `pytest -m integration` against live Arc RPCs (read-only) |
| `publish.yml` | Push of `v*` tag | Builds wheel + sdist, publishes to PyPI, creates GitHub Release |

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

> **Arc Mainnet is live** (launched 2026-09-16) and is Arc DevKit's default network as of v0.9.0. Arc Testnet remains fully supported for development (`ARC_NETWORK=testnet`). Some CCTP bridge details (attestation API support for Arc, V2 ABI) are not yet validated against live traffic — see [docs/mainnet/MAINNET_MIGRATION_REPORT.md](docs/mainnet/MAINNET_MIGRATION_REPORT.md) for known limitations. Pin your version in production: `pip install arc-devkit==0.9.0`.
