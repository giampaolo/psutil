Development guide
=================

.. seealso:: `Contributing to psutil project <https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md>`_

Build, setup and test
---------------------

- psutil makes extensive use of C code, so a C compiler and the Python
  development headers are required. First clone the repository:

  .. code-block:: bash

     git clone https://github.com/giampaolo/psutil.git
     cd psutil

  On Linux, FreeBSD, OpenBSD, NetBSD and Solaris, install the system deps:

  .. code-block:: bash

     make install-sysdeps       # compiler + python headers
     make install-sysdeps-test  # CLI tools used by tests

  On macOS, AIX and Windows there's no such target, see
  :ref:`install_from_source`. Then, everywhere:

  .. code-block:: bash

     make install-pydeps-dev    # python development deps (linters, etc)
     make build                 # compile the C extension in place
     make test

- ``make`` (via the :src:`Makefile`) is used for building, testing and general
  development tasks, including on Windows (see below):

  .. code-block:: bash

     make clean
     make test
     make test-parallel
     make test-memleaks
     make coverage
     make lint-all
     make fix-all
     make uninstall
     make help

- To run a specific test:

  .. code-block:: none

     make test ARGS=tests/test_system.py

- ``make build`` compiles the extension in place, so you can import psutil
  straight from the repo. No need to install it.

- Don't use ``sudo``, except for the ``install-sysdeps-*`` targets, which
  invoke it themselves when needed.

- To target a specific Python version, pass ``PYTHON`` to every step, so that
  the extension is built by the same interpreter that runs the tests:

  .. code-block:: none

     make install-pydeps-dev PYTHON=python3.13
     make build PYTHON=python3.13
     make test PYTHON=python3.13

Windows
-------

- The recommended way to develop on Windows is to use ``make``.
- For the build tools, Git Bash and GNU Make setup see :ref:`install_windows`.
- Once inside a Git Bash shell, run:

  .. code-block:: bash

     make install-pydeps-dev
     make build
     make test-parallel

.. _devguide_debug_mode:

Debug mode
----------

If you need to debug unusual situations or report a bug, you can enable debug
mode via the :envvar:`PSUTIL_DEBUG` environment variable. In this mode, psutil
may print additional information to stderr. Usually these are non-severe error
conditions that are ignored instead of causing a crash. Unit tests
automatically run with debug mode enabled. To enable debug mode in UNIX (or on
Windows + Bash):

.. code-block:: none

  $ PSUTIL_DEBUG=1 python3 test_script.py
  psutil-debug [psutil/_psutil_linux.c:150]> setmntent() failed (ignored)

On Windows using cmd.exe:

.. code-block:: none

  set PSUTIL_DEBUG=1 && python.exe test_script.py
  psutil-debug [psutil/arch/windows/proc.c:56]> ReadProcessMemory -> ERROR_NOACCESS (ignored)

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

Not every API reaches C: many are implemented in python alone (on Linux, by
parsing ``/proc``). For those that do, a call travels down through the
platform-specific layers. Linux is used here as an example:

.. code-block:: none

   import psutil
        │
        ▼
   psutil/__init__.py          public API, Process class
        │
        ▼
   psutil/_pslinux.py          python layer: parses /proc, calls into C
        │
        ▼
   psutil/_psutil_linux.c      C extension entry point (arg parsing)
        │
        ▼
   psutil/arch/linux/*.c       platform-specific C implementation
                               + arch/posix/*.c   shared by POSIX
                               + arch/all/*.c     shared by everything

Where things live:

.. code-block:: bash

   psutil/__init__.py                   # Public API ("import psutil")
   psutil/_common.py                    # Generic utilities
   psutil/_ntuples.py                   # Named tuples returned by psutil APIs
   psutil/_enums.py                     # Enum containers
   psutil/_ps{platform}.py              # OS-specific python wrapper
   psutil/_psutil_{platform}.c          # OS-specific C extension (entry point)
   psutil/arch/all/*.c                  # C code common to all OSes
   psutil/arch/posix/*.c                # C code common to POSIX OSes
   psutil/arch/bsd/*.c                  # C code common to the BSDs
   psutil/arch/{platform}/*.c           # OS-specific C implementation
   tests/test_process.py                # Main process API tests
   tests/test_system.py                 # Main system API tests
   tests/test_{platform}.py             # OS-specific tests

Adding a new API
----------------

- Define the public API in :src:`psutil/__init__.py`.
- Implement it for each applicable platform in ``psutil/_ps{platform}.py``
  (e.g. :src:`psutil/_pslinux.py`).
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
- Stage and commit: ``git add <files>`` then
  ``git commit -m 'Add some feature'``
- Push: ``git push origin new-feature``
- Open a pull request (see :src:`CONTRIBUTING.md`).

Continuous integration
----------------------

Tests run automatically on pull requests and on relevant pushes, covering all
regularly tested platforms except AIX. See
`.github/workflows <https://github.com/giampaolo/psutil/tree/master/.github/workflows>`_.

Documentation
-------------

- Source is in the :src:`docs/ <docs/>` directory.
- To build HTML:

  .. code-block:: bash

     cd docs/
     python3 -m pip install -r requirements.txt
     make html

- The documentation is hosted at https://psutil.io. It's a single version,
  rebuilt and deployed automatically on every push to ``master``.

Releases
--------

For project maintainers:

- Releases are uploaded to `PyPI`_ via ``make release``.
- Git tags use the ``vX.Y.Z`` format (e.g. ``v7.2.2``).
- The version string is defined in :src:`psutil/__init__.py` (``__version__``).

.. _`PEP-7`: https://www.python.org/dev/peps/pep-0007/
.. _`PEP-8`: https://www.python.org/dev/peps/pep-0008/
.. _`PyPI`: https://pypi.org/project/psutil/
