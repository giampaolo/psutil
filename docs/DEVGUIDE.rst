Build, setup and running tests
===============================

Make sure to `install <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`__
a C compiler first, then:

.. code-block:: bash

  git clone git@github.com:giampaolo/psutil.git
  make setup-dev-env
  make test

- bear in mind that ``make``(see `Makefile`_) is the designated tool to run
  tests, build, install etc. and that it is also available on Windows (see
  `make.bat`_ ).
- do not use ``sudo``; ``make install`` installs psutil as a limited user in
  "edit" mode; also ``make setup-dev-env`` installs deps as a limited user.
- use `make help` to see the list of available commands.

Coding style
============

- python code strictly follows `PEP-8`_ styling guides and this is enforced by
  a commit GIT hook installed via ``make install-git-hooks``.
- C code follows `PEP-7`_ styling guides.

Makefile
========

Some useful make commands:

.. code-block:: bash

    make install        # install
    make setup-dev-env  # install useful dev libs (flake8, unittest2, etc.)
    make test           # run unit tests
    make test-memleaks  # run memory leak tests
    make test-coverage  # run test coverage
    make lint           # run Python (PEP8) and C linters

There are some differences between ``make`` on UNIX and Windows.
For instance, to run a specific Python version. On UNIX:

.. code-block:: bash

    make test PYTHON=python3.5

On Windows:

.. code-block:: bat

    make -p C:\python35\python.exe test

If you want to modify psutil and run a script on the fly which uses it do
(on UNIX):

.. code-block:: bash

    make test TSCRIPT=foo.py

On Windows:

.. code-block:: bat

    make test foo.py

Adding a new feature
====================

Usually the files involved when adding a new functionality are:

.. code-block:: bash

    psutil/__init__.py                   # main psutil namespace
    psutil/_ps{platform}.py              # python platform wrapper
    psutil/_psutil_{platform}.c          # C platform extension
    psutil/_psutil_{platform}.h          # C header file
    psutil/tests/test_process|system.py  # main test suite
    psutil/tests/test_{platform}.py      # platform specific test suite

Typical process occurring when adding a new functionality (API):

- define the new function in `psutil/__init__.py`_.
- write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. `psutil/_pslinux.py`_).
- if the change requires C, write the C implementation in
  ``psutil/_psutil_{platform}.c`` (e.g. `psutil/_psutil_linux.c`_).
- write a generic test in `psutil/tests/test_system.py`_ or
  `psutil/tests/test_process.py`_.
- if possible, write a platform specific test in
  ``psutil/tests/test_{platform}.py`` (e.g. `psutil/tests/test_linux.py`_).
  This usually means testing the return value of the new feature against
  a system CLI tool.
- update doc in ``doc/index.py``.
- update ``HISTORY.rst``.
- make a pull request.

Make a pull request
===================

- fork psutil (go to https://github.com/giampaolo/psutil and click on "fork")
- git clone your fork locally: ``git clone git@github.com:YOUR-USERNAME/psutil.git``)
- create your feature branch:``git checkout -b new-feature``
- commit your changes: ``git commit -am 'add some feature'``
- push to the branch: ``git push origin new-feature``
- create a new pull request by via github web interface
- remember to update `HISTORY.rst`_ and `CREDITS`_ files.

Continuous integration
======================

All of the services listed below are automatically run on ``git push``.

Unit tests
----------

Tests are automatically run for every GIT push on **Linux**, **macOS** and
**Windows** by using:

- `Travis`_ (Linux, macOS)
- `Appveyor`_ (Windows)

Test files controlling these are `.travis.yml`_ and `appveyor.yml`_.
Both services run psutil test suite against all supported python version
(2.6 - 3.6).
Two icons in the home page (README) always show the build status:

.. image:: https://img.shields.io/travis/giampaolo/psutil/master.svg?maxAge=3600&label=Linux,%20OSX,%20PyPy
    :target: https://travis-ci.org/giampaolo/psutil
    :alt: Linux, macOS and PyPy3 tests (Travis)

.. image:: https://img.shields.io/appveyor/ci/giampaolo/psutil/master.svg?maxAge=3600&label=Windows
    :target: https://ci.appveyor.com/project/giampaolo/psutil
    :alt: Windows tests (Appveyor)

.. image:: https://img.shields.io/cirrus/github/giampaolo/psutil?label=FreeBSD
    :target: https://cirrus-ci.com/github/giampaolo/psutil-cirrus-ci
    :alt: FreeBSD tests (Cirrus-CI)

BSD, AIX and Solaris are currently tested manually.

Test coverage
-------------

Test coverage is provided by `coveralls.io`_ and it is controlled via
`.travis.yml`_.
An icon in the home page (README) always shows the last coverage percentage:

.. image:: https://coveralls.io/repos/giampaolo/psutil/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/giampaolo/psutil?branch=master
    :alt: Test coverage (coverall.io)

Documentation
=============

- doc source code is written in a single file: `/docs/index.rst`_.
- it uses `RsT syntax`_
  and it's built with `sphinx`_.
- doc can be built with ``make setup-dev-env; cd docs; make html``.
- public doc is hosted on http://psutil.readthedocs.io/

Releasing a new version
=======================

These are notes for myself (Giampaolo):

- ``make release``
- post announce (``make print-announce``) on psutil and python-announce mailing
  lists, twitter, g+, blog.


.. _`.travis.yml`: https://github.com/giampaolo/psutil/blob/master/.travis.ym
.. _`appveyor.yml`: https://github.com/giampaolo/psutil/blob/master/appveyor.ym
.. _`Appveyor`: https://ci.appveyor.com/project/giampaolo/psuti
.. _`coveralls.io`: https://coveralls.io/github/giampaolo/psuti
.. _`doc/index.rst`: https://github.com/giampaolo/psutil/blob/master/doc/index.rst
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
.. _`Travis`: https://travis-ci.org/giampaolo/psuti
.. _`HISTORY.rst`: https://github.com/giampaolo/psutil/blob/master/HISTORY.rst
.. _`CREDITS`: https://github.com/giampaolo/psutil/blob/master/CREDITS
