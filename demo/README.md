# Arc DevKit — Mainnet Demo (Arc Microgrants evidence)

Everything here exists to prove one concrete claim: **`pip install arc-devkit` works, today, against real Arc Mainnet**, using nothing but the SDK's own public API (`arc_devkit.Arc`). Arc DevKit is a Python toolkit (SDK + CLI) — this demo does not change that positioning; the website page and API below are thin, read-only wrappers around the same Python SDK, not a reimplementation.

## Contents

| Path | What it is |
|---|---|
| [`mainnet_demo.py`](mainnet_demo.py) | Standalone script — connect, health-check, read the latest block, find/read/analyze a real transaction. Depends only on the public `arc-devkit` package. |
| [`recording/`](recording/) | A real recorded terminal session: fresh venv → `pip install arc-devkit==0.10.0` → live Mainnet query. `.cast`, browser player, `.webm`/`.mp4`, transcript. |
| [`Dockerfile`](Dockerfile) | Builds the read-only demo API (`arc_devkit.api.demo_app`) that backs the website's `/demo` page. |
| [`render.yaml`](render.yaml) | Example deploy config (Render) for that API — a template, not an active deployment. |

The website integration (`website/app/demo/`) and the backend it calls (`arc_devkit/api/demo_app.py`) live in their usual places in the repo — see [`docs/mainnet/MAINNET_DEMO.md`](../docs/mainnet/MAINNET_DEMO.md) for the full write-up, live-vs-recorded distinction, and current publication status.

## Run the script yourself

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install arc-devkit==0.10.0
python3 mainnet_demo.py                    # auto-finds a recent confirmed tx
python3 mainnet_demo.py 0xYourTxHash...    # or inspect a specific one
```

Read-only, public data only — no `.env`, no wallet, no signing, no transactions sent, no contracts deployed. Exits non-zero with a clear message if the RPC is unreachable or the hash is invalid.

## Run the demo API yourself

```bash
pip install -e ".[dev]"   # from the repo root
uvicorn arc_devkit.api.demo_app:app --reload --port 8010
curl http://127.0.0.1:8010/demo/status
```

Needs no `ANTHROPIC_API_KEY` / `ARC_PRIVATE_KEY` — see the module docstring in [`arc_devkit/api/demo_app.py`](../arc_devkit/api/demo_app.py) for the two optional env vars it does read.

## Run the website page against it locally

```bash
cd website
NEXT_PUBLIC_DEMO_API_URL=http://127.0.0.1:8010 npm run dev
```

Open `/demo`. Without `NEXT_PUBLIC_DEMO_API_URL` set, the page still renders (code sample, install instructions, the recorded historical reference) but clearly shows a "backend unavailable / not configured" state instead of live data — it never fabricates a live-looking result.

## What is NOT included

- No PyPI publish was performed for this task (the `arc-devkit` used throughout is the already-published `0.10.0`).
- No production deployment of the demo API — see [`docs/mainnet/MAINNET_DEMO.md`](../docs/mainnet/MAINNET_DEMO.md) for exactly what's blocking that and what's already validated locally/in Docker.
