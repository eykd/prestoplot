#!/bin/sh
set -e
set -x

# Automatically reformat code, but ignore breakpoint():
exec uv run ruff check --fix --ignore T100
exec uv run ruff format

exec uv run python -m pytest \
    --failed-first \
    --exitfirst \
    --cov=src \
    --cov-branch \
    --no-cov-on-fail $@
