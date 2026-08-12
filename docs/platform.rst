Platform support
================

Python
^^^^^^

.. list-table::
   :class: wide-table
   :header-rows: 1

   * - Feature
     - Support
     - Notes
   * - Minimum Python version
     - 3.8
     - last version supporting 3.6 / 3.7 is
       `psutil 7.2.2 <https://pypi.org/project/psutil/7.2.2/>`_ (Jan 2026)
   * - PyPy
     - yes
     - not tested on CI
   * - Free-threaded Python
     - yes
     - ``cp314t`` wheels are published
   * - Stable ABI (abi3)
     - yes
     - ``cp38-abi3`` wheels support CPython 3.8+
   * - Inline type hints
     - yes
     -
   * - Sub-interpreters
     - partial
     - legacy shared-GIL sub-interpreters work; ``concurrent.interpreters``
       does not (:gh:`2576`)
   * - PEP 561 (``py.typed``)
     - no
     -
   * - Python 2.7
     - no
     - last version supporting it is
       `psutil 6.1.1 <https://pypi.org/project/psutil/6.1.1/>`_ (Dec 2024)

Operating systems
^^^^^^^^^^^^^^^^^

.. list-table::
   :class: wide-table
   :header-rows: 1

   * - Platform
     - Minimum version
     - Released
     - Enforcement
     - CI coverage
   * - Linux
     - 2.6.13 (soft)
     - 2005
     - graceful fallbacks; no hard check
     - yes
   * - Windows
     - 10
     - 2015
     - hard check at import and build time
     - yes
   * - macOS
     - 10.7 (Lion)
     - 2011
     - ``MAC_OS_X_VERSION_MIN_REQUIRED`` in C
     - yes
   * - FreeBSD
     - 12.0
     - 2018
     - graceful fallbacks via ``#if __FreeBSD_version``
     - yes
   * - NetBSD
     - 5.0
     - 2009
     - graceful fallbacks via ``#if __NetBSD_Version__``
     - yes
   * - OpenBSD
     - unknown
     -
     -
     - yes
   * - SunOS / Solaris
     - 11
     - 2011
     -
     - memleak tests only
   * - AIX
     - unknown
     -
     -
     - no

Except where a hard minimum is enforced, older releases may also work but are
not guaranteed to be supported.

Architectures
^^^^^^^^^^^^^

.. list-table::
   :class: wide-table
   :header-rows: 1

   * - Architecture
     - CI coverage
     - Prebuilt wheels
     - Manual testing
   * - x86_64
     - Linux, Windows, macOS
     - Linux, Windows, macOS
     -
   * - aarch64 / ARM64
     - Linux, Windows, macOS
     - Linux, Windows, macOS
     -
   * - ppc64le
     -
     - Linux
     - Debian 13
   * - s390x
     -
     - Linux
     -
   * - i686
     -
     -
     - Debian 13
   * - ppc64 (big endian)
     -
     -
     - Debian 14
   * - riscv64
     -
     -
     - Debian 13
   * - sparc64
     -
     -
     - Debian 14

Occasional manual testing is done on the
`GCC compile farm <https://portal.cfarm.net/>`_, which provides free shell
access to uncommon hardware.

On architectures without prebuilt wheels, psutil can be installed from source
(see :ref:`install_from_source`):

.. code-block:: bash

   pip install psutil --no-binary psutil

Linux wheels are published for both glibc (manylinux) and musl. The musl ones
cover x86_64 and aarch64 only.

Support history
^^^^^^^^^^^^^^^

.. list-table::
   :class: wide-table
   :header-rows: 1

   * - Version
     - Date
     - Change
   * - :pypi:`8.0.0`
     -
     - add wheels for Linux ppc64le and s390x
   * - :pypi:`8.0.0`
     -
     - drop Python 3.6 and 3.7
   * - :pypi:`8.0.0`
     -
     - drop PyPy older than 7.3.14 on Windows
   * - :pypi:`8.0.0`
     -
     - drop Windows Vista, 7, 8 and 8.1 (+ Server 2008 to 2012 R2)
   * - :pypi:`8.0.0`
     -
     - drop Intel wheel support for macOS < 10.15
   * - :pypi:`8.0.0`
     -
     - drop wheels for free-threaded Python 3.13
   * - :pypi:`7.2.0`
     - 2025-12
     - drop wheels for Linux musl
   * - :pypi:`7.1.2`
     - 2025-10
     - drop wheels for free-threaded Python
   * - :pypi:`7.1.2`
     - 2025-10
     - drop wheels for 32-bit Python (Linux and Windows)
   * - :pypi:`7.1.1`
     - 2025-10
     - drop SunOS 10
   * - :pypi:`7.1.0`
     - 2025-09
     - drop FreeBSD 8
   * - :pypi:`7.0.0`
     - 2025-02
     - drop Python 2.7
   * - :pypi:`5.9.6`
     - 2023-10
     - drop Python 3.4 and 3.5
   * - :pypi:`5.9.1`
     - 2022-05
     - drop Python 2.6
   * - :pypi:`5.9.0`
     - 2021-12
     - add MidnightBSD
   * - :pypi:`5.8.0`
     - 2020-12
     - add PyPy2 on Windows
   * - :pypi:`5.7.1`
     - 2020-07
     - add Windows Nano
   * - :pypi:`5.7.0`
     - 2020-02
     - drop Windows XP & Windows Server 2003
   * - :pypi:`5.7.0`
     - 2020-02
     - add PyPy3 on Windows
   * - :pypi:`5.4.0`
     - 2017-11
     - add AIX
   * - :pypi:`3.4.1`
     - 2016-01
     - add NetBSD
   * - :pypi:`3.3.0`
     - 2015-11
     - add OpenBSD
   * - :pypi:`1.0.0`
     - 2013-07
     - add Solaris
   * - :pypi:`0.1.1`
     - 2009-03
     - add FreeBSD
   * - :pypi:`0.1.0`
     - 2009-01
     - add Linux, Windows, macOS
