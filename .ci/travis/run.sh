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

# Run memory leak tests and linter only on Linux and latest major Python
# versions.
if [ "$PYVER" == "2.7" ] || [ "$PYVER" == "3.6" ]; then
    python psutil/tests/test_memory_leaks.py
    if [[ "$(uname -s)" != 'Darwin' ]]; then
        python -m flake8
    fi
fi
