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

# install psutil
make clean
python setup.py build
python setup.py develop

# run tests (with coverage)
if [[ $PYVER == '2.7' ]] && [[ "$(uname -s)" != 'Darwin' ]]; then
    PSUTIL_TESTING=1 python -Wa -m coverage run psutil/tests/runner.py
else
    PSUTIL_TESTING=1 python -Wa psutil/tests/runner.py
fi

if [ "$PYVER" == "2.7" ] || [ "$PYVER" == "3.6" ]; then
    # run mem leaks test
    PSUTIL_TESTING=1 python -Wa psutil/tests/test_memory_leaks.py
    # run linter (on Linux only)
    if [[ "$(uname -s)" != 'Darwin' ]]; then
        make lint PYTHON=python
    fi
fi

PSUTIL_TESTING=1 python -Wa scripts/internal/print_access_denied.py
PSUTIL_TESTING=1 python -Wa scripts/internal/print_api_speed.py
