"""Tests for prestoplot.seeds module."""

import random
from typing import Any
from unittest.mock import MagicMock, patch

from prestoplot import seeds


class TestMakeSeed:
    """Test cases for make_seed function."""

    def test_returns_32_character_hex_string(self) -> None:
        """Test that make_seed returns a 32-character hexadecimal string."""
        result = seeds.make_seed()
        assert len(result) == 32
        assert all(c in '0123456789abcdef' for c in result)

    def test_different_calls_produce_different_seeds(self) -> None:
        """Test that consecutive calls produce different seeds."""
        seed1 = seeds.make_seed()
        seed2 = seeds.make_seed()
        assert seed1 != seed2

    def test_uses_provided_rng(self) -> None:
        """Test that make_seed uses the provided random number generator."""
        mock_rng = MagicMock()
        mock_rng.random.return_value = 0.5

        result = seeds.make_seed(mock_rng)
        mock_rng.random.assert_called_once()
        assert len(result) == 32

    @patch('prestoplot.seeds.hashlib.md5')
    def test_md5_hash_generation(self, mock_md5: MagicMock) -> None:
        """Test that make_seed uses MD5 hashing correctly."""
        mock_hash = MagicMock()
        mock_hash.hexdigest.return_value = 'a' * 32
        mock_md5.return_value = mock_hash

        mock_rng = MagicMock()
        mock_rng.random.return_value = 0.123456789

        result = seeds.make_seed(mock_rng)

        mock_md5.assert_called_once_with(b'0.123456789')
        mock_hash.hexdigest.assert_called_once()
        assert result == 'a' * 32


class TestSetSeed:
    """Test cases for set_seed function."""

    def test_sets_string_seed_in_context(self) -> None:
        """Test setting a string seed in context."""
        context: dict[str, Any] = {}
        seeds.set_seed(context, 'test_seed')
        assert context['seed'] == 'test_seed'

    def test_generates_seed_when_none(self) -> None:
        """Test that a seed is generated when None is provided."""
        context: dict[str, Any] = {}
        seeds.set_seed(context, None)
        assert 'seed' in context
        assert len(context['seed']) == 32

    def test_generates_seed_when_random_module(self) -> None:
        """Test that a seed is generated when random module is provided."""
        context: dict[str, Any] = {}
        seeds.set_seed(context, random)
        assert 'seed' in context
        assert len(context['seed']) == 32

    def test_generates_seed_from_random_instance(self) -> None:
        """Test that a seed is generated from a Random instance."""
        context: dict[str, Any] = {}
        rng = random.Random(42)  # noqa: S311
        seeds.set_seed(context, rng)
        assert 'seed' in context
        assert len(context['seed']) == 32

    def test_overwrites_existing_seed(self) -> None:
        """Test that existing seed in context is overwritten."""
        context: dict[str, Any] = {'seed': 'old_seed'}
        seeds.set_seed(context, 'new_seed')
        assert context['seed'] == 'new_seed'


class TestGetSeed:
    """Test cases for get_seed function."""

    def test_returns_existing_seed(self) -> None:
        """Test that existing seed is returned from context."""
        context = {'seed': 'existing_seed'}
        result = seeds.get_seed(context)
        assert result == 'existing_seed'

    def test_generates_seed_when_missing(self) -> None:
        """Test that a seed is generated when missing from context."""
        context: dict[str, Any] = {}
        result = seeds.get_seed(context)
        assert len(result) == 32
        assert context['seed'] == result

    def test_converts_random_module_to_seed(self) -> None:
        """Test that random module is converted to a seed string."""
        context: dict[str, Any] = {'seed': random}
        result = seeds.get_seed(context)
        assert len(result) == 32
        assert context['seed'] == result

    def test_converts_random_instance_to_seed(self) -> None:
        """Test that Random instance is converted to a seed string."""
        rng = random.Random(42)  # noqa: S311
        context: dict[str, Any] = {'seed': rng}
        result = seeds.get_seed(context)
        assert len(result) == 32
        assert context['seed'] == result

    def test_appends_key_when_present(self) -> None:
        """Test that key is appended to seed when present in context."""
        context = {'seed': 'base_seed', 'key': 'test_key'}
        result = seeds.get_seed(context)
        assert result == 'base_seed-test_key'

    def test_no_key_appending_when_key_none(self) -> None:
        """Test that no key is appended when key is None."""
        context = {'seed': 'base_seed', 'key': None}
        result = seeds.get_seed(context)
        assert result == 'base_seed'

    def test_no_key_appending_when_key_missing(self) -> None:
        """Test that no key is appended when key is not in context."""
        context = {'seed': 'base_seed'}
        result = seeds.get_seed(context)
        assert result == 'base_seed'

    def test_key_appending_with_generated_seed(self) -> None:
        """Test that key is appended to generated seed."""
        context: dict[str, Any] = {'key': 'test_key'}
        result = seeds.get_seed(context)
        # Should be in format: {32-char-seed}-test_key
        parts = result.split('-')
        assert len(parts) == 2
        assert len(parts[0]) == 32
        assert parts[1] == 'test_key'


class TestGetRng:
    """Test cases for get_rng function."""

    def test_returns_global_random_when_none(self) -> None:
        """Test that global random is returned when seed is None."""
        result = seeds.get_rng(None)
        assert result is random

    def test_returns_same_random_instance_when_provided(self) -> None:
        """Test that the same Random instance is returned when provided."""
        rng = random.Random(42)  # noqa: S311
        result = seeds.get_rng(rng)
        assert result is rng

    def test_creates_random_instance_from_string_seed(self) -> None:
        """Test that a Random instance is created from string seed."""
        result = seeds.get_rng('test_seed')
        assert isinstance(result, random.Random)
        assert result is not random

    def test_same_string_seed_produces_same_sequence(self) -> None:
        """Test that same string seed produces deterministic random sequence."""
        rng1 = seeds.get_rng('test_seed')
        rng2 = seeds.get_rng('test_seed')

        # Generate a sequence from each RNG
        sequence1 = [rng1.random() for _ in range(10)]
        sequence2 = [rng2.random() for _ in range(10)]

        assert sequence1 == sequence2

    def test_different_string_seeds_produce_different_sequences(self) -> None:
        """Test that different string seeds produce different sequences."""
        rng1 = seeds.get_rng('seed1')
        rng2 = seeds.get_rng('seed2')

        # Generate a sequence from each RNG
        sequence1 = [rng1.random() for _ in range(10)]
        sequence2 = [rng2.random() for _ in range(10)]

        assert sequence1 != sequence2

    def test_integer_seed_works(self) -> None:
        """Test that integer seeds work correctly."""
        rng = seeds.get_rng(12345)
        assert isinstance(rng, random.Random)
        # Test that it produces deterministic results
        value1 = rng.random()
        rng = seeds.get_rng(12345)
        value2 = rng.random()
        assert value1 == value2


class TestSeedsIntegration:
    """Integration tests for seeds module functionality."""

    def test_complete_seed_workflow(self) -> None:
        """Test complete workflow of seed generation and usage."""
        # Start with empty context
        context: dict[str, Any] = {}

        # Set a seed
        seeds.set_seed(context, 'integration_test')

        # Get the seed (should return the same one)
        retrieved_seed = seeds.get_seed(context)
        assert retrieved_seed == 'integration_test'

        # Get RNG from the seed
        rng = seeds.get_rng(retrieved_seed)
        assert isinstance(rng, random.Random)

        # Generate some values
        values = [rng.random() for _ in range(5)]

        # Reset and verify reproducibility
        rng = seeds.get_rng(retrieved_seed)
        values2 = [rng.random() for _ in range(5)]
        assert values == values2

    def test_key_based_seeding(self) -> None:
        """Test that key-based seeding produces different but deterministic results."""
        base_context = {'seed': 'base_seed'}

        # Get seeds with different keys
        context1 = {**base_context, 'key': 'key1'}
        context2 = {**base_context, 'key': 'key2'}

        seed1 = seeds.get_seed(context1)
        seed2 = seeds.get_seed(context2)

        # Seeds should be different
        assert seed1 != seed2
        assert seed1 == 'base_seed-key1'
        assert seed2 == 'base_seed-key2'

        # But should be deterministic
        seed1_again = seeds.get_seed(context1)
        seed2_again = seeds.get_seed(context2)
        assert seed1 == seed1_again
        assert seed2 == seed2_again

    def test_auto_generation_workflow(self) -> None:
        """Test workflow with automatic seed generation."""
        context: dict[str, Any] = {}

        # First call should generate a seed
        seed1 = seeds.get_seed(context)
        assert len(seed1) == 32
        assert 'seed' in context

        # Second call should return the same seed
        seed2 = seeds.get_seed(context)
        assert seed1 == seed2

        # Adding a key should modify the returned seed but not the stored one
        context['key'] = 'test_key'
        seed_with_key = seeds.get_seed(context)
        assert seed_with_key == f'{seed1}-test_key'
        assert context['seed'] == seed1  # Original seed unchanged
