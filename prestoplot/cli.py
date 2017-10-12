import logging

import click

from . import story


@click.group()
@click.option('--debug', is_flag=True)
def main(debug):
    logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)


@main.command()
@click.argument('path')
@click.option('--count', default=1)
@click.option('--markov-start', default='')
@click.option('--markov-chainlen', default=2)
def run(path, count, markov_start, markov_chainlen):
    if markov_start and len(markov_start) < markov_chainlen:
        raise click.UsageError(f'--markov-start must be at least as long as --markov-chainlen, currently {markov_chainlen}.')
    for n in range(count):
        print(story.render_story(
            path,
            start_markov=markov_start,
            markov_chainlen=markov_chainlen,
        ))
        if n + 1 != count:
            print('\n---\n')
