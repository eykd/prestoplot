import hashlib
import random


def make_seed(rng=random):
    return hashlib.md5(str(rng.random()).encode("utf-8")).hexdigest()


def set_seed(context, seed):
    if seed is None or seed is random:
        seed = make_seed()
    elif isinstance(seed, random.Random):
        seed = make_seed(seed)

    context["seed"] = seed


def get_seed(context):
    try:
        seed = context["seed"]
    except KeyError:
        seed = context["seed"] = make_seed()

    if seed is random or isinstance(seed, random.Random):
        seed = context["seed"] = make_seed(seed)

    key = context.get("key")
    if key is not None:
        seed = f"{seed}-{key}"

    return seed


def get_rng(seed=None):
    if seed is None:
        return random
    elif isinstance(seed, random.Random):
        return seed
    else:
        return random.Random(seed)
