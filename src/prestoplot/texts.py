"""Text rendering and template processing."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

import jinja2
from funcy import cached_property, identity, isa

if TYPE_CHECKING:
    from collections.abc import Callable

jinja2_env = jinja2.Environment(undefined=jinja2.DebugUndefined)  # noqa: S701

logger = logging.getLogger(__name__)


def render_ftemplate(
    tmpl: str, grammar_path: str, context: dict[str, Any]
) -> RenderedStr:
    """Render template using Python f-string evaluation.

    Args:
        tmpl: Template string with f-string syntax
        grammar_path: Path identifier for error reporting
        context: Grammar context for variable substitution

    Returns:
        RenderedStr with evaluated template content

    Raises:
        Exception: If template evaluation fails

    """
    global_ctx = {**context}
    local_ctx = {'result': tmpl}
    try:
        exec("result = eval(f'''f{result!r}''')", global_ctx, local_ctx)  # noqa: S102
    except Exception:
        logger.exception('Could not render template %s: %s', grammar_path, tmpl)
        raise
    return RenderedStr(local_ctx['result'])


def render_jinja2(tmpl: str, grammar_path: str, context: dict[str, Any]) -> RenderedStr:
    """Render template using Jinja2 template engine.

    Args:
        tmpl: Jinja2 template string
        grammar_path: Path identifier for error reporting
        context: Grammar context for variable substitution

    Returns:
        RenderedStr with rendered template content

    Raises:
        ValueError: If Jinja2 template rendering fails

    """
    try:
        return RenderedStr(jinja2_env.from_string(tmpl).render(context))
    except jinja2.TemplateError as exc:
        logger.exception('Could not render Jinja2 template: %s, %s', grammar_path, tmpl)
        msg = f'Could not render Jinja2 template ({exc}): '
        if hasattr(exc, 'source') and exc.source:
            lineno = exc.lineno
            line = exc.source.splitlines()[lineno - 1]
            logger.exception('Line %s: %s', lineno, line)
            msg += f'\n{grammar_path}, line {lineno}'
            msg += f'\n--> {line}'
        else:  # pragma: no cover
            msg += f'\n{grammar_path}'
            msg += f'\n{tmpl}'
        raise ValueError(msg) from exc


class Text:
    """Base text class with article generation and string delegation.

    Provides 'a'/'an' article properties and delegates string methods
    to the underlying value.
    """

    vowels: ClassVar[set[str]] = set('aeiou')

    def __init__(
        self,
        value: Any,  # noqa: ANN401
        grammar_path: str,
        context: dict[str, Any],
        transformer: Callable[[Any], Any] = identity,
    ) -> None:
        """Initialize text object.

        Args:
            value: Text content
            grammar_path: Path identifier for the grammar stanza
            context: Grammar rendering context
            transformer: Function to transform the value during rendering

        """
        self.value = value
        self.context = context
        self.grammar_path = grammar_path
        self.transformer = transformer

    @cached_property
    def an(self) -> str:
        """Get appropriate indefinite article ('a' or 'an').

        Returns:
            'an' if text starts with vowel, 'a' otherwise

        """
        if str(self.value)[0].lower() in self.vowels:
            return 'an'
        return 'a'

    a = an

    @cached_property
    def An(self) -> str:  # noqa: N802
        """Get capitalized indefinite article ('A' or 'An').

        Returns:
            'An' if text starts with vowel, 'A' otherwise

        """
        return self.an.capitalize()

    A = An

    def __str__(self) -> str:
        """Get string representation by rendering.

        Returns:
            Rendered string content

        """
        return self.render()

    def __repr__(self) -> str:
        """Get string representation of underlying value.

        Returns:
            repr() of the underlying value

        """
        return repr(self.value)

    def __getattr__(self, attr: str) -> Any:  # noqa: ANN401
        """Delegate string methods to underlying value.

        Args:
            attr: Attribute name to access

        Returns:
            Attribute value from underlying string value

        """
        if hasattr(str, attr):
            return getattr(self.value, attr)
        return super().__getattr__(attr)

    def __hash__(self) -> int:
        """Get hash of underlying value.

        Returns:
            Hash of the underlying value

        """
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        """Compare with other object as strings.

        Args:
            other: Object to compare with

        Returns:
            True if string representations are equal

        """
        return str(self) == other

    def render(self, context: dict[str, Any] | None = None) -> RenderedStr:  # noqa: ARG002
        """Render text by applying transformer.

        Args:
            context: Rendering context (unused in base class)

        Returns:
            RenderedStr with transformed value

        """
        return RenderedStr(self.transformer(self.value))


class RenderableText(Text):
    """Text class that supports template rendering.

    Extends Text with configurable template rendering strategies.
    """

    def __init__(
        self,
        value: Any,  # noqa: ANN401
        grammar_path: str,
        context: dict[str, Any],
        transformer: Callable[[Any], Any] = identity,
        render_strategy: Callable[
            [str, str, dict[str, Any]], RenderedStr
        ] = render_ftemplate,
    ) -> None:
        """Initialize renderable text.

        Args:
            value: Text content with template syntax
            grammar_path: Path identifier for the grammar stanza
            context: Grammar rendering context
            transformer: Function to transform the value during rendering
            render_strategy: Template rendering function to use

        """
        super().__init__(value, grammar_path, context, transformer=transformer)
        self._render = render_strategy

    def __str__(self) -> str:
        """Get string representation by rendering with context.

        Returns:
            Rendered string content

        """
        return self.render(self.context)

    def render(self, context: dict[str, Any] | None = None) -> RenderedStr:
        """Render text using configured template strategy.

        Args:
            context: Optional rendering context (defaults to instance context)

        Returns:
            RenderedStr with template-rendered content

        """
        return RenderedStr(
            self._render(super().render(), self.grammar_path, context or self.context)
        )


is_text = isa(Text)
"""Function to check if an object is a Text instance."""


class RenderedStr(str):  # noqa: SLOT000
    """String subclass with article generation methods.

    Extends str with 'a'/'an' article properties for grammatical correctness.
    """

    vowels: ClassVar[set[str]] = set('aeiou')

    @cached_property
    def an(self) -> str:
        """Get appropriate indefinite article ('a' or 'an').

        Returns:
            'an' if string starts with vowel, 'a' otherwise

        """
        if self[0].lower() in self.vowels:
            return 'an'
        return 'a'

    a = an

    @cached_property
    def An(self) -> str:  # noqa: N802
        """Get capitalized indefinite article ('A' or 'An').

        Returns:
            'An' if string starts with vowel, 'A' otherwise

        """
        return self.an.capitalize()

    A = An
