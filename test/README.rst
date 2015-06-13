- The recommended way to run tests (also on Windows) is to cd into parent
  directory and run ``make test``

- Dependencies for running tests:
   -  python 2.6: ipaddress, mock, unittest2
   -  python 2.7: ipaddress, mock
   -  python 3.2: ipaddress, mock
   -  python 3.3: ipaddress
   -  python >= 3.4: no deps required

- The main test script is ``test_psutil.py``, which also imports platform-specific
  ``_*.py`` scripts (which should be ignored).

- ``test_memory_leaks.py`` looks for memory leaks into C extension modules and must
  be run separately with ``make test-memleaks``.

- To run tests on all supported Python version install tox (pip install tox)
  then run ``tox``.

- Every time a commit is pushed tests are automatically run on Travis:
  https://travis-ci.org/giampaolo/psutil/
