"""Grammar file parsing and processing."""

import textwrap
from collections.abc import Callable
from typing import Any

from funcy import is_list, is_mapping, isa

from . import db, texts

is_bool = isa(bool)


def parse_grammar_file(
    storage: Any,  # noqa: ANN401
    grammar_path: str,
    context: Any,  # noqa: ANN401
    included: set[str] | None = None,
) -> Any:  # noqa: ANN401
    """Parse a grammar file and its includes into the context.

    Args:
        storage: Storage backend for loading grammar files
        grammar_path: Path/name of the grammar file to parse
        context: Current grammar context to populate
        included: Set of already included files (for cycle detection)

    Returns:
        Updated context with parsed grammar data

    """
    if included is None:
        included = {grammar_path}
    else:
        if grammar_path in included:
            return context
        included.add(grammar_path)

    doc = storage.resolve_module(grammar_path)
    context = parse_includes(
        storage, grammar_path, doc.pop('include', ()), context, included
    )

    render_strategy = parse_render_strategy(
        doc.pop('render', 'ftemplate'), grammar_path
    )

    return parse_data(doc, grammar_path, context, render_strategy=render_strategy)


def parse_render_strategy(
    render_mode: str, grammar_path: str
) -> Callable[[str, str, Any], Any]:
    """Parse and return the appropriate template rendering function.

    Args:
        render_mode: Name of the render strategy ('ftemplate' or 'jinja2')
        grammar_path: Grammar file path (for error messages)

    Returns:
        Rendering function for the specified strategy

    Raises:
        ValueError: If render_mode is not recognized

    """
    if render_mode == 'ftemplate':
        return texts.render_ftemplate
    if render_mode == 'jinja2' or render_mode == 'jinja':
        return texts.render_jinja2
    raise ValueError('Unrecognized render strategy', render_mode, grammar_path)


def parse_includes(
    storage: Any,  # noqa: ANN401
    grammar_path: str,  # noqa: ARG001
    includes: list[str],
    context: Any,  # noqa: ANN401
    included: set[str],
) -> Any:  # noqa: ANN401
    """Process include directives to load additional grammar files.

    Args:
        storage: Storage backend for loading grammar files
        grammar_path: Current grammar file path (unused but kept for signature)
        includes: List of grammar files to include
        context: Current grammar context
        included: Set of already included files

    Returns:
        Updated context with included grammar data

    """
    for include in includes:
        context = parse_grammar_file(storage, include, context, included)
    return context


def parse_data(
    data: dict[str, Any],
    grammar_path: str,
    context: Any,  # noqa: ANN401
    render_strategy: Callable[[str, str, Any], Any] = texts.render_ftemplate,
) -> Any:  # noqa: ANN401
    """Parse grammar data into context objects.

    Args:
        data: Dictionary of grammar stanza data
        grammar_path: Path of the grammar file being parsed
        context: Current grammar context
        render_strategy: Template rendering function to use

    Returns:
        Updated context with parsed stanza data

    """
    for key, value in data.items():
        context[key] = parse_value(
            value, f'{grammar_path}:{key}', context, render_strategy=render_strategy
        )

    return context


def get_list_setting(value: list[Any], grammar_path: str) -> tuple[str, list[Any]]:  # noqa: ARG001
    """Extract mode setting from list configuration.

    Args:
        value: List value that may contain a mode setting as first element
        grammar_path: Grammar file path (unused but kept for signature)

    Returns:
        Tuple of (mode, cleaned_value) where mode defaults to 'reuse'

    """
    mode = 'reuse'
    if value and is_mapping(value[0]) and len(value[0]) == 1 and 'mode' in value[0]:
        mode = value.pop(0)['mode']
    return mode, value


def parse_value(
    value: list[Any] | dict[str, Any] | bool | str,  # noqa: FBT001
    grammar_path: str,
    context: Any,  # noqa: ANN401
    render_strategy: Callable[[str, str, Any], Any] = texts.render_ftemplate,
) -> Any:  # noqa: ANN401
    """Parse a grammar value into appropriate database/text objects.

    Args:
        value: Raw value from grammar file (list, dict, string, bool)
        grammar_path: Path identifier for the grammar stanza
        context: Current grammar context
        render_strategy: Template rendering function to use

    Returns:
        Appropriate database or text object based on value type and mode

    """
    if is_list(value):
        mode, value = get_list_setting(value, grammar_path)
        if mode == 'reuse':
            return db.Database(
                db.choose([
                    parse_value(
                        v, grammar_path, context, render_strategy=render_strategy
                    )
                    for v in value
                ]),
                grammar_path,
                context,
            )
        if mode == 'pick':
            return db.Database(
                db.pick([
                    parse_value(
                        v, grammar_path, context, render_strategy=render_strategy
                    )
                    for v in value
                ]),
                grammar_path,
                context,
            )
        if mode == 'markov':
            return db.Database(
                db.markovify([texts.RenderedStr(v) for v in value]),
                grammar_path,
                context,
            )
        if mode == 'ratchet':
            return db.Database(
                db.ratchet([texts.RenderedStr(v) for v in value]), grammar_path, context
            )
        if mode == 'list':
            return db.Datalist(
                grammar_path, context, [texts.RenderedStr(v) for v in value]
            )
    elif is_mapping(value):
        return db.Databag(
            grammar_path,
            context,
            {
                k: parse_value(
                    v, grammar_path, context, render_strategy=render_strategy
                )
                for k, v in value.items()
            },
        )
    elif is_bool(value):
        return value
    else:
        return texts.RenderableText(
            fix_text(value), grammar_path, context, render_strategy=render_strategy
        )
    return None  # pragma: no cover


def fix_text(text: str) -> str:
    """Clean up text by removing common indentation and trailing whitespace.

    Args:
        text: Raw text string from grammar file

    Returns:
        Cleaned text with dedented and stripped whitespace

    """
    return textwrap.dedent(text).strip()
