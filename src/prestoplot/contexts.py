"""Context management for grammar rendering."""

from __future__ import annotations

import contextlib
from typing import TYPE_CHECKING, Any

from . import seeds

if TYPE_CHECKING:
    from collections.abc import Generator


def get_context(seed: str | None, **kwargs: dict[str, Any]) -> dict[str, Any]:
    """Create a new grammar context with optional seed and parameters.

    Args:
        seed: Random seed for reproducible generation
        **kwargs: Additional context parameters

    Returns:
        Dictionary containing context with seed initialized

    """
    context = {**kwargs}
    seeds.set_seed(context, seed)
    return context


@contextlib.contextmanager
def update_context(
    ctx: dict[str, Any], **kwargs: dict[str, Any]
) -> Generator[dict[str, Any]]:
    """Temporarily update context with new values.

    Args:
        ctx: Context dictionary to update
        **kwargs: Temporary context values

    Yields:
        Updated context dictionary

    Restores original context values on exit.

    """
    old_ctx = {key: ctx.get(key) for key in kwargs}
    ctx.update(kwargs)
    yield ctx
    ctx.update(old_ctx)
