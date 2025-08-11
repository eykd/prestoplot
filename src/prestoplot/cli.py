"""Command-line interface for PrestoPlot."""

from __future__ import annotations

import atexit
import logging
import pathlib
import sys
import textwrap

import click

from . import storages, story


@click.group()
@click.option('--debug', is_flag=True)
@click.option('--pdb', is_flag=True)
def main(debug: bool, pdb: bool) -> None:  # noqa: FBT001
    """Main CLI group for PrestoPlot commands.

    Args:
        debug: Enable debug logging
        pdb: Enable post-mortem debugging on exceptions

    """
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    if pdb:

        @atexit.register
        def debug_on_exit() -> None:
            """Enter debugger on exit if an exception occurred."""
            if hasattr(sys, 'last_traceback'):  # pragma: no branch
                import pdb

                pdb.pm()


@main.command()
@click.argument(
    'path',
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    '--count', default=1, help='How many times to consult the oracle. Default 1.'
)
@click.option(
    '--markov-start',
    default='',
    help="Characters to start any Markov chains with, e.g. 'Ba'. Default ''.",
)
@click.option(
    '--markov-chainlen', default=2, help='Length of Markov chain links. Default 2.'
)
@click.option('--wrap', is_flag=True, help='Wrap text?')
@click.option(
    '--wrap-length', default=78, help='Maximum line length when wrapping text.'
)
@click.option('--seed', help='Pre-seed the random generator.')
def run(
    path: pathlib.Path,
    count: int,
    markov_start: str,
    markov_chainlen: int,
    wrap: bool,  # noqa: FBT001
    wrap_length: int,
    seed: str | None = None,
) -> None:
    r"""Parse and consult a YAML generative grammar oracle file.

    The "oracle" consulted directly must include a `Begin:` stanza.

    Example:
    \b
    $ cat names.yaml
    Begin:
      - "{Name}"
    \b
    Name:
      - George
      - Martha
    \b
    $ presto run names.yaml
    George

    """
    if markov_start and len(markov_start) < markov_chainlen:
        msg = (
            f'--markov-start must be at least as long as '
            f'--markov-chainlen, currently {markov_chainlen}.'
        )
        raise click.UsageError(msg)
    kwargs = {'start_markov': markov_start, 'markov_chainlen': markov_chainlen}
    if seed is not None:
        kwargs['seed'] = seed

    storage = storages.FileStorage(path.parent)

    for n in range(count):
        result = story.render_story(storage, path.stem, **kwargs)
        if not wrap:
            click.echo(result)
        else:
            for line in result.splitlines():
                if line.strip():
                    for new_line in textwrap.wrap(line, wrap_length):
                        click.echo(new_line)
                else:  # pragma: no cover
                    click.echo(line)
        if n + 1 != count:
            click.echo('\n---\n')


@main.command()
@click.argument(
    'path',
    type=click.Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
        readable=True,
        resolve_path=True,
        path_type=pathlib.Path,
    ),
)
@click.option(
    '--markov-start',
    default='',
    help="Characters to start any Markov chains with, e.g. 'Ba'. Default ''.",
)
@click.option(
    '--markov-chainlen', default=2, help='Length of Markov chain links. Default 2.'
)
@click.option('--port', default=5555, help='Port to listen at for HTTP requests.')
def http(
    path: pathlib.Path, markov_start: str, markov_chainlen: int, port: int
) -> None:
    r"""Parse a YAML generative grammar oracle file and serve it at the given port.

    The "oracle" consulted directly must include a `Begin:` stanza.

    Example:
    \b
    $ cat names.yaml
    Begin:
      - "{Name}"
    \b
    Name:
      - George
      - Martha
    \b
    $ presto run names.yaml
    George

    """
    if markov_start and len(markov_start) < markov_chainlen:
        msg = (
            '--markov-start must be at least as long as '
            f'--markov-chainlen, currently {markov_chainlen}.'
        )
        raise click.UsageError(msg)

    from http.server import HTTPServer

    from . import http

    logging.basicConfig()
    http_server = HTTPServer(
        ('', port), http.create_handler(path, markov_start, markov_chainlen)
    )
    click.echo(f'Serving on http://localhost:{port}')
    http_server.serve_forever()
