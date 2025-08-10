"""Integration tests for ratchet mode in grammar files."""

import pathlib
from typing import Final

from prestoplot import storages, story

DATA: Final[pathlib.Path] = pathlib.Path(__file__).parent / 'data'


def test_ratchet_mode_integration() -> None:
    """Test that ratchet mode works within a single grammar evaluation."""
    storage = storages.FileStorage(str(DATA))

    # Single generation should show ratchet progression within the template
    result = story.render_story(storage, 'test_ratchet', seed='test')

    # Should get: red blue green red (cycling back on fourth access)
    expected = 'red blue green red'
    assert result == expected


def test_ratchet_mode_different_keys() -> None:
    """Test that each new story generation creates a fresh ratchet."""
    storage = storages.FileStorage(str(DATA))

    # Each call creates a new ratchet, so should start from beginning
    result1 = story.render_story(storage, 'test_ratchet', seed='key1')
    result2 = story.render_story(storage, 'test_ratchet', seed='key2')
    result3 = story.render_story(storage, 'test_ratchet', seed='key1')

    # All should be the same since each starts fresh
    expected = 'red blue green red'
    assert result1 == expected
    assert result2 == expected
    assert result3 == expected
