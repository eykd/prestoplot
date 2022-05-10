import contextlib

from . import seeds


def get_context(seed, **kwargs):
    context = {**kwargs}
    seeds.set_seed(context, seed)
    return context


@contextlib.contextmanager
def update_context(ctx, **kwargs):
    old_ctx = {key: ctx.get(key) for key in kwargs}
    ctx.update(kwargs)
    yield ctx
    ctx.update(old_ctx)
