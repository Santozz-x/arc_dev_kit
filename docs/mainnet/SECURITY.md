# Security — Read This Before Sending Real Funds

Arc DevKit now defaults to **Arc Mainnet**. Everything that was safe to experiment with on testnet can move real money on mainnet. This page is the single place that collects every protection Arc DevKit provides, and — just as important — what it does *not* protect you from.

## What Arc DevKit does for you

1. **Visual network distinction.** `arc status`/`arcdevkit status` render mainnet in red with an explicit "⚠ Real funds — mainnet" line; testnet renders in cyan with no warning. Never rely on chain ID alone at a glance — the label is there for a reason.
2. **Pre-broadcast confirmation on mainnet.** `arc send --broadcast` and `arcdevkit bridge send` print the network and a real-funds warning, then require interactive confirmation (or `--yes` for scripts) before broadcasting. Testnet never prompts.
3. **No silent chain ID fallback.** If a network's chain ID can't be resolved (no profile default, no `ARC_CHAIN_ID` override), `arc_devkit.config` raises at startup instead of silently defaulting to a different network's chain ID — a class of bug that existed before this migration and could have led to a transaction being built and signed for the wrong chain without any warning.
4. **Mandatory pre-broadcast simulation.** `PaymentAgent.execute()` runs the transaction through `eth_call` before broadcasting; a simulated revert aborts the send unless you explicitly pass `force=True`.
5. **`arcdevkit doctor` / `arc doctor`.** A read-only health check — RPC reachability, chain ID match, USDC contract actually deployed on-chain — that never signs or sends anything, safe to run anywhere including CI.
6. **Guardrails (opt-in).** `Guardrails` adds a daily USDC spend limit, a recipient whitelist, and a kill switch to `PaymentAgent`/`CCTPBridge`/`JobRegistry`. **Not enabled by default** — see below.

## What Arc DevKit does NOT do for you

- **It does not enable guardrails by default.** `MAX_SPEND_PER_DAY_USDC` and `AGENT_ALLOWED_RECIPIENTS` are empty in `.env.example`. An agent constructed without a `Guardrails` instance has no spend limit and no recipient restriction. If an agent signs without a human confirming each send, configure `Guardrails` explicitly — see [WALLETS.md](WALLETS.md).
- **It does not validate contract ABIs for correctness or safety.** `contracts.loader.send_tx()`/`ArcContract.send()` will happily call whatever function you name, with whatever arguments you pass. Review what you're calling.
- **It does not audit contracts you deploy or interact with.** `ContractDeployer` deploys exactly the bytecode you give it. Deployment on mainnet is irreversible.
- **It does not provide a `--network` per-command override yet** — see [CLI.md](CLI.md) Known Limitation. Double-check `ARC_NETWORK` in your active shell/`.env` before running anything that signs.
- **It does not manage secrets for you beyond the OS keyring fallback.** `ARC_PRIVATE_KEY` in a plaintext `.env` is convenient for development, not appropriate for production signing — use a proper secrets manager or hardware signer for production mainnet keys (hardware/PQ signer support is a stub today, see [WALLETS.md](WALLETS.md)).

## A pre-mainnet-transaction checklist

Before running anything that broadcasts on mainnet:

1. Run `arcdevkit doctor` — confirm `READY`.
2. Confirm `ARC_NETWORK` in your `.env`/shell is what you expect (`echo $ARC_NETWORK` or `arcdevkit config get ARC_NETWORK`).
3. Test the exact same code path against testnet first (`ARC_NETWORK=testnet`), including a failure case if relevant.
4. For an agent that runs unattended, configure `Guardrails` with a spend limit and recipient whitelist.
5. For a new contract, deploy and exercise it on testnet before mainnet deployment.
6. Read the transaction the CLI shows you before confirming — recipient, amount, network.

## Reporting a security issue

If you find a security issue in Arc DevKit itself (not in Arc the blockchain, which is Circle's), please open a private security advisory on the GitHub repository rather than a public issue.
