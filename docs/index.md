# Arc DevKit

**Arc DevKit** is an open-source toolkit for developers building on the Arc blockchain — an EVM-compatible Layer 1 by Circle where USDC is the gas token and Malachite consensus delivers sub-second block finality.

---

## Modules

### Dev Copilot

An AI assistant backed by `claude-sonnet-4-6` with Arc-specific context embedded in its system prompt. It maintains conversation history across turns, streams responses token by token, and caches identical prompts for up to five minutes. Inject custom context — such as a contract ABI — through the `extra_context` constructor argument to narrow its responses to your specific deployment.

```bash
arc ask "How do I deploy an ERC-20 on Arc testnet?"
arc ask "Explain the Circle Agent Stack" --stream
```

### Agent Starter Kit

`BaseAgent` is an abstract class that wires up RPC connection with automatic multi-RPC fallback and tenacity-backed retry. Two concrete implementations ship out of the box: `PaymentAgent`, which builds and signs transactions with automatic gas estimation, receipt polling, success/failure callbacks, and a `execute_batch()` method for sequential multi-payments; and `MonitorAgent`, which watches multiple wallets simultaneously, fires callbacks only when balance changes exceed a configurable threshold, and persists its last-seen state to disk across restarts.

```bash
arc wallet create
arc balance 0xYourAddress...
arcdevkit agent pay 0xDest... 5.0 --send
```

### USDC

`USDCToken` wraps the USDC ERC-20 contract on Arc (`0x3600...0000`, identical on mainnet/testnet). It exposes `balance()`, `transfer()`, `transfer_from()`, `allowance()`, and `approve()` using `Decimal` with 6-decimal precision. USDC is also Arc's native gas token at 18 decimals — use `native_usdc_balance()` for that separately (see [docs/mainnet/USDC.md](mainnet/USDC.md)).

```python
from arc_devkit.usdc import USDCToken
usdc = USDCToken(contract_address="0x...")
print(usdc.balance("0xYourWallet..."))
```

### Contracts

Generic EVM contract utilities: `load_abi()` reads a JSON file in either raw-list or `{"abi": [...]}` format; `call_view()` executes read-only functions; `send_tx()` signs and broadcasts state-changing calls; `decode_events()` parses logs from a receipt into structured dicts.

```python
from arc_devkit.contracts import load_abi, call_view
abi = load_abi("MyToken.json")
supply = call_view(abi, "0xContract...", "totalSupply")
```

### Tx Debugger

`TxAnalyzer.analyze()` fetches a transaction and its receipt via RPC, computes the USDC gas cost, and generates a natural-language diagnosis through Dev Copilot. The result includes raw transaction data alongside the AI summary so you can verify the analysis against on-chain facts.

```bash
arc debug 0xTxHash...
arcdevkit debug tx 0xTxHash... --json
```

### REST API

A FastAPI server exposing all modules over HTTP. The `/health` endpoint reports live RPC latency and block number. Authentication is opt-in via the `API_KEY` environment variable and the `X-API-Key` header. Rate limiting caps the health endpoint at 30 requests per minute. The copilot route includes an SSE streaming endpoint at `POST /copilot/ask/stream`.

```bash
uvicorn arc_devkit.api.main:app --reload
# Swagger UI: http://localhost:8000/docs
```

### CLI

Two entry points cover the same feature set. `arcdevkit` uses grouped subcommands (`arcdevkit copilot ask`, `arcdevkit agent pay`). `arc` is a flat command set for scripting (`arc ask`, `arc balance`, `arc config set`). Both support `--json` for machine-readable output and `-v` for debug logging.

---

## Quick Start

```bash
pip install arc-devkit
```

Configure your `.env`:

```dotenv
ANTHROPIC_API_KEY=sk-ant-...
# Optional — defaults to mainnet; RPC/chain ID are pre-configured per network
ARC_NETWORK=testnet   # or mainnet (the SDK default)
ARC_PRIVATE_KEY=0x...
ANTHROPIC_MODEL=claude-sonnet-4-6
API_KEY=your-api-key
```

Verify the connection:

```bash
arc status
```

---

## Arc Blockchain Reference

| Property | Value |
|---|---|
| **EVM-compatible** | Solidity contracts without modification |
| **Gas token** | USDC — no separate native token needed |
| **Consensus** | Malachite — sub-second finality |
| **Agent Stack** | Native infrastructure for autonomous economic agents |
| **Mainnet RPC** | `https://rpc.mainnet.arc.io` — Chain ID `5042` |
| **Testnet RPC** | `https://rpc.testnet.arc.io` — Chain ID `5042002` |
| **Mainnet status** | Live — launched 2026-09-16 |

---

[Get started →](getting-started.md)
