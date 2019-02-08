PrestoPlot
==========

Boom! Instant plot!

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

PrestoPlot may be invoked with the `presto` CLI script::

    presto --help

The "oracle" consulted directly must include a `Begin:` stanza::

    $ cat names.yaml
    Begin:
      - "{Name}"

    Name:
      - George
      - Martha

    $ presto run names.yaml
    George


About
-----

I wrote PrestoPlot to support idea generation and name generation for my
pulp-inspired science fiction space opera series, `Salvage of Empire`_:

  When his brother-in-law threatens to reveal his terrible secret, Director Kolteo
  Ais must sacrifice everything he has worked for to save the Galactic Empire—and
  his marriage—from utter ruin.

.. _Salvage of Empire: https://eykd.net/salvage/

The main feature right now is a generative grammar that uses a simple YAML-based
language and `Python f-string syntax` to create "oracles" for idea generation.

.. _PrestoPlot Oracles: https://github.com/eykd/prestoplot-oracles/
.. _Python f-string syntax: https://realpython.com/python-f-strings/
