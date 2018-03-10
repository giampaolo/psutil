Instructions for running tests
==============================

* To run tests::

    make setup-dev-env  # install test deps (+ other things)
    make test

* To run tests on all supported Python versions install tox
  (``pip install tox``) then run ``tox`` from within psutil root directory.

* Every time a commit is pushed tests are automatically run on Travis
  (Linux, OSX) and appveyor (Windows):

  * Travis builds: https://travis-ci.org/giampaolo/psutil
  * AppVeyor builds: https://ci.appveyor.com/project/giampaolo/psutil
