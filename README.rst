PrestoPlot
==========

.. image:: https://travis-ci.org/eykd/prestoplot.svg?branch=master
    :target: https://travis-ci.org/eykd/prestoplot
    :alt: Build status

A library and tool for text generation, inspired by Tracery.

PrestoPlot is a tool for idea generation, name generation, and other tomfoolery
when you should otherwise be writing.

Goes best with the oracles from the `PrestoPlot Oracles repository`_.

.. _PrestoPlot Oracles repository: https://github.com/eykd/prestoplot-oracles/

Install
-------

PrestoPlot is available from PyPI::

    pip install prestoplot

Usage
-----

PrestoPlot may be invoked with the ``presto`` CLI script::

    presto --help

The "oracle" consulted directly must include a ``Begin:`` stanza::

    $ cat names.yaml
    Begin:
      - "{Name}"

    Name:
      - George
      - Martha

    $ presto run names.yaml
    George


Generative Grammars
-------------------

The main feature right now is a generative grammar that uses a simple YAML-based
language and `Python f-string syntax`_ to create `"oracles"`_ for idea generation.

.. _"oracles": https://github.com/eykd/prestoplot-oracles/
.. _Python f-string syntax: https://realpython.com/python-f-strings/

The best way to learn the grammar is to look at examples. We'll consider the
`YAML for generating a Pirate story`_, which begins like this::

  include:
    - setup

  Begin:
    - "{PiratesOracle}"

.. _YAML for generating a Pirate story: https://github.com/eykd/prestoplot-oracles/blob/master/oracles/pirates.yaml

There is the ``Begin:`` stanza that we require to directly consult an oracle.
This contains a list of strings that may be chosen from by the random generator.
In this case, we have an f-string template that invokes ``PiratesOracle``. We
find that below::

  PiratesOracle:
    - |
      {Setup}
      - {Letters.One}
      - {Letters.Two}
      - {Letters.Three}
      - {Letters.Four}
    - |
      {Setup}
      - {CutlassDagger.One}
      - {CutlassDagger.Two}
      - {CutlassDagger.Three}
      - {CutlassDagger.Four}

We see another list of strings. ``|`` followed by an indented new line means to
treat what follows at that indentation level as a literal string, instead of
YAML::

  {Setup}
    - {Letters.One}
    - {Letters.Two}
    - {Letters.Three}
    - {Letters.Four}

So this is a string with a Markdown-style list, instead of a YAML list, all
because of the ``|``.

So here we see ``Setup`` invoked, and then ``Letters`` invoked four times.
``Letters`` is defined below::

  Letters:
    - mode: pick
    - "Betrayal and treachery!"
    - "Captured {Nationality} charts, carefully copied, and used by the Royal Navy."
    - "Dolphins, seen frolicking in the bow-wake of a ship, perhaps leading it toward its goal."
    - "Flotsam and jetsam, washed ashore after a sea-battle."
    - "Fo’c’sle gossip blaming the ship’s misfortunes on a crewman who killed an albatross."
    - "Forged documents, implying that their bearer speaks for the Crown."
    - "Hidden reefs, which at low tide endanger any ship that passes over them."

We have another list, containing piratical thematic elements. ``mode: pick``
tells the generator to randomly pick from among them, then remove that option
from consideration for future picks. The normal mode is ``reuse`` which allows
list items to be re-used by the generator. Another mode, ``markov``, tells the
generator to build a Markov chain from the list, as with `these name lists`_.

.. _these name lists: https://github.com/eykd/prestoplot-oracles/blob/master/oracles/names-markov.yaml

Going back to ``PiratesOracle``, we see that ``Letters`` is invoked four times,
each time with a new *key*. The values of the keys are important only to the
reader. Each new key acts as a fresh seed for the random generator when working
inside that stanza. For instance, if ``{Letters.One}`` picked the element
``"Captured {Nationality} charts, carefully copied, and used by the Royal
Navy."``, the value ``One`` provides the seed for picking a ``Nationality``,
say, ``English``. Later, if ``{Letters.Two}`` encounters another element
containing ``{Nationality}``, the key ``Two`` will provide a different seed for
picking a nationality the second time.

The plot thickens when we examine the ``include`` stanza, which includes the
``setup.yaml`` file `next door`_. This file includes more files. We will next examine `characters.yaml`_.

.. _next door: https://github.com/eykd/prestoplot-oracles/blob/master/oracles/setup.yaml
.. _characters.yaml: https://github.com/eykd/prestoplot-oracles/blob/master/oracles/characters.yaml

Inside of ``characters.yaml`` we find this fascinating set of stanzas::

  Sex:
    - male
    - female

  He:
    - >
      {'She' if Sex[key] == 'female' else 'He'}
  his:
    - >
      {'her' if Sex[key] == 'female' else 'his'}
  His:
    - >
      {'Her' if Sex[key] == 'female' else 'His'}
  hero:
    - "{'heroine' if Sex[key] == 'female' else 'hero'}"


With this set of tools, we could write the following string::

  That {hero.protag}! {He.protag} sure loves {his.protag} mom.

The long and short of it is that, depending on the sex of the protagonist, this
will render either::

  That heroine! She sure loves her mom.

or::

  That hero! He sure loves his mom.

So here we see that inside of f-string syntax, we can use pythonic expressions,
and the variable ``key`` contains the key from the outer scope: ``{He.protag}``
assigns the value ``"protag"`` to ``key``. ``{Sex[key]}`` will reliably produce
the same result for the same key (assuming the same initial seed).

Everything else is just YAML syntax and Python f-string expressions.


About
-----

I wrote PrestoPlot to support idea generation and name generation for my
pulp-inspired science fiction space opera series, `Salvage of Empire`_:

  When his brother-in-law threatens to reveal his terrible secret, Director Kolteo
  Ais must sacrifice everything he has worked for to save the Galactic Empire—and
  his marriage—from utter ruin.

.. _Salvage of Empire: https://eykd.net/salvage/

