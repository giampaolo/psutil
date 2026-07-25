Development guide
=================

.. seealso:: `Contributing to psutil project <https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md>`_

Build, setup and test
---------------------

- psutil makes extensive use of C extension modules, meaning a C compiler is
  required, see :doc:`install instructions <install>`. Once installed run:

  .. code-block:: bash

     git clone git@github.com:giampaolo/psutil.git
     make install-sysdeps      # install gcc and python headers
     make install-pydeps-test  # install test dependencies
     make build
     make install
     make test

- ``make`` (via the :src:`Makefile`) is used for building, testing and general
  development tasks, including on Windows (see below):

  .. code-block:: bash

     make clean
     make install-pydeps-dev   # install dev deps (ruff, black, coverage, ...)
     make test
     make test-parallel
     make test-memleaks
     make test-coverage
     make lint-all
     make fix-all
     make uninstall
     make help

- To run a specific test:

  .. code-block:: none

     make test ARGS=tests/test_system.py

- Do not use ``sudo``. ``make install`` installs psutil in editable mode, so
  you can modify the code while developing.

- To target a specific Python version:

  .. code-block:: none

     make test PYTHON=python3.8

Windows
-------

- The recommended way to develop on Windows is to use ``make``.
- Install `Git for Windows`_ and launch a *Git Bash shell*, which provides a
  Unix-like environment where ``make`` works.
- Then run:

  .. code-block:: bash

     make build
     make test-parallel

.. _devguide_debug_mode:

Debug mode
----------

If you need to debug unusual situations or report a bug, you can enable debug
mode via the :envvar:`PSUTIL_DEBUG` environment variable. In this mode, psutil
may print additional information to stderr. Usually these are non-severe error
conditions that are ignored instead of causing a crash. Unit tests
automatically run with debug mode enabled. On UNIX:

.. code-block:: none

  $ PSUTIL_DEBUG=1 python3 script.py
  psutil-debug [psutil/_psutil_linux.c:150]> setmntent() failed (ignored)

On Windows:

.. code-block:: none

  set PSUTIL_DEBUG=1 && python.exe script.py
  psutil-debug [psutil/arch/windows/proc_info.c:56]> ReadProcessMemory -> ERROR_NOACCESS (ignored)

Coding style
------------

All style and formatting checks are enforced locally on each ``git commit`` and
via a GitHub Actions pipeline.

- Python: follows `PEP-8`_, formatted and linted with ``black`` and ``ruff``.
- C: generally follows `PEP-7`_, formatted with ``clang-format``.
- Other files (``.rst``, ``.toml``, ``.md``, ``.yml``): validated by linters.

The pipeline re-runs all checks for consistency (``make lint-all``).

Run ``make fix-all`` before committing; it usually fixes Python issues (via
``black`` and ``ruff``) and C issues (via ``clang-format``).

Code organization
-----------------

.. code-block:: bash

   psutil/__init__.py                   # Main API namespace ("import psutil")
   psutil/_common.py                    # Generic utilities
   psutil/_ntuples.py                   # Named tuples returned by psutil APIs
   psutil/_enums.py                     # Enum containers
   psutil/_ps{platform}.py              # OS-specific python wrapper
   psutil/_psutil_{platform}.c          # OS-specific C extension (entry point)
   psutil/arch/all/*.c                  # C code common to all OSes
   psutil/arch/{platform}/*.c           # OS-specific C extension
   tests/test_process|system.py         # Main system/process API tests
   tests/test_{platform}.py             # OS-specific tests

Adding a new API
----------------

- Define the API in :src:`psutil/__init__.py`.
- Implement it in ``psutil/_ps{platform}.py`` (e.g. :src:`psutil/_pslinux.py`).
- If needed, add C code in ``psutil/arch/{platform}/file.c``.
- Add a generic test in :src:`tests/test_system.py` or
  :src:`tests/test_process.py`.
- Add a platform-specific test in ``tests/test_{platform}.py``.
- Update :src:`docs/api.rst`.
- Open a pull request.

Make a pull request
-------------------

- Fork psutil on GitHub.
- Clone your fork: ``git clone git@github.com:YOUR-USERNAME/psutil.git``
- Create a branch: ``git checkout -b new-feature``
- Commit changes: ``git commit -am 'add some feature'``
- Push: ``git push origin new-feature``
- Open a PR and sign off your work (see :src:`CONTRIBUTING.md`).

Continuous integration
----------------------

Unit tests run automatically on every ``git push`` on all platforms except AIX.
See
`.github/workflows <https://github.com/giampaolo/psutil/tree/master/.github/workflows>`_.

Documentation
-------------

- Source is in the :src:`docs/ <docs/>` directory.
- To build HTML:

  .. code-block:: bash

     cd docs/
     python3 -m pip install -r requirements.txt
     make html

- Doc is hosted at https://psutil.io. It's a single version, rebuilt and
  deployed automatically on every push to ``master``.

Releases
--------

- Uploaded to `PyPI`_ via ``make release``.
- Git tags use the ``vX.Y.Z`` format (e.g. ``v7.2.2``).
- The version string is defined in :src:`psutil/__init__.py` (``__version__``).

.. _`Git for Windows`: https://git-scm.com/install/windows
.. _`PEP-7`: https://www.python.org/dev/peps/pep-0007/
.. _`PEP-8`: https://www.python.org/dev/peps/pep-0008/
.. _`PyPI`: https://pypi.org/project/psutil/
