- The recommended way to run tests (also on Windows) is to cd into psutil root
  directory and run ``make test``.

- Depending on the Python version dependencies for running tests include
  ipaddress, mock and unittest2 modules (get them on PYPI.
  On Windows also pywin32 and WMIC modules are recommended (although optional).
  Run ``make setup-dev-env`` to install them (also on Windows).

- To run tests on all supported Python version install tox (pip install tox)
  then run ``tox``.

- Every time a commit is pushed tests are automatically run on Travis:
  https://travis-ci.org/giampaolo/psutil/
