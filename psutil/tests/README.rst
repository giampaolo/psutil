Instructions for running tests
==============================

* There are two ways of running tests. As a "user", if psutil is already
  installed and you just want to test it works::

    python -m psutil.tests

  As a "developer", if you have a copy of the source code and you wish to hack
  on psutil::

    make setup-dev-env  # install missing third-party deps
    make test           # serial run
    make test-parallel  # parallel run
