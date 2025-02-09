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

- If you don't have the source code, and just want to test psutil installation.
  This will work also if ``pytest`` module is not installed (e.g. production
  environments) by using unittest's test runner:

.. code-block:: bash

    python3 -m psutil.tests

- ``make`` (and the accompanying `Makefile`_) is the designated tool to build,
  install, run tests and do pretty much anything that involves development.
  This also includes Windows, meaning that you can run `make command` similarly
  as if you were on UNIX (see `make.bat`_ and `winmake.py`_). Some useful
  commands are:

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

    make test ARGS=psutil/tests/test_system.py::TestDiskAPIs::test_disk_usage

- If you're working on a new feature and you wish to compile & test it "on the
  fly" from a test script, this is a quick & dirty way to do it:

.. code-block:: bash

    make test ARGS=test_script.py     # on UNIX
    make test test_script.py          # on Windows

- Do not use ``sudo``. ``make install`` installs psutil as a limited user in
  "edit" / development mode, meaning you can edit psutil code on the fly while
  you develop.

- If you want to target a specific Python version:

.. code-block:: bash

    make test PYTHON=python3.5           # UNIX
    make test -p C:\python35\python.exe  # Windows

Coding style
------------

- Python code strictly follows `PEP-8`_ styling guide. In addition we use
  ``black`` and ``ruff`` code formatters / linters. This is enforced by a GIT
  commit hook, installed via ``make install-git-hooks``, which will reject the
  commit if code is not compliant.
- C code should follow `PEP-7`_ styling guides, but things are more relaxed.
- Linters are enforced also for ``.rst`` and ``.toml`` files.

Code organization
-----------------

.. code-block:: bash

    psutil/__init__.py                   # main psutil namespace ("import psutil")
    psutil/_ps{platform}.py              # platform-specific python wrapper
    psutil/_psutil_{platform}.c          # platform-specific C extension
    psutil/tests/test_process|system.py  # main test suite
    psutil/tests/test_{platform}.py      # platform-specific test suite

Adding a new API
----------------

Typically, this is what you do:

- Define the new API in `psutil/__init__.py`_.
- Write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. `psutil/_pslinux.py`_).
- If the change requires C code, write the C implementation in
  ``psutil/_psutil_{platform}.c`` (e.g. `psutil/_psutil_linux.c`_).
- Write a generic test in `psutil/tests/test_system.py`_ or
  `psutil/tests/test_process.py`_.
- If possible, write a platform-specific test in
  ``psutil/tests/test_{platform}.py`` (e.g. `psutil/tests/test_linux.py`_).
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

.. _`CREDITS`: https://github.com/giampaolo/psutil/blob/master/CREDITS
.. _`CONTRIBUTING.md`: https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md
.. _`HISTORY.rst`: https://github.com/giampaolo/psutil/blob/master/HISTORY.rst
.. _`make.bat`: https://github.com/giampaolo/psutil/blob/master/make.bat
.. _`winmake.py`: https://github.com/giampaolo/psutil/blob/master/scripts/internal/winmake.py
.. _`Makefile`: https://github.com/giampaolo/psutil/blob/master/Makefile
.. _`PEP-7`: https://www.python.org/dev/peps/pep-0007/
.. _`PEP-8`: https://www.python.org/dev/peps/pep-0008/
.. _`psutil/__init__.py`: https://github.com/giampaolo/psutil/blob/master/psutil/__init__.py
.. _`psutil/_pslinux.py`: https://github.com/giampaolo/psutil/blob/master/psutil/_pslinux.py
.. _`psutil/_psutil_linux.c`: https://github.com/giampaolo/psutil/blob/master/psutil/_psutil_linux.c
.. _`psutil/tests/test_linux.py`: https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_linux.py
.. _`psutil/tests/test_process.py`: https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_process.py
.. _`psutil/tests/test_system.py`: https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_system.py
