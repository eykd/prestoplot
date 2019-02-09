#!/bin/sh
set -x
./runtests.sh $@
watchmedo shell-command \
    --patterns="*.py" \
    --recursive \
    --command="./runtests.sh $@" \
    .
