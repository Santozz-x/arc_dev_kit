"""Arc DevKit REST API — FastAPI."""

import hmac
import logging
import time
import uuid

from fastapi import FastAPI, HTTPException, Request, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security.api_key import APIKeyHeader
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from arc_devkit import __version__
from arc_devkit.api.auth import get_api_key, is_production
from arc_devkit.api.rate_limit import limiter
from arc_devkit.api.routes import agent_economy, agents, bridge, copilot, debugger, fees
from arc_devkit.api.routes.agents import ws_router as agents_ws_router

logger = logging.getLogger(__name__)

# Maximum accepted request body size (DoS protection)
MAX_BODY_BYTES = 64 * 1024  # 64 KB
_is_production = is_production


_DESCRIPTION = """\
**Arc DevKit** — developer toolkit for the [Arc blockchain](https://arc.io) by Circle.

Arc is an EVM-compatible Layer 1 that uses **USDC as the gas token** and achieves
sub-second finality with the Malachite consensus engine.

## Modules

| Module | Prefix | Description |
|---|---|---|
| 🤖 Dev Copilot | `/copilot` | Claude-powered AI assistant for Arc development |
| 💸 Agents | `/agents` | Wallet management, payment & monitor agents |
| 🔍 Tx Debugger | `/debug` | Transaction analysis, revert decoding, gas estimation |

## Authentication

Set the `API_KEY` environment variable to enable key-based authentication.
Pass the key via the `X-API-Key` header on every request.
If `API_KEY` is unset, authentication is **disabled** (suitable for local dev).

## Rate Limiting

`GET /health` is limited to **30 requests/minute** per IP.
"""

_TAGS_METADATA = [
    {
        "name": "Dev Copilot",
        "description": "AI assistant powered by Claude. Specializes in Arc/EVM development, Solidity, web3.py, and USDC integration.",
    },
    {
        "name": "Agents",
        "description": "Wallet creation, balance queries, payment execution (native ARC or USDC ERC-20), and block info.",
    },
    {
        "name": "Tx Debugger",
        "description": "Analyze transactions, decode reverts and ABI input data, estimate gas costs, and paginate analysis history.",
    },
    {
        "name": "Fees",
        "description": "Quote transfer fees in USDC (native ARC or stablecoin transfers) and paymaster availability.",
    },
    {
        "name": "Bridge",
        "description": "Cross-chain USDC transfers via CCTP: start a burn, check status, resume after a failure.",
    },
    {
        "name": "Agent Economy",
        "description": "ERC-8004 agent identity/reputation and ERC-8183 job marketplace with USDC escrow.",
    },
    {
        "name": "Infra",
        "description": "Health check and connectivity status.",
    },
]

app = FastAPI(
    title="Arc DevKit API",
    description=_DESCRIPTION,
    version=__version__,
    contact={
        "name": "Jeielsantosdev",
        "url": "https://github.com/Jeielsantosdev/arc-devkit",
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT",
    },
    openapi_tags=_TAGS_METADATA,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)  # type: ignore[arg-type]

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Header for API Key authentication
_API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(request: Request, api_key: str | None = Security(_API_KEY_HEADER)) -> None:
    """
    Verify the API key if API_KEY is set in the environment.

    In development, a missing API_KEY disables authentication. In production
    (ENV=production), API_KEY is mandatory — requests fail with 503 until it
    is configured, so authentication can never be silently disabled.
    """
    required_key = get_api_key()

    if not required_key:
        if _is_production():
            logger.error("API_KEY is not configured but ENV=production — refusing request.")
            raise HTTPException(
                status_code=503,
                detail="API_KEY must be configured when ENV=production.",
            )
        return

    if api_key is None or not hmac.compare_digest(api_key, required_key):
        client_ip = request.client.host if request.client else "unknown"
        logger.warning("Failed authentication attempt: ip=%s path=%s", client_ip, request.url.path)
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")


# Security middleware: HTTPS redirect (prod), body size limit, security headers
@app.middleware("http")
async def security_middleware(request: Request, call_next):
    if _is_production() and request.url.scheme == "http":
        forwarded_proto = request.headers.get("x-forwarded-proto", "")
        if forwarded_proto != "https":
            https_url = request.url.replace(scheme="https")
            return RedirectResponse(url=str(https_url), status_code=308)

    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body too large (max {MAX_BODY_BYTES} bytes)."},
        )

    response = await call_next(request)

    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    if _is_production():
        response.headers.setdefault(
            "Strict-Transport-Security", "max-age=63072000; includeSubDomains"
        )
    return response


# Structured logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    request_id = str(uuid.uuid4())[:8]
    inicio = time.time()

    logger.info(
        "request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path,
    )

    response = await call_next(request)
    latencia_ms = int((time.time() - inicio) * 1000)

    logger.info(
        "request_id=%s status=%d latency_ms=%d",
        request_id,
        response.status_code,
        latencia_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response


# Register routers with API key verification as a global dependency
app.include_router(
    copilot.router,
    prefix="/copilot",
    tags=["Dev Copilot"],
    dependencies=[Security(verify_api_key)],
)
app.include_router(
    agents.router,
    prefix="/agents",
    tags=["Agents"],
    dependencies=[Security(verify_api_key)],
)
app.include_router(
    debugger.router,
    prefix="/debug",
    tags=["Tx Debugger"],
    dependencies=[Security(verify_api_key)],
)
app.include_router(
    fees.router,
    prefix="/fees",
    tags=["Fees"],
    dependencies=[Security(verify_api_key)],
)
app.include_router(
    bridge.router,
    prefix="/bridge",
    tags=["Bridge"],
    dependencies=[Security(verify_api_key)],
)
app.include_router(
    agent_economy.router,
    prefix="/agents",
    tags=["Agent Economy"],
    dependencies=[Security(verify_api_key)],
)


app.include_router(
    agents_ws_router,
    prefix="/agents",
    tags=["Agents"],
)


@app.get("/health", tags=["Infra"])
@limiter.limit("30/minute")
async def health(request: Request) -> dict:
    """
    Return API status including Arc RPC connectivity for the active network
    (ARC_NETWORK — mainnet or testnet).

    Fields:
    - status: "ok" or "degraded"
    - version: installed package version
    - rpc_connected: True if the configured Arc RPC responds
    - block_number: current block (if connected)
    - latency_ms: RPC call latency in milliseconds
    """
    from arc_devkit.core.connection import get_web3

    rpc_info: dict = {"rpc_connected": False}
    try:
        t0 = time.time()
        w3 = get_web3()
        block = w3.eth.block_number
        latencia_ms = int((time.time() - t0) * 1000)
        rpc_info = {
            "rpc_connected": True,
            "block_number": block,
            "chain_id": w3.eth.chain_id,
            "latency_ms": latencia_ms,
        }
    except Exception as exc:
        rpc_info["rpc_error"] = str(exc)

    return {
        "status": "ok" if rpc_info["rpc_connected"] else "degraded",
        "version": __version__,
        **rpc_info,
    }
