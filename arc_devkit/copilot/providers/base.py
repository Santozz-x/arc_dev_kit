"""Provider-agnostic interface for Dev Copilot's LLM backend.

DevCopilot (arc_devkit.copilot.agent) talks to whichever backend is active
only through this interface — it never imports anthropic/google-genai/openai
directly. This keeps ask()/ask_stream()/history/caching/offline-mode
provider-agnostic while each concrete provider owns the translation to its
own wire format.
"""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass


@dataclass
class ChatMessage:
    """One turn of conversation, in DevCopilot's neutral (non-provider) format."""

    role: str  # "user" or "assistant"
    content: str
    image_path: str | None = None  # only meaningful when role == "user"


class LLMProvider(ABC):
    """A chat-completion backend for Dev Copilot."""

    #: Model identifier this provider instance is configured with — every
    #: provider must set this in __init__ for logging/cache-key purposes.
    model: str

    @abstractmethod
    def ask(self, system: str, history: list[ChatMessage], max_tokens: int) -> str:
        """Send `history` (already including the current user turn) and return the reply text."""

    @abstractmethod
    def ask_stream(self, system: str, history: list[ChatMessage], max_tokens: int) -> Iterator[str]:
        """Same as ask(), but yields text chunks as they arrive."""

    def count_tokens(self, system: str, prompt: str) -> int:
        """
        Best-effort input token count for `prompt` (no completion call made).

        Providers without a dedicated counting endpoint return 0 rather than
        estimating — an approximate count presented as exact would be worse
        than admitting it's unavailable.
        """
        return 0

    @property
    def supports_tools(self) -> bool:
        """Whether this provider backs DevCopilot.run_agent() (tool-use loop)."""
        return False
