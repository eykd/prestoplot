#!/usr/bin/env bash
set -x
while sleep 1; do find src/ -iname '*.py' | entr -d ./runtests.sh; done
