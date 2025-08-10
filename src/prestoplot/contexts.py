"""Context management for grammar rendering."""

import contextlib

from . import seeds


def get_context(seed, **kwargs):
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
def update_context(ctx, **kwargs):
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
