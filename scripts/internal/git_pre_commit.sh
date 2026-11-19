#!/bin/sh

# Git pre-commit hook: lint the staged files.
exec make -s lint-all STAGED=1
