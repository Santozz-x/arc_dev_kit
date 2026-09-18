# Changelog

All notable changes to Arc DevKit are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Versioning: [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.9.0] — 2026-09-18 — Arc Mainnet Support

Arc Mainnet launched 2026-09-16. This release makes it Arc DevKit's default,
first-class network, with Arc Testnet remaining fully supported. Full audit,
plan, architecture map, and final report: [`docs/mainnet/`](docs/mainnet/).

**Breaking change:** `ARC_NETWORK` now defaults to `mainnet` (was `testnet`).
Set `ARC_NETWORK=testnet` explicitly to keep developing against testnet — see
[`docs/mainnet/MIGRATION_FROM_TESTNET.md`](docs/mainnet/MIGRATION_FROM_TESTNET.md).

### Added

- **Native Arc Mainnet configuration** — `arc_devkit/networks.py` now has
  fully sourced, verified values for both networks: chain ID, RPC/WS URL,
  explorer, and contract addresses for USDC, EURC, USYC, CCTP V2
  (TokenMessenger/MessageTransmitter/TokenMinter/Message), Gateway
  (Wallet/Minter), Multicall3, and Permit2. Every value cites its official
  source in `docs/mainnet/MIGRATION_AUDIT.md` Part B.
- **`arc_devkit.Arc`** — a new, additive facade class over the existing
  modules: `Arc.mainnet()` / `Arc.testnet()` / `Arc(network=..., rpc_url=...)`
  with `.get_balance()`, `.get_transaction()`, `.wait_for_transaction()`,
  `.latest_block()`, `.get_block()`, `.debug_transaction()`, `.usdc`,
  `.contract()`, and `.health_check()`. Every existing per-module import path
  keeps working unchanged.
- **`arc doctor` / `arcdevkit doctor`** (and `Arc.health_check()`) — read-only
  network health check: RPC reachability, chain ID match, latest block,
  latency, and USDC contract code presence (`eth_getCode`), backed by a new
  shared `arc_devkit.health` module.
- **USDC native/ERC-20 dual interface support** — USDC is Arc's native gas
  token (18 decimals) *and* an ERC-20 (6 decimals) at a fixed, network-shared
  address (`0x3600...0000`). New `native_usdc_balance()` reads the 18-decimal
  native view; `StablecoinToken`/`USDCToken` continue to cover the 6-decimal
  ERC-20 view, with `transfer_from()` added for completeness.
- **Mainnet safety prompts** — `arc send --broadcast` and
  `arcdevkit bridge send` print `Network: ARC MAINNET` /
  `WARNING: This transaction uses real funds.` and require confirmation (or
  `--yes`) before broadcasting on mainnet; testnet is unaffected.
- **`arc status`/`arcdevkit status`** now render the active network by name
  (with a red "real funds" warning on mainnet) instead of a hardcoded
  "Arc Testnet" label.
- **CCTP V2 support** — `CCTPBridge` now targets the correct
  `depositForBurn` V2 signature (destinationCaller/maxFee/minFinalityThreshold)
  and resolves the burn-token address from the active network instead of a
  hardcoded placeholder. **Not yet validated** against a live Arc CCTP
  contract — see Known Limitations below.
- `examples/mainnet/` — 10 runnable scripts (01–07 read-only, validated live
  against Arc Mainnet on 2026-09-18; 08–10 write real funds, gated behind an
  explicit `CONFIRM=yes`).
- `docs/mainnet/` — full mainnet documentation set: getting started, network
  config, USDC, transactions, gas/fees, smart contracts, wallets, transaction
  debugger, CLI, security, migration-from-testnet, plus the audit/plan/
  architecture/report docs behind this release.

### Fixed

- `config.py` no longer silently falls back to testnet's chain ID (`5042002`)
  when a network profile has no chain ID and none is set explicitly — it now
  raises a clear error instead of risking a transaction signed for the wrong
  chain.
- `core/gas.py`, `agents/payment_agent.py`, and `bridge/cctp.py` no longer
  import a hardcoded testnet USDC placeholder address — they resolve it from
  the active network's config, so `fees quote --token usdc` and USDC payments
  now work correctly regardless of `ARC_NETWORK`.
- `USDCToken()` no longer defaults to the zero address — it defaults to the
  real, official USDC ERC-20 address.
- Stale "testnet"/RPC/faucet references corrected throughout the CLI, API
  docstrings, Copilot's system prompt (which previously told Claude "mainnet
  expected Summer 2026" as ground truth), and portfolio AI analysis prompts.
- Default testnet RPC updated from `arc-testnet.drpc.org` to Circle's current
  official `rpc.testnet.arc.io`; faucet reference updated from the stale
  `faucet.arc.io` to the current `faucet.circle.com`.

### Known limitations

- CCTP V2 `depositForBurn` ABI is implemented per Circle's public
  documentation but **not exercised against a live Arc CCTP contract**.
- Circle's public Iris attestation API has an open, unresolved report (as of
  2026-09-18) of not returning attestations for Arc Testnet's CCTP domain 26.
- No per-command `--network` CLI override flag yet (use `ARC_NETWORK` in
  `.env`/shell).
- `debug_traceTransaction` support on Circle's default RPC is unconfirmed
  from an official source for either network.

See [`docs/mainnet/MAINNET_MIGRATION_REPORT.md`](docs/mainnet/MAINNET_MIGRATION_REPORT.md) for the full validation checklist.

---

## [0.8.0] — 2026-07-25

Implements all six sprints of `SPRINTS_2026H2.md` — multi-network config,
fees/paymaster, CCTP bridge, the ERC-8004/8183 agentic economy, an
Arc-aligned Copilot with its own MCP server, and privacy/post-quantum
groundwork. Wherever Arc/Circle haven't published a contract address or
endpoint yet (CCTP, paymasters, ERC-8004/8183 registries, confidential
transfers, price feeds), the affected code fails with a clear, explicit
error instead of guessing — that convention is used consistently across
every new module below.

### Added — Networks & Stablecoins (Sprint 1)

- `arc_devkit/networks.py` — `NetworkProfile`/`ContractAddresses` registry for `testnet`/`mainnet`; mainnet fields are explicit `None` placeholders
- `ARC_NETWORK` env var selects RPC/chain-ID defaults from the registry; explicit `ARC_RPC_URL`/`ARC_CHAIN_ID` always win, so existing `.env` files keep working unchanged
- `arc_devkit/stablecoins/` — generalizes `usdc/token.py` into `StablecoinToken` (`USDCToken`, `EURCToken`); `usdc/token.py` is now a backward-compatible re-export shim
- `arcdevkit network list|show|check-mainnet` CLI commands (the last is a mainnet-readiness dry-run — see `MAINNET_CHECKLIST.md`)
- Offline RPC regression tests via `vcrpy` cassette replay
- Keyring backend failures (e.g. no libsecret/D-Bus on headless Linux) now log a warning instead of failing silently

### Added — Fees & Paymaster (Sprint 2)

- `core/gas.py::quote_fee()` — fee quote in USDC for native or USDC ERC-20 transfers, plus paymaster availability (always `False` today — no Arc paymaster is published)
- `arc_devkit/paymaster/` — `detect_paymaster()` and a standard, chain-agnostic ERC-4337 `UserOperation` builder, ready for when Arc publishes Account Abstraction infrastructure
- `PaymentAgent.execute(..., use_paymaster=True)` fails clearly instead of pretending to sponsor the fee
- `arcdevkit fees quote` CLI + `GET /fees/quote` API

### Added — CCTP Bridge & Unified Balance (Sprint 3)

- `arc_devkit/bridge/` — `CCTPBridge` implements Circle's CCTP burn → attestation → mint flow; raises clearly when the active network has no published `cctp_token_messenger` address (true for testnet and mainnet today) or no `CCTP_ATTESTATION_API_URL` configured. `BridgeTransfer` records persist locally; `resume()` is the error-recovery entrypoint
- `MonitorAgent(watch_bridge_transfers=[...])` + `on_bridge_completed()` trigger
- `PortfolioAnalyzer.unified_balance()` — chain-agnostic USDC balance across Arc plus caller-supplied EVM chains
- `arcdevkit bridge send|status|resume` CLI + `POST /bridge/transfer`, `GET /bridge/status/{id}` API

### Added — Agentic Economy: ERC-8004 / ERC-8183 (Sprint 4)

- `agents/identity.py` — `AgentRegistry`: on-chain agent registration and reputation (ERC-8004)
- `agents/jobs.py` — `JobRegistry`: ERC-8183 escrow lifecycle (create → accept → deliver → settle), auditable via `Guardrails`
- `agents/job_agent.py` — `JobAgent(BaseAgent)` accepts and executes jobs autonomously within the kill switch
- `CoordinatorAgent.hire_agent()` — hires another agent via a job, through the coordinator's registered `PaymentAgent`
- `arcdevkit agent register|reputation|job create|accept|deliver|settle|status` CLI + `/agents/register`, `/agents/reputation/{id}`, `/agents/jobs*` API
- Cookbook recipe + `examples/06_agent_job_negotiation.py`: two agents negotiating a job end to end
- No canonical ERC-8004/8183 registry address is published for Arc — both clients always require an explicit registry address

### Added — Copilot, MCP Server & Debugger (Sprint 5)

- Copilot system prompt covers Stable Fee Design, Malachite finality, CCTP, and the agentic economy; explicitly told to say a feature "isn't published yet" rather than invent one
- New `run_agent()` tools: `get_fee_quote`, `get_bridge_status`, `get_agent_reputation`, `search_arc_docs` (keyword search over `ARC_LLMS_TXT_URL`'s llms.txt, when configured)
- `TxAnalyzer.trace_transaction()` — `debug_traceTransaction` support, with a clear "not supported by this RPC" result instead of a crash (most public RPCs, including Arc's default testnet endpoint, disable the `debug_*` namespace)
- `arcdevkit debug trace|compare` CLI commands
- `arc_devkit/mcp_server.py` — `arcdevkit mcp serve` runs a `FastMCP` stdio server exposing the same read-only tools to Claude Code and other MCP clients (optional `mcp` extra)

### Added — Privacy, Post-Quantum Prep & Mainnet Readiness (Sprint 6)

- `core/signer.py` — pluggable `Signer` interface; `LocalKeySigner` is the functional default (wired additively into `BaseAgent`), `LedgerSigner`/`TrezorSigner`/`MLDSASigner` are explicit stubs pending vendor SDKs / an Arc-published post-quantum scheme
- `arc_devkit/privacy/view_key.py` — working ECIES encryption (ECDH secp256k1 → HKDF-SHA256 → AES-256-GCM) for selective disclosure, independent of any on-chain protocol; `confidential_transfer.py` is the on-chain half, gated behind an explicit contract address
- `arc_devkit/oracle/price_feed.py` — Chainlink `AggregatorV3Interface`-compatible price feed client
- `locustfile.py` (read-only load tests) and `cliff.toml` (git-cliff changelog config)
- `MAINNET_CHECKLIST.md` and `arcdevkit network check-mainnet`
- `docs/playground.md` — hands-on guide across all six sprints' modules

### Fixed — Security

- `verify_api_key()` now uses `hmac.compare_digest()` instead of `!=` for the `X-API-Key` check (was vulnerable to a timing side-channel)
- The WebSocket monitor endpoint (`/agents/monitor/{address}`) previously bypassed `API_KEY` entirely despite a code comment claiming otherwise — it now requires the same key via an `api_key` query param (a WS handshake can't carry custom headers from a browser)

### Fixed — Usability

- Every new address-taking constructor (`JobRegistry`, `AgentRegistry`, `PriceOracle`, `ConfidentialTransferClient`, `CCTPBridge`) now validates input through `core/validation.validate_address()`. Previously, an invalid address crashed with an unhandled, web3-internal `ValueError` and a full traceback in both the CLI and REST API; it now returns a clean one-line error (CLI: `✗ Error: ...`, exit 1; API: `400` with a clear `detail`) — found via a dedicated usability pass across every new CLI command

---

## [0.4.7] — 2026-07-06

### Added — Agentic

- **DevCopilot tool use** — new `run_agent()` method: the model can call read-only on-chain tools (`get_balance`, `get_block_info`, `estimate_gas`, `debug_transaction`, `call_view_function`) in a tool-use loop with a 10-iteration circuit breaker; exposed via `arcdevkit copilot agent "..."` and `POST /copilot/agent`
- **Declarative triggers on `MonitorAgent`** — `on_low_balance()` (fires once per crossing, re-arms on recovery), `on_incoming_transfer()`, `on_block_interval()`; trigger failures are isolated from the polling loop
- **`AutoRefueler`** (`agents/autonomous.py`) — keeps a target address funded via guarded automatic top-ups
- **Replace-by-fee** — `PaymentAgent.speed_up(tx_hash)` resends a stuck tx with +10% gas; `execute(..., rbf=True)` applies it automatically on receipt timeout
- **`EventBus`** (`agents/event_bus.py`) — async pub/sub for inter-agent communication with isolated handler failures
- **`CoordinatorAgent`** (`agents/coordinator.py`) — plans workflows from natural-language goals using the agentic Copilot; `maintain_balance()` declarative workflow
- **`AgentDashboard`** — live terminal panel (`rich.Live`) via `arcdevkit agent dashboard <addrs...>`

### Added — Security

- **Autonomy guardrails** (`agents/guardrails.py`) — daily spend limit (`MAX_SPEND_PER_DAY_USDC`), recipient whitelist (`AGENT_ALLOWED_RECIPIENTS`), JSON-lines audit log (`~/.arc_devkit/audit.log`), kill switch (`arcdevkit agent stop` / `resume` / `audit`)
- **Mandatory pre-broadcast simulation** — `PaymentAgent.execute(enviar=True)` now aborts with `simulation_failed` when `eth_call` detects a revert (previously the simulation result was ignored); `force=True` bypasses
- **Gas price ceiling** — `MAX_GAS_PRICE_GWEI` rejects transactions above the configured limit
- **Shared input validation** (`core/validation.py`) — addresses, tx hashes, prompts (20k chars), amounts, ABIs, block ranges; applied across CLI, API, `TxAnalyzer`, and `PortfolioAnalyzer`
- **API hardening** — 64 KB body limit (413), `API_KEY` mandatory when `ENV=production` (503), HTTP→HTTPS redirect in production, security headers (`X-Content-Type-Options`, `X-Frame-Options`, HSTS), per-route rate limiting on all endpoints, failed-auth logging with client IP, 400 (not 500) for invalid addresses/hashes
- **OS keyring support** — `arc config keyring-set` / `keyring-clear` store `ARC_PRIVATE_KEY` outside `.env` (install with `pip install "arc-devkit[security]"`); `init` applies `chmod 600` and warns when a private key lands in `.env`
- **Prompt-injection mitigation** — tool results are truncated and wrapped as untrusted on-chain data before returning to the model
- **CI security job** — `bandit` static analysis and `pip-audit` dependency CVE scan

### Changed

- `TxAnalyzer.analyze()` validates the tx hash format and accepts `use_ai=False` for data-only analysis (used by Copilot tools to avoid recursion)
- `load_abi()` validates ABI structure before returning
- `PortfolioAnalyzer.analyze()` caps `scan_blocks` at 10,000

---

## [0.4.3] — 2026-06-28

### Fixed

- **`config.py`** — `load_dotenv()` replaced with `load_dotenv(find_dotenv(usecwd=True))` so the `.env` file is resolved from the user's current working directory instead of the installed package directory; fixes env vars not loading for Ubuntu/bash users
- **`__init__.py`** — `__version__` is now read dynamically from `importlib.metadata` instead of being hardcoded, so it always reflects the installed package version

### Added

- **`arcdevkit init`** — interactive `.env` wizard is now available as `arcdevkit init` (was only `arc init`), matching the CLI reference documentation
- **DevCopilot system prompt** — model is now explicitly instructed to prefer `arc_devkit.*` imports over raw `web3.py`, with the PyPI page and documentation URL added as authoritative references

---

## [0.4.2] — 2026-06-25

### Fixed

- Re-release of 0.4.1 fix: PyPI does not allow overwriting existing files; bumped patch to publish corrected `TxAnalyzer` with `rpc_url` support

---

## [0.4.1] — 2026-06-25

### Fixed

- **`TxAnalyzer.__init__`** — added `rpc_url: str | None` parameter for API consistency with `BaseAgent` and `AsyncMonitorAgent`; callers can now do `TxAnalyzer(rpc_url="https://...")` without constructing a `Web3` instance manually; `w3` parameter still accepted for backward compatibility
- `TxAnalyzer` builds the connection with `ExtraDataToPOAMiddleware` when `rpc_url` is provided, matching Arc testnet PoA requirements

---

## [0.4.0] — 2026-06-23

### Added

#### Async Agent Layer
- **`arc_devkit/agents/async_base.py`** — `AsyncBaseAgent` ABC: inherits wallet/RPC init from `BaseAgent`; abstract `async get_balance()` and `async execute()`; `_acall_rpc()` dispatches blocking web3 calls to thread pool via `asyncio.to_thread()`
- **`arc_devkit/agents/async_monitor.py`** — `AsyncMonitorAgent`: async monitoring loop with `asyncio.sleep`, supports both sync and async callbacks, async webhook delivery via `httpx.AsyncClient`, `event_stream(max_events)` async generator for WebSocket consumption, JSON state persistence

#### WebSocket Monitor (REST API)
- **`WS /agents/monitor/{address}`** — real-time balance-change event stream; query params `interval` (1–300 s) and `min_change_wei`; heartbeat `{"event_type": "ping"}` every second; events include native balance changes and ERC-20 Transfer events
- `ws_router` is registered without `APIKeyHeader` dependency (HTTP security schemes are incompatible with WebSocket scope)

#### DevCopilot Enhancements
- **Offline mode** — `DevCopilot(offline=True)`: all methods return a static message without making any Anthropic API call; ideal for CI environments or local tests without an API key
- **Image support** — `ask(prompt, image_path=)` and `ask_stream(prompt, image_path=)`: accepts PNG, JPEG, GIF, or WebP; base64-encodes the file and attaches it as an Anthropic image content block; `ValueError` on unsupported types
- `count_tokens()` returns `0` in offline mode

### Changed
- `agents/__init__.py` now exports `AsyncBaseAgent` and `AsyncMonitorAgent`
- `api/main.py` registers `agents_ws_router` on `/agents` prefix without auth dependency
- `ROADMAP.md` updated: 70/80 items complete (87.5%); v0.4.0 milestone marked done

### Tests
- 22 new tests in `tests/test_async_agents.py`
- Total: **223 unit tests passing**, **80.52% coverage** (threshold: 80%)

---

## [0.3.0] — 2026-06-22

### Added

#### MonitorAgent — ERC-20 events + webhook
- `_scan_erc20_events()`: scans Transfer logs from USDC contract on every polling cycle
- `_fire_webhook()`: HTTP POST via `httpx` to a configurable URL
- `_emit()`: centralizes callback + webhook dispatch
- `webhook_url` constructor parameter
- State format upgraded to `{"balances": {...}, "last_erc20_block": N}` (backward-compatible)

#### API
- `GET /debug/history?limit=20&offset=0` — paginated analysis history (newest-first)
- OpenAPI customization: description table, contact, license, tag metadata

#### Documentation
- `docs/migration-rpc.md` — migration guide from old RPC to `arc-testnet.drpc.org`
- `docs/cookbook.md` — 9 ready-to-use recipes: monitor+webhook, ERC-20 events, payment bot, debug batch, deploy, portfolio, events, API curl, shell completion
- `docs/api-reference.md` — complete REST API reference with curl examples
- `mkdocs.yml` updated with new pages

#### DevOps
- `Dockerfile` — Python 3.11-slim with non-root user
- `docker-compose.yml` — `api` service with healthcheck and `env_file`
- `README.md` — badges: PyPI, CI, coverage, Python, MIT, Testnet

---

## [0.2.0] — 2026-06-20

### Added

#### DevCopilot
- `ask_stream()` — streaming response via `Iterator[str]`
- `self._history` — in-memory conversation history
- `ANTHROPIC_MODEL` env var support (default: `claude-sonnet-4-6`)
- `count_tokens()` — token count estimate via Anthropic API
- `extra_context` constructor parameter injected into system prompt
- Response cache: MD5 hash of prompt+model, 5-minute TTL
- `clear_history()` and `history` property

#### Agents
- `BaseAgent`: tenacity retry on `ConnectionError/TimeoutError/OSError` (3 attempts, exponential backoff); multi-RPC fallback via comma-separated `ARC_RPC_URL`
- `PaymentAgent`: `_estimate_gas()`, `_wait_for_receipt()`, `_simulate()`, `on_success`/`on_failure` callbacks, `execute_batch()`
- `MonitorAgent`: `watched_addresses` (multiple wallets), `min_change_wei` threshold, `state_file` JSON persistence, stub ERC-20 ABI

#### New Modules
- **`arc_devkit/usdc/`** — `USDCToken`: `balance()`, `transfer()`, `allowance()`, `approve()` (6 decimals)
- **`arc_devkit/contracts/`** — `load_abi()`, `call_view()`, `send_tx()`, `decode_events()`
- **`arc_devkit/events/`** — `EventListener`: `eth_getLogs` polling with registered callbacks
- **`arc_devkit/deploy/`** — `ContractDeployer`: ABI+bytecode deploy and Solidity source deploy
- **`arc_devkit/analytics/`** — `PortfolioAnalyzer`: `PortfolioSnapshot`, `_scan_transactions()`, activity score, balance history, multi-wallet report

#### API
- `slowapi` rate limiting (30 req/min on `/health`)
- `X-API-Key` authentication via `API_KEY` env var (disabled if unset)
- Structured logging middleware with `X-Request-ID`
- `/health` with `rpc_connected`, `block_number`, `chain_id`, `latency_ms`
- `POST /copilot/ask/stream` — SSE streaming endpoint

#### CLI (`arc`)
- `arc config get/set/list`, `arc wallet create/balance`, `arc history`
- `arc init` — interactive `.env` wizard
- `arc portfolio analyze/report`
- `--json` flag (all commands), `-v/--verbose` flag
- `_validate_address()` for EVM checksum validation

#### Quality
- `mypy` type checking — 0 errors across all modules
- `pytest-cov` with 80% minimum threshold enforced in CI
- 201 unit tests at 82.78% coverage
- `@pytest.mark.integration` tests against live Arc testnet

#### DevOps
- `.github/workflows/ci.yml` — lint + unit + mypy + integration jobs
- `.github/workflows/publish.yml` — PyPI publish on `v*` tag push
- `.pre-commit-config.yaml` — ruff + mypy hooks
- `dependabot.yml` — automatic dependency updates
- GitHub Actions release automation via `gh release create`

---

---

## [0.2.1] — 2026-06-18

### Added
- **`examples/`** — 5 scripts executáveis prontos para uso: `01_check_connection.py`, `02_copilot_ask.py`, `03_estimate_gas.py`, `04_monitor_wallet.py`, `05_debug_tx.py`
- **`.github/workflows/ci.yml`** — pipeline de CI com lint (ruff) e testes unitários em Python 3.11, 3.12 e 3.13
- **`Makefile`** — atalhos de desenvolvimento: `make install`, `make test`, `make lint`, `make format`, `make build`, `make docs`
- **`mkdocs.yml`** — configuração do site de documentação com tema Material

### Changed
- **`README.md`** — reescrito em inglês com exemplos de instalação, uso da CLI, API REST e snippets de código
- **`docs/`** — documentação dos módulos alinhada com a API real do código v0.1/v0.2

### Fixed
- **`.env.example`** — token PyPI de teste removido do arquivo de exemplo (segurança)

---


---

## [0.1.0] — 2026-06-17

### Added
- `arc_devkit/config.py` — Settings from `.env`, validates required vars at import
- `arc_devkit/core/connection.py` — web3.py with `ExtraDataToPOAMiddleware` for Arc PoA testnet
- `arc_devkit/core/wallet.py` — EVM wallet creation and balance query
- `arc_devkit/core/gas.py` — USDC gas cost estimation
- `arc_devkit/copilot/agent.py` — `DevCopilot.ask()` with Arc system prompt
- `arc_devkit/agents/base_agent.py` — `BaseAgent` ABC with private key resolution and read-only mode
- `arc_devkit/agents/payment_agent.py` — build, sign, and (optionally) broadcast transactions
- `arc_devkit/agents/monitor_agent.py` — balance polling loop with callback
- `arc_devkit/debugger/tx_analyzer.py` — fetch tx via RPC + AI diagnosis
- `arc_devkit/api/` — FastAPI REST API with CORS for localhost
- `arc_devkit/cli/` — `arcdevkit` CLI with Typer subcommands
- 27 unit tests, MkDocs documentation, GitHub Actions CI

---

[0.4.0]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.2.0...v0.3.0
[0.2.1]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/Jeielsantosdev/arc-devkit/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Jeielsantosdev/arc-devkit/releases/tag/v0.1.0
