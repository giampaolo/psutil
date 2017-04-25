Instructions for running tests
==============================

* There are two ways of running tests. If psutil is already installed:

    python -m psutil.tests

  If you have a copy of the source code:

    make test

* Depending on the Python version, dependencies for running tests include
  ``ipaddress``, ``mock`` and ``unittest2`` modules.
  On Windows you'll also need ``pywin32`` and ``wmi`` modules.
  If you have a copy of the source code you can run ``make setup-dev-env`` to
  install all deps (also on Windows).

* To run tests on all supported Python versions install tox
  (``pip install tox``) then run ``tox`` from psutil root directory.

* Every time a commit is pushed tests are automatically run on Travis
  (Linux, OSX) and appveyor (Windows):
  * https://travis-ci.org/giampaolo/psutil/
  * https://ci.appveyor.com/project/giampaolo/psutil
