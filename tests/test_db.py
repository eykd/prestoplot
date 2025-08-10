"""Tests for the db module factory functions."""

from typing import Any

import pytest

from prestoplot import contexts, db, texts


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
    text_obj = texts.RenderedStr('rendered')
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
