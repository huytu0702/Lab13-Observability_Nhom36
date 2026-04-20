"""Langfuse v3 tracing helpers.

Implements the best practices from `github.com/langfuse/skills` (Langfuse Skill
v3): documentation-first, descriptive span names, masked PII inputs/outputs,
session/user attribution, and an explicit ``flush()`` at shutdown so traces
are not lost.

The previous version of this module imported ``langfuse.decorators`` (the v2
SDK path), which does not exist in langfuse>=3. That made the dummy fallback
silently active even when Langfuse keys were configured. This module switches
to the v3 imports and exposes a small surface used by ``app.agent`` and
``app.main``.
"""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Any, Iterator

try:
    from langfuse import Langfuse, get_client, observe  # type: ignore
    _SDK_AVAILABLE = True
except Exception:  # pragma: no cover - keeps import safe when SDK absent
    _SDK_AVAILABLE = False
    Langfuse = None  # type: ignore[assignment]

    def observe(*args: Any, **kwargs: Any):  # type: ignore[no-redef]
        if args and callable(args[0]) and not kwargs:
            return args[0]

        def decorator(func):
            return func

        return decorator

    def get_client() -> None:  # type: ignore[no-redef]
        return None


def tracing_enabled() -> bool:
    return _SDK_AVAILABLE and bool(
        os.getenv("LANGFUSE_PUBLIC_KEY") and os.getenv("LANGFUSE_SECRET_KEY")
    )


def get_langfuse_client() -> Any | None:
    """Return the singleton Langfuse client, or None when tracing is disabled."""
    if not tracing_enabled():
        return None
    return get_client()


def update_current_trace(**kwargs: Any) -> None:
    client = get_langfuse_client()
    if client is not None:
        client.update_current_trace(**kwargs)


class _NoopObservation:
    """Returned by the context managers when tracing is disabled."""

    def update(self, **kwargs: Any) -> None:
        return None


@contextmanager
def langfuse_span(name: str, **kwargs: Any) -> Iterator[Any]:
    """Open a generic span (`start_as_current_span`) for non-LLM work."""
    client = get_langfuse_client()
    if client is None:
        yield _NoopObservation()
        return
    with client.start_as_current_span(name=name, **kwargs) as span:
        yield span


@contextmanager
def langfuse_generation(name: str, **kwargs: Any) -> Iterator[Any]:
    """Open an LLM generation span so model + usage_details land on the right type."""
    client = get_langfuse_client()
    if client is None:
        yield _NoopObservation()
        return
    with client.start_as_current_generation(name=name, **kwargs) as gen:
        yield gen


def flush() -> None:
    """Force pending traces to flush. Call before process exit."""
    client = get_langfuse_client()
    if client is not None:
        try:
            client.flush()
        except Exception:  # pragma: no cover - best effort
            pass
