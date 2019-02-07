import contextlib
from . import db
from . import characters


def get_context(seed):
    context = {}
    context['seed'] = seed
    # context['C'] = db.Database(lambda ctx: characters.CharacterFactory.build(context=ctx), context)
    return context


@contextlib.contextmanager
def update_context(ctx, **kwargs):
    old_ctx = {
        key: ctx.get(key)
        for key in kwargs
    }
    ctx.update(kwargs)
    yield ctx
    ctx.update(old_ctx)
