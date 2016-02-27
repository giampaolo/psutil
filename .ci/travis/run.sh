#!/bin/bash

set -e
set -x

if [[ "$(uname -s)" == 'Darwin' ]]; then
    if which pyenv > /dev/null; then
        eval "$(pyenv init -)"
    fi
    pyenv activate psutil
fi

python setup.py build
python setup.py develop

if [[ "$(uname -s)" != 'Darwin' ]]; then
    coverage run psutil/tests/runner.py --include="psutil/*" --omit="test/*,*setup*"
else
    python psutil/tests/runner.py
fi

python psutil/tests/test_memory_leaks.py
flake8
pep8
