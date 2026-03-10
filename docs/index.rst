.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola' <grodola@gmail.com>
.. include:: _links.rst


.. toctree::
   :maxdepth: 2

   Install <install>
   API Reference <api>
   Recipes <recipes>
   Development guide <devguide>

psutil documentation
====================

Quick links
-----------

- `Home page <https://github.com/giampaolo/psutil>`__
- `Install <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`_
- `Forum <http://groups.google.com/group/psutil/topics>`__
- `Download <https://pypi.org/project/psutil/#files>`__
- `Blog <https://gmpy.dev/tags/psutil>`__
- `Contributing <https://github.com/giampaolo/psutil/blob/master/CONTRIBUTING.md>`__
- `Development guide <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`_
- `What's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst>`__

About
-----

psutil (python system and process utilities) is a cross-platform library for
retrieving information on running
**processes** and **system utilization** (CPU, memory, disks, network, sensors)
in **Python**.
It is useful mainly for **system monitoring**, **profiling**, **limiting
process resources** and the **management of running processes**.
It implements many functionalities offered by UNIX command line tools
such as: *ps, top, lsof, netstat, ifconfig, who, df, kill, free, nice,
ionice, iostat, iotop, uptime, pidof, tty, taskset, pmap*.
psutil currently supports the following platforms:

- **Linux**
- **Windows**
- **macOS**
- **FreeBSD, OpenBSD**, **NetBSD**
- **Sun Solaris**
- **AIX**

Supported Python versions are cPython 3.7+ and `PyPy <https://pypy.org/>`__.
Latest psutil version supporting Python 2.7 is
`psutil 6.1.1 <https://pypi.org/project/psutil/6.1.1/>`__.

The psutil documentation you're reading is distributed as a single HTML page.

Sponsors
========

.. raw:: html

    <table border="0" cellpadding="10" cellspacing="0">
      <tr>
        <td align="center">
          <a href="https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme">
            <img width="200" src="https://github.com/giampaolo/psutil/raw/master/docs/_static/tidelift-logo.svg">
          </a>
        </td>
        <td align="center">
          <a href="https://sansec.io/">
            <img src="https://sansec.io/assets/images/logo.svg">
          </a>
        </td>
        <td align="center">
          <a href="https://www.apivoid.com/">
            <img width="180" src="https://gmpy.dev/images/apivoid-logo.svg">
          </a>
        </td>
      </tr>
    </table>

    <sup><a href="https://github.com/sponsors/giampaolo">add your logo</a></sup>

Funding
=======

While psutil is free software and will always be, the project would benefit
immensely from some funding.
psutil is among the `top 100 <https://clickpy.clickhouse.com/dashboard/psutil>`__
most-downloaded Python packages, and keeping up with bug reports, user support,
and ongoing maintenance has become increasingly difficult to sustain as a
one-person effort.
If you're a company that's making significant use of psutil you can consider
becoming a sponsor via `GitHub <https://github.com/sponsors/giampaolo>`__,
`Open Collective <https://opencollective.com/psutil>`__ or
`PayPal <https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A9ZS7PKKRM3S8>`__.
Sponsors can have their logo displayed here and in the psutil `documentation <https://psutil.readthedocs.io>`__.

FAQs
====

* Q: Why do I get :class:`AccessDenied` for certain processes?
* A: This may happen when you query processes owned by another user,
  especially on macOS (see issue `#883`_) and Windows.
  Unfortunately there's not much you can do about this except running the
  Python process with higher privileges.
  On Unix you may run the Python process as root or use the SUID bit
  (``ps`` and ``netstat`` does this).
  On Windows you may run the Python process as NT AUTHORITY\\SYSTEM or install
  the Python script as a Windows service (ProcessHacker does this).

* Q: is MinGW supported on Windows?
* A: no, you should Visual Studio (see `development guide <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`_).

Debug mode
==========

If you want to debug unusual situations or want to report a bug, it may be
useful to enable debug mode via ``PSUTIL_DEBUG`` environment variable.
In this mode, psutil may (or may not) print additional information to stderr.
Usually these are error conditions which are not severe, and hence are ignored
(instead of crashing).
Unit tests automatically run with debug mode enabled.
On UNIX:

::

  $ PSUTIL_DEBUG=1 python3 script.py
  psutil-debug [psutil/_psutil_linux.c:150]> setmntent() failed (ignored)

On Windows:

::

  set PSUTIL_DEBUG=1 python.exe script.py
  psutil-debug [psutil/arch/windows/proc.c:90]> NtWow64ReadVirtualMemory64(pbi64.PebBaseAddress) -> 998 (Unknown error) (ignored)

Python 2.7
==========

Latest version spporting Python 2.7 is `psutil 6.1.1 <https://pypi.org/project/psutil/6.1.1/>`__.
The 6.1.X serie may receive critical bug-fixes but no new features. It will
be maintained in the dedicated
`python2 <https://github.com/giampaolo/psutil/tree/python2>`__ branch.
To install it:

::

    $ python2 -m pip install psutil==6.1.*

Security
========

To report a security vulnerability, please use the `Tidelift security
contact`_.  Tidelift will coordinate the fix and disclosure.

Development guide
=================

If you want to develop psutil take a look at the `DEVGUIDE.rst`_.

Platforms support history
=========================

* psutil 8.0.0 (XXXX-XX): drop Python 3.6
* psutil 7.2.0 (2025-12): publish wheels for Linux musl
* psutil 7.1.2 (2025-10): publish wheels for free-threaded Python
* psutil 7.1.2 (2025-10): no longer publish wheels for 32-bit Python
  (**Linux** and **Windows**)
* psutil 7.1.1 (2025-10): drop **SunOS 10**
* psutil 7.1.0 (2025-09): drop **FreeBSD 8**
* psutil 7.0.0 (2025-02): drop Python 2.7
* psutil 5.9.6 (2023-10): drop Python 3.4 and 3.5
* psutil 5.9.1 (2022-05): drop Python 2.6
* psutil 5.9.0 (2021-12): add **MidnightBSD**
* psutil 5.8.0 (2020-12): add **PyPy 2** on Windows
* psutil 5.7.1 (2020-07): add **Windows Nano**
* psutil 5.7.0 (2020-02): drop Windows XP & Windows Server 2003
* psutil 5.7.0 (2020-02): add **PyPy 3** on Windows
* psutil 5.4.0 (2017-11): add **AIX**
* psutil 3.4.1 (2016-01): add **NetBSD**
* psutil 3.3.0 (2015-11): add **OpenBSD**
* psutil 1.0.0 (2013-07): add **Solaris**
* psutil 0.1.1 (2009-03): add **FreeBSD**
* psutil 0.1.0 (2009-01): add **Linux, Windows, macOS**

Supported Python versions at the time of writing are cPython 2.7, 3.6+ and
PyPy3.

Timeline
========

- 2026-02-08:
  `7.2.3 <https://pypi.org/project/psutil/7.2.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#723>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.2.2...release-7.2.3#files_bucket>`__
- 2026-01-28:
  `7.2.2 <https://pypi.org/project/psutil/7.2.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#722>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.2.1...release-7.2.2#files_bucket>`__
- 2025-12-29:
  `7.2.1 <https://pypi.org/project/psutil/7.2.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#721>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.2.0...release-7.2.1#files_bucket>`__
- 2025-12-23:
  `7.2.0 <https://pypi.org/project/psutil/7.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#720>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.1.3...release-7.2.0#files_bucket>`__
- 2025-11-02:
  `7.1.3 <https://pypi.org/project/psutil/7.1.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#713>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.1.2...release-7.1.3#files_bucket>`__
- 2025-10-25:
  `7.1.2 <https://pypi.org/project/psutil/7.1.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#712>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.1.1...release-7.1.2#files_bucket>`__
- 2025-10-19:
  `7.1.1 <https://pypi.org/project/psutil/7.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#711>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.1.0...release-7.1.1#files_bucket>`__
- 2025-09-17:
  `7.1.0 <https://pypi.org/project/psutil/7.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#710>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-7.0.0...release-7.1.1#files_bucket>`__
- 2025-02-13:
  `7.0.0 <https://pypi.org/project/psutil/7.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#700>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-6.1.1...release-7.0.0#files_bucket>`__
- 2024-12-19:
  `6.1.1 <https://pypi.org/project/psutil/6.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#611>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-6.1.0...release-6.1.1#files_bucket>`__
- 2024-10-17:
  `6.1.0 <https://pypi.org/project/psutil/6.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#610>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-6.0.0...release-6.1.0#files_bucket>`__
- 2024-06-18:
  `6.0.0 <https://pypi.org/project/psutil/6.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#600>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.8...release-6.0.0#files_bucket>`__
- 2024-01-19:
  `5.9.8 <https://pypi.org/project/psutil/5.9.8/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#598>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.7...release-5.9.8#files_bucket>`__
- 2023-12-17:
  `5.9.7 <https://pypi.org/project/psutil/5.9.7/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#597>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.6...release-5.9.7#files_bucket>`__
- 2023-10-15:
  `5.9.6 <https://pypi.org/project/psutil/5.9.6/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#596>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.5...release-5.9.6#files_bucket>`__
- 2023-04-17:
  `5.9.5 <https://pypi.org/project/psutil/5.9.5/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#595>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.4...release-5.9.5#files_bucket>`__
- 2022-11-07:
  `5.9.4 <https://pypi.org/project/psutil/5.9.4/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#594>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.3...release-5.9.4#files_bucket>`__
- 2022-10-18:
  `5.9.3 <https://pypi.org/project/psutil/5.9.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#593>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.2...release-5.9.3#files_bucket>`__
- 2022-09-04:
  `5.9.2 <https://pypi.org/project/psutil/5.9.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#592>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.1...release-5.9.2#files_bucket>`__
- 2022-05-20:
  `5.9.1 <https://pypi.org/project/psutil/5.9.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#591>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.9.0...release-5.9.1#files_bucket>`__
- 2021-12-29:
  `5.9.0 <https://pypi.org/project/psutil/5.9.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#590>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.8.0...release-5.9.0#files_bucket>`__
- 2020-12-19:
  `5.8.0 <https://pypi.org/project/psutil/5.8.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#580>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.7.3...release-5.8.0#files_bucket>`__
- 2020-10-24:
  `5.7.3 <https://pypi.org/project/psutil/5.7.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#573>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.7.2...release-5.7.3#files_bucket>`__
- 2020-07-15:
  `5.7.2 <https://pypi.org/project/psutil/5.7.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#572>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.7.1...release-5.7.2#files_bucket>`__
- 2020-07-15:
  `5.7.1 <https://pypi.org/project/psutil/5.7.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#571>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.7.0...release-5.7.1#files_bucket>`__
- 2020-02-18:
  `5.7.0 <https://pypi.org/project/psutil/5.7.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#570>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.7...release-5.7.0#files_bucket>`__
- 2019-11-26:
  `5.6.7 <https://pypi.org/project/psutil/5.6.7/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#567>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.6...release-5.6.7#files_bucket>`__
- 2019-11-25:
  `5.6.6 <https://pypi.org/project/psutil/5.6.6/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#566>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.5...release-5.6.6#files_bucket>`__
- 2019-11-06:
  `5.6.5 <https://pypi.org/project/psutil/5.6.5/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#565>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.4...release-5.6.5#files_bucket>`__
- 2019-11-04:
  `5.6.4 <https://pypi.org/project/psutil/5.6.4/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#564>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.3...release-5.6.4#files_bucket>`__
- 2019-06-11:
  `5.6.3 <https://pypi.org/project/psutil/5.6.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#563>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.2...release-5.6.3#files_bucket>`__
- 2019-04-26:
  `5.6.2 <https://pypi.org/project/psutil/5.6.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#562>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.1...release-5.6.2#files_bucket>`__
- 2019-03-11:
  `5.6.1 <https://pypi.org/project/psutil/5.6.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#561>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.6.0...release-5.6.1#files_bucket>`__
- 2019-03-05:
  `5.6.0 <https://pypi.org/project/psutil/5.6.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#560>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.5.1...release-5.6.0#files_bucket>`__
- 2019-02-15:
  `5.5.1 <https://pypi.org/project/psutil/5.5.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#551>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.5.0...release-5.5.1#files_bucket>`__
- 2019-01-23:
  `5.5.0 <https://pypi.org/project/psutil/5.5.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#550>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.8...release-5.5.0#files_bucket>`__
- 2018-10-30:
  `5.4.8 <https://pypi.org/project/psutil/5.4.8/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#548>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.7...release-5.4.8#files_bucket>`__
- 2018-08-14:
  `5.4.7 <https://pypi.org/project/psutil/5.4.7/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#547>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.6...release-5.4.7#files_bucket>`__
- 2018-06-07:
  `5.4.6 <https://pypi.org/project/psutil/5.4.6/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#546>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.5...release-5.4.6#files_bucket>`__
- 2018-04-13:
  `5.4.5 <https://pypi.org/project/psutil/5.4.5/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#545>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.4...release-5.4.5#files_bucket>`__
- 2018-04-13:
  `5.4.4 <https://pypi.org/project/psutil/5.4.4/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#544>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.3...release-5.4.4#files_bucket>`__
- 2018-01-01:
  `5.4.3 <https://pypi.org/project/psutil/5.4.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#543>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.2...release-5.4.3#files_bucket>`__
- 2017-12-07:
  `5.4.2 <https://pypi.org/project/psutil/5.4.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#542>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.1...release-5.4.2#files_bucket>`__
- 2017-11-08:
  `5.4.1 <https://pypi.org/project/psutil/5.4.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#541>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.4.0...release-5.4.1#files_bucket>`__
- 2017-10-12:
  `5.4.0 <https://pypi.org/project/psutil/5.4.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#540>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.3.1...release-5.4.0#files_bucket>`__
- 2017-09-10:
  `5.3.1 <https://pypi.org/project/psutil/5.3.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#531>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.3.0...release-5.3.1#files_bucket>`__
- 2017-09-01:
  `5.3.0 <https://pypi.org/project/psutil/5.3.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#530>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.2.2...release-5.3.0#files_bucket>`__
- 2017-04-10:
  `5.2.2 <https://pypi.org/project/psutil/5.2.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#522>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.2.1...release-5.2.2#files_bucket>`__
- 2017-03-24:
  `5.2.1 <https://pypi.org/project/psutil/5.2.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#521>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.2.0...release-5.2.1#files_bucket>`__
- 2017-03-05:
  `5.2.0 <https://pypi.org/project/psutil/5.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#520>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.1.3...release-5.2.0#files_bucket>`__
- 2017-02-07:
  `5.1.3 <https://pypi.org/project/psutil/5.1.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#513>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.1.2...release-5.1.3#files_bucket>`__
- 2017-02-03:
  `5.1.2 <https://pypi.org/project/psutil/5.1.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#512>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.1.1...release-5.1.2#files_bucket>`__
- 2017-02-03:
  `5.1.1 <https://pypi.org/project/psutil/5.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#511>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.1.0...release-5.1.1#files_bucket>`__
- 2017-02-01:
  `5.1.0 <https://pypi.org/project/psutil/5.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#510>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.0.1...release-5.1.0#files_bucket>`__
- 2016-12-21:
  `5.0.1 <https://pypi.org/project/psutil/5.0.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#501>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-5.0.0...release-5.0.1#files_bucket>`__
- 2016-11-06:
  `5.0.0 <https://pypi.org/project/psutil/5.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#500>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.4.2...release-5.0.0#files_bucket>`__
- 2016-10-05:
  `4.4.2 <https://pypi.org/project/psutil/4.4.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#442>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.4.1...release-4.4.2#files_bucket>`__
- 2016-10-25:
  `4.4.1 <https://pypi.org/project/psutil/4.4.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#441>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.4.0...release-4.4.1#files_bucket>`__
- 2016-10-23:
  `4.4.0 <https://pypi.org/project/psutil/4.4.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#440>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.3.1...release-4.4.0#files_bucket>`__
- 2016-09-01:
  `4.3.1 <https://pypi.org/project/psutil/4.3.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#431>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.3.0...release-4.3.1#files_bucket>`__
- 2016-06-18:
  `4.3.0 <https://pypi.org/project/psutil/4.3.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#430>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.2.0...release-4.3.0#files_bucket>`__
- 2016-05-14:
  `4.2.0 <https://pypi.org/project/psutil/4.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#420>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.1.0...release-4.2.0#files_bucket>`__
- 2016-03-12:
  `4.1.0 <https://pypi.org/project/psutil/4.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#410>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-4.0.0...release-4.1.0#files_bucket>`__
- 2016-02-17:
  `4.0.0 <https://pypi.org/project/psutil/4.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#400>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.4.2...release-4.0.0#files_bucket>`__
- 2016-01-20:
  `3.4.2 <https://pypi.org/project/psutil/3.4.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#342>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.4.1...release-3.4.2#files_bucket>`__
- 2016-01-15:
  `3.4.1 <https://pypi.org/project/psutil/3.4.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#341>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.3.0...release-3.4.1#files_bucket>`__
- 2015-11-25:
  `3.3.0 <https://pypi.org/project/psutil/3.3.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#330>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.2.2...release-3.3.0#files_bucket>`__
- 2015-10-04:
  `3.2.2 <https://pypi.org/project/psutil/3.2.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#322>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.2.1...release-3.2.2#files_bucket>`__
- 2015-09-03:
  `3.2.1 <https://pypi.org/project/psutil/3.2.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#321>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.2.0...release-3.2.1#files_bucket>`__
- 2015-09-02:
  `3.2.0 <https://pypi.org/project/psutil/3.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#320>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.1.1...release-3.2.0#files_bucket>`__
- 2015-07-15:
  `3.1.1 <https://pypi.org/project/psutil/3.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#311>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.1.0...release-3.1.1#files_bucket>`__
- 2015-07-15:
  `3.1.0 <https://pypi.org/project/psutil/3.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#310>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.0.1...release-3.1.0#files_bucket>`__
- 2015-06-18:
  `3.0.1 <https://pypi.org/project/psutil/3.0.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#301>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-3.0.0...release-3.0.1#files_bucket>`__
- 2015-06-13:
  `3.0.0 <https://pypi.org/project/psutil/3.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#300>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.2.1...release-3.0.0#files_bucket>`__
- 2015-02-02:
  `2.2.1 <https://pypi.org/project/psutil/2.2.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#221>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.2.0...release-2.2.1#files_bucket>`__
- 2015-01-06:
  `2.2.0 <https://pypi.org/project/psutil/2.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#220>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.1.3...release-2.2.0#files_bucket>`__
- 2014-09-26:
  `2.1.3 <https://pypi.org/project/psutil/2.1.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#213>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.1.2...release-2.1.3#files_bucket>`__
- 2014-09-21:
  `2.1.2 <https://pypi.org/project/psutil/2.1.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#212>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.1.1...release-2.1.2#files_bucket>`__
- 2014-04-30:
  `2.1.1 <https://pypi.org/project/psutil/2.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#211>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.1.0...release-2.1.1#files_bucket>`__
- 2014-04-08:
  `2.1.0 <https://pypi.org/project/psutil/2.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#210>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-2.0.0...release-2.1.0#files_bucket>`__
- 2014-03-10:
  `2.0.0 <https://pypi.org/project/psutil/2.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#200>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.2.1...release-2.0.0#files_bucket>`__
- 2013-11-25:
  `1.2.1 <https://pypi.org/project/psutil/1.2.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#121>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.2.0...release-1.2.1#files_bucket>`__
- 2013-11-20:
  `1.2.0 <https://pypi.org/project/psutil/1.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#120>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.1.2...release-1.2.0#files_bucket>`__
- 2013-10-22:
  `1.1.2 <https://pypi.org/project/psutil/1.1.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#112>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.1.1...release-1.1.2#files_bucket>`__
- 2013-10-08:
  `1.1.1 <https://pypi.org/project/psutil/1.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#111>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.1.0...release-1.1.1#files_bucket>`__
- 2013-09-28:
  `1.1.0 <https://pypi.org/project/psutil/1.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#110>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.0.1...release-1.1.0#files_bucket>`__
- 2013-07-12:
  `1.0.1 <https://pypi.org/project/psutil/1.0.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#101>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-1.0.0...release-1.0.1#files_bucket>`__
- 2013-07-10:
  `1.0.0 <https://pypi.org/project/psutil/1.0.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#100>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.7.1...release-1.0.0#files_bucket>`__
- 2013-05-03:
  `0.7.1 <https://pypi.org/project/psutil/0.7.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#071>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.7.0...release-0.7.1#files_bucket>`__
- 2013-04-12:
  `0.7.0 <https://pypi.org/project/psutil/0.7.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#070>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.6.1...release-0.7.0#files_bucket>`__
- 2012-08-16:
  `0.6.1 <https://pypi.org/project/psutil/0.6.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#061>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.6.0...release-0.6.1#files_bucket>`__
- 2012-08-13:
  `0.6.0 <https://pypi.org/project/psutil/0.6.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#060>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.5.1...release-0.6.0#files_bucket>`__
- 2012-06-29:
  `0.5.1 <https://pypi.org/project/psutil/0.5.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#051>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.5.0...release-0.5.1#files_bucket>`__
- 2012-06-27:
  `0.5.0 <https://pypi.org/project/psutil/0.5.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#050>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.4.1...release-0.5.0#files_bucket>`__
- 2011-12-14:
  `0.4.1 <https://pypi.org/project/psutil/0.4.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#041>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.4.0...release-0.4.1#files_bucket>`__
- 2011-10-29:
  `0.4.0 <https://pypi.org/project/psutil/0.4.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#040>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.3.0...release-0.4.0#files_bucket>`__
- 2011-07-08:
  `0.3.0 <https://pypi.org/project/psutil/0.3.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#030>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.2.1...release-0.3.0#files_bucket>`__
- 2011-03-20:
  `0.2.1 <https://pypi.org/project/psutil/0.2.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#021>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.2.0...release-0.2.1#files_bucket>`__
- 2010-11-13:
  `0.2.0 <https://pypi.org/project/psutil/0.2.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#020>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.1.3...release-0.2.0#files_bucket>`__
- 2010-03-02:
  `0.1.3 <https://pypi.org/project/psutil/0.1.3/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#013>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.1.2...release-0.1.3#files_bucket>`__
- 2009-05-06:
  `0.1.2 <https://pypi.org/project/psutil/0.1.2/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#012>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.1.1...release-0.1.2#files_bucket>`__
- 2009-03-06:
  `0.1.1 <https://pypi.org/project/psutil/0.1.1/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#011>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/release-0.1.0...release-0.1.1#files_bucket>`__
- 2009-01-27:
  `0.1.0 <https://pypi.org/project/psutil/0.1.0/#files>`__ -
  `what's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst#010>`__ -
  `diff <https://github.com/giampaolo/psutil/compare/d84cc9a783d977368a64016cdb3568d2c9bceacc...release-0.1.0#files_bucket>`__
