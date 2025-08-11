# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PrestoPlot is a Python library and CLI tool for text generation using YAML-based generative grammars. It supports idea generation, name generation, and story creation through a template system inspired by Tracery.

## Development Commands

### Testing
- Run tests: `./runtests.sh` (uses uv and pytest with coverage)
- Single test: `uv run python -m pytest tests/test_specific.py`
- Test with tox: `tox` (tests across multiple Python versions)

### Linting and Code Quality
- Lint code: `uv run ruff check src/ tests/`
- Format code: `uv run ruff format src/ tests/`
- Type checking: Not configured (but we do use type annotations, lightly checked by ruff)

### Building and Installation
- Install in development mode: `uv sync --all-groups`
- Build package: `uv build`
- Run CLI: `uv run presto --help`

## Core Architecture

### CLI Entry Point
- Main CLI script: `presto` command (defined in `src/prestoplot/cli.py`)
- Two main commands:
  - `presto run <file.yaml>`: Generate text from YAML grammar files
  - `presto http <file.yaml>`: Serve HTTP endpoint for text generation

### Core Components

**Storage Layer** (`storages.py`):
- `FileStorage`: Loads YAML grammar files from filesystem
- `CompilingFileStorage`: Caches compiled grammars as MessagePack files

**Grammar Processing** (`grammars.py`):
- Parses YAML grammar files with `include` support
- Supports f-string and Jinja2 template rendering
- Handles recursive grammar includes

**Story Rendering** (`story.py`):
- Main entry point: `render_story(storage, name, start="Begin", seed=None, **kwargs)`
- Requires `Begin:` stanza in grammar files

**Context Management** (`contexts.py`):
- Manages random seeds and generation context
- Provides deterministic generation with same seeds

**Text Processing** (`texts.py`):
- Template rendering engines (f-string and Jinja2)
- Text generation utilities

**Additional Features**:
- `markov.py`: Markov chain text generation
- `db.py`: Database utilities for grammar storage
- `http.py`: HTTP server for web-based generation

### Grammar File Format
- YAML-based with Python f-string syntax
- Required `Begin:` stanza as entry point
- Support for `include:` to compose grammar files
- Modes: `reuse` (default), `pick` (no replacement), `markov` (chain generation)
- Seeded generation using keys (e.g., `{Name.character1}`)

## Test Structure
- Unit tests in `tests/` directory
- Test data in `tests/data/` (sample YAML grammars)
- Coverage reporting enabled by default


## When asked to create new conventions

When asked to create a new convention (`CLAUDE.md`), add a second-level
heading section to this document, `CLAUDE.md`.

* Name the new convention heading with a short, descriptive title.
* Use the first line of the section to elaborate on the "When..." of the heading.
* Use bullet points to organize further details for the convention.
* Use full imperative sentences.
* Keep new conventions short and to the point.
* Use short examples for complex conventions.

## Python code style and quality

When writing or editing Python code (`*.py`), follow these quality standards:

* Use PEP8 style with CamelCase for class names and snake\_case for variables/functions.
* Include type annotations for all functions, methods, and complex structures.
* Add Google Style docstrings to all packages, modules, functions, classes, and methods.
* Run code quality tools:

  * Format: `uv run ruff format`
  * Lint: `uv run ruff check --fix`


## Testing

When writing Python code (`*.py`), follow these testing practices:

* Write tests first for each change using pytest.
* Organize tests in a dedicated `tests/` folder in the project root.
* Name test files by package and module, omitting the root `cloudmarch` package name.

  * Example: `tests/test_config_loader.py` tests `src/cloudmarch/config/loader.py`
* Use descriptive names for test functions and methods.
* Group related tests in test classes.
* Use fixtures for complex setup.
* Aim for 100% test coverage for code under `src/`.
* When writing tests, move common fixtures to `tests/conftest.py`.
* Run tests with `./scripts/runtests.sh` (which accepts normal `pytest` arguments and flags).

  * Example: `./scripts/runtests.sh tests/test_config_loader.py`

## Test organization with classes

When organizing tests in pytest, group related tests using `TestX` classes:

* Use `TestX` classes to group tests for the same module, function, or behavior.
* Name test classes with descriptive titles like `TestGrammarParser` or `TestFileStorage`.
* Do not inherit from `unittest.TestCase` since pytest handles plain classes.
* Place setup and teardown logic in `setup_method` and `teardown_method`.
* Example:
  ```python
  class TestGrammarParser:
      @pytest.fixture
      def parser(self) -> GrammarParser:
          return GrammarParser()

      def test_parses_simple_grammar(self, parser: GrammarParser) -> None:
          result = parser.parse("Begin: hello")
          assert result["Begin"] == ["hello"]
  ```

## Unit testing with pytest

When writing unit tests for Python libraries, follow these pytest best practices:

* Test public APIs and behaviors, not implementation details.
* Focus on testing function contracts: inputs, outputs, and side effects.
* Use pytest's built-in `assert` statements rather than unittest-style assertions.
* Structure tests with arrange-act-assert pattern for clarity.
* Test edge cases: empty inputs, None values, boundary conditions, and error states.
* Use parametrized tests for testing multiple similar cases:
  ```python
  @pytest.mark.parametrize("input_val,expected", [(1, 2), (3, 4)])
  def test_increment(input_val, expected):
      assert increment(input_val) == expected
  ```
* Mock external dependencies using `pytest-mock` or `unittest.mock`.
* Test exception handling explicitly with `pytest.raises()`:
  ```python
  def test_raises_value_error():
      with pytest.raises(ValueError, match="invalid input"):
          parse_config("bad_input")
  ```
* Use fixtures for test data and setup, preferring function-scoped fixtures.
* Test one behavior per test function to maintain clarity and isolation.
* Avoid testing private methods directly; test through public interfaces.
* Do not test third-party library functionality; focus on your code's usage of it.

## Test failure resolution

When tests fail during development, always fix them immediately:

* Stop all development work until failing tests are addressed.
* Identify the root cause of test failures before making changes.
* Fix the underlying issue rather than updating tests to match broken behavior.
* Ensure all tests pass before continuing with new development.
* Run the full test suite after fixes to prevent regression.
* Update mocks, test data, or test logic only when the intended behavior has genuinely changed.
* Never ignore or skip failing tests without explicit justification.

## Variable naming

When naming variables in Python code, follow these naming practices:

* Use concise but descriptive variable names that clearly indicate purpose.
* Avoid single-character names except in the simplest comprehensions.
* Follow snake\_case for all variables and functions.
* Use plural forms for collections and singular for items.
* Prefix boolean variables with verbs like `is_`, `has_`, or `should_`.

## Exception style

When raising exceptions in Python code, follow these practices:

* Do not raise `Exception`, `RuntimeError`, or any built-in base exception.
* Define specific exceptions in `src/cloudmarch/exceptions.py`.
* Use `raise NewError from original_error` for context chaining.
* Avoid interpolated strings in exception messages.
* Attach context as explicit parameters to exception classes.
* Example:

  ```python
  try:
      ...
  except ValueError as exc:
      raise MissingBucketError("S3 bucket missing", bucket_name) from exc
  ```

## TYPE\_CHECKING blocks

When using `TYPE_CHECKING` imports in Python:

* Always include `# pragma: no cover` to exclude them from test coverage.
* Place all type-only imports inside the block.
* Example:

  ```python
  from typing import TYPE_CHECKING

  if TYPE_CHECKING:  # pragma: no cover
      from cloudmarch.config.types import DeployConfig
  ```

## Test coverage pragmas

When writing Python code with untestable defensive programming constructs:

* Use `# pragma: no cover` for lines that cannot be practically tested.
* Use `# pragma: no branch` for branch conditions that cannot be practically tested.
* Apply pragmas to defensive re-raises, impossible conditions, and safety checks.
* Examples:

  ```python
  except DeploymentError:
      raise  # pragma: no cover - defensive re-raise

  if some_impossible_condition:  # pragma: no branch
      raise RuntimeError("This should never happen")

  except Exception as exc:
      if isinstance(exc, SpecificError):  # pragma: no branch
          raise  # pragma: no cover
  ```

## Git commit style

When committing changes to the repository, use conventional commit format:

* Use the format: `<type>(<scope>): <description>`
* Common types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`
* Keep the first line under 50 characters
* Use present tense imperative mood ("add feature" not "added feature")
* Examples:
  * `feat(cli): add new grammar validation command`
  * `fix(storage): handle missing YAML files gracefully`
  * `docs: update installation instructions`
  * `test(grammars): add tests for include functionality`
