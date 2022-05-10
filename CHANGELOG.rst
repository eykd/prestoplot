CHANGES
=======

0.5
---

* Allow instances of ``random.Random()`` as seeds.
* Rename ``ChangeLog`` to ``CHANGELOG.rst``, include in ``long_description``.
* Changelog is now manually written, instead of derived from git logs.

0.4
---

* Fixed major instability of markov generator in the presence of a seed.


0.3.4
-----

* Update packaging and requirements

0.3.3
-----

* Improved badge
* Update README w/ build status and better lede
* Update dev and test requirements
* Allow customization of start key when rendering story
* Add python 3.8 to tests

0.3.2
-----

* Remove more debug logging

0.3.1
-----

* Remove debug logging
* Add extra whitespace
* Add known third parties to isort cfg
* Add twine dev dependency

0.3
---

* Add msgpack-compiled test data
* Add new more efficient storages
* Improve runtests invocation
* Tailor flake8 exclusions
* Pin versions; add msgpack
* Add some debug logging
* Add pyyaml requirement
* Revert "Use strictyaml instead of yaml"
* Add dev and test requirements
* Move prestplot package into src/
* Add Travis CI integration
* Add .isort.cfg
* Use collections.abc in prep for python 3.8
* Use strictyaml instead of yaml
* Add requirements.txt
* Use longer python environ specifiers for tox.ini
* Add project URLs

0.2
---

* A whole bunch of refactoring
* Improve dev and test harness w/ dev requirements and test scripts

0.1.3
-----

* Add extended documentation on generative grammar syntax
* Further README improvements

0.1.2
-----

* Improve README

0.1.1
-----

* Add ``--seed`` option to CLI for pre-seeding oracles
* Add install/usage documentation to README
* Add documentation to CLI

0.1
---

* Add basic test to exercise render\_story()
* Fix email, summary
* Remove future features from setup.cfg
* Finish writing README
* Fix link in README
* Initial commit
