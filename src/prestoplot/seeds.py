import hashlib
import random


def make_seed(rng=random):
    return hashlib.md5(str(rng.random()).encode("utf-8")).hexdigest()


def get_seed(context):
    try:
        seed = context["seed"]
    except KeyError:
        seed = context["seed"] = make_seed()

    key = context.get("key")
    if key is not None:
        seed = f"{seed}-{key}"

    return seed
