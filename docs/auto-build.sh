#!/usr/bin/env bash

# This script uses inotifywait to watch for changes in the current directory
# and its parents, and automatically rebuilds the Sphinx doc whenever a change
# is detected. Requires: sudo apt install inotify-tools.

DIR="."
make clean
make html
while inotifywait -r -e modify,create,delete,move "$DIR"; do
    make html
done
