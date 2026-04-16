from __future__ import annotations

import os
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])

LANGSMITH_TRACING_ENABLED = os.getenv("LANGSMITH_TRACING", "").lower() == "true"

try:
    from langsmith import traceable as _traceable
    from langsmith.wrappers import wrap_openai as _wrap_openai
except Exception:  # pragma: no cover - optional dependency
    _traceable = None
    _wrap_openai = None


def traceable(*args, **kwargs):
    """
    Optional LangSmith decorator.

    If LangSmith is unavailable, this becomes a no-op decorator so the app keeps
    working without local tracing dependencies.
    """

    if _traceable is None or not LANGSMITH_TRACING_ENABLED:
        def decorator(func: F) -> F:
            return func

        if args and callable(args[0]) and len(args) == 1 and not kwargs:
            return args[0]
        return decorator

    return _traceable(*args, **kwargs)


def maybe_wrap_openai(client: Any) -> Any:
    """
    Wrap the provider client with LangSmith if the SDK is available.
    """
    if _wrap_openai is None or not LANGSMITH_TRACING_ENABLED:
        return client
    return _wrap_openai(client)
