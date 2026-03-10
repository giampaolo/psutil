Platform support
================

Python
------

Supported Python versions: cPython 3.7+ and PyPy3.

Python 2.7
----------

Latest psutil version supporting Python 2.7 is `psutil 6.1.1 <https://pypi.org/project/psutil/6.1.1/>`__.
The 6.1.X serie may receive critical bug-fixes but no new features. It will
be maintained in the dedicated
`python2 <https://github.com/giampaolo/psutil/tree/python2>`__ branch.
To install it:

::

    $ python2 -m pip install psutil==6.1.*

History
-------

* psutil 8.0.0 (2026-XX): drop Python 3.6
* psutil 7.2.0 (2025-12): publish Linux musl wheels
* psutil 7.1.2 (2025-10): publish free-threaded Python wheels
* psutil 7.1.2 (2025-10): no longer publish wheels for 32-bit Python (Linux and
  Windows)
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
