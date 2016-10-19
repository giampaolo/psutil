#!/bin/bash

set -e
set -x

PYVER=`python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'`

# setup OSX
if [[ "$(uname -s)" == 'Darwin' ]]; then
    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi
    pyenv activate psutil
fi

# install psutil
python setup.py build
python setup.py develop

# run tests (with coverage)
if [[ "$(uname -s)" != 'Darwin' ]]; then
    coverage run psutil/tests/runner.py --include="psutil/*" --omit="test/*,*setup*"
else
    python psutil/tests/runner.py
fi

# run mem leaks test
python psutil/tests/test_memory_leaks.py

# run linters
if [ "$PYVER" != "2.6" ]; then
    flake8
    pep8
fi
