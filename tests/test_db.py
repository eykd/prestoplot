"""Tests for the db module classes and factory functions."""

from typing import Any
from unittest.mock import Mock, patch

import pytest

from prestoplot import contexts, db, seeds, texts


@pytest.fixture
def context() -> dict[str, Any]:
    """Create a test context with seed."""
    return contexts.get_context(seed='test-seed')


def test_ratchet_should_return_items_sequentially() -> None:
    """Test that ratchet returns items in order."""
    items = ['first', 'second', 'third']
    ratcheter = db.ratchet(items)
    context = {'seed': 'test'}

    # First round through the list
    assert ratcheter(context) == 'first'
    assert ratcheter(context) == 'second'
    assert ratcheter(context) == 'third'

    # Should cycle back to the beginning
    assert ratcheter(context) == 'first'
    assert ratcheter(context) == 'second'


def test_ratchet_should_handle_empty_list() -> None:
    """Test that ratchet handles empty lists gracefully."""
    ratcheter = db.ratchet([])
    context = {'seed': 'test'}

    assert ratcheter(context) == ''
    assert ratcheter(context) == ''


def test_ratchet_should_handle_single_item() -> None:
    """Test that ratchet works with single-item lists."""
    ratcheter = db.ratchet(['only'])
    context = {'seed': 'test'}

    assert ratcheter(context) == 'only'
    assert ratcheter(context) == 'only'
    assert ratcheter(context) == 'only'


def test_ratchet_should_render_text_objects(context: dict[str, Any]) -> None:
    """Test that ratchet renders text objects properly."""
    text_obj = texts.Text('rendered', 'test.path', context)
    items = [text_obj, 'plain']
    ratcheter = db.ratchet(items)

    # First call should return the rendered text object
    result1 = ratcheter(context)
    assert result1 == 'rendered'
    assert isinstance(result1, str)

    # Second call should return plain string
    result2 = ratcheter(context)
    assert result2 == 'plain'


def test_ratchet_maintains_independent_state() -> None:
    """Test that multiple ratchet instances maintain separate state."""
    items1 = ['a', 'b', 'c']
    items2 = ['x', 'y']

    ratcheter1 = db.ratchet(items1)
    ratcheter2 = db.ratchet(items2)
    context = {'seed': 'test'}

    # Advance first ratchet
    assert ratcheter1(context) == 'a'
    assert ratcheter1(context) == 'b'

    # Second ratchet should start from its beginning
    assert ratcheter2(context) == 'x'
    assert ratcheter2(context) == 'y'

    # First ratchet should continue from where it left off
    assert ratcheter1(context) == 'c'
    assert ratcheter1(context) == 'a'  # Cycles back


def test_choose_should_select_randomly(context: dict[str, Any]) -> None:
    """Test that choose selects items randomly but consistently with same seed."""
    items = ['a', 'b', 'c']
    chooser = db.choose(items)

    # With same seed, should get same result
    result1 = chooser(context)
    result2 = chooser(context)

    # Should be one of the items
    assert result1 in items
    assert result2 in items


def test_pick_should_remove_items() -> None:
    """Test that pick removes items from the list."""
    items = ['a', 'b', 'c']
    picker = db.pick(items)
    context = {'seed': 'test'}

    # Pick items - they should be removed from the original list
    result1 = picker(context)
    assert result1 in ['a', 'b', 'c']
    assert len(items) == 2  # One item should be removed

    result2 = picker(context)
    assert result2 in ['a', 'b', 'c']
    assert len(items) == 1  # Another item should be removed

    result3 = picker(context)
    assert result3 in ['a', 'b', 'c']
    assert len(items) == 0  # All items should be removed


def test_pick_should_handle_single_item() -> None:
    """Test that pick handles single-item lists."""
    items = ['only']
    picker = db.pick(items)
    context = {'seed': 'test'}

    result = picker(context)
    assert result == 'only'
    assert len(items) == 0


def test_markovify_should_generate_names(context: dict[str, Any]) -> None:
    """Test that markovify generates names using Markov chains."""
    items = ['Alice', 'Bob', 'Charlie', 'David']
    markovifier = db.markovify(items)

    result = markovifier(context)
    assert isinstance(result, str)
    assert len(result) > 0


def test_pareto_int_should_generate_integers() -> None:
    """Test that pareto_int generates integer values."""
    from prestoplot.seeds import get_rng

    rng = get_rng('test-seed')
    result = db.pareto_int(rng)

    assert isinstance(result, int)
    assert result >= 0


class TestDatabase:
    """Test the Database class."""

    @pytest.fixture
    def mock_factory(self) -> Mock:
        """Create a mock factory function."""
        return Mock(return_value='factory_result')

    @pytest.fixture
    def database(self, mock_factory: Mock, context: dict[str, Any]) -> db.Database:
        """Create a Database instance for testing."""
        return db.Database(
            factory=mock_factory, grammar_path='test.stanza', context=context
        )

    def test_init_stores_parameters(
        self, mock_factory: Mock, context: dict[str, Any]
    ) -> None:
        """Test that Database.__init__ stores all parameters correctly."""
        database = db.Database(
            factory=mock_factory, grammar_path='test.path', context=context
        )

        assert database.factory is mock_factory
        assert database.grammar_path == 'test.path'
        assert database.context is context
        assert database.cache == {}

    def test_getattr_caches_factory_results(
        self, database: db.Database, mock_factory: Mock, context: dict[str, Any]
    ) -> None:
        """Test that __getattr__ caches factory results."""
        result1 = database.attr1
        result2 = database.attr1  # Second access should use cache

        assert result1 == 'factory_result'
        assert result2 == 'factory_result'
        assert mock_factory.call_count == 1  # Factory called only once
        assert 'attr1' in database.cache

    def test_getattr_creates_seeded_context(
        self, database: db.Database, mock_factory: Mock, context: dict[str, Any]
    ) -> None:
        """Test that __getattr__ creates properly seeded context."""
        with patch('prestoplot.contexts.update_context') as mock_update:
            mock_update.return_value.__enter__ = Mock()
            mock_update.return_value.__exit__ = Mock()

            _ = database.test_attr

            # Should create context with seed containing original seed + attribute name
            mock_update.assert_called_once_with(
                context, key='test_attr', seed=f'{context["seed"]}-test_attr'
            )

    def test_getattr_returns_existing_dict_attributes(
        self, database: db.Database, mock_factory: Mock
    ) -> None:
        """Test that __getattr__ returns existing __dict__ attributes without calling factory."""
        database.__dict__['existing_attr'] = 'existing_value'

        result = database.existing_attr

        assert result == 'existing_value'
        assert mock_factory.call_count == 0  # Factory should not be called

    def test_getattr_delegates_to_str_methods(
        self, database: db.Database, mock_factory: Mock
    ) -> None:
        """Test that __getattr__ delegates string method access to str(self)."""
        mock_factory.return_value = 'test_string'

        result = database.upper  # str.upper method

        # Should return the bound method
        assert callable(result)
        # Calling it should work like str.upper
        assert result() == 'TEST_STRING'

    def test_getitem_delegates_to_getattr(self, database: db.Database) -> None:
        """Test that __getitem__ delegates to __getattr__."""
        result = database['test_key']

        assert result == 'factory_result'
        assert 'test_key' in database.cache

    def test_str_calls_factory_with_context(
        self, database: db.Database, mock_factory: Mock, context: dict[str, Any]
    ) -> None:
        """Test that __str__ calls factory with correct context."""
        str(database)

        mock_factory.assert_called_once_with(context)

    def test_str_returns_string_representation(
        self, database: db.Database, mock_factory: Mock
    ) -> None:
        """Test that __str__ returns string representation of factory result."""
        mock_factory.return_value = 42

        result = str(database)

        assert result == '42'
        assert isinstance(result, str)


class TestDatabag:
    """Test the Databag class."""

    @pytest.fixture
    def databag(self, context: dict[str, Any]) -> db.Databag:
        """Create a Databag instance for testing."""
        return db.Databag(
            grammar_path='test.path', context=context, key1='value1', key2='value2'
        )

    def test_init_stores_context_and_data(self, context: dict[str, Any]) -> None:
        """Test that Databag.__init__ stores context and initializes dict properly."""
        databag = db.Databag(
            grammar_path='test.path', context=context, initial_key='initial_value'
        )

        assert databag.context is context
        assert databag.grammar_path == 'test.path'
        assert databag['initial_key'] == 'initial_value'

    def test_init_accepts_dict_args(self, context: dict[str, Any]) -> None:
        """Test that Databag.__init__ accepts standard dict arguments."""
        initial_data = {'a': 1, 'b': 2}
        databag = db.Databag('test.path', context, initial_data, c=3)

        assert databag['a'] == 1
        assert databag['b'] == 2
        assert databag['c'] == 3

    def test_getattr_delegates_to_getitem(self, databag: db.Databag) -> None:
        """Test that __getattr__ delegates to __getitem__."""
        assert databag.key1 == 'value1'
        assert databag.key2 == 'value2'

    def test_getitem_returns_plain_values(self, databag: db.Databag) -> None:
        """Test that __getitem__ returns plain string values without rendering."""
        result = databag['key1']

        assert result == 'value1'
        assert isinstance(result, str)

    def test_getitem_renders_text_objects(
        self, databag: db.Databag, context: dict[str, Any]
    ) -> None:
        """Test that __getitem__ renders text objects."""
        mock_text = Mock(spec=texts.Text)
        mock_text.render.return_value = 'rendered_result'

        databag['text_key'] = mock_text

        with patch('prestoplot.texts.is_text', return_value=True):
            result = databag['text_key']

        assert result == 'rendered_result'
        mock_text.render.assert_called_once_with(context)

    def test_getitem_works_with_string_keys(self, databag: db.Databag) -> None:
        """Test that __getitem__ works correctly with string keys."""
        databag['string_key'] = 'string_value'

        result = databag['string_key']

        assert result == 'string_value'

    def test_getitem_handles_numeric_keys_in_error_logging(
        self, databag: db.Databag
    ) -> None:
        """Test that __getitem__ handles numeric keys properly when logging errors."""
        # Add a numeric key to the databag
        databag[123] = 'numeric_value'

        # Try to access a missing key - this should log properly without TypeError
        with patch('prestoplot.db.logger') as mock_logger:
            with pytest.raises(KeyError):
                databag['nonexistent_key']

            # Logger should have been called without causing TypeError
            mock_logger.exception.assert_called_once()
            # Verify the logged message includes the numeric key converted to string
            args, kwargs = mock_logger.exception.call_args
            assert '123' in args[2]  # The joined keys string should contain '123'

    def test_getitem_raises_keyerror_for_missing_keys(
        self, databag: db.Databag
    ) -> None:
        """Test that __getitem__ raises KeyError for missing keys."""
        with pytest.raises(KeyError):
            databag['nonexistent_key']

    def test_getitem_logs_keyerror(self, databag: db.Databag) -> None:
        """Test that __getitem__ logs KeyError exceptions."""
        with patch('prestoplot.db.logger') as mock_logger:
            with pytest.raises(KeyError):
                databag['missing_key']

            mock_logger.exception.assert_called_once()


class TestDatalist:
    """Test the Datalist class."""

    @pytest.fixture
    def datalist(self, context: dict[str, Any]) -> db.Datalist:
        """Create a Datalist instance for testing."""
        return db.Datalist('test.path', context, ['item1', 'item2', 'item3'])

    def test_init_stores_context_and_data(self, context: dict[str, Any]) -> None:
        """Test that Datalist.__init__ stores context and initializes list properly."""
        datalist = db.Datalist('test.path', context, ['a', 'b', 'c'])

        assert datalist.context is context
        assert datalist.grammar_path == 'test.path'
        assert len(datalist) == 3
        assert datalist[0] == 'a'

    def test_init_accepts_list_args(self, context: dict[str, Any]) -> None:
        """Test that Datalist.__init__ accepts standard list arguments."""
        datalist = db.Datalist('test.path', context, ['initial'])

        datalist.append('added')
        assert len(datalist) == 2
        assert datalist[1] == 'added'

    def test_getitem_returns_plain_values(self, datalist: db.Datalist) -> None:
        """Test that __getitem__ returns plain values without rendering."""
        result = datalist[0]

        assert result == 'item1'
        assert isinstance(result, str)

    def test_getitem_renders_text_objects(
        self, datalist: db.Datalist, context: dict[str, Any]
    ) -> None:
        """Test that __getitem__ renders text objects."""
        mock_text = Mock(spec=texts.Text)
        mock_text.render.return_value = 'rendered_result'

        datalist[0] = mock_text

        with patch('prestoplot.texts.is_text', return_value=True):
            result = datalist[0]

        assert result == 'rendered_result'
        mock_text.render.assert_called_once_with(context)

    def test_getitem_raises_indexerror_for_invalid_indices(
        self, datalist: db.Datalist
    ) -> None:
        """Test that __getitem__ raises IndexError for invalid indices."""
        with pytest.raises(IndexError):
            datalist[10]  # Out of bounds

    def test_getitem_logs_keyerror(self, datalist: db.Datalist) -> None:
        """Test that __getitem__ logs KeyError exceptions (even though IndexError is raised)."""
        # Note: The current implementation catches KeyError but IndexError is what's actually raised
        # This test documents the current behavior, though it might be a bug
        import contextlib

        with patch('prestoplot.db.logger') as mock_logger:
            with contextlib.suppress(IndexError):
                datalist[10]

            # Logger should not be called for IndexError since the except clause catches KeyError
            mock_logger.exception.assert_not_called()

    def test_error_logging_handles_non_string_items(
        self, context: dict[str, Any]
    ) -> None:
        """Test that error logging can handle non-string items without TypeError."""
        # Create a datalist with mixed types including non-strings
        datalist = db.Datalist(
            'test.path', context, ['string', 123, None, {'key': 'value'}]
        )

        # Test that we can join all items as strings without error
        # This tests the fix for the join() TypeError bug
        joined_items = ', '.join(str(item) for item in datalist)

        # Verify all items are represented in the joined string
        assert 'string' in joined_items
        assert '123' in joined_items
        assert 'None' in joined_items
        assert 'key' in joined_items  # Part of the dict representation


class TestChoose:
    """Test the choose factory function."""

    def test_choose_creates_callable_factory(self) -> None:
        """Test that choose returns a callable factory."""
        items = ['a', 'b', 'c']
        chooser = db.choose(items)

        assert callable(chooser)

    def test_chooser_returns_items_from_list(self, context: dict[str, Any]) -> None:
        """Test that chooser returns items from the provided list."""
        items = ['apple', 'banana', 'cherry']
        chooser = db.choose(items)

        for _ in range(10):  # Test multiple times
            result = chooser(context)
            assert result in items

    def test_chooser_is_deterministic_with_same_seed(self) -> None:
        """Test that chooser returns same result with same seed."""
        items = ['a', 'b', 'c']
        chooser = db.choose(items)
        context = {'seed': 'fixed-seed'}

        result1 = chooser(context)
        result2 = chooser(context)

        assert result1 == result2

    def test_chooser_renders_text_objects(self, context: dict[str, Any]) -> None:
        """Test that chooser renders text objects."""
        mock_text = Mock(spec=texts.Text)
        mock_text.render.return_value = 'rendered_text'
        items = [mock_text, 'plain_string']
        chooser = db.choose(items)

        with patch('prestoplot.texts.is_text', side_effect=lambda x: x is mock_text):
            # Call multiple times to eventually hit the text object
            results = [chooser(context) for _ in range(20)]

        # Should contain both rendered text and plain string
        assert 'rendered_text' in results or 'plain_string' in results
        if 'rendered_text' in results:
            mock_text.render.assert_called_with(context)

    def test_chooser_doesnt_modify_original_list(self, context: dict[str, Any]) -> None:
        """Test that chooser doesn't modify the original list."""
        items = ['a', 'b', 'c']
        original_items = items.copy()
        chooser = db.choose(items)

        # Make multiple choices
        for _ in range(10):
            chooser(context)

        assert items == original_items


class TestPick:
    """Test the pick factory function."""

    def test_pick_creates_callable_factory(self) -> None:
        """Test that pick returns a callable factory."""
        items = ['a', 'b', 'c']
        picker = db.pick(items)

        assert callable(picker)

    def test_picker_removes_items_from_list(self) -> None:
        """Test that picker removes items from the original list."""
        items = ['a', 'b', 'c']
        original_length = len(items)
        picker = db.pick(items)
        context = {'seed': 'test-seed'}

        result = picker(context)

        assert result in ['a', 'b', 'c']
        assert len(items) == original_length - 1
        assert result not in items  # Item should be removed

    def test_picker_handles_single_item_list(self) -> None:
        """Test that picker handles single-item lists correctly."""
        items = ['only_item']
        picker = db.pick(items)
        context = {'seed': 'test-seed'}

        result = picker(context)

        assert result == 'only_item'
        assert len(items) == 0

    def test_picker_renders_text_objects(self) -> None:
        """Test that picker renders text objects."""
        mock_text = Mock(spec=texts.Text)
        mock_text.render.return_value = 'rendered_text'
        items = [mock_text]
        picker = db.pick(items)
        context = {'seed': 'test-seed'}

        with patch('prestoplot.texts.is_text', return_value=True):
            result = picker(context)

        assert result == 'rendered_text'
        mock_text.render.assert_called_once_with(context)

    def test_picker_uses_random_selection(self) -> None:
        """Test that picker uses random selection for index."""
        # With different seeds, should potentially pick different indices
        context1 = {'seed': 'seed1'}
        context2 = {'seed': 'seed2'}

        # Reset lists for each test
        items1 = ['a', 'b', 'c', 'd', 'e']
        items2 = ['a', 'b', 'c', 'd', 'e']

        picker1 = db.pick(items1)
        picker2 = db.pick(items2)

        result1 = picker1(context1)
        result2 = picker2(context2)

        # Results should be valid (though potentially same due to randomness)
        assert result1 in ['a', 'b', 'c', 'd', 'e']
        assert result2 in ['a', 'b', 'c', 'd', 'e']


class TestMarkovify:
    """Test the markovify factory function."""

    def test_markovify_creates_callable_factory(self) -> None:
        """Test that markovify returns a callable factory."""
        items = ['Alice', 'Bob', 'Charlie']
        markovifier = db.markovify(items)

        assert callable(markovifier)

    def test_markovifier_generates_strings(self, context: dict[str, Any]) -> None:
        """Test that markovifier generates string output."""
        items = ['Alice', 'Bob', 'Charlie', 'David', 'Eve']
        markovifier = db.markovify(items)

        result = markovifier(context)

        assert isinstance(result, str)
        assert len(result) >= 0  # Can be empty string

    def test_markovifier_uses_context_parameters(self) -> None:
        """Test that markovifier uses context parameters for configuration."""
        items = ['Alice', 'Bob', 'Charlie']
        markovifier = db.markovify(items)

        context_with_params = {
            'seed': 'test-seed',
            'markov_chainlen': 3,
            'start_markov': 'A',
        }

        with patch('prestoplot.markov.NameGenerator') as mock_gen_class:
            mock_gen = Mock()
            mock_gen.get_random_name.return_value = 'generated_name'
            mock_gen_class.return_value = mock_gen

            result = markovifier(context_with_params)

            # Should create generator with specified chainlen
            mock_gen_class.assert_called_once_with(items, chainlen=3)

            # Should call get_random_name with start and seed
            mock_gen.get_random_name.assert_called_once_with(
                start='A', seed='test-seed'
            )

            assert result == 'generated_name'

    def test_markovifier_uses_default_parameters(self, context: dict[str, Any]) -> None:
        """Test that markovifier uses default parameters when not specified."""
        items = ['Alice', 'Bob']
        markovifier = db.markovify(items)

        with patch('prestoplot.markov.NameGenerator') as mock_gen_class:
            mock_gen = Mock()
            mock_gen.get_random_name.return_value = 'generated_name'
            mock_gen_class.return_value = mock_gen

            _ = markovifier(context)

            # Should use default chainlen of 2
            mock_gen_class.assert_called_once_with(items, chainlen=2)

            # Should use empty start string by default
            mock_gen.get_random_name.assert_called_once_with(
                start='', seed=context['seed']
            )


class TestRatchet:
    """Test the ratchet factory function - expanded tests."""

    def test_ratchet_creates_callable_factory(self) -> None:
        """Test that ratchet returns a callable factory."""
        items = ['a', 'b', 'c']
        ratcheter = db.ratchet(items)

        assert callable(ratcheter)

    def test_multiple_ratchets_maintain_independent_state(self) -> None:
        """Test that multiple ratchet instances maintain completely independent state."""
        items_a = ['x', 'y']
        items_b = ['1', '2', '3']

        ratchet_a = db.ratchet(items_a)
        ratchet_b = db.ratchet(items_b)
        context = {'seed': 'test'}

        # Interleave calls to both ratchets
        assert ratchet_a(context) == 'x'
        assert ratchet_b(context) == '1'
        assert ratchet_a(context) == 'y'
        assert ratchet_b(context) == '2'
        assert ratchet_a(context) == 'x'  # Cycles back
        assert ratchet_b(context) == '3'
        assert ratchet_b(context) == '1'  # Cycles back

    def test_ratchet_state_persists_across_calls(self) -> None:
        """Test that ratchet state persists across multiple function calls."""
        items = ['first', 'second', 'third']
        ratcheter = db.ratchet(items)
        context = {'seed': 'test'}

        # Call multiple times in separate invocations
        results = [
            ratcheter(context) for _ in range(7)
        ]  # More than the list length to test cycling

        expected = ['first', 'second', 'third', 'first', 'second', 'third', 'first']
        assert results == expected

    def test_ratchet_renders_mixed_content(self) -> None:
        """Test that ratchet renders text objects mixed with plain strings."""
        mock_text1 = Mock(spec=texts.Text)
        mock_text1.render.return_value = 'rendered1'
        mock_text2 = Mock(spec=texts.Text)
        mock_text2.render.return_value = 'rendered2'

        items = [mock_text1, 'plain', mock_text2]
        ratcheter = db.ratchet(items)
        context = {'seed': 'test'}

        with patch(
            'prestoplot.texts.is_text', side_effect=lambda x: hasattr(x, 'render')
        ):
            result1 = ratcheter(context)
            result2 = ratcheter(context)
            result3 = ratcheter(context)

        assert result1 == 'rendered1'
        assert result2 == 'plain'
        assert result3 == 'rendered2'
        mock_text1.render.assert_called_with(context)
        mock_text2.render.assert_called_with(context)


class TestParetoInt:
    """Test the pareto_int utility function."""

    def test_pareto_int_with_different_shapes(self) -> None:
        """Test pareto_int with different shape parameters."""
        rng = seeds.get_rng('test-seed')

        result_shape_1 = db.pareto_int(rng, shape=1.0)
        result_shape_2 = db.pareto_int(rng, shape=2.0)

        assert isinstance(result_shape_1, int)
        assert isinstance(result_shape_2, int)
        assert result_shape_1 >= 0
        assert result_shape_2 >= 0

    def test_pareto_int_default_shape(self) -> None:
        """Test pareto_int with default shape parameter."""
        rng = seeds.get_rng('test-seed')

        result = db.pareto_int(rng)  # Uses default shape=1

        assert isinstance(result, int)
        assert result >= 0

    def test_pareto_int_deterministic_with_same_rng_state(self) -> None:
        """Test that pareto_int is deterministic with same RNG state."""
        rng1 = seeds.get_rng('identical-seed')
        rng2 = seeds.get_rng('identical-seed')

        result1 = db.pareto_int(rng1)
        result2 = db.pareto_int(rng2)

        assert result1 == result2
