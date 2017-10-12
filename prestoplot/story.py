from . import contexts
from . import grammars
from . import seeds


def render_story(path, **kwargs):
    ctx = contexts.get_context(seeds.make_seed())
    ctx.update(kwargs)
    ctx = grammars.parse_grammar_file(path, ctx)
    return str(ctx['Begin'])
