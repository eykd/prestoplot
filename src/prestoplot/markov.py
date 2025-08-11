"""Markov chain text generation for names and words."""

from __future__ import annotations

import collections
import random
from typing import TYPE_CHECKING, Any

from . import seeds

if TYPE_CHECKING:
    from collections.abc import Iterator


class MarkovChainDict(collections.abc.Mapping):
    """A Markov Chain dictionary, for generating random strings.

    Derived from Peter Corbett's CGI random name generator:
    http://www.pick.ucam.org/~ptc24/mchain.html
    """

    def __init__(self) -> None:
        """Initialize empty Markov chain dictionary."""
        self._dict = collections.defaultdict(list)

    def __getitem__(self, key: str) -> list[str]:
        """Get suffixes for a given prefix key.

        Args:
            key: Prefix string to look up

        Returns:
            List of possible suffixes for the prefix

        """
        return self._dict[key]

    def __len__(self) -> int:
        """Get number of prefix keys in the chain.

        Returns:
            Number of prefix keys

        """
        return len(self._dict)

    def __iter__(self) -> Iterator[str]:
        """Iterate over prefix keys.

        Returns:
            Iterator over prefix keys

        """
        return iter(self._dict)

    def add_key(self, prefix: str, suffix: str) -> None:
        """Add a prefix-suffix pair to the chain.

        Args:
            prefix: Prefix string (key)
            suffix: Suffix character to add for this prefix

        """
        self._dict[prefix].append(suffix)

    def get_suffix(self, prefix: str, rng: Any = random) -> str:  # noqa: ANN401
        """Get random suffix for a prefix.

        Args:
            prefix: Prefix string to get suffix for
            rng: Random number generator to use

        Returns:
            Randomly chosen suffix character

        """
        return rng.choice(self[prefix])


class NameGenerator(collections.abc.Iterator):
    """Uses a Markov Chain to generate random names.

    Derived from Peter Corbett's CGI random name generator, with input
    from the ElderLore object-oriented variation.

    http://www.pick.ucam.org/~ptc24/mchain.html
    """

    def __init__(self, source_names: list[str], chainlen: int = 2) -> None:
        """Initialize name generator with source data.

        Args:
            source_names: List of source names to build chain from
            chainlen: Length of prefix chains (1-10)

        Raises:
            ValueError: If chainlen is not between 1 and 10

        """
        if not (1 <= chainlen <= 10):
            raise ValueError('Chain length must be between 1 and 10, inclusive')
        self.chainlen = chainlen
        self.markov = MarkovChainDict()
        self.read_data(source_names)

    def __next__(self) -> str:
        """Generate next random name (iterator protocol).

        Returns:
            Random generated name

        """
        return self.get_random_name()

    def clear(self) -> None:
        """Clear the Markov chain."""
        del self.markov
        self.markov = MarkovChainDict()

    def read_data(self, names: list[str]) -> None:
        """Build Markov chain from source names.

        Args:
            names: List of names to process

        """
        oldnames = []
        chainlen = self.chainlen

        for name in names:
            oldnames.append(name)
            spacer = ''.join((' ' * chainlen, name))
            name_len = len(name)
            for num in range(name_len):
                self.markov.add_key(
                    spacer[num : num + chainlen], spacer[num + chainlen]
                )
            self.markov.add_key(spacer[name_len : name_len + chainlen], '\n')

    def get_random_name(
        self, start: str = '', max_length: int = 10, seed: str | None = None
    ) -> str:
        """Generate a random name using the Markov chain.

        Args:
            start: Starting characters for the name
            max_length: Maximum length of generated name
            seed: Random seed for reproducible generation

        Returns:
            Generated name string

        """
        rng = seeds.get_rng(seed)
        prefix = start[-self.chainlen :] or ' ' * self.chainlen
        name = start
        suffix = ''
        while 1:
            suffix = self.markov.get_suffix(prefix, rng=rng)
            if suffix == '-':
                continue  # pragma: no cover
            if suffix == '\n' or len(name) == max_length:
                break
            name = f'{name}{suffix}'
            prefix = f'{prefix[1:]}{suffix}'
        return name
