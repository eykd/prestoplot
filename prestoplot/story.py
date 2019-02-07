import random


from . import db
from . import contexts
from . import grammars
from . import seeds


def render_story(path, **kwargs):
    ctx = contexts.get_context(seeds.make_seed())
    ctx.update(kwargs)
    ctx = grammars.parse_grammar_file(path, ctx)
    return str(ctx['Begin'])


def ratchet_story(path, max_yield=None, **kwargs):
    ctx = contexts.get_context(seeds.make_seed())
    ctx.update(kwargs)
    ctx = grammars.parse_grammar_file(path, ctx)
    storyline = ctx['Ratchet']
    rng = random.Random(ctx['seed'])

    max_length = len(storyline)
    if max_yield is None:
        max_yield = max_length
    idx = min(-1 + db.pareto_int(rng), max_length // 3)
    end_idx = max(len(storyline) - db.pareto_int(rng), (max_length * 2) // 3)

    yielded = 0

    max_advance = ((end_idx - idx) // max_yield) or 4

    while idx < end_idx and yielded < (max_yield - 1):
        yield str(storyline[idx])
        yielded += 1
        idx += min(db.pareto_int(rng), end_idx - idx, max_advance)

    yield str(storyline[end_idx])
