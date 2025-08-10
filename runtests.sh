#!/bin/sh
set -e
set -x

# Automatically reformat code, but ignore breakpoint():
uv run ruff check --fix --ignore T100
uv run ruff format

uv run python -m pytest \
    --failed-first \
    --exitfirst \
    --cov=src \
    --cov-branch \
    --no-cov-on-fail $@
