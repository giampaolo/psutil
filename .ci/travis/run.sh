#!/bin/bash

set -e
set -x

PYVER=`python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'`

# setup macOS
if [[ "$(uname -s)" == 'Darwin' ]]; then
    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi
    pyenv activate psutil
fi

make clean
make install PYTHON=python

echo "Testing on Python $PYVER"
$PYTHON -m pip freeze

# run tests (with coverage)
if [[ $PYVER == '2.7' ]] && [[ "$(uname -s)" != 'Darwin' ]]; then
    PSUTIL_TESTING=1 python -Wa -m coverage run psutil/tests/runner.py
else
    make test PYTHON=python
fi

if [ "$PYVER" == "2.7" ] || [ "$PYVER" == "3.6" ]; then
    # run mem leaks test
    make test-memleaks PYTHON=python
    # run linter (on Linux only)
    if [[ "$(uname -s)" != 'Darwin' ]]; then
        make lint PYTHON=python
    fi
fi

make print-access-denied PYTHON=python
make print-api-speed PYTHON=python
