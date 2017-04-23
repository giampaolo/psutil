#!/bin/bash

set -e
set -x

PYVER=`python -c 'import sys; print(".".join(map(str, sys.version_info[:2])))'`

uname -a
echo $PYVER

if [[ "$(uname -s)" == 'Darwin' ]]; then
    brew update
    brew install python
    virtualenv env -p python
    source env/bin/activate
    # brew update || brew update
    # brew outdated pyenv || brew upgrade pyenv
    # brew install pyenv-virtualenv

    # if which pyenv > /dev/null; then
    #     eval "$(pyenv init -)"
    # fi

    # case "${PYVER}" in
    #     py27)
    #         pyenv install 2.7.10
    #         pyenv virtualenv 2.7.10 psutil
    #         ;;
    #     py34)
    #         pyenv install 3.4.3
    #         pyenv virtualenv 3.4.3 psutil
    #         ;;
    # esac
    # pyenv rehash
    # pyenv activate psutil
fi

# old python versions
if [[ $PYVER == '2.6' ]]; then
    pip install -U ipaddress unittest2 argparse mock==1.0.1
elif [[ $PYVER == '2.7' ]]; then
    pip install -U ipaddress mock
elif [[ $PYVER == '3.3' ]]; then
    pip install -U ipaddress
fi

pip install --upgrade coverage coveralls setuptools flake8
