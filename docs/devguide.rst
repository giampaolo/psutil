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

- ``make`` (via the `Makefile`_) is used for building, testing and general
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

- Do not use ``sudo``. ``make install`` installs psutil in editable mode,
  so you can modify the code while developing.

- To target a specific Python version:

  .. code-block:: none

     make test PYTHON=python3.8


Windows
-------

- The recommended way to develop on Windows is to use ``make``.
- Install `Git for Windows`_ and launch a **Git Bash shell**, which provides
  a Unix-like environment where ``make`` works.
- Then run:

  .. code-block:: bash

     make build
     make test-parallel


.. _devguide_debug_mode:

Debug mode
----------

If you need to debug unusual situations or report a bug, you can enable
debug mode via the ``PSUTIL_DEBUG`` environment variable. In this
mode, psutil may print additional information to stderr. Usually these are
non-severe error conditions that are ignored instead of causing a crash.
Unit tests automatically run with debug mode enabled. On UNIX:

.. code-block:: none

  $ PSUTIL_DEBUG=1 python3 script.py
  psutil-debug [psutil/_psutil_linux.c:150]> setmntent() failed (ignored)

On Windows:

.. code-block:: none

  set PSUTIL_DEBUG=1 && python.exe script.py
  psutil-debug [psutil/arch/windows/proc.c:90]> NtWow64ReadVirtualMemory64(...) -> 998 (Unknown error) (ignored)


Coding style
------------

All style and formatting checks are enforced locally on each
`git commit` and via a GitHub Actions pipeline.

- Python: follows `PEP-8`_, formatted and linted with ``black`` and ``ruff``.
- C: generally follows `PEP-7`_, formatted with ``clang-format``.
- Other files (``.rst``, ``.toml``, ``.md``, ``.yml``): validated by linters.

The pipeline re-runs all checks for consistency (``make lint-all``).

Run ``make fix-all`` before committing; it usually fixes Python issues
(via ``black`` and ``ruff``) and C issues (via ``clang-format``).


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

- Define the API in `psutil/__init__.py`_.
- Implement it in ``psutil/_ps{platform}.py`` (e.g. `psutil/_pslinux.py`_).
- If needed, add C code in ``psutil/arch/{platform}/file.c``.
- Add a generic test in `tests/test_system.py`_ or `tests/test_process.py`_.
- Add a platform-specific test in ``tests/test_{platform}.py``.
- Update ``docs/api.rst``.
- Update `changelog.rst`_ and `credits.rst`_.
- Open a pull request.

Make a pull request
-------------------

- Fork psutil on GitHub.
- Clone your fork: ``git clone git@github.com:YOUR-USERNAME/psutil.git``
- Create a branch: ``git checkout -b new-feature``
- Commit changes: ``git commit -am 'add some feature'``
- Push: ``git push origin new-feature``
- Open a PR and sign off your work (see `CONTRIBUTING.md`_).


Continuous integration
----------------------

Unit tests run automatically on every ``git push`` on all platforms except
AIX. See `.github/workflows <https://github.com/giampaolo/psutil/tree/master/.github/workflows>`_.


Documentation
-------------

- Source is in the `docs/`_ directory.
- To build HTML:

  .. code-block:: bash

     cd docs/
     python3 -m pip install -r requirements.txt
     make html

- Doc is hosted at https://psutil.readthedocs.io (redirects to `/stable`_).
- There's 2 versions of the doc (can be selected via dropdown on the top left):

  - `/stable`_: latest release published on `PyPI`_
  - `/latest`_: ``master`` development branch

.. note::

   ``/latest`` may contain unreleased changes. Use ``/stable`` for
   production docs.

Releases
--------

- Uploaded to `PyPI`_ via ``make release``.
- Git tags use the ``vX.Y.Z`` format (e.g. ``v7.2.2``).
- The version string is defined in ``psutil/__init__.py`` (``__version__``).

.. _`/latest`: https://psutil.readthedocs.io/latest
.. _`/stable`: https://psutil.readthedocs.io/stable
.. _`changelog.rst`: https://github.com/giampaolo/psutil/blob/master/docs/changelog.rst
.. _`CONTRIBUTING.md`: https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md
.. _`credits.rst`: https://github.com/giampaolo/psutil/blob/master/docs/credits.rst
.. _`docs/`: https://github.com/giampaolo/psutil/blob/master/psutil/docs/
.. _`Git for Windows`: https://git-scm.com/install/windows
.. _`Makefile`: https://github.com/giampaolo/psutil/blob/master/Makefile
.. _`PEP-7`: https://www.python.org/dev/peps/pep-0007/
.. _`PEP-8`: https://www.python.org/dev/peps/pep-0008/
.. _`psutil/__init__.py`: https://github.com/giampaolo/psutil/blob/master/psutil/__init__.py
.. _`psutil/_pslinux.py`: https://github.com/giampaolo/psutil/blob/master/psutil/_pslinux.py
.. _`PyPI`: https://pypi.org/project/psutil/
.. _`tests/test_process.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_process.py
.. _`tests/test_system.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_system.py
