Development guide
=================

Build, setup and running tests
------------------------------

- psutil makes extensive use of C extension modules, meaning a C compiler is
  required, see :doc:`install instructions <install>`. Once you have a compiler
  installed run:

  .. code-block:: bash

      git clone git@github.com:giampaolo/psutil.git
      make install-sysdeps      # install gcc and python headers
      make install-pydeps-test  # install python deps necessary to run unit tests
      make build
      make install
      make test

- ``make`` (and the accompanying `Makefile`_) is the designated tool to build,
  install, run tests and do pretty much anything that involves development,
  including on Windows. Some useful commands:

  .. code-block:: bash

      make clean                # remove build files
      make install-pydeps-dev   # install all development deps (ruff, black, coverage, ...)
      make test                 # run tests
      make test-parallel        # run tests in parallel (faster)
      make test-memleaks        # run memory leak tests
      make test-coverage        # run test coverage
      make lint-all             # run linters
      make fix-all              # fix linters errors
      make uninstall
      make help

- To run a specific unit test:

  .. code-block::

      make test ARGS=tests/test_system.py

- Do not use ``sudo``. ``make install`` installs psutil as a limited user in
  "edit" / development mode, meaning you can edit psutil code on the fly while
  you develop.

- If you want to target a specific Python version:

  .. code-block::

      make test PYTHON=python3.8

Windows
-------

- The recommended way to develop on Windows is using ``make``, just like on
  UNIX systems.
- First, install `Git for Windows`_ and launch a **Git Bash shell**. This
  provides a Unix-like environment where ``make`` works.
- Once inside Git Bash, you can run the usual ``make`` commands:

  .. code-block:: bash

      make build
      make test-parallel

.. _devguide_debug_mode:

Debug mode
----------

If you want to debug unusual situations or want to report a bug, it may be
useful to enable debug mode via ``PSUTIL_DEBUG`` environment variable. In this
mode, psutil may print additional information to stderr. Usually these are
non-severe error conditions that are ignored instead of causing a crash.
Unit tests automatically run with debug mode enabled. On UNIX:

::

  $ PSUTIL_DEBUG=1 python3 script.py
  psutil-debug [psutil/_psutil_linux.c:150]> setmntent() failed (ignored)

On Windows:

::

  set PSUTIL_DEBUG=1 && python.exe script.py
  psutil-debug [psutil/arch/windows/proc.c:90]> NtWow64ReadVirtualMemory64(pbi64.PebBaseAddress) -> 998 (Unknown error) (ignored)


Coding style
------------

All style and formatting checks are automatically enforced both **locally on
each `git commit`** and **remotely via a GitHub Actions pipeline**.

- **Python** code follows the `PEP-8`_ style guide. We use `black` and `ruff`
  for formatting and linting.
- **C** code generally follows the `PEP-7`_ style guide, with formatting
  enforced by `clang-format`.
- **Other files** (`.rst`, `.toml`, `.md`, `.yml`) are also validated by
  dedicated command-line linters.
- The **GitHub Actions pipeline** re-runs all these checks to ensure
  consistency (via ``make lint-all``).

Code organization
-----------------

.. code-block:: bash

    psutil/__init__.py                   # Main API namespace ("import psutil")
    psutil/_common.py                    # Generic utilities
    psutil/_ntuples.py                   # Named tuples returned by psutil APIs
    psutil/_enums.py                     # Enum containers backing psutil constants
    psutil/_ps{platform}.py              # Platform-specific python wrappers
    psutil/_psutil_{platform}.c          # Platform-specific C extensions (entry point)
    psutil/arch/all/*.c                  # C code common to all platforms
    psutil/arch/{platform}/*.c           # Platform-specific C extension
    tests/test_process|system.py         # Main system/process API tests
    tests/test_{platform}.py             # Platform-specific tests

Adding a new API
----------------

Typically, this is what you do:

- Define the new API in `psutil/__init__.py`_.
- Write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. `psutil/_pslinux.py`_).
- If the change requires C code, write the C implementation in
  ``psutil/arch/{platform}/file.c`` (e.g. `psutil/arch/linux/disk.c`_).
- Write a generic test in `tests/test_system.py`_ or
  `tests/test_process.py`_.
- If possible, write a platform-specific test in
  ``tests/test_{platform}.py`` (e.g. `tests/test_linux.py`_).
  This usually means testing the return value of the new API against
  a system CLI tool.
- Update the doc in ``docs/api.rst``.
- Update `changelog.rst`_ and `credits.rst`_ files.
- Make a pull request.

Make a pull request
-------------------

- Fork psutil (go to https://github.com/giampaolo/psutil and click on "fork")
- Git clone the fork locally: ``git clone git@github.com:YOUR-USERNAME/psutil.git``
- Create a branch: ``git checkout -b new-feature``
- Commit your changes: ``git commit -am 'add some feature'``
- Push the branch: ``git push origin new-feature``
- Create a new PR via the GitHub web interface and sign-off your work (see
  `CONTRIBUTING.md`_ guidelines)

Continuous integration
----------------------

Unit tests are automatically run on every ``git push`` on all platforms except
AIX. See config files in the `.github/workflows <https://github.com/giampaolo/psutil/tree/master/.github/workflows>`_
directory.

Documentation
-------------

- The documentation source is located in the `docs/`_ directory.
- To build it and generate the HTML (in the ``_build/html`` directory):

  .. code-block:: bash

    cd docs/
    python3 -m pip install -r requirements.txt
    make html

- The public documentation is hosted at https://psutil.readthedocs.io.
- There are 2 versions, which you can select from the dropdown menu at the top
  of the page:

  - `/stable <https://psutil.readthedocs.io/stable>`_: generated from the most
    recent Git tag (latest released psutil version).
  - `/latest <https://psutil.readthedocs.io/latest>`_: generated from the
    master branch. It is automatically updated on git push.

Redirects:

- https://psutil.readthedocs.io redirects to
  `/stable <https://psutil.readthedocs.io/stable>`_ by default.

Releases
--------

- Releases are uploaded to `PyPI <https://pypi.org/project/psutil/>`_ via
  ``make release``.
- Git tags use the ``vX.Y.Z`` format (e.g. ``v7.2.2``).
- The version string is defined in ``psutil/__init__.py`` (``__version__``).

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
.. _`psutil/arch/linux/disk.c`: https://github.com/giampaolo/psutil/blob/master/psutil/arch/linux/disk.c
.. _`tests/test_linux.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_linux.py
.. _`tests/test_process.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_process.py
.. _`tests/test_system.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_system.py
