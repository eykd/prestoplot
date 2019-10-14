import contextlib


def get_context(seed):
    context = {}
    context["seed"] = seed
    return context


@contextlib.contextmanager
def update_context(ctx, **kwargs):
    old_ctx = {key: ctx.get(key) for key in kwargs}
    ctx.update(kwargs)
    yield ctx
    ctx.update(old_ctx)
