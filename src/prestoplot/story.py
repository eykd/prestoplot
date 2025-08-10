"""Story rendering from grammar files."""

import logging
from typing import Any

from . import contexts, grammars


def render_story(
    storage: Any,
    name: str,
    start: str = 'Begin',
    seed: str | None = None,
    **kwargs: Any,
) -> str:
    """Render a complete story from a grammar file.

    Args:
        storage: Storage backend for loading grammar files
        name: Name of the grammar module to load
        start: Starting stanza name (default 'Begin')
        seed: Random seed for reproducible generation
        **kwargs: Additional context parameters

    Returns:
        Generated story text as string

    """
    logging.debug(f'Rendering {name} w/ {storage}')

    ctx = contexts.get_context(seed, **kwargs)
    ctx = grammars.parse_grammar_file(storage, name, ctx)
    return str(ctx[start])
