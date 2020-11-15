Setup
=====

psutil makes extensive use of C extension modules, meaning a C compiler is
required, see
`install instructions <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`__.

Build, setup and running tests
===============================

Once you have a compiler installed:

.. code-block:: bash

    git clone git@github.com:giampaolo/psutil.git
    make setup-dev-env  # install useful dev libs (flake8, coverage, ...)
    make build
    make install
    make test

- ``make`` (see `Makefile`_) is the designated tool to run tests, build, install
  try new features you're developing, etc. This also includes Windows (see
  `make.bat`_ ).
  Some useful commands are:

.. code-block:: bash

    make test-parallel   # faster
    make test-memleaks
    make test-coverage
    make lint            # Python (PEP8) and C linters
    make uninstall
    make help

- if you're working on a new feature and you whish to compile & test it "on the
  fly" from a test script, this is a quick & dirty way to do it:

.. code-block:: bash

    make test TSCRIPT=test_script.py  # on UNIX
    make test test_script.py          # on Windows

- do not use ``sudo``. ``make install`` installs psutil as a limited user in
  "edit" mode, meaning you can edit psutil code on the fly while you develop.

- if you want to target a specific Python version:

.. code-block:: bash

    make test PYTHON=python3.5           # UNIX
    make test -p C:\python35\python.exe  # Windows

Coding style
============

- python code strictly follows `PEP-8`_ styling guides and this is enforced by
  a commit GIT hook installed via ``make install-git-hooks`` which will reject
  commits if code is not PEP-8 complieant.
- C code should follow `PEP-7`_ styling guides.

Code organization
=================

.. code-block:: bash

    psutil/__init__.py                   # main psutil namespace ("import psutil")
    psutil/_ps{platform}.py              # platform-specific python wrapper
    psutil/_psutil_{platform}.c          # platform-specific C extension
    psutil/tests/test_process|system.py  # main test suite
    psutil/tests/test_{platform}.py      # platform-specific test suite

Adding a new API
================

Typically, this is what you do:

- define the new API in `psutil/__init__.py`_.
- write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. `psutil/_pslinux.py`_).
- if the change requires C code, write the C implementation in
  ``psutil/_psutil_{platform}.c`` (e.g. `psutil/_psutil_linux.c`_).
- write a generic test in `psutil/tests/test_system.py`_ or
  `psutil/tests/test_process.py`_.
- if possible, write a platform-specific test in
  ``psutil/tests/test_{platform}.py`` (e.g. `psutil/tests/test_linux.py`_).
  This usually means testing the return value of the new API against
  a system CLI tool.
- update the doc in ``doc/index.py``.
- update ``HISTORY.rst``.
- make a pull request.

Make a pull request
===================

- fork psutil (go to https://github.com/giampaolo/psutil and click on "fork")
- git clone the fork locally: ``git clone git@github.com:YOUR-USERNAME/psutil.git``)
- create a branch:``git checkout -b new-feature``
- commit your changes: ``git commit -am 'add some feature'``
- push the branch: ``git push origin new-feature``
- create a new PR by via GitHub web interface

Continuous integration
======================

All of the services listed below are automatically run on each ``git push``.

Unit tests
----------

Tests are automatically run on every GIT push and PR on **Linux**, **macOS**,
**Windows** and **FreeBSD** by using:

- `Github Actions`_ (Linux, macOS, Windows)
- `Appveyor`_ (Windows)

.. image:: https://img.shields.io/github/workflow/status/giampaolo/psutil/CI?label=linux%2C%20macos%2C%20freebsd
    :target: https://github.com/giampaolo/psutil/actions?query=workflow%3ACI

.. image:: https://img.shields.io/appveyor/ci/giampaolo/psutil/master.svg?maxAge=3600&label=windows
    :target: https://ci.appveyor.com/project/giampaolo/psutil

OpenBSD, NetBSD, AIX and Solaris does not have continuos test integration.

Test coverage
-------------

Test coverage is provided by `coveralls.io`_.

.. image:: https://coveralls.io/repos/giampaolo/psutil/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/giampaolo/psutil?branch=master
    :alt: Test coverage (coverall.io)

Documentation
=============

- doc source code is written in a single file: `/docs/index.rst`_.
- doc can be built with ``make setup-dev-env; cd docs; make html``.
- public doc is hosted at https://psutil.readthedocs.io


.. _`appveyor.yml`: https://github.com/giampaolo/psutil/blob/master/appveyor.yml
.. _`Appveyor`: https://ci.appveyor.com/project/giampaolo/psuti
.. _`coveralls.io`: https://coveralls.io/github/giampaolo/psuti
.. _`CREDITS`: https://github.com/giampaolo/psutil/blob/master/CREDITS
.. _`doc/index.rst`: https://github.com/giampaolo/psutil/blob/master/doc/index.rst
.. _`Github Actions`: https://github.com/giampaolo/psutil/actions
.. _`HISTORY.rst`: https://github.com/giampaolo/psutil/blob/master/HISTORY.rst
.. _`make.bat`: https://github.com/giampaolo/psutil/blob/master/make.bat
.. _`Makefile`: https://github.com/giampaolo/psutil/blob/master/Makefile
.. _`PEP-7`: https://www.python.org/dev/peps/pep-0007/
.. _`PEP-8`: https://www.python.org/dev/peps/pep-0008/
.. _`psutil/__init__.py`: https://github.com/giampaolo/psutil/blob/master/psutil/__init__.py
.. _`psutil/_pslinux.py`: https://github.com/giampaolo/psutil/blob/master/psutil/_pslinux.py
.. _`psutil/_psutil_linux.c`: https://github.com/giampaolo/psutil/blob/master/psutil/_psutil_linux.c
.. _`psutil/tests/test_linux.py`: https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_linux.py
.. _`psutil/tests/test_process.py`: https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_process.py
.. _`psutil/tests/test_system.py`: https://github.com/giampaolo/psutil/blob/master/psutil/tests/test_system.py
.. _`RsT syntax`: http://docutils.sourceforge.net/docs/user/rst/quickref.htm
.. _`sphinx`: http://sphinx-doc.org
