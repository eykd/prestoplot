import atexit
import logging
import pathlib
import sys
import textwrap

import click

from . import storages, story


@click.group()
@click.option("--debug", is_flag=True)
@click.option("--pdb", is_flag=True)
def main(debug, pdb):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
    if pdb:

        @atexit.register
        def debug_on_exit():
            if hasattr(sys, "last_traceback"):
                try:
                    import ipdb as pdb
                except ImportError:
                    import pdb
                pdb.pm()


@main.command()
@click.argument("path")
@click.option(
    "--count", default=1, help="How many times to consult the oracle. Default 1."
)
@click.option(
    "--markov-start",
    default="",
    help="Characters to start any Markov chains with, e.g. 'Ba'. Default ''.",
)
@click.option(
    "--markov-chainlen", default=2, help="Length of Markov chain links. Default 2."
)
@click.option("--wrap", is_flag=True, help="Wrap text?")
@click.option(
    "--wrap-length", default=78, help="Maximum line length when wrapping text."
)
@click.option("--seed", help="Pre-seed the random generator.")
def run(path, count, markov_start, markov_chainlen, wrap, wrap_length, seed=None):
    """Parse and consult a YAML generative grammar oracle file.

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
        raise click.UsageError(
            f"--markov-start must be at least as long as "
            f"--markov-chainlen, currently {markov_chainlen}."
        )
    kwargs = dict(start_markov=markov_start, markov_chainlen=markov_chainlen)
    if seed is not None:
        kwargs["seed"] = seed

    path = pathlib.Path(path)
    storage = storages.FileStorage(path.parent)

    for n in range(count):
        result = story.render_story(storage, path.stem, **kwargs)
        if not wrap:
            print(result)
        else:
            for line in result.splitlines():
                if line.strip():
                    for new_line in textwrap.wrap(line, wrap_length):
                        print(new_line)
                else:
                    print(line)
        if n + 1 != count:
            print("\n---\n")
