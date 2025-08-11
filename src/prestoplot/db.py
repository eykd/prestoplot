"""Database objects for grammar value storage and access."""

from __future__ import annotations

import logging
import math
from typing import TYPE_CHECKING, Any

from . import contexts, markov, seeds
from .texts import is_text

if TYPE_CHECKING:
    from collections.abc import Callable
    from random import Random

logger = logging.getLogger(__name__)


class Database:
    """Dynamic database for grammar values with attribute-based access.

    Provides lazy evaluation and caching of values based on factory functions.
    Each attribute access creates a new seeded context for reproducible results.
    """

    def __init__(
        self,
        factory: Callable[[dict[str, Any]], Any],
        grammar_path: str,
        context: dict[str, Any],
    ) -> None:
        """Initialize database with factory function and context.

        Args:
            factory: Function that generates values from context
            grammar_path: Path identifier for the grammar stanza
            context: Grammar rendering context

        """
        self.factory = factory
        self.context = context
        self.grammar_path = grammar_path
        self.cache = {}

    def __getattr__(self, attr: str) -> Any:  # noqa: ANN401
        """Get attribute value with lazy evaluation and caching.

        Creates a new seeded context for each unique attribute name
        to ensure reproducible but varied results.

        Args:
            attr: Attribute name to access

        Returns:
            Cached or newly generated value for the attribute

        """
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
        return self.cache[attr]

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        """Get item by key (delegates to __getattr__).

        Args:
            key: Key to access

        Returns:
            Value for the given key

        Raises:
            TypeError: If key access fails

        """
        try:
            return getattr(self, key)
        except TypeError:  # pragma: no cover
            logger.exception('No key %r in %s', key, self)
            raise

    def __str__(self) -> str:
        """Generate string representation by calling factory.

        Returns:
            String representation of generated value

        """
        return str(self.factory(self.context))


class Databag(dict):
    """Dictionary-like container for grammar values with context.

    Extends dict to provide context-aware rendering of text values.
    """

    def __init__(  # noqa: D417
        self,
        grammar_path: str,
        context: dict[str, Any],
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize databag with context.

        Args:
            grammar_path: Path identifier for the grammar stanza
            context: Grammar rendering context
            *args, **kwargs: Arguments passed to dict constructor

        """
        self.context = context
        self.grammar_path = grammar_path
        super().__init__(*args, **kwargs)

    def __getattr__(self, attr: str) -> Any:  # noqa: ANN401
        """Get attribute as dictionary key.

        Args:
            attr: Attribute name

        Returns:
            Value from dictionary

        """
        return self[attr]

    def __getitem__(self, key: str) -> Any:  # noqa: ANN401
        """Get item with context-aware text rendering.

        Args:
            key: Dictionary key

        Returns:
            Value with text objects rendered in current context

        Raises:
            KeyError: If key not found

        """
        try:
            value = super().__getitem__(str(key))
        except KeyError:
            logger.exception(
                'No key %r in %s', key, ', '.join(str(k) for k in self.keys())
            )
            raise
        if is_text(value):
            value = value.render(self.context)

        return value


class Datalist(list):
    """List-like container for grammar values with context.

    Extends list to provide context-aware rendering of text values.
    """

    def __init__(  # noqa: D417
        self,
        grammar_path: str,
        context: dict[str, Any],
        *args: tuple[Any, ...],
        **kwargs: dict[str, Any],
    ) -> None:
        """Initialize datalist with context.

        Args:
            grammar_path: Path identifier for the grammar stanza
            context: Grammar rendering context
            *args, **kwargs: Arguments passed to list constructor

        """
        self.context = context
        self.grammar_path = grammar_path
        super().__init__(*args, **kwargs)

    def __getitem__(self, idx: int) -> Any:  # noqa: ANN401
        """Get item with context-aware text rendering.

        Args:
            idx: List index

        Returns:
            Value with text objects rendered in current context

        Raises:
            KeyError: If index not found (note: should be IndexError)

        """
        try:
            value = super().__getitem__(idx)
        except KeyError:  # pragma: no cover
            logger.exception(
                'No index %r in %s', idx, ', '.join(str(item) for item in self)
            )
            raise
        if is_text(value):
            value = value.render(self.context)

        return value


def choose(items: list[Any]) -> Callable[[dict[str, Any]], Any]:
    """Create a factory that randomly chooses from items (with replacement).

    Args:
        items: List of items to choose from

    Returns:
        Factory function that chooses random item from list

    """

    def chooser(context: dict[str, Any]) -> Any:  # noqa: ANN401
        """Choose random item from list.

        Args:
            context: Grammar rendering context containing seed

        Returns:
            Randomly chosen and rendered item

        """
        rng = seeds.get_rng(context['seed'])
        result = rng.choice(items)
        if is_text(result):
            result = result.render(context)
        return result

    return chooser


def pick(items: list[Any]) -> Callable[[dict[str, Any]], Any]:
    """Create a factory that picks from items without replacement.

    Args:
        items: Mutable list of items to pick from

    Returns:
        Factory function that picks and removes random item from list

    """

    def picker(context: dict[str, Any]) -> Any:  # noqa: ANN401
        """Pick and remove random item from list.

        Args:
            context: Grammar rendering context containing seed

        Returns:
            Randomly picked and rendered item (removed from source list)

        """
        rng = seeds.get_rng(context['seed'])
        idx = rng.randint(0, len(items) - 1) if len(items) > 1 else 0
        result = items.pop(idx)
        if is_text(result):
            result = result.render(context)
        return result

    return picker


def markovify(items: list[str]) -> Callable[[dict[str, Any]], str]:
    """Create a factory that generates text using Markov chains.

    Args:
        items: List of text items to build Markov model from

    Returns:
        Factory function that generates Markov chain text

    """

    def generator(context: dict[str, Any]) -> str:
        """Generate text using Markov chain model.

        Args:
            context: Grammar rendering context with optional markov settings

        Returns:
            Generated text based on Markov model of input items

        """
        gen = markov.NameGenerator(items, chainlen=context.get('markov_chainlen', 2))

        return gen.get_random_name(
            start=context.get('start_markov', ''), seed=context['seed']
        )

    return generator


def ratchet(items: list[Any]) -> Callable[[dict[str, Any]], Any]:
    """Create a factory that returns items sequentially with state tracking.

    Returns the first item on first call, second on second call, etc.
    Cycles back to the beginning when all items have been returned.

    Args:
        items: List of items to return sequentially

    Returns:
        Factory function that returns items in sequential order

    """
    state = {'index': 0}

    def ratcheter(context: dict[str, Any]) -> Any:  # noqa: ANN401
        """Return next item in sequence, cycling back to start when needed.

        Args:
            context: Grammar rendering context (unused for ratcheting)

        Returns:
            Next item in the sequence, rendered if it's a text object

        """
        if not items:
            return ''

        result = items[state['index']]
        state['index'] = (state['index'] + 1) % len(items)

        if is_text(result):
            result = result.render(context)
        return result

    return ratcheter


def pareto_int(rng: Random, shape: float = 1) -> int:
    """Generate integer from Pareto distribution.

    Args:
        rng: Random number generator
        shape: Shape parameter for Pareto distribution

    Returns:
        Integer value from Pareto distribution

    """
    return math.floor(rng.paretovariate(shape))
