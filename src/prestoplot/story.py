import logging

from . import contexts, grammars


def render_story(storage, name, start="Begin", seed=None, **kwargs):
    logging.debug(f"Rendering {name} w/ {storage}")

    ctx = contexts.get_context(seed, **kwargs)
    ctx = grammars.parse_grammar_file(storage, name, ctx)
    return str(ctx[start])
