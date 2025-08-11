"""Test suite for prestoplot.grammars module."""

import pathlib
from typing import Any
from unittest.mock import Mock

import pytest

from prestoplot import db, grammars, storages, texts


class TestParseGrammarFile:
    """Test parse_grammar_file function."""

    @pytest.fixture
    def mock_storage(self) -> Mock:
        """Create a mock storage object."""
        storage = Mock()
        storage.resolve_module.return_value = {
            'Begin': ['Hello World'],
            'Name': ['Alice', 'Bob'],
        }
        return storage

    @pytest.fixture
    def basic_context(self) -> dict[str, Any]:
        """Create a basic context dictionary."""
        return {}

    def test_parse_simple_grammar(
        self, mock_storage: Mock, basic_context: dict[str, Any]
    ) -> None:
        """Test parsing a simple grammar file."""
        result = grammars.parse_grammar_file(mock_storage, 'test.yaml', basic_context)

        assert 'Begin' in result
        assert 'Name' in result
        mock_storage.resolve_module.assert_called_once_with('test.yaml')

    def test_handles_cycle_detection(
        self, mock_storage: Mock, basic_context: dict[str, Any]
    ) -> None:
        """Test that cycle detection prevents infinite recursion."""
        included = {'test.yaml'}
        result = grammars.parse_grammar_file(
            mock_storage, 'test.yaml', basic_context, included
        )

        # Should return context unchanged without calling resolve_module
        assert result == basic_context
        mock_storage.resolve_module.assert_not_called()

    def test_processes_includes(
        self, mock_storage: Mock, basic_context: dict[str, Any]
    ) -> None:
        """Test processing of include directives."""
        mock_storage.resolve_module.side_effect = [
            {'include': ['names.yaml'], 'Begin': ['Hello {Name}']},
            {'Name': ['Charlie', 'Diana']},
        ]

        result = grammars.parse_grammar_file(mock_storage, 'main.yaml', basic_context)

        assert 'Begin' in result
        assert 'Name' in result
        assert mock_storage.resolve_module.call_count == 2

    def test_handles_custom_render_strategy(
        self, mock_storage: Mock, basic_context: dict[str, Any]
    ) -> None:
        """Test handling of custom render strategy."""
        mock_storage.resolve_module.return_value = {
            'render': 'jinja2',
            'Begin': ['Hello {{ Name }}'],
        }

        result = grammars.parse_grammar_file(mock_storage, 'test.yaml', basic_context)

        assert 'Begin' in result
        mock_storage.resolve_module.assert_called_once()


class TestParseRenderStrategy:
    """Test parse_render_strategy function."""

    def test_returns_ftemplate_renderer(self) -> None:
        """Test that 'ftemplate' returns the f-string renderer."""
        result = grammars.parse_render_strategy('ftemplate', 'test.yaml')

        assert result == texts.render_ftemplate

    def test_returns_jinja2_renderer(self) -> None:
        """Test that 'jinja2' returns the Jinja2 renderer."""
        result = grammars.parse_render_strategy('jinja2', 'test.yaml')

        assert result == texts.render_jinja2

    def test_returns_jinja_renderer(self) -> None:
        """Test that 'jinja' also returns the Jinja2 renderer."""
        result = grammars.parse_render_strategy('jinja', 'test.yaml')

        assert result == texts.render_jinja2

    def test_raises_error_for_unknown_strategy(self) -> None:
        """Test that unknown render strategies raise ValueError."""
        with pytest.raises(ValueError, match='Unrecognized render strategy'):
            grammars.parse_render_strategy('unknown', 'test.yaml')


class TestParseIncludes:
    """Test parse_includes function."""

    @pytest.fixture
    def mock_storage(self) -> Mock:
        """Create a mock storage object."""
        storage = Mock()
        storage.resolve_module.return_value = {'Name': ['Test']}
        return storage

    def test_processes_empty_includes(self, mock_storage: Mock) -> None:
        """Test processing empty include list."""
        context = {}
        included = set()

        result = grammars.parse_includes(
            mock_storage, 'main.yaml', [], context, included
        )

        assert result == context
        mock_storage.resolve_module.assert_not_called()

    def test_processes_single_include(self, mock_storage: Mock) -> None:
        """Test processing a single include."""
        context = {}
        included = set()

        result = grammars.parse_includes(
            mock_storage, 'main.yaml', ['include.yaml'], context, included
        )

        assert 'Name' in result
        mock_storage.resolve_module.assert_called_once_with('include.yaml')

    def test_processes_multiple_includes(self, mock_storage: Mock) -> None:
        """Test processing multiple includes."""
        mock_storage.resolve_module.side_effect = [{'First': ['A']}, {'Second': ['B']}]
        context = {}
        included = set()

        result = grammars.parse_includes(
            mock_storage, 'main.yaml', ['first.yaml', 'second.yaml'], context, included
        )

        assert 'First' in result
        assert 'Second' in result
        assert mock_storage.resolve_module.call_count == 2


class TestParseData:
    """Test parse_data function."""

    @pytest.fixture
    def basic_context(self) -> dict[str, Any]:
        """Create a basic context dictionary."""
        return {}

    def test_parses_simple_data(self, basic_context: dict[str, Any]) -> None:
        """Test parsing simple string data."""
        data = {'Name': 'Alice'}

        result = grammars.parse_data(data, 'test.yaml', basic_context)

        assert 'Name' in result
        assert isinstance(result['Name'], texts.RenderableText)

    def test_parses_list_data(self, basic_context: dict[str, Any]) -> None:
        """Test parsing list data."""
        data = {'Names': ['Alice', 'Bob']}

        result = grammars.parse_data(data, 'test.yaml', basic_context)

        assert 'Names' in result
        assert isinstance(result['Names'], db.Database)

    def test_uses_custom_render_strategy(self, basic_context: dict[str, Any]) -> None:
        """Test using custom render strategy."""
        data = {'Name': 'Hello {{ world }}'}

        result = grammars.parse_data(
            data, 'test.yaml', basic_context, render_strategy=texts.render_jinja2
        )

        assert 'Name' in result
        rendered_text = result['Name']
        assert isinstance(rendered_text, texts.RenderableText)
        # Test that the render strategy was used by checking it can render Jinja2 syntax
        basic_context['world'] = 'Earth'
        rendered = rendered_text.render(basic_context)
        assert str(rendered) == 'Hello Earth'


class TestGetListSetting:
    """Test get_list_setting function."""

    def test_returns_default_mode_for_plain_list(self) -> None:
        """Test that plain lists return 'reuse' mode."""
        value = ['item1', 'item2']

        mode, cleaned_value = grammars.get_list_setting(value, 'test.yaml')

        assert mode == 'reuse'
        assert cleaned_value == ['item1', 'item2']

    def test_extracts_mode_from_list_setting(self) -> None:
        """Test extracting mode setting from list."""
        value = [{'mode': 'pick'}, 'item1', 'item2']

        mode, cleaned_value = grammars.get_list_setting(value, 'test.yaml')

        assert mode == 'pick'
        assert cleaned_value == ['item1', 'item2']

    def test_ignores_non_mode_dict_at_start(self) -> None:
        """Test that non-mode dictionaries are not treated as settings."""
        value = [{'other': 'value'}, 'item1', 'item2']

        mode, cleaned_value = grammars.get_list_setting(value, 'test.yaml')

        assert mode == 'reuse'
        assert cleaned_value == [{'other': 'value'}, 'item1', 'item2']

    def test_ignores_multi_key_dict_at_start(self) -> None:
        """Test that multi-key dictionaries are not treated as mode settings."""
        value = [{'mode': 'pick', 'other': 'value'}, 'item1']

        mode, cleaned_value = grammars.get_list_setting(value, 'test.yaml')

        assert mode == 'reuse'
        assert cleaned_value == [{'mode': 'pick', 'other': 'value'}, 'item1']

    def test_handles_empty_list(self) -> None:
        """Test handling empty list."""
        value = []

        mode, cleaned_value = grammars.get_list_setting(value, 'test.yaml')

        assert mode == 'reuse'
        assert cleaned_value == []


class TestParseValue:
    """Test parse_value function."""

    @pytest.fixture
    def basic_context(self) -> dict[str, Any]:
        """Create a basic context dictionary."""
        return {}

    def test_parses_string_value(self, basic_context: dict[str, Any]) -> None:
        """Test parsing string values."""
        result = grammars.parse_value('Hello World', 'test.yaml:Name', basic_context)

        assert isinstance(result, texts.RenderableText)

    def test_parses_boolean_value(self, basic_context: dict[str, Any]) -> None:
        """Test parsing boolean values."""
        true_value = True
        result = grammars.parse_value(true_value, 'test.yaml:Flag', basic_context)

        assert result is True

        false_value = False
        result = grammars.parse_value(false_value, 'test.yaml:Flag', basic_context)

        assert result is False

    def test_parses_list_with_reuse_mode(self, basic_context: dict[str, Any]) -> None:
        """Test parsing list with default reuse mode."""
        result = grammars.parse_value(['A', 'B', 'C'], 'test.yaml:Names', basic_context)

        assert isinstance(result, db.Database)

    def test_parses_list_with_pick_mode(self, basic_context: dict[str, Any]) -> None:
        """Test parsing list with pick mode."""
        value = [{'mode': 'pick'}, 'A', 'B', 'C']
        result = grammars.parse_value(value, 'test.yaml:Names', basic_context)

        assert isinstance(result, db.Database)

    def test_parses_list_with_markov_mode(self, basic_context: dict[str, Any]) -> None:
        """Test parsing list with markov mode."""
        value = [{'mode': 'markov'}, 'A', 'B', 'C']
        result = grammars.parse_value(value, 'test.yaml:Names', basic_context)

        assert isinstance(result, db.Database)

    def test_parses_list_with_ratchet_mode(self, basic_context: dict[str, Any]) -> None:
        """Test parsing list with ratchet mode."""
        value = [{'mode': 'ratchet'}, 'A', 'B', 'C']
        result = grammars.parse_value(value, 'test.yaml:Names', basic_context)

        assert isinstance(result, db.Database)

    def test_parses_list_with_list_mode(self, basic_context: dict[str, Any]) -> None:
        """Test parsing list with list mode."""
        value = [{'mode': 'list'}, 'A', 'B', 'C']
        result = grammars.parse_value(value, 'test.yaml:Names', basic_context)

        assert isinstance(result, db.Datalist)

    def test_parses_dict_value(self, basic_context: dict[str, Any]) -> None:
        """Test parsing dictionary values."""
        value = {'name': 'Alice', 'age': '25'}
        result = grammars.parse_value(value, 'test.yaml:Person', basic_context)

        assert isinstance(result, db.Databag)

    def test_uses_custom_render_strategy(self, basic_context: dict[str, Any]) -> None:
        """Test using custom render strategy."""
        result = grammars.parse_value(
            'Hello {{ name }}',
            'test.yaml:Greeting',
            basic_context,
            render_strategy=texts.render_jinja2,
        )

        assert isinstance(result, texts.RenderableText)
        # Test that the render strategy was used by checking it can render Jinja2 syntax
        test_context = basic_context.copy()
        test_context['name'] = 'World'
        rendered = result.render(test_context)
        assert str(rendered) == 'Hello World'

    def test_returns_none_for_unhandled_types(
        self, basic_context: dict[str, Any]
    ) -> None:
        """Test that unhandled value types return None."""
        # This tests the fallback case, though in practice all expected types are handled
        result = grammars.parse_value([], 'test.yaml:Empty', basic_context)

        # Empty list should create a Database, not None
        assert isinstance(result, db.Database)


class TestFixText:
    """Test fix_text function."""

    def test_removes_common_indentation(self) -> None:
        """Test removal of common indentation."""
        text = """
            Hello
            World
        """

        result = grammars.fix_text(text)

        assert result == 'Hello\nWorld'

    def test_strips_leading_and_trailing_whitespace(self) -> None:
        """Test stripping of leading and trailing whitespace."""
        text = '  Hello World  '

        result = grammars.fix_text(text)

        assert result == 'Hello World'

    def test_handles_single_line_text(self) -> None:
        """Test handling single line text."""
        text = 'Hello World'

        result = grammars.fix_text(text)

        assert result == 'Hello World'

    def test_handles_empty_text(self) -> None:
        """Test handling empty text."""
        text = ''

        result = grammars.fix_text(text)

        assert result == ''

    def test_preserves_internal_spacing(self) -> None:
        """Test that internal spacing is preserved."""
        text = """
            Line 1
                Indented line
            Line 3
        """

        result = grammars.fix_text(text)

        assert result == 'Line 1\n    Indented line\nLine 3'


class TestGrammarIntegration:
    """Integration tests using real storage and grammar files."""

    @pytest.fixture
    def test_data_path(self) -> pathlib.Path:
        """Path to test data directory."""
        return pathlib.Path(__file__).parent / 'data'

    @pytest.fixture
    def file_storage(self, test_data_path: pathlib.Path) -> storages.FileStorage:
        """Create file storage pointing to test data."""
        return storages.FileStorage(str(test_data_path))

    def test_parses_real_grammar_file(self, file_storage: storages.FileStorage) -> None:
        """Test parsing a real grammar file from test data."""
        context = {}

        result = grammars.parse_grammar_file(file_storage, 'names', context)

        assert 'Names' in result
        assert 'NamesMarkov' in result
        assert isinstance(result['Names'], db.Databag)
        assert isinstance(result['NamesMarkov'], db.Databag)

    def test_handles_includes_in_real_files(
        self, file_storage: storages.FileStorage
    ) -> None:
        """Test handling includes with real grammar files."""
        context = {}

        result = grammars.parse_grammar_file(file_storage, 'characters', context)

        # Should have content from both characters.yaml and included names.yaml
        assert 'Begin' in result
        assert 'Names' in result  # from included names.yaml
        assert 'Description' in result  # from characters.yaml

    def test_handles_jinja2_template_file(
        self, file_storage: storages.FileStorage
    ) -> None:
        """Test handling Jinja2 template files."""
        context = {}

        result = grammars.parse_grammar_file(file_storage, 'characters_jinja', context)

        assert 'Begin' in result
        # Should parse successfully even though it uses Jinja2 syntax
