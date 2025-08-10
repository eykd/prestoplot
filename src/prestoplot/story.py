"""Story rendering from grammar files."""

from __future__ import annotations

import logging
from typing import Any

from . import contexts, grammars

logger = logging.getLogger(__name__)


def render_story(
    storage: Any,  # noqa: ANN401
    name: str,
    start: str = 'Begin',
    seed: str | None = None,
    **kwargs: dict[str, Any],
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
    logger.debug('Rendering %s w/ %s', name, storage)

    ctx = contexts.get_context(seed, **kwargs)
    ctx = grammars.parse_grammar_file(storage, name, ctx)
    return str(ctx[start])
