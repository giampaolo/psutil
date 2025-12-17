psutil development guide
========================

Build, setup and running tests
..............................

psutil makes extensive use of C extension modules, meaning a C compiler is
required, see
`install instructions <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`__.
Once you have a compiler installed run:

.. code-block:: bash

    git clone git@github.com:giampaolo/psutil.git
    make install-sysdeps      # install gcc and python headers
    make install-pydeps-test  # install python deps necessary to run unit tests
    make build
    make install
    make test

- ``make`` (and the accompanying `Makefile`_) is the designated tool to build,
  install, run tests and do pretty much anything that involves development.
  useful commands are:

.. code-block:: bash

    make clean                # remove build files
    make install-pydeps-dev   # install dev deps (ruff, black, ...)
    make test                 # run tests
    make test-parallel        # run tests in parallel (faster)
    make test-memleaks        # run memory leak tests
    make test-coverage        # run test coverage
    make lint-all             # run linters
    make fix-all              # fix linters errors
    make uninstall
    make help

- To run a specific unit test:

.. code-block:: bash

    make test ARGS=tests/test_system.py

- Do not use ``sudo``. ``make install`` installs psutil as a limited user in
  "edit" / development mode, meaning you can edit psutil code on the fly while
  you develop.

- If you want to target a specific Python version:

.. code-block:: bash

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

Coding style
------------

All style and formatting checks are automatically enforced both **locally on
each `git commit`** and **remotely via a GitHub Actions pipeline**.

- A **Git commit hook**, installed with `make install-git-hooks`, runs all
  formatters and linters before each commit. The commit is rejected if any
  check fails.
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

    psutil/__init__.py                   # main psutil namespace ("import psutil")
    psutil/_ps{platform}.py              # platform-specific python wrapper
    psutil/_psutil_{platform}.c          # platform-specific C extension
    psutil/arch/{platform}/*.c           # platform-specific C extension
    tests/test_process|system.py         # main test suite
    tests/test_{platform}.py             # platform-specific test suite

Adding a new API
----------------

Typically, this is what you do:

- Define the new API in `psutil/__init__.py`_.
- Write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. `psutil/_pslinux.py`_).
- If the change requires C code, write the C implementation in
  ``psutil/arch/{platform}/file.c`` (e.g. `psutil/arch/linux/cpu.c`).
- Write a generic test in `tests/test_system.py`_ or
  `tests/test_process.py`_.
- If possible, write a platform-specific test in
  ``tests/test_{platform}.py`` (e.g. `tests/test_linux.py`_).
  This usually means testing the return value of the new API against
  a system CLI tool.
- Update the doc in ``docs/index.py``.
- Update `HISTORY.rst`_ and `CREDITS`_ files.
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

Unit tests are automatically run on every ``git push`` on **Linux**, **macOS**,
**Windows**, **FreeBSD**, **NetBSD**, **OpenBSD**.
AIX and Solaris does not have continuous test integration.

Documentation
-------------

- doc source code is written in a single file: ``docs/index.rst``.
- doc can be built with ``make install-pydeps-dev; cd docs; make html``.
- public doc is hosted at https://psutil.readthedocs.io.

.. _`CONTRIBUTING.md`: https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md
.. _`CREDITS`: https://github.com/giampaolo/psutil/blob/master/CREDITS
.. _`Git for Windows`: <https://git-scm.com/install/windows>`
.. _`HISTORY.rst`: https://github.com/giampaolo/psutil/blob/master/HISTORY.rst
.. _`Makefile`: https://github.com/giampaolo/psutil/blob/master/Makefile
.. _`PEP-7`: https://www.python.org/dev/peps/pep-0007/
.. _`PEP-8`: https://www.python.org/dev/peps/pep-0008/
.. _`psutil/__init__.py`: https://github.com/giampaolo/psutil/blob/master/psutil/__init__.py
.. _`psutil/_pslinux.py`: https://github.com/giampaolo/psutil/blob/master/psutil/_pslinux.py
.. _`psutil/_psutil_linux.c`: https://github.com/giampaolo/psutil/blob/master/psutil/_psutil_linux.c
.. _`tests/test_linux.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_linux.py
.. _`tests/test_process.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_process.py
.. _`tests/test_system.py`: https://github.com/giampaolo/psutil/blob/master/tests/test_system.py
.. _`winmake.py`: https://github.com/giampaolo/psutil/blob/master/scripts/internal/winmake.py
