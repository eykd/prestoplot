import logging

from . import contexts, grammars, seeds


def render_story(storage, name, start="Begin", **kwargs):
    logging.debug(f"Rendering {name} w/ {storage}")
    ctx = contexts.get_context(seeds.make_seed())
    ctx.update(kwargs)
    ctx = grammars.parse_grammar_file(storage, name, ctx)
    return str(ctx[start])
