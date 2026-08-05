"""
LLM provider abstraction for natural-language-to-SQL generation.

Supports Anthropic, OpenAI, OpenRouter, and local Ollama models behind a single
interface so the rest of the server doesn't need to know which backend is in use.
"""

import os
import logging
from abc import ABC, abstractmethod
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

SQL_SYSTEM_PROMPT = (
    "You are a SQL generator. Given a database schema and a natural language question, "
    "output ONLY the {dialect} SQL query that answers it. No explanation, no markdown "
    "fences, no commentary - just the raw SQL statement starting with SELECT."
)


def build_sql_prompt(nl_query: str, schema_context: str, dialect: str) -> Tuple[str, str]:
    """Build (system_prompt, user_prompt) for SQL generation, shared by all providers."""
    system = SQL_SYSTEM_PROMPT.format(dialect=dialect)
    user = f"Schema:\n{schema_context}\n\nQuestion: {nl_query}\n\nSQL:"
    return system, user


class LLMProvider(ABC):
    """Common interface for all LLM backends used for NL-to-SQL generation."""

    def __init__(self, model: str, temperature: float, max_tokens: int):
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens

    @abstractmethod
    async def generate_sql(self, nl_query: str, schema_context: str, dialect: str) -> str:
        """Return a raw SQL string generated from the natural language query."""
        raise NotImplementedError


class AnthropicProvider(LLMProvider):
    def __init__(self, model: str, api_key: str, temperature: float, max_tokens: int):
        super().__init__(model, temperature, max_tokens)
        import anthropic
        self._client = anthropic.AsyncAnthropic(api_key=api_key)

    async def generate_sql(self, nl_query: str, schema_context: str, dialect: str) -> str:
        system, user = build_sql_prompt(nl_query, schema_context, dialect)
        response = await self._client.messages.create(
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", None) == "text"
        ).strip()


class OpenAIProvider(LLMProvider):
    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        base_url: Optional[str] = None,
    ):
        super().__init__(model, temperature, max_tokens)
        import openai
        self._client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)

    async def generate_sql(self, nl_query: str, schema_context: str, dialect: str) -> str:
        system, user = build_sql_prompt(nl_query, schema_context, dialect)
        response = await self._client.chat.completions.create(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return (response.choices[0].message.content or "").strip()


class OpenRouterProvider(OpenAIProvider):
    """OpenRouter exposes an OpenAI-compatible API, so we reuse OpenAIProvider's
    client with a fixed base_url and OpenRouter's recommended attribution headers."""

    def __init__(
        self,
        model: str,
        api_key: str,
        temperature: float,
        max_tokens: int,
        base_url: Optional[str] = None,
    ):
        super().__init__(
            model, api_key, temperature, max_tokens,
            base_url=base_url or "https://openrouter.ai/api/v1",
        )
        self._client = self._client.with_options(
            default_headers={
                "HTTP-Referer": os.getenv("OPENROUTER_SITE_URL", "https://github.com/mcp-db-server"),
                "X-Title": os.getenv("OPENROUTER_APP_NAME", "mcp-db-server"),
            }
        )


class OllamaProvider(LLMProvider):
    """Local Ollama models via its native /api/chat endpoint. No API key required."""

    def __init__(
        self,
        model: str,
        temperature: float,
        max_tokens: int,
        base_url: Optional[str] = None,
    ):
        super().__init__(model, temperature, max_tokens)
        import httpx
        self.base_url = (base_url or "http://localhost:11434").rstrip("/")
        self._client = httpx.AsyncClient(timeout=120.0)

    async def generate_sql(self, nl_query: str, schema_context: str, dialect: str) -> str:
        system, user = build_sql_prompt(nl_query, schema_context, dialect)
        response = await self._client.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "stream": False,
                # Reasoning models (qwen3.x, deepseek-r1, etc.) put chain-of-thought in a
                # separate "thinking" field and leave "content" empty until reasoning
                # finishes - which can exceed num_predict and return nothing usable.
                # think=False skips that and puts the answer straight into "content".
                "think": False,
                "options": {"temperature": self.temperature, "num_predict": self.max_tokens},
            },
        )
        response.raise_for_status()
        data = response.json()
        message = data.get("message", {})
        return (message.get("content") or message.get("thinking") or "").strip()


def _resolve_api_key(*fallback_env_vars: str) -> Optional[str]:
    """LLM_API_KEY takes priority; falls back to the provider's conventional env var
    so users with ANTHROPIC_API_KEY/OPENAI_API_KEY/OPENROUTER_API_KEY already set keep working."""
    key = os.getenv("LLM_API_KEY")
    if key:
        return key
    for var in fallback_env_vars:
        key = os.getenv(var)
        if key:
            return key
    return None


def get_llm_provider() -> Optional[LLMProvider]:
    """Build an LLMProvider from environment variables, or None if not configured
    (callers should fall back to rule-based SQL generation in that case)."""
    provider_name = os.getenv("LLM_PROVIDER", "").strip().lower()
    if not provider_name:
        return None

    model = os.getenv("LLM_MODEL")
    if not model:
        logger.warning("LLM_PROVIDER=%s set but LLM_MODEL is missing; disabling LLM generation.", provider_name)
        return None

    temperature = float(os.getenv("LLM_TEMPERATURE", "0.0"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "512"))
    base_url = os.getenv("LLM_BASE_URL")

    try:
        if provider_name == "anthropic":
            api_key = _resolve_api_key("ANTHROPIC_API_KEY")
            if not api_key:
                raise ValueError("No Anthropic API key found (set LLM_API_KEY or ANTHROPIC_API_KEY)")
            return AnthropicProvider(model, api_key, temperature, max_tokens)

        if provider_name == "openai":
            api_key = _resolve_api_key("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("No OpenAI API key found (set LLM_API_KEY or OPENAI_API_KEY)")
            return OpenAIProvider(model, api_key, temperature, max_tokens, base_url=base_url)

        if provider_name == "openrouter":
            api_key = _resolve_api_key("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("No OpenRouter API key found (set LLM_API_KEY or OPENROUTER_API_KEY)")
            return OpenRouterProvider(model, api_key, temperature, max_tokens, base_url=base_url)

        if provider_name == "ollama":
            return OllamaProvider(model, temperature, max_tokens, base_url=base_url)

        logger.warning("Unknown LLM_PROVIDER=%s; disabling LLM generation.", provider_name)
        return None

    except Exception as e:
        logger.warning("Failed to initialize LLM provider '%s': %s", provider_name, e)
        return None
