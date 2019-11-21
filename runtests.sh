#!/bin/sh
set -e
set -x
pytest \
    --failed-first \
    --exitfirst \
    --cov=src \
    --cov-branch \
    --no-cov-on-fail $@
