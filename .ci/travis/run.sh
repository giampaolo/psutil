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

if [ "$PYVER" == "2.7" ] || [ "$PYVER" == "3.5" ]; then
    # run mem leaks test
    python psutil/tests/test_memory_leaks.py
    # run linter (on Linux only)
    if [[ "$(uname -s)" != 'Darwin' ]]; then
        python -m flake8
    fi
fi
