from unittest.mock import Mock

import pytest

from prestoplot import markov, seeds

NAMES: list[str] = [
    'Noah',
    'Liam',
    'William',
    'Mason',
    'James',
    'Benjamin',
    'Jacob',
    'Michael',
    'Elijah',
    'Ethan',
    'Alexander',
    'Oliver',
    'Daniel',
    'Lucas',
    'Matthew',
    'Aiden',
    'Jackson',
    'Logan',
    'David',
    'Joseph',
    'Samuel',
    'Henry',
    'Owen',
    'Sebastian',
    'Gabriel',
    'Carter',
    'Jayden',
    'John',
    'Luke',
    'Anthony',
    'Isaac',
    'Dylan',
    'Wyatt',
    'Andrew',
    'Joshua',
    'Christopher',
    'Grayson',
    'Jack',
    'Julian',
    'Ryan',
    'Jaxon',
    'Levi',
    'Nathan',
]


class TestMarkovChainDict:
    """Tests for MarkovChainDict class."""

    def test_init_creates_empty_dict(self) -> None:
        """Test that initialization creates an empty MarkovChainDict."""
        chain = markov.MarkovChainDict()
        assert len(chain) == 0
        assert list(chain) == []

    def test_add_key_adds_suffix_to_prefix(self) -> None:
        """Test that add_key adds suffixes to prefixes."""
        chain = markov.MarkovChainDict()
        chain.add_key('ab', 'c')

        assert len(chain) == 1
        assert chain['ab'] == ['c']

    def test_add_key_appends_multiple_suffixes(self) -> None:
        """Test that add_key appends multiple suffixes to same prefix."""
        chain = markov.MarkovChainDict()
        chain.add_key('ab', 'c')
        chain.add_key('ab', 'd')
        chain.add_key('ab', 'e')

        assert len(chain) == 1
        assert chain['ab'] == ['c', 'd', 'e']

    def test_getitem_returns_empty_list_for_missing_key(self) -> None:
        """Test that accessing missing key returns empty list."""
        chain = markov.MarkovChainDict()
        assert chain['nonexistent'] == []

    def test_iter_yields_all_keys(self) -> None:
        """Test that iteration yields all prefix keys."""
        chain = markov.MarkovChainDict()
        chain.add_key('ab', 'c')
        chain.add_key('bc', 'd')
        chain.add_key('cd', 'e')

        keys = list(chain)
        assert set(keys) == {'ab', 'bc', 'cd'}

    def test_len_returns_number_of_prefixes(self) -> None:
        """Test that len returns number of unique prefixes."""
        chain = markov.MarkovChainDict()
        chain.add_key('ab', 'c')
        chain.add_key('ab', 'd')  # Same prefix
        chain.add_key('bc', 'e')

        assert len(chain) == 2

    def test_get_suffix_returns_random_suffix(self) -> None:
        """Test that get_suffix returns a suffix from the prefix's list."""
        chain = markov.MarkovChainDict()
        chain.add_key('ab', 'c')
        chain.add_key('ab', 'd')
        chain.add_key('ab', 'e')

        mock_rng = Mock()
        mock_rng.choice.return_value = 'd'

        result = chain.get_suffix('ab', rng=mock_rng)

        assert result == 'd'
        mock_rng.choice.assert_called_once_with(['c', 'd', 'e'])

    def test_get_suffix_uses_default_random(self) -> None:
        """Test that get_suffix works with default random module."""
        chain = markov.MarkovChainDict()
        chain.add_key('ab', 'c')

        # Should not raise an exception
        result = chain.get_suffix('ab')
        assert result == 'c'


class TestNameGenerator:
    """Tests for NameGenerator class."""

    def test_init_with_default_chainlen(self) -> None:
        """Test that NameGenerator initializes with default chain length."""
        gen = markov.NameGenerator(['Alice', 'Bob'])
        assert gen.chainlen == 2

    @pytest.mark.parametrize('chainlen', [1, 2, 3, 5, 10])
    def test_init_with_valid_chainlen(self, chainlen: int) -> None:
        """Test that NameGenerator accepts valid chain lengths."""
        gen = markov.NameGenerator(['Alice', 'Bob'], chainlen=chainlen)
        assert gen.chainlen == chainlen

    @pytest.mark.parametrize('chainlen', [0, 11, -1, 100])
    def test_init_with_invalid_chainlen_raises_error(self, chainlen: int) -> None:
        """Test that invalid chain lengths raise ValueError."""
        with pytest.raises(ValueError, match='Chain length must be between 1 and 10'):
            markov.NameGenerator(['Alice', 'Bob'], chainlen=chainlen)

    def test_init_builds_markov_chain(self) -> None:
        """Test that initialization builds the Markov chain."""
        gen = markov.NameGenerator(['Ab'])

        # Should have entries for the name "Ab"
        assert len(gen.markov) > 0
        assert '  ' in gen.markov  # Starting spaces
        assert ' A' in gen.markov
        assert 'Ab' in gen.markov

    def test_clear_resets_markov_chain(self) -> None:
        """Test that clear() resets the Markov chain."""
        gen = markov.NameGenerator(['Alice', 'Bob'])
        initial_len = len(gen.markov)
        assert initial_len > 0

        gen.clear()
        assert len(gen.markov) == 0

    def test_read_data_processes_names(self) -> None:
        """Test that read_data processes names into Markov chain."""
        gen = markov.NameGenerator([])
        assert len(gen.markov) == 0

        gen.read_data(['Cat', 'Dog'])

        # Should now have entries
        assert len(gen.markov) > 0
        assert '  ' in gen.markov
        assert ' C' in gen.markov
        assert 'Ca' in gen.markov

    def test_read_data_adds_termination_newlines(self) -> None:
        """Test that read_data adds newline terminators."""
        gen = markov.NameGenerator(['Ab'], chainlen=2)

        # The last prefix should map to newline
        last_chars = 'Ab'
        assert '\n' in gen.markov[last_chars]

    def test_get_random_name_generates_name(self) -> None:
        """Test that get_random_name generates a name."""
        gen = markov.NameGenerator(NAMES)

        name = gen.get_random_name()

        assert isinstance(name, str)
        assert len(name) > 0

    def test_get_random_name_respects_max_length(self) -> None:
        """Test that get_random_name respects max_length parameter."""
        gen = markov.NameGenerator(NAMES)

        name = gen.get_random_name(max_length=3)

        assert len(name) <= 3

    def test_get_random_name_with_start_parameter(self) -> None:
        """Test that get_random_name uses start parameter."""
        gen = markov.NameGenerator(NAMES)

        name = gen.get_random_name(start='Jo')

        assert name.startswith('Jo')

    def test_get_random_name_deterministic_with_seed(self) -> None:
        """Test that same seed produces same name."""
        gen = markov.NameGenerator(NAMES)

        name1 = gen.get_random_name(seed='test_seed')
        name2 = gen.get_random_name(seed='test_seed')

        assert name1 == name2

    def test_get_random_name_different_with_different_seeds(self) -> None:
        """Test that different seeds produce different names."""
        gen = markov.NameGenerator(NAMES)

        name1 = gen.get_random_name(seed='seed1')
        name2 = gen.get_random_name(seed='seed2')

        # While theoretically possible they could be the same, it's highly unlikely
        assert name1 != name2

    def test_get_random_name_with_empty_source_raises_error(self) -> None:
        """Test that generator with empty source raises IndexError when generating names."""
        gen = markov.NameGenerator([])

        # Should raise IndexError when trying to choose from empty sequence
        with pytest.raises(IndexError, match='Cannot choose from an empty sequence'):
            gen.get_random_name(start='A')

    def test_get_random_name_basic_functionality(self) -> None:
        """Test that get_random_name generates valid names."""
        gen = markov.NameGenerator(NAMES[:5])  # Use smaller set for faster test

        # Generate multiple names to verify functionality
        names = [gen.get_random_name(seed=f'test{i}') for i in range(5)]

        # All names should be strings and non-empty
        assert all(isinstance(name, str) for name in names)
        assert all(len(name) > 0 for name in names)

    def test_next_method_returns_random_name(self) -> None:
        """Test that __next__ method returns a random name."""
        gen = markov.NameGenerator(NAMES)

        name = next(gen)

        assert isinstance(name, str)
        assert len(name) > 0

    def test_iterator_protocol(self) -> None:
        """Test that NameGenerator works as an iterator."""
        gen = markov.NameGenerator(NAMES)

        names = [next(gen) for _ in range(3)]

        assert len(names) == 3
        assert all(isinstance(name, str) for name in names)
        assert all(len(name) > 0 for name in names)

    def test_chainlen_affects_generation(self) -> None:
        """Test that different chain lengths affect name generation."""
        names = ['Alexander', 'Alexandra', 'Alexandria']

        gen1 = markov.NameGenerator(names, chainlen=1)
        gen2 = markov.NameGenerator(names, chainlen=3)

        # Generate multiple names to see differences
        names1 = [gen1.get_random_name(seed=f'test{i}') for i in range(5)]
        names2 = [gen2.get_random_name(seed=f'test{i}') for i in range(5)]

        # Different chain lengths should generally produce different results
        assert names1 != names2


# Legacy tests for backward compatibility
def test_it_should_generate_stable_names_from_seed() -> None:
    gen = markov.NameGenerator(NAMES)

    result = gen.get_random_name(seed='foo')
    assert result == 'Anden'

    result = gen.get_random_name(seed='foo')
    assert result == 'Anden'


def test_it_should_generate_stable_names_with_seeded_rng() -> None:
    gen = markov.NameGenerator(NAMES)
    rng = seeds.get_rng('foo')

    result = gen.get_random_name(seed=rng)
    assert result == 'Anden'

    result = gen.get_random_name(seed=rng)
    assert result == 'Andrew'
