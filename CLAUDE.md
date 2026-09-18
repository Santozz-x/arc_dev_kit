# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Arc DevKit is a complete Python SDK for developers building on the **Arc blockchain** (by Circle) — EVM-compatible Layer 1 with USDC as gas token and Malachite consensus (<1s finality). Arc Mainnet launched 2026-09-16 and is the SDK's default network; Arc Testnet remains fully supported (`ARC_NETWORK=testnet`). Twelve modules: `Arc` facade, Dev Copilot, Payment Agent, Monitor Agent, Async Monitor, Tx Debugger, Portfolio Analyzer, USDC Token, Contracts, Event Listener, Contract Deployer, REST API + CLI.

Primary language: **Python 3.11+**. Mainnet RPC: `https://rpc.mainnet.arc.io` (chain ID `5042`). Testnet RPC: `https://rpc.testnet.arc.io` (chain ID `5042002`). Both are registered in `arc_devkit/networks.py` — see `docs/mainnet/MIGRATION_AUDIT.md` Part B for sourced network config (chain IDs, RPCs, explorers, USDC/EURC/CCTP/Gateway contract addresses). Claude model: `claude-sonnet-4-6`. Current version: **0.9.0**.

## Commands

```bash
# Install (development)
pip install -e ".[dev]"

# Run tests
pytest
pytest -k "test_name"        # single test

# Linting / formatting
ruff check .
ruff format .

# Primary CLI (grouped subcommands)
arcdevkit --help
arcdevkit status                    # check active network (mainnet/testnet) connection
arcdevkit doctor                    # RPC/chain-ID/USDC-contract/explorer health check
arcdevkit init                      # interactive .env wizard
arcdevkit copilot ask "..."
arcdevkit copilot ask "..." --stream
arcdevkit agent wallet create
arcdevkit agent pay <to> <amount>
arcdevkit debug tx <hash>
arcdevkit debug batch <h1> <h2>
arcdevkit config get ARC_RPC_URL
arcdevkit config set LOG_LEVEL DEBUG
arcdevkit portfolio analyze <address>
arcdevkit network list
arcdevkit network show <testnet|mainnet>
arcdevkit fees quote <to> <value> [--token native|usdc]
arcdevkit bridge send <to> <amount> --dest-domain <id> --dest-chain-id <id>
arcdevkit bridge status <transfer_id>
arcdevkit bridge resume <transfer_id> [--dest-rpc ... --message-transmitter ...]
arcdevkit agent register <domain> --registry <addr>
arcdevkit agent reputation <agent_id> --registry <addr> --reputation-registry <addr>
arcdevkit agent job create|accept|deliver|settle|status <args> --registry <addr>
arcdevkit debug trace <hash>                 # debug_traceTransaction (if RPC supports it)
arcdevkit debug compare <h1> <h2>
arcdevkit mcp serve                          # MCP server exposing on-chain tools (pip install arc-devkit[mcp])
arcdevkit oracle price <feed_address>        # Chainlink AggregatorV3Interface feed
arcdevkit privacy generate-view-key          # experimental: view-key encryption
arcdevkit privacy encrypt <pubkey_hex> "<message>"
arcdevkit network check-mainnet              # mainnet readiness dry-run
arcdevkit history
arcdevkit codegen "<description>"

# Flat CLI (direct commands — same functionality, no subgroups)
arc status / arc ask "..." / arc balance <addr> / arc gas <to> <amt>
arc debug <hash> / arc init / arc config / arc portfolio / arc history

# REST API server
uvicorn arc_devkit.api.main:app --reload

# Build docs
mkdocs serve       # local preview
mkdocs build       # static build
```

## Architecture

```
arc_devkit/
├── config.py           # Settings dataclass; reads env vars at import time
├── networks.py         # NetworkProfile/ContractAddresses registry (testnet/mainnet)
├── core/               # connection.py (web3 + PoA middleware), wallet.py, gas.py (quote_fee)
├── paymaster/          # detector.py (PaymasterInfo, always unavailable today), user_operation.py (ERC-4337)
├── bridge/             # cctp.py (CCTPBridge: burn→attestation→mint), models.py, store.py
├── privacy/            # view_key.py (working ECIES encryption), confidential_transfer.py (placeholder contract)
├── oracle/             # price_feed.py — Chainlink AggregatorV3Interface client
├── mcp_server.py       # FastMCP server — `arcdevkit mcp serve` (optional `mcp` extra)
├── copilot/            # agent.py — DevCopilot wrapping Anthropic SDK, tools.py — agentic tool registry
├── agents/             # base_agent.py (ABC), payment_agent.py, monitor_agent.py
│                       # async_base.py (AsyncBaseAgent ABC), async_monitor.py
│                       # identity.py (ERC-8004), jobs.py + job_agent.py (ERC-8183)
├── debugger/           # tx_analyzer.py — RPC fetch + AI analysis via DevCopilot
├── analytics/          # portfolio.py — PortfolioAnalyzer, PortfolioSnapshot, BalanceHistory
├── stablecoins/        # token.py — StablecoinToken (USDCToken, EURCToken), ERC-20 view (6 dec);
│                       # native_usdc_balance() for the native gas balance (18 dec)
├── usdc/               # legacy import path — thin re-export shim into stablecoins.token
├── contracts/          # loader.py — load_abi, call_view, send_tx, decode_events
├── events/             # listener.py — EventListener: eth_getLogs polling + callbacks
├── deploy/             # deployer.py — ContractDeployer: deploy from ABI+bytecode or Solidity
├── api/                # FastAPI app: routes/copilot, routes/agents (WebSocket), routes/debugger
└── cli/
    ├── flat.py         # `arc` entry point — direct commands (arc ask, arc balance, …)
    ├── main.py         # `arcdevkit` entry point — grouped subcommands (reuses flat.py sub-apps)
    └── commands/       # agent.py (+ nested job_app), copilot.py, debug.py, network.py, fees.py,
    │                   # bridge.py, mcp.py, oracle.py, privacy.py
```

**config.py** is the entry point for all configuration — loads `.env` via `find_dotenv(usecwd=True)` and exposes a global `settings` singleton. Raises `OSError` at import if `ANTHROPIC_API_KEY` or `ARC_RPC_URL` (with no `ARC_NETWORK` default available) are missing, and also if the resolved network has no chain ID from either the profile or an explicit `ARC_CHAIN_ID` (never silently falls back to another network's chain ID). `ARC_NETWORK` (`mainnet` default, or `testnet`) selects defaults from `networks.py` for RPC URL and chain ID — explicit `ARC_RPC_URL`/`ARC_CHAIN_ID` always take precedence, so existing `.env` files keep working unchanged. Both `mainnet` and `testnet` have official default RPCs filled in (Circle's `rpc.mainnet.arc.io` / `rpc.testnet.arc.io`) — `ARC_RPC_URL` is only needed to override with a private/paid provider.

**core/connection.py** wraps web3.py with `ExtraDataToPOAMiddleware` (required for Arc's permissioned-validator model on both mainnet and testnet). `get_web3()` is called per-use, not cached globally.

**core/signer.py** — pluggable `Signer` ABC (`address` property + `sign_transaction()`) preparing for Arc mainnet's planned post-quantum signer and hardware wallets. `LocalKeySigner` is the fully-functional default (wraps `eth_account`, same as every agent's existing signing path); `BaseAgent` builds one additively as `self._signer` whenever a private key is resolved (existing `self._private_key`-based signing is unchanged). `LedgerSigner`/`TrezorSigner`/`MLDSASigner` are stubs that raise `NotImplementedError` — they require vendor SDKs or an Arc-published PQ scheme that don't exist yet; do not treat their presence as working hardware/PQ support.

**privacy/** (experimental) — `view_key.py` is a fully working, generic ECIES construction (ephemeral ECDH over secp256k1 → HKDF-SHA256 → AES-256-GCM, built on `cryptography`'s audited primitives) for encrypting transfer details to a specific viewer's public key; usable today, independent of any on-chain protocol. `confidential_transfer.py::ConfidentialTransferClient` is the on-chain half — raises at construction without an explicit `contract_address` since Arc's confidential-transfer (TEE-based shielded amounts) protocol isn't exposed on testnet yet.

**oracle/price_feed.py** — `PriceOracle` reads a Chainlink `AggregatorV3Interface`-compatible feed (a stable, generic public standard, not Arc-specific). No feed address is bundled — pass one explicitly via `feed_address`.

**copilot/agent.py** — `DevCopilot` is instantiated per-call (not a singleton). Supports `offline=True` mode (no API calls), image attachments, multi-turn history, response cache (MD5, 5-min TTL), `ask_stream()` for SSE, and `run_agent()` (agentic tool-use loop, read-only tools only — never signs/sends).

**copilot/tools.py** — read-only tool registry for `run_agent()`: `get_balance`, `get_block_info`, `estimate_gas`, `debug_transaction`, `call_view_function`, `get_fee_quote`, `get_bridge_status`, `get_agent_reputation`, and `search_arc_docs` (keyword search over `ARC_LLMS_TXT_URL`'s llms.txt — returns a clear "not configured" result when the env var is unset, never fabricates doc content). All results are sanitized/truncated and marked untrusted before being fed back to the model.

**debugger/tx_analyzer.py** — `TxAnalyzer.analyze()` fetches via `eth_getTransaction` + `eth_getTransactionReceipt`, then calls `DevCopilot.ask()` for natural-language diagnosis; the result dict always includes a `network` field (best-effort chain-ID → "Arc Mainnet"/"Arc Testnet" label) so reports never get confused between networks. Accepts `rpc_url` or `w3` in constructor. `trace_transaction()` calls `debug_traceTransaction` via `w3.manager.request_blocking()` and returns `supported=False` with a clear message when the RPC disables the debug_* namespace (unconfirmed whether Circle's default RPC enables it on either network — see `docs/mainnet/MIGRATION_AUDIT.md` B.12) instead of raising.

**mcp_server.py** — `arcdevkit mcp serve` runs a `FastMCP("arc-devkit")` stdio server exposing the same read-only capabilities as `copilot/tools.py` (get_balance, get_block_info, get_fee_quote, debug_transaction, get_bridge_status, get_agent_reputation, call_view_function) to external MCP clients (Claude Code, etc). Requires the optional `mcp` extra (`pip install arc-devkit[mcp]`); the CLI command fails with a clear message if it's not installed.

**agents/base_agent.py** — `BaseAgent` (ABC) resolves `private_key` from constructor → `settings.arc_private_key` → `None` (read-only mode). Tenacity retry on connection errors. Multi-RPC fallback via comma-separated `ARC_RPC_URL`. Subclasses implement `get_balance()` and `execute()`.

**agents/async_base.py / async_monitor.py** — `AsyncBaseAgent` and `AsyncMonitorAgent` are the async-native variants for FastAPI/WebSocket use. `_acall_rpc()` dispatches blocking web3 calls to thread pool via `asyncio.to_thread()`. Supports async callbacks, webhook delivery via `httpx.AsyncClient`, and `event_stream()` async generator.

**analytics/portfolio.py** — `PortfolioAnalyzer` snapshots native + USDC balances, scans recent transactions, scores wallet activity (`high/medium/low/inactive`), and persists history as JSONL under `~/.arc_devkit/portfolio_history/`. `unified_balance(address, other_chains)` aggregates USDC balance across Arc plus caller-supplied EVM chains (Unified Balance view) — each chain is queried independently and a failure is recorded per-chain, not raised.

**bridge/cctp.py** — `CCTPBridge` implements Circle's CCTP V2 burn → attestation → mint flow. Arc is CCTP domain 26; TokenMessengerV2/MessageTransmitterV2/TokenMinterV2/MessageV2 addresses are published for both networks (see `networks.py`, sourced from docs.arc.io, verified 2026-09-18) — the depositForBurn ABI targets the V2 signature but is NOT VALIDATED against a live Arc contract yet (test on testnet with small amounts first). The attestation API is also not defaulted: set `CCTP_ATTESTATION_API_URL` yourself — as of 2026-09-18 there's an open, unresolved report that Circle's public Iris API doesn't return attestations for Arc Testnet's domain 26 (github.com/circlefin/evm-cctp-contracts/issues/110). `BridgeTransfer` records (`arc_devkit.bridge.models`) persist to `~/.arc_devkit/bridge_transfers/<id>.json`; `CCTPBridge.resume()` is the error-recovery entrypoint, dispatching to `fetch_attestation()`/`mint()` based on the transfer's last status. Optional `guardrails=` applies the same daily-spend/whitelist/kill-switch checks as `PaymentAgent`. `MonitorAgent(watch_bridge_transfers=[...])` + `on_bridge_completed()` fires once a watched transfer reaches `COMPLETE`.

**agents/identity.py / jobs.py / job_agent.py** — ERC-8004 (agent identity/reputation) and ERC-8183 (agent job escrow) are very recent EIPs with no published Arc (or confirmed cross-chain canonical) deployment address — `AgentRegistry`/`JobRegistry` always require an explicit registry address; the built-in ABIs are this SDK's best-effort reconstruction of the draft spec (override via `abi=`). `AgentRegistry.register()`/`get_reputation()`/`give_feedback()` wrap the Identity + Reputation registries. `JobRegistry.create_job()` (requires prior ERC-20 `approve()` for escrow) → `accept_job()` → `deliver_job()` → `settle_job()`, all returning a `Job` with `.error` set on failure (never raises) and auditing via `Guardrails` when configured. `JobAgent(BaseAgent)` accepts + runs a handler + delivers within the kill switch. `CoordinatorAgent.hire_agent()` creates a job through the coordinator's registered `PaymentAgent` wallet.

**stablecoins/token.py** — `StablecoinToken` wraps a Circle stablecoin ERC-20 contract (`USDCToken`, `EURCToken` subclasses) via the **6-decimal** ERC-20 interface. `USDCToken()` defaults to `arc_devkit.networks.USDC_ERC20_ADDRESS` (`0x3600...0000`, identical on mainnet/testnet — no more zero-address placeholder). `_to_atomic()`/`_from_atomic()` convert between `Decimal` (human) and `int` for that 6-decimal view. USDC is *also* Arc's native gas token at **18 decimals** (like ETH) — `native_usdc_balance(address)` reads that separately via `eth_getBalance`; never conflate the two balances. `arc_devkit/usdc/token.py` re-exports the same names for backward compatibility — new code should import from `stablecoins.token`.

**networks.py** — `NETWORKS` registry maps `"mainnet"`/`"testnet"` to a `NetworkProfile` (chain ID, RPC/WS RPC URL, explorer URL, `ContractAddresses`: usdc, eurc, cctp_token_messenger/message_transmitter/token_minter/message, cctp_domain, gateway_wallet/minter, multicall3, permit2). Both networks are fully filled in and sourced from docs.arc.io (verified 2026-09-18 — see `docs/mainnet/MIGRATION_AUDIT.md` Part B). `get_network(name)` raises `ValueError` on unknown names. `settings.network` resolves the active profile from `ARC_NETWORK` (default `mainnet`). USDC's ERC-20 address (`USDC_ERC20_ADDRESS`, `0x3600...0000`) is identical on both networks and is also Arc's native gas token at a different decimal scale (18 native vs. 6 ERC-20) — see `stablecoins/token.py`.

**client.py** — `Arc` is an additive facade over the existing modules (`from arc_devkit import Arc`): `Arc.mainnet()`/`Arc.testnet()`/`Arc(network=..., rpc_url=...)`, with `.get_balance()`, `.get_transaction()`, `.wait_for_transaction()`, `.latest_block()`, `.get_block()`, `.debug_transaction()` (delegates to `TxAnalyzer`), `.usdc` (a bound `USDCToken`), `.contract(address, abi)` (returns `ArcContract` wrapping `contracts.loader.call_view`/`send_tx`), and `.health_check()` (delegates to `health.run_health_check`). Every existing per-module import path keeps working unchanged.

**health.py** — `run_health_check(profile, w3=None)` is the shared, read-only implementation behind both `arc doctor`/`arcdevkit doctor` (`cli/doctor.py`) and `Arc.health_check()`: RPC reachability, chain ID match, latest block, latency, and USDC contract code presence (`eth_getCode`) — never signs or sends anything.

**core/gas.py** — `quote_fee(to, amount, token, from_address)` quotes the fee (always in USDC, the gas token) for a native or USDC ERC-20 transfer, resolving the USDC contract address from `settings.network.contracts.usdc` (fixed from a prior hardcoded testnet placeholder), and reports paymaster availability via `arc_devkit.paymaster.detect_paymaster()`. `estimate_transfer()` (native-only) remains the function backing `/debug/estimate` and `arcdevkit debug estimate`.

**paymaster/** — `detector.py::detect_paymaster(network)` always returns `available=False` today (no Arc paymaster contract or bundler endpoint is published yet — same explicit-placeholder convention as `networks.py`). `user_operation.py` implements the standard (chain-agnostic) ERC-4337 `UserOperation` shape (`build_user_operation()`, `submit_user_operation()` to a caller-supplied bundler) so it's ready once Arc publishes AA infrastructure. `PaymentAgent.execute(..., use_paymaster=True)` fails clearly rather than pretending to sponsor the fee.

**contracts/loader.py** — `load_abi()` reads from JSON file. `call_view()` calls read-only functions. `send_tx()` signs and broadcasts. `decode_events()` parses receipt logs against ABI.

**events/listener.py** — `EventListener` polls `eth_getLogs` on each `poll()` call. Register callbacks with `on(event_name, callback)`. `start_polling(interval)` runs a blocking loop.

**deploy/deployer.py** — `ContractDeployer` deploys from ABI+bytecode or compiles Solidity source (requires `solcx`). Returns `DeployResult` dataclass with address, tx hash, gas used.

**api/main.py** — FastAPI with CORS (`localhost:3000/5173/8080`), `X-API-Key` auth (disabled if `API_KEY` env unset; WebSocket routes take the same key via an `api_key` query param), rate limiting via `slowapi`, structured logging middleware, SSE streaming on `/copilot/ask/stream`, WebSocket monitor on `/agents/monitor/{address}`, fee quotes on `/fees/quote`, CCTP bridge transfers on `/bridge/transfer` + `/bridge/status/{id}`, agent identity/reputation on `/agents/register` + `/agents/reputation/{id}`, and ERC-8183 jobs on `/agents/jobs` + `/agents/jobs/{id}` + `/agents/jobs/{id}/settle`.

## Key Conventions

- All monetary values use Python `Decimal`, never `float`
- Native/gas balances: 18 decimal places (`from_wei(..., "ether")`); USDC: 6 decimals — never mix these
- `ARC_PRIVATE_KEY` is optional; read-only operations work without it
- Tests set env vars in `conftest.py` before any package import to avoid `OSError` from `config.py`
- Integration tests (live RPC) are marked `@pytest.mark.integration` and skipped by default
- `cli/commands/*` and `cli/main.py` are excluded from coverage measurement (covered indirectly via flat.py)
- Coverage threshold: **80%** enforced by pytest-cov (`--cov-fail-under=80`)
