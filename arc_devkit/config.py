"""Configuration loading and validation via environment variables."""

import logging
import os
from dataclasses import dataclass
from decimal import Decimal

from dotenv import find_dotenv, load_dotenv

from arc_devkit.networks import DEFAULT_NETWORK, NetworkProfile, get_network

load_dotenv(find_dotenv(usecwd=True))

logger = logging.getLogger(__name__)

# Keyring service/entry names used to store the private key outside .env
KEYRING_SERVICE = "arc-devkit"
KEYRING_KEY_NAME = "ARC_PRIVATE_KEY"


@dataclass(frozen=True)
class Settings:
    """Global Arc DevKit settings loaded from environment."""

    anthropic_api_key: str
    arc_rpc_url: str
    arc_rpc_urls: tuple[str, ...]
    arc_chain_id: int
    arc_private_key: str | None
    log_level: str
    anthropic_model: str
    arc_network: str = DEFAULT_NETWORK
    env: str = "development"
    max_gas_price_gwei: Decimal | None = None
    max_spend_per_day_usdc: Decimal | None = None
    agent_allowed_recipients: tuple[str, ...] = ()
    cctp_attestation_api_url: str | None = None
    arc_llms_txt_url: str | None = None
    # Dev Copilot LLM backend — see arc_devkit.copilot.providers. "anthropic"
    # (the default) keeps ANTHROPIC_API_KEY required, same as before this was
    # added; any other provider makes it optional and requires that
    # provider's own key/model instead (no model name is ever guessed).
    copilot_provider: str = "anthropic"
    gemini_api_key: str | None = None
    gemini_model: str | None = None
    openai_api_key: str | None = None
    openai_model: str | None = None
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str | None = None

    @property
    def is_production(self) -> bool:
        """True when ENV=production — enables fail-safe security defaults."""
        return self.env == "production"

    @property
    def network(self) -> NetworkProfile:
        """The resolved NetworkProfile for arc_network."""
        return get_network(self.arc_network)


def _load_key_from_keyring() -> str | None:
    """Read the private key from the OS keyring, if the keyring lib is installed."""
    try:
        import keyring

        return keyring.get_password(KEYRING_SERVICE, KEYRING_KEY_NAME) or None
    except ImportError:
        return None
    except Exception as exc:
        logger.warning(
            "Keyring backend unavailable (%s) — falling back to ARC_PRIVATE_KEY from .env, "
            "if set. On Linux this usually means no libsecret/D-Bus session is available.",
            exc,
        )
        return None


def _parse_optional_decimal(name: str) -> Decimal | None:
    raw = os.getenv(name, "").strip()
    if not raw:
        return None
    try:
        return Decimal(raw)
    except Exception:
        logging.getLogger(__name__).warning("Invalid %s=%r — ignoring.", name, raw)
        return None


def _load_settings() -> Settings:
    """Read, validate, and return all settings from the environment."""
    erros: list[str] = []

    api_key = os.getenv("ANTHROPIC_API_KEY", "").strip()
    copilot_provider = os.getenv("COPILOT_PROVIDER", "").strip().lower() or "anthropic"
    gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip() or None
    gemini_model = os.getenv("GEMINI_MODEL", "").strip() or None
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip() or None
    openai_model = os.getenv("OPENAI_MODEL", "").strip() or None
    ollama_model = os.getenv("OLLAMA_MODEL", "").strip() or None

    network_name = os.getenv("ARC_NETWORK", "").strip().lower() or DEFAULT_NETWORK
    try:
        profile = get_network(network_name)
    except ValueError as exc:
        raise OSError(f"\n\n  {exc}\n") from exc

    # ARC_RPC_URL/ARC_CHAIN_ID always win when set explicitly; otherwise fall
    # back to the ARC_NETWORK profile's defaults (e.g. testnet's public RPC).
    rpc_url = os.getenv("ARC_RPC_URL", "").strip() or (profile.rpc_url or "")
    chain_id_raw = os.getenv("ARC_CHAIN_ID", "").strip()

    # ANTHROPIC_API_KEY is only mandatory when it's actually the active
    # Copilot backend (the default) — COPILOT_PROVIDER=gemini/openai/ollama
    # doesn't need it, but does need its own key/model (checked below).
    if copilot_provider == "anthropic" and not api_key:
        erros.append("ANTHROPIC_API_KEY")
    if copilot_provider == "gemini" and not gemini_api_key:
        erros.append("GEMINI_API_KEY")
    if copilot_provider == "gemini" and not gemini_model:
        erros.append("GEMINI_MODEL")
    if copilot_provider == "openai" and not openai_api_key:
        erros.append("OPENAI_API_KEY")
    if copilot_provider == "openai" and not openai_model:
        erros.append("OPENAI_MODEL")
    if copilot_provider == "ollama" and not ollama_model:
        erros.append("OLLAMA_MODEL")
    if copilot_provider not in ("anthropic", "gemini", "openai", "ollama"):
        raise OSError(
            f"\n\n  Unknown COPILOT_PROVIDER {copilot_provider!r}. "
            "Supported: anthropic, gemini, openai, ollama.\n"
        )
    if not rpc_url:
        erros.append("ARC_RPC_URL")

    if erros:
        lista = ", ".join(erros)
        extra = (
            f"\n  Network {network_name!r} has no default RPC yet — set ARC_RPC_URL explicitly."
            if "ARC_RPC_URL" in erros and profile.rpc_url is None
            else ""
        )
        raise OSError(
            f"\n\n  Required variables not configured: {lista}\n"
            f"  Run: cp .env.example .env  and fill in the values.\n"
            f"{extra}"
        )

    # Support multiple comma-separated RPCs
    rpc_urls = tuple(u.strip() for u in rpc_url.split(",") if u.strip())

    if chain_id_raw:
        chain_id = int(chain_id_raw)
    elif profile.chain_id is not None:
        chain_id = profile.chain_id
    else:
        # Never silently default to another network's chain ID — that would
        # let a transaction get signed for the wrong chain without warning.
        raise OSError(
            f"\n\n  Network {network_name!r} has no default chain ID and ARC_CHAIN_ID "
            "is not set.\n  Set ARC_CHAIN_ID explicitly in your .env.\n"
        )

    # Private key resolution: env var > OS keyring > None (read-only mode)
    private_key = os.getenv("ARC_PRIVATE_KEY", "").strip() or _load_key_from_keyring()

    whitelist = tuple(
        a.strip() for a in os.getenv("AGENT_ALLOWED_RECIPIENTS", "").split(",") if a.strip()
    )

    return Settings(
        anthropic_api_key=api_key,
        arc_rpc_url=rpc_urls[0],  # Primary URL
        arc_rpc_urls=rpc_urls,
        arc_chain_id=chain_id,
        arc_private_key=private_key,
        log_level=os.getenv("LOG_LEVEL", "INFO").upper(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
        arc_network=network_name,
        env=os.getenv("ENV", "development").strip().lower() or "development",
        max_gas_price_gwei=_parse_optional_decimal("MAX_GAS_PRICE_GWEI"),
        max_spend_per_day_usdc=_parse_optional_decimal("MAX_SPEND_PER_DAY_USDC"),
        agent_allowed_recipients=whitelist,
        cctp_attestation_api_url=os.getenv("CCTP_ATTESTATION_API_URL", "").strip() or None,
        arc_llms_txt_url=os.getenv("ARC_LLMS_TXT_URL", "").strip() or None,
        copilot_provider=copilot_provider,
        gemini_api_key=gemini_api_key,
        gemini_model=gemini_model,
        openai_api_key=openai_api_key,
        openai_model=openai_model,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "").strip() or "http://localhost:11434",
        ollama_model=ollama_model,
    )


# Global singleton — imported by all modules
settings = _load_settings()

# Configure global logging with level from .env
logging.basicConfig(
    level=getattr(logging, settings.log_level, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
