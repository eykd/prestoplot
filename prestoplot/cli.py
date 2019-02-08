import logging

import click

from . import story


@click.group()
@click.option('--debug', is_flag=True)
def main(debug):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)


@main.command()
@click.argument('path')
@click.option('--count', default=1, help="How many times to consult the oracle. Default 1.")
@click.option('--markov-start', default='', help="Characters to start any Markov chains with, e.g. 'Ba'. Default ''.")
@click.option('--markov-chainlen', default=2, help="Length of Markov chain links. Default 2.")
@click.option('--seed', help="Pre-seed the random generator.")
def run(path, count, markov_start, markov_chainlen, seed=None):
    '''Parse and consult a YAML generative grammar oracle file.

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

    '''
    if markov_start and len(markov_start) < markov_chainlen:
        raise click.UsageError(f'--markov-start must be at least as long as --markov-chainlen, currently {markov_chainlen}.')
    kwargs = dict(
        start_markov=markov_start,
        markov_chainlen=markov_chainlen,
    )
    if seed is not None:
        kwargs['seed'] = seed

    for n in range(count):
        print(story.render_story(path, **kwargs))
        if n + 1 != count:
            print('\n---\n')
