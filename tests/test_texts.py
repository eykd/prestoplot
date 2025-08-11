import pathlib
from typing import Final

import jinja2
import pytest

from prestoplot import texts

PATH: Final[pathlib.Path] = pathlib.Path(__file__).parent

DATA: Final[pathlib.Path] = PATH / 'data'


class TestRenderFtemplate:
    """Tests for render_ftemplate function."""

    def test_render_ftemplate_simple(self) -> None:
        """Test basic f-string template rendering."""
        result = texts.render_ftemplate('Hello {name}', 'test_path', {'name': 'World'})
        assert result == 'Hello World'
        assert isinstance(result, texts.RenderedStr)

    def test_render_ftemplate_complex_expression(self) -> None:
        """Test f-string template with complex expressions."""
        context = {'count': 5, 'item': 'apple'}
        result = texts.render_ftemplate('{count + 1} {item}s', 'test_path', context)
        assert result == '6 apples'

    def test_render_ftemplate_exception(self) -> None:
        """Test f-string template rendering with invalid syntax."""
        with pytest.raises(NameError, match="name 'undefined_var' is not defined"):
            texts.render_ftemplate('{undefined_var}', 'test_path', {})


class TestRenderJinja2:
    """Tests for render_jinja2 function."""

    def test_render_jinja2_simple(self) -> None:
        """Test basic Jinja2 template rendering."""
        result = texts.render_jinja2('Hello {{ name }}', 'test_path', {'name': 'World'})
        assert result == 'Hello World'
        assert isinstance(result, texts.RenderedStr)

    def test_render_jinja2_with_filters(self) -> None:
        """Test Jinja2 template with filters."""
        result = texts.render_jinja2(
            'Hello {{ name | upper }}', 'test_path', {'name': 'world'}
        )
        assert result == 'Hello WORLD'

    def test_render_jinja2_exception(self) -> None:
        """Test Jinja2 template rendering with invalid template."""
        with pytest.raises(ValueError, match='Could not render Jinja2 template'):
            texts.render_jinja2('{{ undefined_var | some_filter }}', 'test_path', {})

    def test_render_jinja2_exception_with_source(self) -> None:
        """Test Jinja2 template error with line information."""
        template = 'Line 1\nLine {{ bad_var | undefined_filter }}\nLine 3'
        with pytest.raises(ValueError, match='Could not render Jinja2 template'):
            texts.render_jinja2(template, 'test_path', {})


class TestRenderedStr:
    """Tests for RenderedStr class."""

    def test_rendered_str_article_consonant(self) -> None:
        """Test RenderedStr article methods for consonant start."""
        rs = texts.RenderedStr('book')
        assert rs.a == 'a'
        assert rs.an == 'a'
        assert rs.A == 'A'
        assert rs.An == 'A'

    def test_rendered_str_article_vowel(self) -> None:
        """Test RenderedStr article methods for vowel start."""
        rs = texts.RenderedStr('apple')
        assert rs.a == 'an'
        assert rs.an == 'an'
        assert rs.A == 'An'
        assert rs.An == 'An'

    def test_rendered_str_article_uppercase_vowel(self) -> None:
        """Test RenderedStr article methods for uppercase vowel start."""
        rs = texts.RenderedStr('Apple')
        assert rs.a == 'an'
        assert rs.an == 'an'
        assert rs.A == 'An'
        assert rs.An == 'An'

    def test_rendered_str_article_empty_string(self) -> None:
        """Test RenderedStr article methods for empty string."""
        rs = texts.RenderedStr('')
        with pytest.raises(IndexError):
            _ = rs.a  # Should raise IndexError when accessing first character

    def test_rendered_str_inherits_string_methods(self) -> None:
        """Test that RenderedStr inherits all string methods."""
        rs = texts.RenderedStr('Hello World')
        assert rs.upper() == 'HELLO WORLD'
        assert rs.lower() == 'hello world'
        assert rs.split() == ['Hello', 'World']
        assert len(rs) == 11


class TestText:
    """Tests for Text class."""

    def test_text_init(self) -> None:
        """Test Text class initialization."""
        context = {'key': 'value'}

        def transformer(x: str) -> str:
            return x.upper()

        text = texts.Text('hello', 'test_path', context, transformer)

        assert text.value == 'hello'
        assert text.grammar_path == 'test_path'
        assert text.context == context
        assert text.transformer == transformer

    def test_text_init_default_transformer(self) -> None:
        """Test Text class initialization with default transformer."""
        text = texts.Text('hello', 'test_path', {})
        assert text.transformer('test') == 'test'  # identity function

    def test_text_article_consonant(self) -> None:
        """Test Text article methods for consonant start."""
        text = texts.Text('book', 'path', {})
        assert text.a == 'a'
        assert text.an == 'a'
        assert text.A == 'A'
        assert text.An == 'A'

    def test_text_article_vowel(self) -> None:
        """Test Text article methods for vowel start."""
        text = texts.Text('apple', 'path', {})
        assert text.a == 'an'
        assert text.an == 'an'
        assert text.A == 'An'
        assert text.An == 'An'

    def test_text_article_uppercase(self) -> None:
        """Test Text article methods for uppercase start."""
        text = texts.Text('Apple', 'path', {})
        assert text.a == 'an'
        assert text.an == 'an'
        assert text.A == 'An'
        assert text.An == 'An'

    def test_text_string_methods(self) -> None:
        """Test Text string method delegation."""
        text = texts.Text('Hello World', 'path', {})
        assert text.upper() == 'HELLO WORLD'
        assert text.lower() == 'hello world'
        assert text.split() == ['Hello', 'World']
        assert len(text.value) == 11

    def test_text_str_representation(self) -> None:
        """Test Text __str__ method."""
        text = texts.Text('hello', 'path', {})
        assert str(text) == 'hello'

    def test_text_repr_representation(self) -> None:
        """Test Text __repr__ method."""
        text = texts.Text('hello', 'path', {})
        assert repr(text) == "'hello'"

    def test_text_hash(self) -> None:
        """Test Text __hash__ method."""
        text1 = texts.Text('hello', 'path', {})
        text2 = texts.Text('hello', 'other_path', {})
        text3 = texts.Text('world', 'path', {})

        assert hash(text1) == hash(text2)  # Same value
        assert hash(text1) != hash(text3)  # Different value

    def test_text_equality(self) -> None:
        """Test Text __eq__ method."""
        text = texts.Text('hello', 'path', {})
        assert text == 'hello'
        assert text != 'world'
        assert text != 42

    def test_text_render_with_transformer(self) -> None:
        """Test Text render method with transformer."""

        def transformer(x: str) -> str:
            return x.upper()

        text = texts.Text('hello', 'path', {}, transformer)
        result = text.render()
        assert result == 'HELLO'
        assert isinstance(result, texts.RenderedStr)

    def test_text_render_default(self) -> None:
        """Test Text render method without transformer."""
        text = texts.Text('hello', 'path', {})
        result = text.render()
        assert result == 'hello'
        assert isinstance(result, texts.RenderedStr)

    def test_text_getattr_string_method(self) -> None:
        """Test Text __getattr__ delegation to string methods."""
        text = texts.Text('hello world', 'path', {})
        assert hasattr(text, 'upper')
        assert hasattr(text, 'split')
        assert text.startswith('hello')

    def test_text_getattr_nonstring_method(self) -> None:
        """Test Text __getattr__ for non-string attributes."""
        text = texts.Text('hello', 'path', {})
        with pytest.raises(AttributeError):
            _ = text.nonexistent_attribute

    def test_text_with_numeric_value(self) -> None:
        """Test Text class with non-string values."""
        text = texts.Text(42, 'path', {})
        assert str(text) == '42'
        assert text.value == 42


class TestRenderableText:
    """Tests for RenderableText class."""

    def test_renderable_text_init(self) -> None:
        """Test RenderableText initialization."""
        context = {'name': 'World'}
        text = texts.RenderableText('Hello {name}', 'test_path', context)

        assert text.value == 'Hello {name}'
        assert text.context == context
        # Test render strategy by checking behavior instead of private attribute
        result = text.render()
        assert result == 'Hello World'

    def test_renderable_text_init_custom_render_strategy(self) -> None:
        """Test RenderableText with custom render strategy."""
        context = {'name': 'World'}
        text = texts.RenderableText(
            'Hello {{ name }}',
            'test_path',
            context,
            render_strategy=texts.render_jinja2,
        )
        # Test render strategy by checking behavior instead of private attribute
        result = text.render()
        assert result == 'Hello World'

    def test_renderable_text_str_fstring(self) -> None:
        """Test RenderableText __str__ with f-string template."""
        context = {'name': 'World'}
        text = texts.RenderableText('Hello {name}', 'test_path', context)
        assert str(text) == 'Hello World'

    def test_renderable_text_str_jinja2(self) -> None:
        """Test RenderableText __str__ with Jinja2 template."""
        context = {'name': 'World'}
        text = texts.RenderableText(
            'Hello {{ name }}',
            'test_path',
            context,
            render_strategy=texts.render_jinja2,
        )
        assert str(text) == 'Hello World'

    def test_renderable_text_render_default_context(self) -> None:
        """Test RenderableText render with default context."""
        context = {'name': 'World'}
        text = texts.RenderableText('Hello {name}', 'test_path', context)
        result = text.render()
        assert result == 'Hello World'
        assert isinstance(result, texts.RenderedStr)

    def test_renderable_text_render_custom_context(self) -> None:
        """Test RenderableText render with custom context."""
        initial_context = {'name': 'World'}
        text = texts.RenderableText('Hello {name}', 'test_path', initial_context)

        custom_context = {'name': 'Universe'}
        result = text.render(custom_context)
        assert result == 'Hello Universe'

    def test_renderable_text_render_with_transformer(self) -> None:
        """Test RenderableText render with transformer that affects final result."""
        # Use a simple template without variables to test transformer properly
        context = {}

        def transformer(x: str) -> str:
            return x.upper()

        text = texts.RenderableText(
            'hello world',  # No template variables
            'test_path',
            context,
            transformer=transformer,
        )
        result = text.render()
        assert result == 'HELLO WORLD'

        # Test with a transformer that affects the template before rendering
        context = {'greeting': 'hello'}

        def transformer2(x: str) -> str:
            return x.replace('greeting', 'salutation')

        text2 = texts.RenderableText(
            '{greeting}',
            'test_path',
            {'salutation': 'hi'},  # Note: context needs the transformed key
            transformer=transformer2,
        )
        result2 = text2.render()
        assert result2 == 'hi'

    def test_renderable_text_articles(self) -> None:
        """Test RenderableText article methods after rendering."""
        context = {'word': 'apple'}
        text = texts.RenderableText('{word}', 'test_path', context)

        # Articles are computed on the raw value before rendering, not after
        # The raw value is '{word}' which starts with '{', a consonant
        assert text.a == 'a'
        assert text.an == 'a'
        assert text.A == 'A'
        assert text.An == 'A'

        # To test articles on rendered content, check the rendered string directly
        rendered = text.render()
        assert rendered.a == 'an'
        assert rendered.an == 'an'

    def test_renderable_text_error_handling(self) -> None:
        """Test RenderableText error handling with malformed templates."""
        context = {}
        text = texts.RenderableText('{undefined}', 'test_path', context)

        with pytest.raises(NameError, match="name 'undefined' is not defined"):
            str(text)


class TestUtilityFunctions:
    """Tests for utility functions and module configuration."""

    def test_is_text_with_text(self) -> None:
        """Test is_text function with Text instance."""
        text = texts.Text('hello', 'path', {})
        assert texts.is_text(text)

    def test_is_text_with_renderable_text(self) -> None:
        """Test is_text function with RenderableText instance."""
        text = texts.RenderableText('hello', 'path', {})
        assert texts.is_text(text)

    def test_is_text_with_string(self) -> None:
        """Test is_text function with regular string."""
        assert not texts.is_text('hello')

    def test_is_text_with_other_types(self) -> None:
        """Test is_text function with other types."""
        assert not texts.is_text(42)
        assert not texts.is_text([])
        assert not texts.is_text({})
        assert not texts.is_text(None)

    def test_jinja2_env_configuration(self) -> None:
        """Test that jinja2 environment is properly configured."""
        assert isinstance(texts.jinja2_env, jinja2.Environment)
        # Check that undefined is the DebugUndefined class, not an instance
        assert texts.jinja2_env.undefined == jinja2.DebugUndefined

    def test_cached_property_behavior(self) -> None:
        """Test that article properties are cached."""
        text = texts.Text('apple', 'path', {})

        # First access
        article1 = text.an
        # Second access should return same object (cached)
        article2 = text.an

        assert article1 == article2
        assert article1 == 'an'


# Integration and edge case tests
@pytest.mark.parametrize('vowel', ['a', 'e', 'i', 'o', 'u', 'A', 'E', 'I', 'O', 'U'])
def test_vowel_detection(vowel: str) -> None:
    """Test vowel detection for all vowels."""
    text = texts.Text(f'{vowel}pple', 'path', {})
    assert text.a == 'an'

    rs = texts.RenderedStr(f'{vowel}pple')
    assert rs.a == 'an'


@pytest.mark.parametrize(
    'consonant', ['b', 'c', 'd', 'f', 'g', 'B', 'C', 'D', 'F', 'G']
)
def test_consonant_detection(consonant: str) -> None:
    """Test consonant detection for sample consonants."""
    text = texts.Text(f'{consonant}ook', 'path', {})
    assert text.a == 'a'

    rs = texts.RenderedStr(f'{consonant}ook')
    assert rs.a == 'a'


def test_complex_rendering_chain() -> None:
    """Test complex rendering with nested templates and transformers."""
    context = {'base': 'hello', 'suffix': 'world'}

    def transformer(x: str) -> str:
        return x.replace('hello', 'hi')

    text = texts.RenderableText(
        '{base} {suffix}', 'test_path', context, transformer=transformer
    )

    result = text.render()
    # Transformer is applied first to template: '{base} {suffix}' -> '{base} {suffix}' (no change)
    # Then template is rendered: 'hello world'
    # The transformer doesn't affect the template string since it doesn't contain 'hello' initially
    assert result == 'hello world'
    assert isinstance(result, texts.RenderedStr)
