Platform support
================

Python
^^^^^^

**Current Python:** 3.7 and PyPy3.

**Python 2.7**: latest psutil version supporting it is
`psutil 6.1.1 <https://pypi.org/project/psutil/6.1.1/>`_ (Dec 2024).
The 6.1.X series may still receive critical bug-fixes but no new features.
To install psutil on Python 2.7 run:

.. code-block:: none

    python2 -m pip install psutil==6.1.*

Operating systems
^^^^^^^^^^^^^^^^^

================  ================  ====  =================================================  =========
Platform          Minimum version   Year  How enforced                                       CI tested
================  ================  ====  =================================================  =========
Linux             2.6.13 (soft)     2005  graceful fallbacks; no hard check                  yes
Windows           Vista             2007  hard check at import + build time                  yes
macOS             10.7 (Lion)       2011  ``MAC_OS_X_VERSION_MIN_REQUIRED`` in C             yes
FreeBSD           12.0              2018  graceful fallbacks via ``#if __FreeBSD_version``   yes
NetBSD            5.0               2009  graceful fallbacks via ``#if __NetBSD_Version__``  yes
OpenBSD           unknown                                                                    yes
SunOS / Solaris   unknown                                                                    memleak tests only
AIX               unknown                                                                    no
================  ================  ====  =================================================  =========

Note: psutil may work on older versions of the above platforms but it is not
guaranteed.

Architectures
^^^^^^^^^^^^^

Supported CPU architectures and platforms tested in CI or with prebuilt wheels:

================  ===========================  ===========================
Architecture      CI-tested platforms          Wheel builds
================  ===========================  ===========================
x86_64            Linux, macOS, Windows        Linux, macOS, Windows
aarch64 / ARM64   Linux, macOS, Windows        Linux, macOS, Windows
================  ===========================  ===========================

Notes:

- Linux wheels are built for both glibc (manylinux) and musl.
- macOS wheels are universal2 (include both x86_64 and arm64 slices).
- Windows wheels are labeled AMD64 or ARM64 according to architecture.
- Other architectures (i686, ppc64le, s390x, riscv64, ...) are supported
  but not CI-tested. They can be compiled from the source tarball
  (``pip install psutil --no-binary psutil``).

Support history
^^^^^^^^^^^^^^^

* psutil 8.0.0 (2026-XX): drop Python 3.6
* psutil 7.2.0 (2025-12): publish wheels for **Linux musl**
* psutil 7.1.2 (2025-10): publish wheels for **free-threaded Python**
* psutil 7.1.2 (2025-10): no longer publish wheels for 32-bit Python (Linux and Windows)
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
