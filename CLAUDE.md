# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PrestoPlot is a Python library and CLI tool for text generation using YAML-based generative grammars. It supports idea generation, name generation, and story creation through a template system inspired by Tracery.

## Development Commands

### Testing
- Run tests: `./runtests.sh` (uses uv and pytest with coverage)
- Watch tests: `./watchtests.sh` (auto-runs tests on file changes)
- Single test: `uv run python -m pytest tests/test_specific.py`
- Test with tox: `tox` (tests across multiple Python versions)

### Linting and Code Quality
- Lint code: `uv run ruff check src/ tests/`
- Format code: `uv run ruff format src/ tests/`
- Type checking: Not configured (no mypy or similar in dependencies)

### Building and Installation
- Install in development mode: `uv sync --dev`
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
