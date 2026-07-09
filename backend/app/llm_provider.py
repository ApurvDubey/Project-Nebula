"""LLM provider configuration and client factories.

Provides cached OpenAI-compatible clients for both async and sync usage,
plus a monkey-patch function so the vendored PageIndex library automatically
picks up the configured LLM provider.
"""

from functools import lru_cache

import openai

from app.config import settings


def _resolve_api_key() -> str:
    """Return the API key, falling back to 'not-needed' for local providers."""
    return settings.LLM_API_KEY or "not-needed"


@lru_cache(maxsize=1)
def get_async_client() -> openai.AsyncOpenAI:
    """Return a cached async OpenAI client configured from settings.

    Returns:
        openai.AsyncOpenAI: The async client instance.
    """
    return openai.AsyncOpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=_resolve_api_key(),
    )


@lru_cache(maxsize=1)
def get_sync_client() -> openai.OpenAI:
    """Return a cached synchronous OpenAI client configured from settings.

    Returns:
        openai.OpenAI: The sync client instance.
    """
    return openai.OpenAI(
        base_url=settings.LLM_BASE_URL,
        api_key=_resolve_api_key(),
    )


def patch_pageindex_defaults() -> None:
    """Monkey-patch openai client constructors so PageIndex uses our provider.

    The vendored PageIndex library creates its own OpenAI clients internally.
    This patch overrides the default __init__ parameters so those internally-
    created clients automatically point to the configured LLM provider.
    """
    _original_sync_init = openai.OpenAI.__init__
    _original_async_init = openai.AsyncOpenAI.__init__

    def _patched_sync_init(self: openai.OpenAI, **kwargs: object) -> None:
        """Patched sync OpenAI init that injects base_url and api_key."""
        kwargs.setdefault("base_url", settings.LLM_BASE_URL)
        kwargs.setdefault("api_key", _resolve_api_key())
        _original_sync_init(self, **kwargs)

    def _patched_async_init(self: openai.AsyncOpenAI, **kwargs: object) -> None:
        """Patched async OpenAI init that injects base_url and api_key."""
        kwargs.setdefault("base_url", settings.LLM_BASE_URL)
        kwargs.setdefault("api_key", _resolve_api_key())
        _original_async_init(self, **kwargs)

    openai.OpenAI.__init__ = _patched_sync_init  # type: ignore[assignment]
    openai.AsyncOpenAI.__init__ = _patched_async_init  # type: ignore[assignment]
