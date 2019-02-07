import logging

import click

from .plotto import plotter
from .plotto import grapher
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


@main.command()
@click.argument('path')
@click.option('--points', default=None, type=int)
def ratchet(path, points=None):
    storyline = story.ratchet_story(
        path,
        max_yield=points,
    )
    for point in storyline:
        print(point + '\n')


@main.command()
def plotto():
    print(plotter.generate_plot())


@main.command()
@click.argument('inpath')
@click.argument('outpath')
def graph(inpath, outpath):
    import networkx as nx

    graph = grapher.graph_plotto(inpath)
    nx.write_graphml(graph, outpath)
