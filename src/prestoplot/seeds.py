"""Random seed generation and management for reproducible results."""

import hashlib
import random


def make_seed(rng=random):
    """Generate a random seed string using MD5 hash.

    Args:
        rng: Random number generator to use

    Returns:
        32-character hexadecimal seed string

    """
    return hashlib.md5(str(rng.random()).encode('utf-8')).hexdigest()


def set_seed(context, seed):
    """Set the random seed in the context.

    Args:
        context: Grammar context dictionary to update
        seed: Seed value (string, Random instance, or None for auto-generation)

    """
    if seed is None or seed is random:
        seed = make_seed()
    elif isinstance(seed, random.Random):
        seed = make_seed(seed)

    context['seed'] = seed


def get_seed(context):
    """Get the current seed from context, creating one if needed.

    Combines the base seed with any key value to create unique
    seeds for different context scopes.

    Args:
        context: Grammar context dictionary

    Returns:
        Seed string, potentially combined with context key

    """
    try:
        seed = context['seed']
    except KeyError:
        seed = context['seed'] = make_seed()

    if seed is random or isinstance(seed, random.Random):
        seed = context['seed'] = make_seed(seed)

    key = context.get('key')
    if key is not None:
        seed = f'{seed}-{key}'

    return seed


def get_rng(seed=None):
    """Get a random number generator for the given seed.

    Args:
        seed: Seed value (None, string, or Random instance)

    Returns:
        Random number generator (global random or seeded Random instance)

    """
    if seed is None:
        return random
    if isinstance(seed, random.Random):
        return seed
    return random.Random(seed)
