=======================
Setup and running tests
=======================

If you plan on hacking on psutil this is what you're supposed to do first:

- clone the GIT repository::

  $ git clone git@github.com:giampaolo/psutil.git

- install test deps and GIT hooks::

  $ make setup-dev-env

- run tests::

  $ make test

- bear in mind that ``make``
  (see `Makefile <https://github.com/giampaolo/psutil/blob/master/Makefile>`_)
  is the designated tool to run tests, build, install etc. and that it is also
  available on Windows
  (see `make.bat <https://github.com/giampaolo/psutil/blob/master/make.bat>`_).
- do not use ``sudo``; ``make install`` installs psutil as a limited user in
  "edit" mode; also ``make setup-dev-env`` installs deps as a limited user.
- use `make help` to see the list of available commands.

============
Coding style
============

- python code strictly follows `PEP 8 <https://www.python.org/dev/peps/pep-0008/>`_
  styling guides and this is enforced by ``make install-git-hooks``.
- C code strictly follows `PEP 7 <https://www.python.org/dev/peps/pep-0007/>`_
  styling guides.

========
Makefile
========

Some useful make commands::

  $ make install        # install
  $ make setup-dev-env  # install useful dev libs (pyflakes, unittest2, etc.)
  $ make test           # run unit tests
  $ make test-memleaks  # run memory leak tests
  $ make test-coverage  # run test coverage
  $ make flake8         # run PEP8 linter

There are some differences between ``make`` on UNIX and Windows.
For instance, to run a specific Python version. On UNIX::

    make test PYTHON=python3.5

On Windows::

    set PYTHON=C:\python35\python.exe && make test

    # ...or:

    make -p 35 test

If you want to modify psutil and run a script on the fly which uses it do
(on UNIX)::

    make test TSCRIPT=foo.py

On Windows::

    set TSCRIPT=foo.py && make test

====================
Adding a new feature
====================

Usually the files involved when adding a new functionality are:

.. code-block:: plain

    psutil/__init__.py                   # main psutil namespace
    psutil/_ps{platform}.py              # python platform wrapper
    psutil/_psutil_{platform}.c          # C platform extension
    psutil/_psutil_{platform}.h          # C header file
    psutil/tests/test_process|system.py  # main test suite
    psutil/tests/test_{platform}.py      # platform specific test suite

Typical process occurring when adding a new functionality (API):

- define the new function in ``psutil/__init__.py``.
- write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. ``psutil/_pslinux.py``).
- if the change requires C, write the C implementation in
  ``psutil/_psutil_{platform}.c`` (e.g. ``psutil/_psutil_linux.c``).
- write a generic test in ``psutil/tests/test_system.py`` or
  ``psutil/tests/test_process.py``.
- if possible, write a platform specific test in
  ``psutil/tests/test_{platform}.py`` (e.g. ``test_linux.py``).
  This usually means testing the return value of the new feature against
  a system CLI tool.
- update doc in ``doc/index.py``.
- update ``HISTORY.rst``.
- update ``README.rst`` (if necessary).
- make a pull request.

===================
Make a pull request
===================

- fork psutil
- create your feature branch (``git checkout -b my-new-feature``)
- commit your changes (``git commit -am 'add some feature'``)
- push to the branch (``git push origin my-new-feature``)
- create a new pull request

======================
Continuous integration
======================

All of the services listed below are automatically run on ``git push``.

Unit tests
----------

Tests are automatically run for every GIT push on **Linux**, **OSX** and
**Windows** by using:

- `Travis <https://travis-ci.org/giampaolo/psutil>`_ (Linux, OSX)
- `Appveyor <https://ci.appveyor.com/project/giampaolo/psutil>`_ (Windows)

Test files controlling these are
`.travis.yml <https://github.com/giampaolo/psutil/blob/master/.travis.yml>`_
and
`appveyor.yml <https://github.com/giampaolo/psutil/blob/master/appveyor.yml>`_.
Both services run psutil test suite against all supported python version
(2.6 - 3.6).
Two icons in the home page (README) always show the build status:

.. image:: https://img.shields.io/travis/giampaolo/psutil/master.svg?maxAge=3600&label=Linux%20/%20OSX
    :target: https://travis-ci.org/giampaolo/psutil
    :alt: Linux tests (Travis)

.. image:: https://img.shields.io/appveyor/ci/giampaolo/psutil/master.svg?maxAge=3600&label=Windows
    :target: https://ci.appveyor.com/project/giampaolo/psutil
    :alt: Windows tests (Appveyor)

OSX, BSD, AIX and Solaris are currently tested manually (sigh!).

Test coverage
-------------

Test coverage is provided by `coveralls.io <https://coveralls.io/github/giampaolo/psutil>`_,
it is controlled via `.travis.yml <https://github.com/giampaolo/psutil/blob/master/.travis.yml>`_
and it is updated on every git push.
An icon in the home page (README) always shows the last coverage percentage:

.. image:: https://coveralls.io/repos/giampaolo/psutil/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/giampaolo/psutil?branch=master
    :alt: Test coverage (coverall.io)

=============
Documentation
=============

- doc source code is written in a single file: `/docs/index.rst <https://raw.githubusercontent.com/giampaolo/psutil/master/docs/index.rst>`_.
- it uses `RsT syntax <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_
  and it's built with `sphinx <http://sphinx-doc.org/>`_.
- doc can be built with ``make setup-dev-env; cd docs; make html``.
- public doc is hosted on http://psutil.readthedocs.io/

=======================
Releasing a new version
=======================

These are notes for myself (Giampaolo):

- ``make release``
- post announce (``make print-announce``) on psutil and python-announce mailing
  lists, twitter, g+, blog.

=============
FreeBSD notes
=============

- setup:

.. code-block:: bash

  $ pkg install python python3 gcc git vim screen bash
  $ chsh -s /usr/local/bin/bash user  # set bash as default shell

- ``/usr/src`` contains the source codes for all installed CLI tools (grep in it).
