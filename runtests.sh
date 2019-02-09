#!/bin/sh
set -e
set -x
pytest --flake8 tests prestoplot --cov=prestoplot $@
