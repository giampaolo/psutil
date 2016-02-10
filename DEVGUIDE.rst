=====
Setup
=====

If you plan on hacking on psutil this is what you're supposed to do first:

- git clone the repo: ``git clone git@github.com:giampaolo/psutil.git``.
- take a look at `install instructions <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`_
  and satisfy system dependencies first.
- bear in mind that ``make`` (see `Makefile <https://github.com/giampaolo/psutil/blob/master/Makefile>`_)
  is the designated tool to run tests, build etc. and that it is also available
  on Windows (see `make.bat <https://github.com/giampaolo/psutil/blob/master/make.bat>`_).
- (UNIX only) run ``make install-git-hooks``: this will reject your commit
  if it's not PEP8 compliant.
- run ``make setup-dev-env``: this will install test deps (e.g. mock lib)
  and other useful tools (e.g. ipdb, flake8).
- run ``make test`` to run tests.

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

Some useful make commands:

- ``make install``
- ``make test``
- ``make test-memleaks``
- ``make coverage``
- ``make flake8``

====================
Adding a new feature
====================

Usually the files involved when adding a new functionality are:

.. code-block:: plain

    psutil/__init__.py            # main psutil namespace
    psutil/_ps{platform}.py       # python platform wrapper
    psutil/_psutil_{platform}.c   # C platform extension
    psutil/_psutil_{platform}.h   # C header file
    test/test_process|system.py   # main test suite
    test/test_{platform}.py       # platform specific test suite

Typical process occurring when adding a new functionality (API):

- define the new function in ``psutil/__init__.py``.
- write the platform specific implementation in ``psutil/_ps{platform}.py``
  (e.g. ``psutil/_pslinux.py``).
- if the change requires C code write the C implementation in
  ``psutil/_psutil_{platform}.c`` (e.g. ``psutil/_psutil_linux.c``).
- write a cross platform test in ``psutil/tests/test_{platform}.py``
  (e.g. ``test_linux.py``).
- update doc.
- make a pull request.

======================
Continuous integration
======================

All of the services listed below are automatically run on ``git push``.

Tests
-----

Tests are automatically run for every GIT push on **Linux**, **OSX** and
**Windows** by using:

- `Travis <https://travis-ci.org/giampaolo/psutil>`_ (Linux, OSX)
- `Appveyor <https://ci.appveyor.com/project/giampaolo/psutil>`_ (Windows)

Test files controlling these are
`.travis.yml <https://github.com/giampaolo/psutil/blob/master/.travis.yml>`_
and
`appveyor.yml <https://github.com/giampaolo/psutil/blob/master/appveyor.yml>`_.
Both services run psutil test suite against all supported python version
(2.6 - 3.4).
Two icons in the home page (README) always show the build status:

.. image:: https://api.travis-ci.org/giampaolo/psutil.png?branch=master
    :target: https://travis-ci.org/giampaolo/psutil
    :alt: Linux tests (Travis)

.. image:: https://ci.appveyor.com/api/projects/status/qdwvw7v1t915ywr5/branch/master?svg=true
    :target: https://ci.appveyor.com/project/giampaolo/psutil
    :alt: Windows tests (Appveyor)

OSX, FreeBSD and Solaris are currently tested manually (sigh!).

Test coverage
-------------

Test coverage is provided by `coveralls.io <https://coveralls.io/github/giampaolo/psutil>`_
and it is controlled via `.travis.yml <https://github.com/giampaolo/psutil/blob/master/.travis.yml>`_.
An icon in the home page (README) always shows the last coverage percentage:

.. image:: https://coveralls.io/repos/giampaolo/psutil/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/giampaolo/psutil?branch=master
    :alt: Test coverage (coverall.io)


=============
Documentation
=============

- doc source code is in `/docs <https://github.com/giampaolo/psutil/tree/master/docs>`_
  directory.
- it uses `RsT syntax <http://docutils.sourceforge.net/docs/user/rst/quickref.html>`_
  and it's built with `sphinx <http://sphinx-doc.org/>`_.
- doc can be built with ``make setup-dev-env; cd docs; make html``.
- public doc is hosted on http://pythonhosted.org/psutil/.
- it is uploaded on every new release with ``make upload-doc``.

=======================
Releasing a new version
=======================

These are note for myself (Giampaolo):

- make sure all tests pass and all builds are green.
- upload source tarball on PYPI with ``make upload-src``.
- upload exe and wheel files for windows on PYPI with ``make upload-all``.
- upload updated doc on http://pythonhosted.org/psutil with ``make upload-doc``.
- GIT tag the new release with ``make git-tag-release``.
- post on psutil and python-announce mailing lists, twitter, g+, blog.
