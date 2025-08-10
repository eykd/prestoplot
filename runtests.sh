#!/bin/sh
set -e
set -x
exec uv run python -m pytest \
    --failed-first \
    --exitfirst \
    --cov=src \
    --cov-branch \
    --no-cov-on-fail $@
