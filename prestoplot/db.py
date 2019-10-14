import logging
import math
import random

from . import contexts, markov
from .texts import is_text


class Database:
    def __init__(self, factory, grammar_path, context):
        self.factory = factory
        self.context = context
        self.grammar_path = grammar_path
        self.cache = {}

    def __getattr__(self, attr):
        logging.debug(f"Database.{attr}")
        if attr not in self.cache:
            try:
                result = self.__dict__[attr]
            except KeyError:
                if hasattr(str, attr):
                    result = getattr(str(self), attr)
                else:
                    seed = f'{self.context["seed"]}-{attr}'
                    with contexts.update_context(self.context, key=attr, seed=seed):
                        result = self.factory(self.context)
            self.cache[attr] = result
        logging.debug(f"Database.{attr}->{self.cache[attr]}")
        return self.cache[attr]

    def __getitem__(self, key):
        try:
            return getattr(self, key)
        except TypeError:
            logging.exception(f"No key {key!r} in {self!r}")
            raise

    def __str__(self):
        return str(self.factory(self.context))


class Databag(dict):
    def __init__(self, grammar_path, context, *args, **kwargs):
        self.context = context
        self.grammar_path = grammar_path
        super().__init__(*args, **kwargs)

    def __getattr__(self, attr):
        return self[attr]

    def __getitem__(self, key):
        try:
            value = super().__getitem__(str(key))
        except KeyError:
            logging.error(f'No key {key!r} in {", ".join(self.keys())}')
            raise
        if is_text(value):
            value = value.render(self.context)

        return value


class Datalist(list):
    def __init__(self, grammar_path, context, *args, **kwargs):
        self.context = context
        self.grammar_path = grammar_path
        super().__init__(*args, **kwargs)

    def __getitem__(self, idx):
        try:
            value = super().__getitem__(idx)
        except KeyError:
            logging.error(f'No index {idx!r} in {", ".join(self)}')
            raise
        if is_text(value):
            value = value.render(self.context)

        return value


def choose(items):
    def chooser(context):
        rng = random.Random(context["seed"])
        result = rng.choice(items)
        if is_text(result):
            result = result.render(context)
        return result

    return chooser


def pick(items):
    def picker(context):
        rng = random.Random(context["seed"])
        if len(items) > 1:
            idx = rng.randint(0, len(items) - 1)
        else:
            idx = 0
        result = items.pop(idx)
        if is_text(result):
            result = result.render(context)
        return result

    return picker


def markovify(items):
    def generator(context):
        gen = markov.NameGenerator(items, chainlen=context.get("markov_chainlen", 2))

        return gen.get_random_name(start=context.get("start_markov", ""))

    return generator


def pareto_int(rng, shape=1):
    return math.floor(rng.paretovariate(shape))
