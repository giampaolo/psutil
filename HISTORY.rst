*Bug tracker at https://github.com/giampaolo/psutil/issues*

6.0.0 (IN DEVELOPMENT)
======================

**Enhancements**

- 2109_: ``maxfile`` and ``maxpath`` fields were removed from the namedtuple
  returned by `disk_partitions()`_. Reason: on network filesystems (NFS) this
  can potentially take a very long time to complete.
- 2366_, [Windows]: log debug message when using slower process APIs.
- 2375_, [macOS]: provide arm64 wheels.  (patch by Matthieu Darbois)
- 2396_: `process_iter()`_ no longer pre-emptively checks whether PIDs have
  been reused. This makes `process_iter()`_ around 20x times faster.
- 2396_: a new ``psutil.process_iter.cache_clear()`` API can be used the clear
  `process_iter()`_ internal cache.
- 2401_, Support building with free-threaded CPython 3.13.
- 2407_: `Process.connections()`_ was renamed to `Process.net_connections()`_.
  The old name is still available, but it's deprecated (triggers a
  ``DeprecationWarning``) and will be removed in the future.

**Bug fixes**

- 2250_, [NetBSD]: `Process.cmdline()`_ sometimes fail with EBUSY. It usually
  happens for long cmdlines with lots of arguments. In this case retry getting
  the cmdline for up to 50 times, and return an empty list as last resort.
- 2254_, [Linux]: offline cpus raise NotImplementedError in cpu_freq() (patch
  by Shade Gladden)
- 2272_: Add pickle support to psutil Exceptions.
- 2359_, [Windows], [CRITICAL]: `pid_exists()`_ disagrees with `Process`_ on
  whether a pid exists when ERROR_ACCESS_DENIED.
- 2360_, [macOS]: can't compile on macOS < 10.13.  (patch by Ryan Schmidt)
- 2362_, [macOS]: can't compile on macOS 10.11.  (patch by Ryan Schmidt)
- 2365_, [macOS]: can't compile on macOS < 10.9.  (patch by Ryan Schmidt)
- 2395_, [OpenBSD]: `pid_exists()`_ erroneously return True if the argument is
  a thread ID (TID) instead of a PID (process ID).
- 2412_, [macOS]: can't compile on macOS 10.4 PowerPC due to missing `MNT_`
  constants.

**Porting notes**

Version 6.0.0 introduces some changes which affect backward compatibility:

- 2109_: the namedtuple returned by `disk_partitions()`_' no longer has
  ``maxfile`` and ``maxpath`` fields.
- 2396_: `process_iter()`_ no longer pre-emptively checks whether PIDs have
  been reused. If you want to check for PID reusage you are supposed to use
  `Process.is_running()`_ against the yielded `Process`_ instances. That will
  also automatically remove reused PIDs from `process_iter()`_ internal cache.
- 2407_: `Process.connections()`_ was renamed to `Process.net_connections()`_.
  The old name is still available, but it's deprecated (triggers a
  ``DeprecationWarning``) and will be removed in the future.

5.9.8
=====

2024-01-19

**Enhancements**

- 2343_, [FreeBSD]: filter `net_connections()`_ returned list in C instead of
  Python, and avoid to retrieve unnecessary connection types unless explicitly
  asked. E.g., on an IDLE system with few IPv6 connections this will run around
  4 times faster. Before all connection types (TCP, UDP, UNIX) were retrieved
  internally, even if only a portion was returned.
- 2342_, [NetBSD]: same as above (#2343) but for NetBSD.
- 2349_: adopted black formatting style.

**Bug fixes**

- 930_, [NetBSD], [critical]: `net_connections()`_ implementation was broken.
  It could either leak memory or core dump.
- 2340_, [NetBSD]: if process is terminated, `Process.cwd()`_ will return an
  empty string instead of raising `NoSuchProcess`_.
- 2345_, [Linux]: fix compilation on older compiler missing DUPLEX_UNKNOWN.
- 2222_, [macOS]: `cpu_freq()` now returns fixed values for `min` and `max`
  frequencies in all Apple Silicon chips.

5.9.7
=====

2023-12-17

**Enhancements**

- 2324_: enforce Ruff rule `raw-string-in-exception`, which helps providing
  clearer tracebacks when exceptions are raised by psutil.

**Bug fixes**

- 2325_, [PyPy]: psutil did not compile on PyPy due to missing
  `PyErr_SetExcFromWindowsErrWithFilenameObject` cPython API.

5.9.6
=====

2023-10-15

**Enhancements**

- 1703_: `cpu_percent()`_ and `cpu_times_percent()`_ are now thread safe,
  meaning they can be called from different threads and still return
  meaningful and independent results. Before, if (say) 10 threads called
  ``cpu_percent(interval=None)`` at the same time, only 1 thread out of 10
  would get the right result.
- 2266_: if `Process`_ class is passed a very high PID, raise `NoSuchProcess`_
  instead of OverflowError.  (patch by Xuehai Pan)
- 2246_: drop python 3.4 & 3.5 support.  (patch by Matthieu Darbois)
- 2290_: PID reuse is now pre-emptively checked for `Process.ppid()`_  and
  `Process.parents()`_.
- 2312_: use ``ruff`` Python linter instead of ``flake8 + isort``. It's an
  order of magnitude faster + it adds a ton of new code quality checks.

**Bug fixes**

- 2195_, [Linux]: no longer print exception at import time in case /proc/stat
  can't be read due to permission error. Redirect it to ``PSUTIL_DEBUG``
  instead.
- 2241_, [NetBSD]: can't compile On NetBSD 10.99.3/amd64.  (patch by Thomas
  Klausner)
- 2245_, [Windows]: fix var unbound error on possibly in `swap_memory()`_
  (patch by student_2333)
- 2268_: ``bytes2human()`` utility function was unable to properly represent
  negative values.
- 2252_, [Windows]: `disk_usage()`_ fails on Python 3.12+.  (patch by
  Matthieu Darbois)
- 2284_, [Linux]: `Process.memory_full_info()`_ may incorrectly raise
  `ZombieProcess`_ if it's determined via ``/proc/pid/smaps_rollup``. Instead
  we now fallback on reading ``/proc/pid/smaps``.
- 2287_, [OpenBSD], [NetBSD]: `Process.is_running()`_ erroneously return
  ``False`` for zombie processes, because creation time cannot be determined.
- 2288_, [Linux]: correctly raise `ZombieProcess`_ on `Process.exe()`_,
  `Process.cmdline()`_ and `Process.memory_maps()`_ instead of returning a
  "null" value.
- 2290_: differently from what stated in the doc, PID reuse is not
  pre-emptively checked for `Process.nice()`_ (set), `Process.ionice()`_,
  (set), `Process.cpu_affinity()`_ (set), `Process.rlimit()`_
  (set), `Process.parent()`_.
- 2308_, [OpenBSD]: `Process.threads()`_ always fail with AccessDenied (also as
  root).

5.9.5
=====

2023-04-17

**Enhancements**

- 2196_: in case of exception, display a cleaner error traceback by hiding the
  `KeyError` bit deriving from a missed cache hit.
- 2217_: print the full traceback when a `DeprecationWarning` or `UserWarning`
  is raised.
- 2230_, [OpenBSD]: `net_connections()`_ implementation was rewritten
  from scratch:
  - We're now able to retrieve the path of AF_UNIX sockets (before it was an
  empty string)
  - The function is faster since it no longer iterates over all processes.
  - No longer produces duplicate connection entries.
- 2238_: there are cases where `Process.cwd()`_ cannot be determined
  (e.g. directory no longer exists), in which case we returned either ``None``
  or an empty string. This was consolidated and we now return ``""`` on all
  platforms.
- 2239_, [UNIX]: if process is a zombie, and we can only determine part of the
  its truncated `Process.name()`_ (15 chars), don't fail with `ZombieProcess`_
  when we try to guess the full name from the `Process.cmdline()`_. Just
  return the truncated name.
- 2240_, [NetBSD], [OpenBSD]: add CI testing on every commit for NetBSD and
  OpenBSD platforms (python 3 only).

**Bug fixes**

- 1043_, [OpenBSD] `net_connections()`_ returns duplicate entries.
- 1915_, [Linux]: on certain kernels, ``"MemAvailable"`` field from
  ``/proc/meminfo`` returns ``0`` (possibly a kernel bug), in which case we
  calculate an approximation for ``available`` memory which matches "free"
  CLI utility.
- 2164_, [Linux]: compilation fails on kernels < 2.6.27 (e.g. CentOS 5).
- 2186_, [FreeBSD]: compilation fails with Clang 15.  (patch by Po-Chuan Hsieh)
- 2191_, [Linux]: `disk_partitions()`_: do not unnecessarily read
  /proc/filesystems and raise `AccessDenied`_ unless user specified `all=False`
  argument.
- 2216_, [Windows]: fix tests when running in a virtual environment (patch by
  Matthieu Darbois)
- 2225_, [POSIX]: `users()`_ loses precision for ``started`` attribute (off by
  1 minute).
- 2229_, [OpenBSD]: unable to properly recognize zombie processes.
  `NoSuchProcess`_ may be raised instead of `ZombieProcess`_.
- 2231_, [NetBSD]: *available*  `virtual_memory()`_ is higher than *total*.
- 2234_, [NetBSD]: `virtual_memory()`_ metrics are wrong: *available* and
  *used* are too high. We now match values shown by *htop* CLI utility.
- 2236_, [NetBSD]: `Process.num_threads()`_ and `Process.threads()`_ return
  threads that are already terminated.
- 2237_, [OpenBSD], [NetBSD]: `Process.cwd()`_ may raise ``FileNotFoundError``
  if cwd no longer exists. Return an empty string instead.

5.9.4
=====

2022-11-07

**Enhancements**

- 2102_: use Limited API when building wheels with CPython 3.6+ on Linux,
  macOS and Windows. This allows to use pre-built wheels in all future versions
  of cPython 3.  (patch by Matthieu Darbois)

**Bug fixes**

- 2077_, [Windows]: Use system-level values for `virtual_memory()`_. (patch by
  Daniel Widdis)
- 2156_, [Linux]: compilation may fail on very old gcc compilers due to missing
  ``SPEED_UNKNOWN`` definition.  (patch by Amir Rossert)
- 2010_, [macOS]: on MacOS, arm64 ``IFM_1000_TX`` and ``IFM_1000_T`` are the
  same value, causing a build failure.  (patch by Lawrence D'Anna)
- 2160_, [Windows]: Get Windows percent swap usage from performance counters.
  (patch by Daniel Widdis)

5.9.3
=====

2022-10-18

**Enhancements**

- 2040_, [macOS]: provide wheels for arm64 architecture.  (patch by Matthieu
  Darbois)

**Bug fixes**

- 2116_, [macOS], [critical]: `net_connections()`_ fails with RuntimeError.
- 2135_, [macOS]: `Process.environ()`_ may contain garbage data. Fix
  out-of-bounds read around ``sysctl_procargs``.  (patch by Bernhard Urban-Forster)
- 2138_, [Linux], **[critical]**: can't compile psutil on Android due to
  undefined ``ethtool_cmd_speed`` symbol.
- 2142_, [POSIX]: `net_if_stats()`_ 's ``flags`` on Python 2 returned unicode
  instead of str.  (patch by Matthieu Darbois)
- 2147_, [macOS] Fix disk usage report on macOS 12+.  (patch by Matthieu Darbois)
- 2150_, [Linux] `Process.threads()`_ may raise ``NoSuchProcess``. Fix race
  condition.  (patch by Daniel Li)
- 2153_, [macOS] Fix race condition in test_posix.TestProcess.test_cmdline.
  (patch by Matthieu Darbois)

5.9.2
=====

2022-09-04

**Bug fixes**

- 2093_, [FreeBSD], **[critical]**: `pids()`_ may fail with ENOMEM. Dynamically
  increase the ``malloc()`` buffer size until it's big enough.
- 2095_, [Linux]: `net_if_stats()`_ returns incorrect interface speed for
  100GbE network cards.
- 2113_, [FreeBSD], **[critical]**: `virtual_memory()`_ may raise ENOMEM due to
  missing ``#include <sys/param.h>`` directive.  (patch by Peter Jeremy)
- 2128_, [NetBSD]: `swap_memory()`_ was miscalculated.  (patch by Thomas Klausner)

5.9.1
=====

2022-05-20

**Enhancements**

- 1053_: drop Python 2.6 support.  (patches by Matthieu Darbois and Hugo van
  Kemenade)
- 2037_: Add additional flags to net_if_stats.
- 2050_, [Linux]: increase ``read(2)`` buffer size from 1k to 32k when reading
  ``/proc`` pseudo files line by line. This should help having more consistent
  results.
- 2057_, [OpenBSD]: add support for `cpu_freq()`_.
- 2107_, [Linux]: `Process.memory_full_info()`_ (reporting process USS/PSS/Swap
  memory) now reads ``/proc/pid/smaps_rollup`` instead of ``/proc/pids/smaps``,
  which makes it 5 times faster.

**Bug fixes**

- 2048_: ``AttributeError`` is raised if ``psutil.Error`` class is raised
  manually and passed through ``str``.
- 2049_, [Linux]: `cpu_freq()`_ erroneously returns ``curr`` value in GHz while
  ``min`` and ``max`` are in MHz.
- 2050_, [Linux]: `virtual_memory()`_ may raise ``ValueError`` if running in a
  LCX container.

5.9.0
=====

2021-12-29

**Enhancements**

- 1851_, [Linux]: `cpu_freq()`_ is slow on systems with many CPUs. Read current
  frequency values for all CPUs from ``/proc/cpuinfo`` instead of opening many
  files in ``/sys`` fs.  (patch by marxin)
- 1992_: `NoSuchProcess`_ message now specifies if the PID has been reused.
- 1992_: error classes (`NoSuchProcess`_, `AccessDenied`_, etc.) now have a better
  formatted and separated ``__repr__`` and ``__str__`` implementations.
- 1996_, [BSD]: add support for MidnightBSD.  (patch by Saeed Rasooli)
- 1999_, [Linux]: `disk_partitions()`_: convert ``/dev/root`` device (an alias
  used on some Linux distros) to real root device path.
- 2005_: ``PSUTIL_DEBUG`` mode now prints file name and line number of the debug
  messages coming from C extension modules.
- 2042_: rewrite HISTORY.rst to use hyperlinks pointing to psutil API doc.

**Bug fixes**

- 1456_, [macOS], **[critical]**: `cpu_freq()`_ ``min`` and ``max`` are set to
  0 if can't be determined (instead of crashing).
- 1512_, [macOS]: sometimes `Process.connections()`_ will crash with
  ``EOPNOTSUPP`` for one connection; this is now ignored.
- 1598_, [Windows]: `disk_partitions()`_ only returns mountpoints on drives
  where it first finds one.
- 1874_, [SunOS]: swap output error due to incorrect range.
- 1892_, [macOS]: `cpu_freq()`_ broken on Apple M1.
- 1901_, [macOS]: different functions, especially `Process.open_files()`_ and
  `Process.connections()`_, could randomly raise `AccessDenied`_ because the
  internal buffer of ``proc_pidinfo(PROC_PIDLISTFDS)`` syscall was not big enough.
  We now dynamically increase the buffer size until it's big enough instead of
  giving up and raising `AccessDenied`_, which was a fallback to avoid crashing.
- 1904_, [Windows]: ``OpenProcess`` fails with ``ERROR_SUCCESS`` due to
  ``GetLastError()`` called after ``sprintf()``.  (patch by alxchk)
- 1913_, [Linux]: `wait_procs()`_ should catch ``subprocess.TimeoutExpired``
  exception.
- 1919_, [Linux]: `sensors_battery()`_ can raise ``TypeError`` on PureOS.
- 1921_, [Windows]: `swap_memory()`_ shows committed memory instead of swap.
- 1940_, [Linux]: psutil does not handle ``ENAMETOOLONG`` when accessing process
  file descriptors in procfs.  (patch by Nikita Radchenko)
- 1948_, **[critical]**: ``memoize_when_activated`` decorator is not thread-safe.
  (patch by Xuehai Pan)
- 1953_, [Windows], **[critical]**: `disk_partitions()`_ crashes due to
  insufficient buffer len. (patch by MaWe2019)
- 1965_, [Windows], **[critical]**: fix "Fatal Python error: deallocating None"
  when calling `users()`_ multiple times.
- 1980_, [Windows]: 32bit / WoW64 processes fails to read `Process.name()`_ longer
  than 128 characters resulting in `AccessDenied`_. This is now fixed.  (patch
  by PetrPospisil)
- 1991_, **[critical]**: `process_iter()`_ is not thread safe and can raise
  ``TypeError`` if invoked from multiple threads.
- 1956_, [macOS]: `Process.cpu_times()`_ reports incorrect timings on M1 machines.
  (patch by Olivier Dormond)
- 2023_, [Linux]: `cpu_freq()`_ return order is wrong on systems with more than
  9 CPUs.

5.8.0
=====

2020-12-19

**Enhancements**

- 1863_: `disk_partitions()`_ exposes 2 extra fields: ``maxfile`` and ``maxpath``,
  which are the maximum file name and path name length.
- 1872_, [Windows]: added support for PyPy 2.7.
- 1879_: provide pre-compiled wheels for Linux and macOS (yey!).
- 1880_: get rid of Travis and Cirrus CI services (they are no longer free).
  CI testing is now done by GitHub Actions on Linux, macOS and FreeBSD (yes).
  AppVeyor is still being used for Windows CI.

**Bug fixes**

- 1708_, [Linux]: get rid of `sensors_temperatures()`_ duplicates.  (patch by Tim
  Schlueter).
- 1839_, [Windows], **[critical]**: always raise `AccessDenied`_ instead of
  ``WindowsError`` when failing to query 64 processes from 32 bit ones by using
  ``NtWoW64`` APIs.
- 1866_, [Windows], **[critical]**: `Process.exe()`_, `Process.cmdline()`_,
  `Process.environ()`_ may raise "[WinError 998] Invalid access to memory
  location" on Python 3.9 / VS 2019.
- 1874_, [SunOS]: wrong swap output given when encrypted column is present.
- 1875_, [Windows], **[critical]**: `Process.username()`_ may raise
  ``ERROR_NONE_MAPPED`` if the SID has no corresponding account name. In this
  case `AccessDenied`_ is now raised.
- 1886_, [macOS]: ``EIO`` error may be raised on `Process.cmdline()`_ and
  `Process.environ()`_. Now it gets translated into `AccessDenied`_.
- 1887_, [Windows], **[critical]**: ``OpenProcess`` may fail with
  "[WinError 0] The operation completed successfully"."
  Turn it into `AccessDenied`_ or `NoSuchProcess`_ depending on whether the
  PID is alive.
- 1891_, [macOS]: get rid of deprecated ``getpagesize()``.

5.7.3
=====

2020-10-23

**Enhancements**

- 809_, [FreeBSD]: add support for `Process.rlimit()`_.
- 893_, [BSD]: add support for `Process.environ()`_ (patch by Armin Gruner)
- 1830_, [POSIX]: `net_if_stats()`_ ``isup`` also checks whether the NIC is
  running (meaning Wi-Fi or ethernet cable is connected).  (patch by Chris Burger)
- 1837_, [Linux]: improved battery detection and charge ``secsleft`` calculation
  (patch by aristocratos)

**Bug fixes**

- 1620_, [Linux]: `cpu_count()`_ with ``logical=False`` result is incorrect on
  systems with more than one CPU socket.  (patch by Vincent A. Arcila)
- 1738_, [macOS]: `Process.exe()`_ may raise ``FileNotFoundError`` if process is still
  alive but the exe file which launched it got deleted.
- 1791_, [macOS]: fix missing include for ``getpagesize()``.
- 1823_, [Windows], **[critical]**: `Process.open_files()`_ may cause a segfault
  due to a NULL pointer.
- 1838_, [Linux]: `sensors_battery()`_: if `percent` can be determined but not
  the remaining values, still return a result instead of ``None``.
  (patch by aristocratos)

5.7.2
=====

2020-07-15

**Bug fixes**

- wheels for 2.7 were inadvertently deleted.

5.7.1
=====

2020-07-15

**Enhancements**

- 1729_: parallel tests on POSIX (``make test-parallel``). They're twice as fast!
- 1741_, [POSIX]: ``make build`` now runs in parallel on Python >= 3.6 and
  it's about 15% faster.
- 1747_: `Process.wait()`_ return value is cached so that the exit code can be
  retrieved on then next call.
- 1747_, [POSIX]: `Process.wait()`_ on POSIX now returns an enum, showing the
  negative signal which was used to terminate the process. It returns something
  like ``<Negsignal.SIGTERM: -15>``.
- 1747_: `Process`_ class provides more info about the process on ``str()``
  and ``repr()`` (status and exit code).
- 1757_: memory leak tests are now stable.
- 1768_, [Windows]: added support for Windows Nano Server. (contributed by
  Julien Lebot)

**Bug fixes**

- 1726_, [Linux]: `cpu_freq()`_ parsing should use spaces instead of tabs on ia64.
  (patch by Michał Górny)
- 1760_, [Linux]: `Process.rlimit()`_ does not handle long long type properly.
- 1766_, [macOS]: `NoSuchProcess`_ may be raised instead of `ZombieProcess`_.
- 1781_, **[critical]**: `getloadavg()`_ can crash the Python interpreter.
  (patch by Ammar Askar)

5.7.0
=====

2020-02-18

**Enhancements**

- 1637_, [SunOS]: add partial support for old SunOS 5.10 Update 0 to 3.
- 1648_, [Linux]: `sensors_temperatures()`_ looks into an additional
  ``/sys/device/`` directory for additional data.  (patch by Javad Karabi)
- 1652_, [Windows]: dropped support for Windows XP and Windows Server 2003.
  Minimum supported Windows version now is Windows Vista.
- 1671_, [FreeBSD]: add CI testing/service for FreeBSD (Cirrus CI).
- 1677_, [Windows]: `Process.exe()`_ will succeed for all process PIDs (instead of
  raising `AccessDenied`_).
- 1679_, [Windows]: `net_connections()`_ and `Process.connections()`_ are 10% faster.
- 1682_, [PyPy]: added CI / test integration for PyPy via Travis.
- 1686_, [Windows]: added support for PyPy on Windows.
- 1693_, [Windows]: `boot_time()`_, `Process.create_time()`_ and `users()`_'s
  login time now have 1 micro second precision (before the precision was of 1
  second).

**Bug fixes**

- 1538_, [NetBSD]: `Process.cwd()`_ may return ``ENOENT`` instead of `NoSuchProcess`_.
- 1627_, [Linux]: `Process.memory_maps()`_ can raise ``KeyError``.
- 1642_, [SunOS]: querying basic info for PID 0 results in ``FileNotFoundError``.
- 1646_, [FreeBSD], **[critical]**: many `Process`_ methods may cause a segfault
  due to a backward incompatible change in a C type on FreeBSD 12.0.
- 1656_, [Windows]: `Process.memory_full_info()`_ raises `AccessDenied`_ even for the
  current user and os.getpid().
- 1660_, [Windows]: `Process.open_files()`_ complete rewrite + check of errors.
- 1662_, [Windows], **[critical]**: `Process.exe()`_ may raise "[WinError 0]
  The operation completed successfully".
- 1665_, [Linux]: `disk_io_counters()`_ does not take into account extra fields
  added to recent kernels.  (patch by Mike Hommey)
- 1672_: use the right C type when dealing with PIDs (int or long). Thus far
  (long) was almost always assumed, which is wrong on most platforms.
- 1673_, [OpenBSD]: `Process.connections()`_, `Process.num_fds()`_ and
  `Process.threads()`_ returned improper exception if process is gone.
- 1674_, [SunOS]: `disk_partitions()`_ may raise ``OSError``.
- 1684_, [Linux]: `disk_io_counters()`_ may raise ``ValueError`` on systems not
  having ``/proc/diskstats``.
- 1695_, [Linux]: could not compile on kernels <= 2.6.13 due to
  ``PSUTIL_HAVE_IOPRIO`` not being defined.  (patch by Anselm Kruis)

5.6.7
=====

2019-11-26

**Bug fixes**

- 1630_, [Windows], **[critical]**: can't compile source distribution due to C
  syntax error.

5.6.6
=====

2019-11-25

**Bug fixes**

- 1179_, [Linux]: `Process.cmdline()`_ now takes into account misbehaving processes
  renaming the command line and using inappropriate chars to separate args.
- 1616_, **[critical]**: use of ``Py_DECREF`` instead of ``Py_CLEAR`` will
  result in double ``free()`` and segfault
  (`CVE-2019-18874 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-18874>`__).
  (patch by Riccardo Schirone)
- 1619_, [OpenBSD], **[critical]**: compilation fails due to C syntax error.
  (patch by Nathan Houghton)

5.6.5
=====

2019-11-06

**Bug fixes**

- 1615_: remove ``pyproject.toml`` as it was causing installation issues.

5.6.4
=====

2019-11-04

**Enhancements**

- 1527_, [Linux]: added `Process.cpu_times()`_ ``iowait`` counter, which is the
  time spent waiting for blocking I/O to complete.
- 1565_: add PEP 517/8 build backend and requirements specification for better
  pip integration.  (patch by Bernát Gábor)

**Bug fixes**

- 875_, [Windows], **[critical]**: `Process.cmdline()`_, `Process.environ()`_ or
  `Process.cwd()`_ may occasionally fail with ``ERROR_PARTIAL_COPY`` which now
  gets translated to `AccessDenied`_.
- 1126_, [Linux], **[critical]**: `Process.cpu_affinity()`_ segfaults on CentOS
  5 / manylinux. `Process.cpu_affinity()`_ support for CentOS 5 was removed.
- 1528_, [AIX], **[critical]**: compilation error on AIX 7.2 due to 32 vs 64
  bit differences. (patch by Arnon Yaari)
- 1535_: ``type`` and ``family`` fields returned by `net_connections()`_ are not
  always turned into enums.
- 1536_, [NetBSD]: `Process.cmdline()`_ erroneously raise `ZombieProcess`_ error if
  cmdline has non encodable chars.
- 1546_: usage percent may be rounded to 0 on Python 2.
- 1552_, [Windows]: `getloadavg()`_ math for calculating 5 and 15 mins values is
  incorrect.
- 1568_, [Linux]: use CC compiler env var if defined.
- 1570_, [Windows]: ``NtWow64*`` syscalls fail to raise the proper error code
- 1585_, [OSX]: avoid calling ``close()`` (in C) on possible negative integers.
  (patch by Athos Ribeiro)
- 1606_, [SunOS], **[critical]**: compilation fails on SunOS 5.10.
  (patch by vser1)

5.6.3
=====

2019-06-11

**Enhancements**

- 1494_, [AIX]: added support for `Process.environ()`_.  (patch by Arnon Yaari)

**Bug fixes**

- 1276_, [AIX]: can't get whole `Process.cmdline()`_.  (patch by Arnon Yaari)
- 1501_, [Windows]: `Process.cmdline()`_ and `Process.exe()`_ raise unhandled
  "WinError 1168 element not found" exceptions for "Registry" and
  "Memory Compression" pseudo processes on Windows 10.
- 1526_, [NetBSD], **[critical]**: `Process.cmdline()`_ could raise
  ``MemoryError``.  (patch by Kamil Rytarowski)

5.6.2
=====

2019-04-26

**Enhancements**

- 604_, [Windows]: add new `getloadavg()`_, returning system load average
  calculation, including on Windows (emulated).  (patch by Ammar Askar)
- 1404_, [Linux]: `cpu_count()`_ with ``logical=False`` uses a second method
  (read from ``/sys/devices/system/cpu/cpu[0-9]/topology/core_id``) in order to
  determine the number of CPU cores in case ``/proc/cpuinfo`` does not provide this
  info.
- 1458_: provide coloured test output. Also show failures on
  ``KeyboardInterrupt``.
- 1464_: various docfixes (always point to Python 3 doc, fix links, etc.).
- 1476_, [Windows]: it is now possible to set process high I/O priority
  (`Process.ionice()`_). Also, I/O priority values are now exposed as 4 new
  constants: ``IOPRIO_VERYLOW``, ``IOPRIO_LOW``, ``IOPRIO_NORMAL``,
  ``IOPRIO_HIGH``.
- 1478_: add make command to re-run tests failed on last run.

**Bug fixes**

- 1223_, [Windows]: `boot_time()`_ may return incorrect value on Windows XP.
- 1456_, [Linux]: `cpu_freq()`_ returns ``None`` instead of 0.0 when ``min``
  and ``max`` fields can't be determined. (patch by Alex Manuskin)
- 1462_, [Linux]: (tests) make tests invariant to ``LANG`` setting (patch by
  Benjamin Drung)
- 1463_: `cpu_distribution.py`_ script was broken.
- 1470_, [Linux]: `disk_partitions()`_: fix corner case when ``/etc/mtab``
  doesn't exist.  (patch by Cedric Lamoriniere)
- 1471_, [SunOS]: `Process.name()`_ and `Process.cmdline()`_ can return
  ``SystemError``.  (patch by Daniel Beer)
- 1472_, [Linux]: `cpu_freq()`_ does not return all CPUs on Raspberry-pi 3.
- 1474_: fix formatting of ``psutil.tests()`` which mimics ``ps aux`` output.
- 1475_, [Windows], **[critical]**: ``OSError.winerror`` attribute wasn't
  properly checked resulting in ``WindowsError(ERROR_ACCESS_DENIED)`` being
  raised instead of `AccessDenied`_.
- 1477_, [Windows]: wrong or absent error handling for private ``NTSTATUS``
  Windows APIs. Different process methods were affected by this.
- 1480_, [Windows], **[critical]**: `cpu_count()`_ with ``logical=False`` could
  cause a crash due to fixed read violation.  (patch by Samer Masterson)
- 1486_, [AIX], [SunOS]: ``AttributeError`` when interacting with `Process`_
  methods involved into `Process.oneshot()`_ context.
- 1491_, [SunOS]: `net_if_addrs()`_: use ``free()`` against ``ifap`` struct
  on error.  (patch by Agnewee)
- 1493_, [Linux]: `cpu_freq()`_: handle the case where
  ``/sys/devices/system/cpu/cpufreq/`` exists but it's empty.

5.6.1
=====

2019-03-11

**Bug fixes**

- 1329_, [AIX]: psutil doesn't compile on AIX 6.1.  (patch by Arnon Yaari)
- 1448_, [Windows], **[critical]**: crash on import due to ``rtlIpv6AddressToStringA``
  not available on Wine.
- 1451_, [Windows], **[critical]**: `Process.memory_full_info()`_ segfaults.
  ``NtQueryVirtualMemory`` is now used instead of ``QueryWorkingSet`` to
  calculate USS memory.

5.6.0
=====

2019-03-05

**Enhancements**

- 1379_, [Windows]: `Process.suspend()`_ and `Process.resume()`_ now use
  ``NtSuspendProcess`` and ``NtResumeProcess`` instead of stopping/resuming all
  threads of a process. This is faster and more reliable (aka this is what
  ProcessHacker does).
- 1420_, [Windows]: in case of exception `disk_usage()`_ now also shows the path
  name.
- 1422_, [Windows]: Windows APIs requiring to be dynamically loaded from DLL
  libraries are now loaded only once on startup (instead of on per function
  call) significantly speeding up different functions and methods.
- 1426_, [Windows]: ``PAGESIZE`` and number of processors is now calculated on
  startup.
- 1428_: in case of error, the traceback message now shows the underlying C
  function called which failed.
- 1433_: new `Process.parents()`_ method.  (idea by Ghislain Le Meur)
- 1437_: `pids()`_ are returned in sorted order.
- 1442_: Python 3 is now the default interpreter used by Makefile.

**Bug fixes**

- 1353_: `process_iter()`_ is now thread safe (it rarely raised ``TypeError``).
- 1394_, [Windows], **[critical]**: `Process.name()`_ and `Process.exe()`_ may
  erroneously return "Registry" or fail with "[Error 0] The operation completed
  successfully".
  ``QueryFullProcessImageNameW`` is now used instead of
  ``GetProcessImageFileNameW`` in order to prevent that.
- 1411_, [BSD]: lack of ``Py_DECREF`` could cause segmentation fault on process
  instantiation.
- 1419_, [Windows]: `Process.environ()`_ raises ``NotImplementedError`` when
  querying a 64-bit process in 32-bit-WoW mode. Now it raises `AccessDenied`_.
- 1427_, [OSX]: `Process.cmdline()`_ and `Process.environ()`_ may erroneously
  raise ``OSError`` on failed ``malloc()``.
- 1429_, [Windows]: ``SE DEBUG`` was not properly set for current process. It is
  now, and it should result in less `AccessDenied`_ exceptions for low PID
  processes.
- 1432_, [Windows]: `Process.memory_info_ex()`_'s USS memory is miscalculated
  because we're not using the actual system ``PAGESIZE``.
- 1439_, [NetBSD]: `Process.connections()`_ may return incomplete results if using
  `Process.oneshot()`_.
- 1447_: original exception wasn't turned into `NoSuchProcess`_ / `AccessDenied`_
  exceptions when using `Process.oneshot()`_ context manager.

**Incompatible API changes**

- 1291_, [OSX], **[critical]**: `Process.memory_maps()`_ was removed because
  inherently broken (segfault) for years.

5.5.1
=====

2019-02-15

**Enhancements**

- 1348_, [Windows]: on Windows >= 8.1 if `Process.cmdline()`_ fails due to
  ``ERROR_ACCESS_DENIED`` attempt using ``NtQueryInformationProcess`` +
  ``ProcessCommandLineInformation``. (patch by EccoTheFlintstone)

**Bug fixes**

- 1394_, [Windows]: `Process.exe()`_ returns "[Error 0] The operation completed
  successfully" when Python process runs in "Virtual Secure Mode".
- 1402_: psutil exceptions' ``repr()`` show the internal private module path.
- 1408_, [AIX], **[critical]**: psutil won't compile on AIX 7.1 due to missing
  header.  (patch by Arnon Yaari)

5.5.0
=====

2019-01-23

**Enhancements**

- 1350_, [FreeBSD]: added support for `sensors_temperatures()`_.  (patch by Alex
  Manuskin)
- 1352_, [FreeBSD]: added support for `cpu_freq()`_.  (patch by Alex Manuskin)

**Bug fixes**

- 1111_: `Process.oneshot()`_ is now thread safe.
- 1354_, [Linux]: `disk_io_counters()`_ fails on Linux kernel 4.18+.
- 1357_, [Linux]: `Process.memory_maps()`_ and `Process.io_counters()`_ methods
  are no longer exposed if not supported by the kernel.
- 1368_, [Windows]: fix `Process.ionice()`_ mismatch.  (patch by
  EccoTheFlintstone)
- 1370_, [Windows]: improper usage of ``CloseHandle()`` may lead to override the
  original error code when raising an exception.
- 1373_, **[critical]**: incorrect handling of cache in `Process.oneshot()`_
  context causes `Process`_ instances to return incorrect results.
- 1376_, [Windows]: ``OpenProcess`` now uses ``PROCESS_QUERY_LIMITED_INFORMATION``
  access rights wherever possible, resulting in less `AccessDenied`_ exceptions
  being thrown for system processes.
- 1376_, [Windows]: check if variable is ``NULL`` before ``free()`` ing it.
  (patch by EccoTheFlintstone)

5.4.8
=====

2018-10-30

**Enhancements**

- 1197_, [Linux]: `cpu_freq()`_ is now implemented by parsing ``/proc/cpuinfo``
  in case ``/sys/devices/system/cpu/*`` filesystem is not available.
- 1310_, [Linux]: `sensors_temperatures()`_ now parses ``/sys/class/thermal``
  in case ``/sys/class/hwmon`` fs is not available (e.g. Raspberry Pi).  (patch
  by Alex Manuskin)
- 1320_, [POSIX]: better compilation support when using g++ instead of GCC.
  (patch by Jaime Fullaondo)

**Bug fixes**

- 715_: do not print exception on import time in case `cpu_times()`_ fails.
- 1004_, [Linux]: `Process.io_counters()`_ may raise ``ValueError``.
- 1277_, [OSX]: available and used memory (`virtual_memory()`_) metrics are
  not accurate.
- 1294_, [Windows]: `Process.connections()`_ may sometimes fail with
  intermittent ``0xC0000001``.  (patch by Sylvain Duchesne)
- 1307_, [Linux]: `disk_partitions()`_ does not honour `PROCFS_PATH`_.
- 1320_, [AIX]: system CPU times (`cpu_times()`_) were being reported with
  ticks unit as opposed to seconds.  (patch by Jaime Fullaondo)
- 1332_, [OSX]: psutil debug messages are erroneously printed all the time.
  (patch by Ilya Yanok)
- 1346_, [SunOS]: `net_connections()`_ returns an empty list.  (patch by Oleksii
  Shevchuk)

5.4.7
=====

2018-08-14

**Enhancements**

- 1286_, [macOS]: ``psutil.OSX`` constant is now deprecated in favor of new
  ``psutil.MACOS``.
- 1309_, [Linux]: added ``psutil.STATUS_PARKED`` constant for `Process.status()`_.
- 1321_, [Linux]: add `disk_io_counters()`_ dual implementation relying on
  ``/sys/block`` filesystem in case ``/proc/diskstats`` is not available.
  (patch by Lawrence Ye)

**Bug fixes**

- 1209_, [macOS]: `Process.memory_maps()`_ may fail with ``EINVAL`` due to poor
  ``task_for_pid()`` syscall. `AccessDenied`_ is now raised instead.
- 1278_, [macOS]: `Process.threads()`_ incorrectly return microseconds instead of
  seconds. (patch by Nikhil Marathe)
- 1279_, [Linux], [macOS], [BSD]: `net_if_stats()`_ may return ``ENODEV``.
- 1294_, [Windows]: `Process.connections()`_ may sometime fail with
  ``MemoryError``.  (patch by sylvainduchesne)
- 1305_, [Linux]: `disk_io_counters()`_ may report inflated r/w bytes values.
- 1309_, [Linux]: `Process.status()`_ is unable to recognize ``"idle"`` and
  ``"parked"`` statuses (returns ``"?"``).
- 1313_, [Linux]: `disk_io_counters()`_ can report inflated values due to
  counting base disk device and its partition(s) twice.
- 1323_, [Linux]: `sensors_temperatures()`_ may fail with ``ValueError``.

5.4.6
=====

2018-06-07

**Bug fixes**

- 1258_, [Windows], **[critical]**: `Process.username()`_ may cause a segfault
  (Python interpreter crash).  (patch by Jean-Luc Migot)
- 1273_: `net_if_addrs()`_ namedtuple's name has been renamed from ``snic`` to
  ``snicaddr``.
- 1274_, [Linux]: there was a small chance `Process.children()`_ may swallow
  `AccessDenied`_ exceptions.

5.4.5
=====

2018-04-14

**Bug fixes**

- 1268_: setup.py's ``extra_require`` parameter requires latest setuptools version,
  breaking quite a lot of installations.

5.4.4
=====

2018-04-13

**Enhancements**

- 1239_, [Linux]: expose kernel ``slab`` memory field for `virtual_memory()`_.
  (patch by Maxime Mouial)

**Bug fixes**

- 694_, [SunOS]: `Process.cmdline()`_ could be truncated at the 15th character when
  reading it from ``/proc``. An extra effort is made by reading it from process
  address space first.  (patch by Georg Sauthoff)
- 771_, [Windows]: `cpu_count()`_ (both logical and cores) return a wrong
  (smaller) number on systems using process groups (> 64 cores).
- 771_, [Windows]: `cpu_times()`_ with ``percpu=True`` return fewer CPUs on
  systems using process groups (> 64 cores).
- 771_, [Windows]: `cpu_stats()`_ and `cpu_freq()`_ may return incorrect results on
  systems using process groups (> 64 cores).
- 1193_, [SunOS]: return uid/gid from ``/proc/pid/psinfo`` if there aren't
  enough permissions for ``/proc/pid/cred``.  (patch by Georg Sauthoff)
- 1194_, [SunOS]: return nice value from ``psinfo`` as ``getpriority()`` doesn't
  support real-time processes.  (patch by Georg Sauthoff)
- 1194_, [SunOS]: fix double ``free()`` in `Process.cpu_num()`_.  (patch by Georg
  Sauthoff)
- 1194_, [SunOS]: fix undefined behavior related to strict-aliasing rules
  and warnings.  (patch by Georg Sauthoff)
- 1210_, [Linux]: `cpu_percent()`_ steal time may remain stuck at 100% due to Linux
  erroneously reporting a decreased steal time between calls. (patch by Arnon
  Yaari)
- 1216_: fix compatibility with Python 2.6 on Windows (patch by Dan Vinakovsky)
- 1222_, [Linux]: `Process.memory_full_info()`_ was erroneously summing "Swap:" and
  "SwapPss:". Same for "Pss:" and "SwapPss". Not anymore.
- 1224_, [Windows]: `Process.wait()`_ may erroneously raise `TimeoutExpired`_.
- 1238_, [Linux]: `sensors_battery()`_ may return ``None`` in case battery is not
  listed as "BAT0" under ``/sys/class/power_supply``.
- 1240_, [Windows]: `cpu_times()`_ float loses accuracy in a long running system.
  (patch by stswandering)
- 1245_, [Linux]: `sensors_temperatures()`_ may fail with ``IOError`` "no such file".
- 1255_, [FreeBSD]: `swap_memory()`_ stats were erroneously represented in KB.
  (patch by Denis Krienbühl)

**Backward compatibility**

- 771_, [Windows]: `cpu_count()`_ with ``logical=False`` on Windows XP and Vista
  is no longer supported and returns ``None``.

5.4.3
=====

*2018-01-01*

**Enhancements**

- 775_: `disk_partitions()`_ on Windows return mount points.

**Bug fixes**

- 1193_: `pids()`_ may return ``False`` on macOS.

5.4.2
=====

*2017-12-07*

**Enhancements**

- 1173_: introduced ``PSUTIL_DEBUG`` environment variable which can be set in order
  to print useful debug messages on stderr (useful in case of nasty errors).
- 1177_, [macOS]: added support for `sensors_battery()`_.  (patch by Arnon Yaari)
- 1183_: `Process.children()`_ is 2x faster on POSIX and 2.4x faster on Linux.
- 1188_: deprecated method `Process.memory_info_ex()`_ now warns by using
  ``FutureWarning`` instead of ``DeprecationWarning``.

**Bug fixes**

- 1152_, [Windows]: `disk_io_counters()`_ may return an empty dict.
- 1169_, [Linux]: `users()`_ ``hostname`` returns username instead.  (patch by
  janderbrain)
- 1172_, [Windows]: ``make test`` does not work.
- 1179_, [Linux]: `Process.cmdline()`_ is now able to split cmdline args for
  misbehaving processes which overwrite ``/proc/pid/cmdline`` and use spaces
  instead of null bytes as args separator.
- 1181_, [macOS]: `Process.memory_maps()`_ may raise ``ENOENT``.
- 1187_, [macOS]: `pids()`_ does not return PID 0 on recent macOS versions.

5.4.1
=====

*2017-11-08*

**Enhancements**

- 1164_, [AIX]: add support for `Process.num_ctx_switches()`_.  (patch by Arnon
  Yaari)
- 1053_: drop Python 3.3 support (psutil still works but it's no longer
  tested).

**Bug fixes**

- 1150_, [Windows]: when a process is terminated now the exit code is set to
  ``SIGTERM`` instead of ``0``.  (patch by Akos Kiss)
- 1151_: ``python -m psutil.tests`` fail.
- 1154_, [AIX], **[critical]**: psutil won't compile on AIX 6.1.0.
  (patch by Arnon Yaari)
- 1167_, [Windows]: `net_io_counters()`_ packets count now include also non-unicast
  packets.  (patch by Matthew Long)

5.4.0
=====

*2017-10-12*

**Enhancements**

- 1123_, [AIX]: added support for AIX platform.  (patch by Arnon Yaari)

**Bug fixes**

- 1009_, [Linux]: `sensors_temperatures()`_ may crash with ``IOError``.
- 1012_, [Windows]: `disk_io_counters()`_ ``read_time`` and ``write_time``
  were expressed in tens of micro seconds instead of milliseconds.
- 1127_, [macOS], **[critical]**: invalid reference counting in
  `Process.open_files()`_ may lead to segfault.  (patch by Jakub Bacic)
- 1129_, [Linux]: `sensors_fans()`_ may crash with ``IOError``.  (patch by
  Sebastian Saip)
- 1131_, [SunOS]: fix compilation warnings.  (patch by Arnon Yaari)
- 1133_, [Windows]: can't compile on newer versions of Visual Studio 2017 15.4.
  (patch by Max Bélanger)
- 1138_, [Linux]: can't compile on CentOS 5.0 and RedHat 5.0. (patch by Prodesire)

5.3.1
=====

*2017-09-10*

**Enhancements**

- 1124_: documentation moved to http://psutil.readthedocs.io

**Bug fixes**

- 1105_, [FreeBSD]: psutil does not compile on FreeBSD 12.
- 1125_, [BSD]: `net_connections()`_ raises ``TypeError``.

**Compatibility notes**

- 1120_: ``.exe`` files for Windows are no longer uploaded on PyPI as per
  PEP-527. Only wheels are provided.

5.3.0
=====

*2017-09-01*

**Enhancements**

- 802_: `disk_io_counters()`_ and `net_io_counters()`_ numbers no longer wrap
  (restart from 0). Introduced a new ``nowrap`` argument.
- 928_: `net_connections()`_ and `Process.connections()`_ ``laddr`` and
  ``raddr`` are now named tuples.
- 1015_: `swap_memory()`_ now relies on ``/proc/meminfo`` instead of ``sysinfo()``
  syscall so that it can be used in conjunction with `PROCFS_PATH`_ in order to
  retrieve memory info about Linux containers such as Docker and Heroku.
- 1022_: `users()`_ provides a new ``pid`` field.
- 1025_: `process_iter()`_ accepts two new parameters in order to invoke
  `Process.as_dict()`_: ``attrs`` and ``ad_value``. With these you can iterate
  over all processes in one shot without needing to catch `NoSuchProcess`_ and
  do list/dict comprehensions.
- 1040_: implemented full unicode support.
- 1051_: `disk_usage()`_ on Python 3 is now able to accept bytes.
- 1058_: test suite now enables all warnings by default.
- 1060_: source distribution is dynamically generated so that it only includes
  relevant files.
- 1079_, [FreeBSD]: `net_connections()`_ ``fd`` number is now being set for real
  (instead of ``-1``).  (patch by Gleb Smirnoff)
- 1091_, [SunOS]: implemented `Process.environ()`_.  (patch by Oleksii Shevchuk)

**Bug fixes**

- 989_, [Windows]: `boot_time()`_ may return a negative value.
- 1007_, [Windows]: `boot_time()`_ can have a 1 sec fluctuation between calls.
  The value of the first call is now cached so that `boot_time()`_ always
  returns the same value if fluctuation is <= 1 second.
- 1013_, [FreeBSD]: `net_connections()`_ may return incorrect PID.  (patch
  by Gleb Smirnoff)
- 1014_, [Linux]: `Process`_ class can mask legitimate ``ENOENT`` exceptions as
  `NoSuchProcess`_.
- 1016_: `disk_io_counters()`_ raises ``RuntimeError`` on a system with no disks.
- 1017_: `net_io_counters()`_ raises ``RuntimeError`` on a system with no network
  cards installed.
- 1021_, [Linux]: `Process.open_files()`_ may erroneously raise `NoSuchProcess`_
  instead of skipping a file which gets deleted while open files are retrieved.
- 1029_, [macOS], [FreeBSD]: `Process.connections()`_ with ``family=unix`` on Python
  3 doesn't properly handle unicode paths and may raise ``UnicodeDecodeError``.
- 1033_, [macOS], [FreeBSD]: memory leak for `net_connections()`_ and
  `Process.connections()`_ when retrieving UNIX sockets (``kind='unix'``).
- 1040_: fixed many unicode related issues such as ``UnicodeDecodeError`` on
  Python 3 + POSIX and invalid encoded data on Windows.
- 1042_, [FreeBSD], **[critical]**: psutil won't compile on FreeBSD 12.
- 1044_, [macOS]: different `Process`_ methods incorrectly raise `AccessDenied`_
  for zombie processes.
- 1046_, [Windows]: `disk_partitions()`_ on Windows overrides user's ``SetErrorMode``.
- 1047_, [Windows]: `Process.username()`_: memory leak in case exception is thrown.
- 1048_, [Windows]: `users()`_ ``host`` field report an invalid IP address.
- 1050_, [Windows]: `Process.memory_maps()`_ leaks memory.
- 1055_: `cpu_count()`_ is no longer cached. This is useful on systems such as
  Linux where CPUs can be disabled at runtime. This also reflects on
  `Process.cpu_percent()`_ which no longer uses the cache.
- 1058_: fixed Python warnings.
- 1062_: `disk_io_counters()`_ and `net_io_counters()`_ raise ``TypeError`` if
  no disks or NICs are installed on the system.
- 1063_, [NetBSD]: `net_connections()`_ may list incorrect sockets.
- 1064_, [NetBSD], **[critical]**: `swap_memory()`_ may segfault in case of error.
- 1065_, [OpenBSD], **[critical]**: `Process.cmdline()`_ may raise ``SystemError``.
- 1067_, [NetBSD]: `Process.cmdline()`_ leaks memory if process has terminated.
- 1069_, [FreeBSD]: `Process.cpu_num()`_ may return 255 for certain kernel
  processes.
- 1071_, [Linux]: `cpu_freq()`_ may raise ``IOError`` on old RedHat distros.
- 1074_, [FreeBSD]: `sensors_battery()`_ raises ``OSError`` in case of no battery.
- 1075_, [Windows]: `net_if_addrs()`_: ``inet_ntop()`` return value is not checked.
- 1077_, [SunOS]: `net_if_addrs()`_ shows garbage addresses on SunOS 5.10.
  (patch by Oleksii Shevchuk)
- 1077_, [SunOS]: `net_connections()`_ does not work on SunOS 5.10. (patch by
  Oleksii Shevchuk)
- 1079_, [FreeBSD]: `net_connections()`_ didn't list locally connected sockets.
  (patch by Gleb Smirnoff)
- 1085_: `cpu_count()`_ return value is now checked and forced to ``None`` if <= 1.
- 1087_: `Process.cpu_percent()`_ guard against `cpu_count()`_ returning ``None``
  and assumes 1 instead.
- 1093_, [SunOS]: `Process.memory_maps()`_ shows wrong 64 bit addresses.
- 1094_, [Windows]: `pid_exists()`_ may lie. Also, all process APIs relying
  on ``OpenProcess`` Windows API now check whether the PID is actually running.
- 1098_, [Windows]: `Process.wait()`_ may erroneously return sooner, when the PID
  is still alive.
- 1099_, [Windows]: `Process.terminate()`_ may raise `AccessDenied`_ even if the
  process already died.
- 1101_, [Linux]: `sensors_temperatures()`_ may raise ``ENODEV``.

**Porting notes**

- 1039_: returned types consolidation. 1) Windows / `Process.cpu_times()`_:
  fields #3 and #4 were int instead of float. 2) Linux / FreeBSD / OpenBSD:
  `Process.connections()`_ ``raddr`` is now set to  ``""`` instead of ``None``
  when retrieving UNIX sockets.
- 1040_: all strings are encoded by using OS fs encoding.
- 1040_: the following Windows APIs on Python 2 now return a string instead of
  unicode: ``Process.memory_maps().path``, ``WindowsService.bin_path()``,
  ``WindowsService.description()``, ``WindowsService.display_name()``,
  ``WindowsService.username()``.

5.2.2
=====

*2017-04-10*

**Bug fixes**

- 1000_: fixed some setup.py warnings.
- 1002_, [SunOS]: remove C macro which will not be available on new Solaris
  versions. (patch by Danek Duvall)
- 1004_, [Linux]: `Process.io_counters()`_ may raise ``ValueError``.
- 1006_, [Linux]: `cpu_freq()`_ may return ``None`` on some Linux versions does not
  support the function. Let's not make the function available instead.
- 1009_, [Linux]: `sensors_temperatures()`_ may raise ``OSError``.
- 1010_, [Linux]: `virtual_memory()`_ may raise ``ValueError`` on Ubuntu 14.04.

5.2.1
=====

*2017-03-24*

**Bug fixes**

- 981_, [Linux]: `cpu_freq()`_ may return an empty list.
- 993_, [Windows]: `Process.memory_maps()`_ on Python 3 may raise
  ``UnicodeDecodeError``.
- 996_, [Linux]: `sensors_temperatures()`_ may not show all temperatures.
- 997_, [FreeBSD]: `virtual_memory()`_ may fail due to missing ``sysctl``
  parameter on FreeBSD 12.

5.2.0
=====

*2017-03-05*

**Enhancements**

- 971_, [Linux]: Add `sensors_fans()`_ function.  (patch by Nicolas Hennion)
- 976_, [Windows]: `Process.io_counters()`_ has 2 new fields: ``other_count`` and
  ``other_bytes``.
- 976_, [Linux]: `Process.io_counters()`_ has 2 new fields: ``read_chars`` and
  ``write_chars``.

**Bug fixes**

- 872_, [Linux]: can now compile on Linux by using MUSL C library.
- 985_, [Windows]: Fix a crash in `Process.open_files()`_ when the worker thread
  for ``NtQueryObject`` times out.
- 986_, [Linux]: `Process.cwd()`_ may raise `NoSuchProcess`_ instead of `ZombieProcess`_.

5.1.3
=====

**Bug fixes**

- 971_, [Linux]: `sensors_temperatures()`_ didn't work on CentOS 7.
- 973_, **[critical]**: `cpu_percent()`_ may raise ``ZeroDivisionError``.

5.1.2
=====

*2017-02-03*

**Bug fixes**

- 966_, [Linux]: `sensors_battery()`_ ``power_plugged`` may erroneously return
  ``None`` on Python 3.
- 968_, [Linux]: `disk_io_counters()`_ raises ``TypeError`` on Python 3.
- 970_, [Linux]: `sensors_battery()`_ ``name`` and ``label`` fields on Python 3
  are bytes instead of str.

5.1.1
=====

*2017-02-03*

**Enhancements**

- 966_, [Linux]: `sensors_battery()`_ ``percent`` is a float and is more precise.

**Bug fixes**

- 964_, [Windows]: `Process.username()`_ and `users()`_ may return badly
  decoded character on Python 3.
- 965_, [Linux]: `disk_io_counters()`_ may miscalculate sector size and report
  the wrong number of bytes read and written.
- 966_, [Linux]: `sensors_battery()`_ may fail with ``FileNotFoundError``.
- 966_, [Linux]: `sensors_battery()`_ ``power_plugged`` may lie.

5.1.0
=====

*2017-02-01*

**Enhancements**

- 357_: added `Process.cpu_num()`_ (what CPU a process is on).
- 371_: added `sensors_temperatures()`_ (Linux only).
- 941_: added `cpu_freq()`_ (CPU frequency).
- 955_: added `sensors_battery()`_ (Linux, Windows, only).
- 956_: `Process.cpu_affinity()`_ can now be passed ``[]`` argument as an
  alias to set affinity against all eligible CPUs.

**Bug fixes**

- 687_, [Linux]: `pid_exists()`_ no longer returns ``True`` if passed a process
  thread ID.
- 948_: cannot install psutil with ``PYTHONOPTIMIZE=2``.
- 950_, [Windows]: `Process.cpu_percent()`_ was calculated incorrectly and showed
  higher number than real usage.
- 951_, [Windows]: the uploaded wheels for Python 3.6 64 bit didn't work.
- 959_: psutil exception objects could not be pickled.
- 960_: `psutil.Popen`_ ``wait()`` did not return the correct negative exit
  status if process is killed by a signal.
- 961_, [Windows]: ``WindowsService.description()`` method may fail with
  ``ERROR_MUI_FILE_NOT_FOUND``.

5.0.1
=====

*2016-12-21*

**Enhancements**

- 939_: tar.gz distribution went from 1.8M to 258K.
- 811_, [Windows]: provide a more meaningful error message if trying to use
  psutil on unsupported Windows XP.

**Bug fixes**

- 609_, [SunOS], **[critical]**: psutil does not compile on Solaris 10.
- 936_, [Windows]: fix compilation error on VS 2013 (patch by Max Bélanger).
- 940_, [Linux]: `cpu_percent()`_ and `cpu_times_percent()`_ was calculated
  incorrectly as ``iowait``, ``guest`` and ``guest_nice`` times were not
  properly taken into account.
- 944_, [OpenBSD]: `pids()`_ was omitting PID 0.

5.0.0
=====

*2016-11-06*

**Enhncements**

- 799_: new `Process.oneshot()`_ context manager making `Process`_ methods around
  +2x faster in general and from +2x to +6x faster on Windows.
- 943_: better error message in case of version conflict on import.

**Bug fixes**

- 932_, [NetBSD]: `net_connections()`_ and `Process.connections()`_ may fail
  without raising an exception.
- 933_, [Windows]: memory leak in `cpu_stats()`_ and
  ``WindowsService.description()`` method.

4.4.2
=====

*2016-10-26*

**Bug fixes**

- 931_, **[critical]**: psutil no longer compiles on Solaris.

4.4.1
=====

*2016-10-25*

**Bug fixes**

- 927_, **[critical]**: `psutil.Popen`_ ``__del__`` may cause maximum recursion
  depth error.

4.4.0
=====

*2016-10-23*

**Enhancements**

- 874_, [Windows]: make `net_if_addrs()`_ also return the ``netmask``.
- 887_, [Linux]: `virtual_memory()`_ ``available`` and ``used`` values are more
  precise and match ``free`` cmdline utility.  ``available`` also takes into
  account LCX containers preventing ``available`` to overflow ``total``.
- 891_: `procinfo.py`_ script has been updated and provides a lot more info.

**Bug fixes**

- 514_, [macOS], **[critical]**: `Process.memory_maps()`_ can segfault.
- 783_, [macOS]: `Process.status()`_ may erroneously return ``"running"`` for
  zombie processes.
- 798_, [Windows]: `Process.open_files()`_ returns and empty list on Windows 10.
- 825_, [Linux]: `Process.cpu_affinity()`_: fix possible double close and use of
  unopened socket.
- 880_, [Windows]: fix race condition inside `net_connections()`_.
- 885_: ``ValueError`` is raised if a negative integer is passed to `cpu_percent()`_
  functions.
- 892_, [Linux], **[critical]**: `Process.cpu_affinity()`_ with ``[-1]`` as arg
  raises ``SystemError`` with no error set; now ``ValueError`` is raised.
- 906_, [BSD]: `disk_partitions()`_ with ``all=False`` returned an empty list.
  Now the argument is ignored and all partitions are always returned.
- 907_, [FreeBSD]: `Process.exe()`_ may fail with ``OSError(ENOENT)``.
- 908_, [macOS], [BSD]: different process methods could errounesuly mask the real
  error for high-privileged PIDs and raise `NoSuchProcess`_ and `AccessDenied`_
  instead of ``OSError`` and ``RuntimeError``.
- 909_, [macOS]: `Process.open_files()`_ and `Process.connections()`_ methods
  may raise ``OSError`` with no exception set if process is gone.
- 916_, [macOS]: fix many compilation warnings.

4.3.1
=====

*2016-09-01*

**Enhancements**

- 881_: ``make install`` now works also when using a virtual env.

**Bug fixes**

- 854_: `Process.as_dict()`_ raises ``ValueError`` if passed an erroneous attrs name.
- 857_, [SunOS]: `Process.cpu_times()`_, `Process.cpu_percent()`_,
  `Process.threads()`_ and `Process.memory_maps()`_ may raise ``RuntimeError`` if
  attempting to query a 64bit process with a 32bit Python. "Null" values are
  returned as a fallback.
- 858_: `Process.as_dict()`_ should not call `Process.memory_info_ex()`_
  because it's deprecated.
- 863_, [Windows]: `Process.memory_maps()`_ truncates addresses above 32 bits.
- 866_, [Windows]: `win_service_iter()`_ and services in general are not able to
  handle unicode service names / descriptions.
- 869_, [Windows]: `Process.wait()`_ may raise `TimeoutExpired`_ with wrong timeout
  unit (ms instead of sec).
- 870_, [Windows]: handle leak inside ``psutil_get_process_data``.

4.3.0
=====

*2016-06-18*

**Enhancements**

- 819_, [Linux]: different speedup improvements:
  `Process.ppid()`_ +20% faster.
  `Process.status()`_ +28% faster.
  `Process.name()`_ +25% faster.
  `Process.num_threads()`_ +20% faster on Python 3.

**Bug fixes**

- 810_, [Windows]: Windows wheels are incompatible with pip 7.1.2.
- 812_, [NetBSD], **[critical]**: fix compilation on NetBSD-5.x.
- 823_, [NetBSD]: `virtual_memory()`_ raises ``TypeError`` on Python 3.
- 829_, [POSIX]: `disk_usage()`_ ``percent`` field takes root reserved space
  into account.
- 816_, [Windows]: fixed `net_io_counters()`_ values wrapping after 4.3GB in
  Windows Vista (NT 6.0) and above using 64bit values from newer win APIs.

4.2.0
=====

*2016-05-14*

**Enhancements**

- 795_, [Windows]: new APIs to deal with Windows services: `win_service_iter()`_
  and `win_service_get()`_.
- 800_, [Linux]: `virtual_memory()`_ returns a new ``shared`` memory field.
- 819_, [Linux]: speedup ``/proc`` parsing:
  `Process.ppid()`_ +20% faster.
  `Process.status()`_ +28% faster.
  `Process.name()`_ +25% faster.
  `Process.num_threads()`_ +20% faster on Python 3.

**Bug fixes**

- 797_, [Linux]: `net_if_stats()`_ may raise ``OSError`` for certain NIC cards.
- 813_: `Process.as_dict()`_ should ignore extraneous attribute names which gets
  attached to the `Process`_ instance.

4.1.0
=====

*2016-03-12*

**Enhancements**

- 777_, [Linux]: `Process.open_files()`_ on Linux return 3 new fields:
  ``position``, ``mode`` and ``flags``.
- 779_: `Process.cpu_times()`_ returns two new fields, ``children_user`` and
  ``children_system`` (always set to 0 on macOS and Windows).
- 789_, [Windows]: `cpu_times()`_ return two new fields: ``interrupt`` and
  ``dpc``. Same for `cpu_times_percent()`_.
- 792_: new `cpu_stats()`_ function returning number of CPU ``ctx_switches``,
  ``interrupts``, ``soft_interrupts`` and ``syscalls``.

**Bug fixes**

- 774_, [FreeBSD]: `net_io_counters()`_ dropout is no longer set to 0 if the kernel
  provides it.
- 776_, [Linux]: `Process.cpu_affinity()`_ may erroneously raise `NoSuchProcess`_.
  (patch by wxwright)
- 780_, [macOS]: psutil does not compile with some GCC versions.
- 786_: `net_if_addrs()`_ may report incomplete MAC addresses.
- 788_, [NetBSD]: `virtual_memory()`_ ``buffers`` and ``shared`` values were
  set to 0.
- 790_, [macOS], **[critical]**: psutil won't compile on macOS 10.4.

4.0.0
=====

*2016-02-17*

**Enhancements**

- 523_, [Linux], [FreeBSD]: `disk_io_counters()`_ return a new ``busy_time`` field.
- 660_, [Windows]: make.bat is smarter in finding alternative VS install
  locations.  (patch by mpderbec)
- 732_: `Process.environ()`_.  (patch by Frank Benkstein)
- 753_, [Linux], [macOS], [Windows]: process USS and PSS (Linux) "real" memory
  stats. (patch by Eric Rahm)
- 755_: `Process.memory_percent()`_ ``memtype`` parameter.
- 758_: tests now live in psutil namespace.
- 760_: expose OS constants (``psutil.LINUX``, ``psutil.OSX``, etc.)
- 756_, [Linux]: `disk_io_counters()`_ return 2 new fields: ``read_merged_count``
  and ``write_merged_count``.
- 762_: new `procsmem.py`_ script.

**Bug fixes**

- 685_, [Linux]: `virtual_memory()`_ provides wrong results on systems with a lot
  of physical memory.
- 704_, [SunOS]: psutil does not compile on Solaris sparc.
- 734_: on Python 3 invalid UTF-8 data is not correctly handled for
  `Process.name()`_, `Process.cwd()`_, `Process.exe()`_, `Process.cmdline()`_
  and `Process.open_files()`_ methods resulting in ``UnicodeDecodeError``
  exceptions. ``'surrogateescape'`` error handler is now used as a workaround for
  replacing the corrupted data.
- 737_, [Windows]: when the bitness of psutil and the target process was
  different, `Process.cmdline()`_ and `Process.cwd()`_ could return a wrong
  result or incorrectly report an `AccessDenied`_ error.
- 741_, [OpenBSD]: psutil does not compile on mips64.
- 751_, [Linux]: fixed call to ``Py_DECREF`` on possible ``NULL`` object.
- 754_, [Linux]: `Process.cmdline()`_ can be wrong in case of zombie process.
- 759_, [Linux]: `Process.memory_maps()`_ may return paths ending with ``" (deleted)"``.
- 761_, [Windows]: `boot_time()`_ wraps to 0 after 49 days.
- 764_, [NetBSD]: fix compilation on NetBSD-6.x.
- 766_, [Linux]: `net_connections()`_ can't handle malformed ``/proc/net/unix``
  file.
- 767_, [Linux]: `disk_io_counters()`_ may raise ``ValueError`` on 2.6 kernels and it's
  broken on 2.4 kernels.
- 770_, [NetBSD]: `disk_io_counters()`_ metrics didn't update.

3.4.2
=====

*2016-01-20*

**Enhancements**

- 728_, [SunOS]: exposed `PROCFS_PATH`_ constant to change the default
  location of ``/proc`` filesystem.

**Bug fixes**

- 724_, [FreeBSD]: `virtual_memory()`_ ``total`` is incorrect.
- 730_, [FreeBSD], **[critical]**: `virtual_memory()`_ crashes with
  "OSError: [Errno 12] Cannot allocate memory".

3.4.1
=====

*2016-01-15*

**Enhancements**

- 557_, [NetBSD]: added NetBSD support.  (contributed by Ryo Onodera and
  Thomas Klausner)
- 708_, [Linux]: `net_connections()`_ and `Process.connections()`_ on Python 2
  can be up to 3x faster in case of many connections.
  Also `Process.memory_maps()`_ is slightly faster.
- 718_: `process_iter()`_ is now thread safe.

**Bug fixes**

- 714_, [OpenBSD]: `virtual_memory()`_ ``cached`` value was always set to 0.
- 715_, **[critical]**: don't crash at import time if `cpu_times()`_ fail for
  some reason.
- 717_, [Linux]: `Process.open_files()`_ fails if deleted files still visible.
- 722_, [Linux]: `swap_memory()`_ no longer crashes if ``sin`` / ``sout`` can't
  be determined due to missing ``/proc/vmstat``.
- 724_, [FreeBSD]: `virtual_memory()`_ ``total`` is slightly incorrect.

3.3.0
=====

*2015-11-25*

**Enhancements**

- 558_, [Linux]: exposed `PROCFS_PATH`_ constant to change the default
  location of ``/proc`` filesystem.
- 615_, [OpenBSD]: added OpenBSD support.  (contributed by Landry Breuil)

**Bug fixes**

- 692_, [POSIX]: `Process.name()`_ is no longer cached as it may change.

3.2.2
=====

*2015-10-04*

**Bug fixes**

- 517_, [SunOS]: `net_io_counters()`_ failed to detect network interfaces
  correctly on Solaris 10
- 541_, [FreeBSD]: `disk_io_counters()`_ r/w times were expressed in seconds instead
  of milliseconds.  (patch by dasumin)
- 610_, [SunOS]: fix build and tests on Solaris 10
- 623_, [Linux]: process or system connections raises ``ValueError`` if IPv6 is not
  supported by the system.
- 678_, [Linux], **[critical]**: can't install psutil due to bug in setup.py.
- 688_, [Windows]: compilation fails with MSVC 2015, Python 3.5. (patch by
  Mike Sarahan)

3.2.1
=====

*2015-09-03*

**Bug fixes**

- 677_, [Linux], **[critical]**: can't install psutil due to bug in setup.py.

3.2.0
=====

*2015-09-02*

**Enhancements**

- 644_, [Windows]: added support for ``CTRL_C_EVENT`` and ``CTRL_BREAK_EVENT``
  signals to use with `Process.send_signal()`_.
- 648_: CI test integration for macOS. (patch by Jeff Tang)
- 663_, [POSIX]: `net_if_addrs()`_ now returns point-to-point (VPNs) addresses.
- 655_, [Windows]: different issues regarding unicode handling were fixed. On
  Python 2 all APIs returning a string will now return an encoded version of it
  by using sys.getfilesystemencoding() codec. The APIs involved are:
  `net_if_addrs()`_, `net_if_stats()`_, `net_io_counters()`_,
  `Process.cmdline()`_, `Process.name()`_, `Process.username()`_, `users()`_.

**Bug fixes**

- 513_, [Linux]: fixed integer overflow for ``RLIM_INFINITY``.
- 641_, [Windows]: fixed many compilation warnings.  (patch by Jeff Tang)
- 652_, [Windows]: `net_if_addrs()`_ ``UnicodeDecodeError`` in case of non-ASCII NIC
  names.
- 655_, [Windows]: `net_if_stats()`_ ``UnicodeDecodeError`` in case of non-ASCII NIC
  names.
- 659_, [Linux]: compilation error on Suse 10. (patch by maozguttman)
- 664_, [Linux]: compilation error on Alpine Linux. (patch by Bart van Kleef)
- 670_, [Windows]: segfgault of `net_if_addrs()`_ in case of non-ASCII NIC names.
  (patch by sk6249)
- 672_, [Windows]: compilation fails if using Windows SDK v8.0. (patch by
  Steven Winfield)
- 675_, [Linux]: `net_connections()`_: ``UnicodeDecodeError`` may occur when
  listing UNIX sockets.

3.1.1
=====

*2015-07-15*

**Bug fixes**

- 603_, [Linux]: `Process.ionice()`_ set value range is incorrect.
  (patch by spacewander)
- 645_, [Linux]: `cpu_times_percent()`_ may produce negative results.
- 656_: ``from psutil import *`` does not work.

3.1.0
=====

*2015-07-15*

**Enhancements**

- 534_, [Linux]: `disk_partitions()`_ added support for ZFS filesystems.
- 646_, [Windows]: continuous tests integration for Windows with
  https://ci.appveyor.com/project/giampaolo/psutil.
- 647_: new dev guide:
  https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst
- 651_: continuous code quality test integration with scrutinizer-ci.com

**Bug fixes**

- 340_, [Windows], **[critical]**: `Process.open_files()`_ no longer hangs.
  Instead it uses a thread which times out and skips the file handle in case it's
  taking too long to be retrieved.  (patch by Jeff Tang)
- 627_, [Windows]: `Process.name()`_ no longer raises `AccessDenied`_ for pids
  owned by another user.
- 636_, [Windows]: `Process.memory_info()`_ raise `AccessDenied`_.
- 637_, [POSIX]: raise exception if trying to send signal to PID 0 as it will
  affect ``os.getpid()`` 's process group and not PID 0.
- 639_, [Linux]: `Process.cmdline()`_ can be truncated.
- 640_, [Linux]: ``*connections`` functions may swallow errors and return an
  incomplete list of connections.
- 642_: ``repr()`` of exceptions is incorrect.
- 653_, [Windows]: add ``inet_ntop()`` function for Windows XP to support IPv6.
- 641_, [Windows]: replace deprecated string functions with safe equivalents.

3.0.1
=====

*2015-06-18*

**Bug fixes**

- 632_, [Linux]: better error message if cannot parse process UNIX connections.
- 634_, [Linux]: `Process.cmdline()`_ does not include empty string arguments.
- 635_, [POSIX], **[critical]**: crash on module import if ``enum`` package is
  installed on Python < 3.4.

3.0.0
=====

*2015-06-13*

**Enhancements**

- 250_: new `net_if_stats()`_ returning NIC statistics (``isup``, ``duplex``,
  ``speed``, ``mtu``).
- 376_: new `net_if_addrs()`_ returning all NIC addresses a-la ``ifconfig``.
- 469_: on Python >= 3.4 ``IOPRIO_CLASS_*`` and ``*_PRIORITY_CLASS`` constants
  returned by `Process.ionice()`_ and `Process.nice()`_ are enums instead of
  plain integers.
- 581_: add ``.gitignore``. (patch by Gabi Davar)
- 582_: connection constants returned by `net_connections()`_ and
  `Process.connections()`_ were turned from int to enums on Python > 3.4.
- 587_: move native extension into the package.
- 589_: `Process.cpu_affinity()`_ accepts any kind of iterable (set, tuple, ...),
  not only lists.
- 594_: all deprecated APIs were removed.
- 599_, [Windows]: `Process.name()`_ can now be determined for all processes even
  when running as a limited user.
- 602_: pre-commit GIT hook.
- 629_: enhanced support for ``pytest`` and ``nose`` test runners.
- 616_, [Windows]: add ``inet_ntop()`` function for Windows XP.

**Bug fixes**

- 428_, [POSIX], **[critical]**: correct handling of zombie processes on POSIX.
  Introduced new `ZombieProcess`_ exception class.
- 512_, [BSD], **[critical]**: fix segfault in `net_connections()`_.
- 555_, [Linux]: `users()`_ correctly handles ``":0"`` as an alias for
  ``"localhost"``.
- 579_, [Windows]: fixed `Process.open_files()`_ for PID > 64K.
- 579_, [Windows]: fixed many compiler warnings.
- 585_, [FreeBSD]: `net_connections()`_ may raise ``KeyError``.
- 586_, [FreeBSD], **[critical]**: `Process.cpu_affinity()`_ segfaults on set
  in case an invalid CPU number is provided.
- 593_, [FreeBSD], **[critical]**: `Process.memory_maps()`_ segfaults.
- 606_: `Process.parent()`_ may swallow `NoSuchProcess`_ exceptions.
- 611_, [SunOS]: `net_io_counters()`_ has send and received swapped
- 614_, [Linux]:: `cpu_count()`_ with ``logical=False`` return the number of
  sockets instead of cores.
- 618_, [SunOS]: swap tests fail on Solaris when run as normal user.
- 628_, [Linux]: `Process.name()`_ truncates string in case it contains spaces
  or parentheses.

2.2.1
=====

*2015-02-02*

**Bug fixes**

- 572_, [Linux]: fix "ValueError: ambiguous inode with multiple PIDs references"
  for `Process.connections()`_. (patch by Bruno Binet)

2.2.0
=====

*2015-01-06*

**Enhancements**

- 521_: drop support for Python 2.4 and 2.5.
- 553_: new `pstree.py`_ script.
- 564_: C extension version mismatch in case the user messed up with psutil
  installation or with sys.path is now detected at import time.
- 568_: new `pidof.py`_ script.
- 569_, [FreeBSD]: add support for `Process.cpu_affinity()`_ on FreeBSD.

**Bug fixes**

- 496_, [SunOS], **[critical]**: can't import psutil.
- 547_, [POSIX]: `Process.username()`_ may raise ``KeyError`` if UID can't be resolved.
- 551_, [Windows]: get rid of the unicode hack for `net_io_counters()`_ NIC names.
- 556_, [Linux]: lots of file handles were left open.
- 561_, [Linux]: `net_connections()`_ might skip some legitimate UNIX sockets.
  (patch by spacewander)
- 565_, [Windows]: use proper encoding for `Process.username()`_ and `users()`_.
  (patch by Sylvain Mouquet)
- 567_, [Linux]: in the alternative implementation of `Process.cpu_affinity()`_
  ``PyList_Append`` and ``Py_BuildValue`` return values are not checked.
- 569_, [FreeBSD]: fix memory leak in `cpu_count()`_ with ``logical=False``.
- 571_, [Linux]: `Process.open_files()`_ might swallow `AccessDenied`_
  exceptions and return an incomplete list of open files.

2.1.3
=====

*2014-09-26*

- 536_, [Linux], **[critical]**: fix "undefined symbol: CPU_ALLOC" compilation
  error.

2.1.2
=====

*2014-09-21*

**Enhancements**

- 407_: project moved from Google Code to Github; code moved from Mercurial
  to Git.
- 492_: use ``tox`` to run tests on multiple Python versions.  (patch by msabramo)
- 505_, [Windows]: distribution as wheel packages.
- 511_: add `ps.py`_ script.

**Bug fixes**

- 340_, [Windows]: `Process.open_files()`_ no longer hangs.  (patch by
  Jeff Tang)
- 501_, [Windows]: `disk_io_counters()`_ may return negative values.
- 503_, [Linux]: in rare conditions `Process.exe()`_, `Process.open_files()`_ and
  `Process.connections()`_ can raise ``OSError(ESRCH)`` instead of `NoSuchProcess`_.
- 504_, [Linux]: can't build RPM packages via setup.py
- 506_, [Linux], **[critical]**: Python 2.4 support was broken.
- 522_, [Linux]: `Process.cpu_affinity()`_ might return ``EINVAL``.  (patch by David
  Daeschler)
- 529_, [Windows]: `Process.exe()`_ may raise unhandled ``WindowsError`` exception
  for PIDs 0 and 4.  (patch by Jeff Tang)
- 530_, [Linux]: `disk_io_counters()`_ may crash on old Linux distros
  (< 2.6.5)  (patch by Yaolong Huang)
- 533_, [Linux]: `Process.memory_maps()`_ may raise ``TypeError`` on old Linux
  distros.

2.1.1
=====

*2014-04-30*

**Bug fixes**

- 446_, [Windows]: fix encoding error when using `net_io_counters()`_ on Python 3.
  (patch by Szigeti Gabor Niif)
- 460_, [Windows]: `net_io_counters()`_ wraps after 4G.
- 491_, [Linux]: `net_connections()`_ exceptions. (patch by Alexander Grothe)

2.1.0
=====

*2014-04-08*

**Enhancements**

- 387_: system-wide open connections a-la ``netstat`` (add `net_connections()`_).

**Bug fixes**

- 421_, [SunOS], **[critical]**: psutil does not compile on SunOS 5.10.
  (patch by Naveed Roudsari)
- 489_, [Linux]: `disk_partitions()`_ return an empty list.

2.0.0
=====

*2014-03-10*

**Enhancements**

- 424_, [Windows]: installer for Python 3.X 64 bit.
- 427_: number of logical CPUs and physical cores (`cpu_count()`_).
- 447_: `wait_procs()`_ ``timeout`` parameter is now optional.
- 452_: make `Process`_ instances hashable and usable with ``set()`` s.
- 453_: tests on Python < 2.7 require ``unittest2`` module.
- 459_: add a Makefile for running tests and other repetitive tasks (also
  on Windows).
- 463_: make timeout parameter of ``cpu_percent*`` functions default to ``0.0``
  'cause it's a common trap to introduce slowdowns.
- 468_: move documentation to readthedocs.com.
- 477_: `Process.cpu_percent()`_ is about 30% faster.  (suggested by crusaderky)
- 478_, [Linux]: almost all APIs are about 30% faster on Python 3.X.
- 479_: long deprecated ``psutil.error`` module is gone; exception classes now
  live in psutil namespace only.

**Bug fixes**

- 193_: `psutil.Popen`_ constructor can throw an exception if the spawned process
  terminates quickly.
- 340_, [Windows]: `Process.open_files()`_ no longer hangs.  (patch by
  jtang@vahna.net)
- 443_, [Linux]: fix a potential overflow issue for `Process.cpu_affinity()`_
  (set) on systems with more than 64 CPUs.
- 448_, [Windows]: `Process.children()`_ and `Process.ppid()`_ memory leak (patch
  by Ulrich Klank).
- 457_, [POSIX]: `pid_exists()`_ always returns ``True`` for PID 0.
- 461_: namedtuples are not pickle-able.
- 466_, [Linux]: `Process.exe()`_ improper null bytes handling.  (patch by
  Gautam Singh)
- 470_: `wait_procs()`_ might not wait.  (patch by crusaderky)
- 471_, [Windows]: `Process.exe()`_ improper unicode handling. (patch by
  alex@mroja.net)
- 473_: `psutil.Popen`_ ``wait()`` method does not set returncode attribute.
- 474_, [Windows]: `Process.cpu_percent()`_ is no longer capped at 100%.
- 476_, [Linux]: encoding error for `Process.name()`_ and `Process.cmdline()`_.

**API changes**

For the sake of consistency a lot of psutil APIs have been renamed.
In most cases accessing the old names will work but it will cause a
``DeprecationWarning``.

- ``psutil.*`` module level constants have being replaced by functions:

  +-----------------------+----------------------------------+
  | Old name              | Replacement                      |
  +=======================+==================================+
  | psutil.NUM_CPUS       | psutil.cpu_count()               |
  +-----------------------+----------------------------------+
  | psutil.BOOT_TIME      | psutil.boot_time()               |
  +-----------------------+----------------------------------+
  | psutil.TOTAL_PHYMEM   | virtual_memory.total             |
  +-----------------------+----------------------------------+

- Renamed ``psutil.*`` functions:

  +------------------------+-------------------------------+
  | Old name               | Replacement                   |
  +========================+===============================+
  | psutil.get_pid_list()  | psutil.pids()                 |
  +------------------------+-------------------------------+
  | psutil.get_users()     | psutil.users()                |
  +------------------------+-------------------------------+
  | psutil.get_boot_time() | psutil.boot_time()            |
  +------------------------+-------------------------------+

- All `Process`_ ``get_*`` methods lost the ``get_`` prefix.
  E.g. ``get_ext_memory_info()`` was renamed to ``memory_info_ex()``.
  Assuming ``p = psutil.Process()``:

  +--------------------------+----------------------+
  | Old name                 | Replacement          |
  +==========================+======================+
  | p.get_children()         | p.children()         |
  +--------------------------+----------------------+
  | p.get_connections()      | p.connections()      |
  +--------------------------+----------------------+
  | p.get_cpu_affinity()     | p.cpu_affinity()     |
  +--------------------------+----------------------+
  | p.get_cpu_percent()      | p.cpu_percent()      |
  +--------------------------+----------------------+
  | p.get_cpu_times()        | p.cpu_times()        |
  +--------------------------+----------------------+
  | p.get_ext_memory_info()  | p.memory_info_ex()   |
  +--------------------------+----------------------+
  | p.get_io_counters()      | p.io_counters()      |
  +--------------------------+----------------------+
  | p.get_ionice()           | p.ionice()           |
  +--------------------------+----------------------+
  | p.get_memory_info()      | p.memory_info()      |
  +--------------------------+----------------------+
  | p.get_memory_maps()      | p.memory_maps()      |
  +--------------------------+----------------------+
  | p.get_memory_percent()   | p.memory_percent()   |
  +--------------------------+----------------------+
  | p.get_nice()             | p.nice()             |
  +--------------------------+----------------------+
  | p.get_num_ctx_switches() | p.num_ctx_switches() |
  +--------------------------+----------------------+
  | p.get_num_fds()          | p.num_fds()          |
  +--------------------------+----------------------+
  | p.get_num_threads()      | p.num_threads()      |
  +--------------------------+----------------------+
  | p.get_open_files()       | p.open_files()       |
  +--------------------------+----------------------+
  | p.get_rlimit()           | p.rlimit()           |
  +--------------------------+----------------------+
  | p.get_threads()          | p.threads()          |
  +--------------------------+----------------------+
  | p.getcwd()               | p.cwd()              |
  +--------------------------+----------------------+

- All `Process`_ ``set_*`` methods lost the ``set_`` prefix.
  Assuming ``p = psutil.Process()``:

  +----------------------+---------------------------------+
  | Old name             | Replacement                     |
  +======================+=================================+
  | p.set_nice()         | p.nice(value)                   |
  +----------------------+---------------------------------+
  | p.set_ionice()       | p.ionice(ioclass, value=None)   |
  +----------------------+---------------------------------+
  | p.set_cpu_affinity() | p.cpu_affinity(cpus)            |
  +----------------------+---------------------------------+
  | p.set_rlimit()       | p.rlimit(resource, limits=None) |
  +----------------------+---------------------------------+

- Except for ``pid``, all `Process`_ class properties have been turned into
  methods. This is the only case which there are no aliases.
  Assuming ``p = psutil.Process()``:

  +---------------+-----------------+
  | Old name      | Replacement     |
  +===============+=================+
  | p.name        | p.name()        |
  +---------------+-----------------+
  | p.parent      | p.parent()      |
  +---------------+-----------------+
  | p.ppid        | p.ppid()        |
  +---------------+-----------------+
  | p.exe         | p.exe()         |
  +---------------+-----------------+
  | p.cmdline     | p.cmdline()     |
  +---------------+-----------------+
  | p.status      | p.status()      |
  +---------------+-----------------+
  | p.uids        | p.uids()        |
  +---------------+-----------------+
  | p.gids        | p.gids()        |
  +---------------+-----------------+
  | p.username    | p.username()    |
  +---------------+-----------------+
  | p.create_time | p.create_time() |
  +---------------+-----------------+

- timeout parameter of ``cpu_percent*`` functions defaults to 0.0 instead of 0.1.
- long deprecated ``psutil.error`` module is gone; exception classes now live in
  "psutil" namespace only.
- `Process`_ instances' ``retcode`` attribute returned by `wait_procs()`_ has
  been renamed to ``returncode`` for consistency with ``subprocess.Popen``.

1.2.1
=====

*2013-11-25*

**Bug fixes**

- 348_, [Windows], **[critical]**: fixed "ImportError: DLL load failed" occurring
  on module import on Windows XP.
- 425_, [SunOS], **[critical]**: crash on import due to failure at determining
  ``BOOT_TIME``.
- 443_, [Linux]: `Process.cpu_affinity()`_ can't set affinity on systems with
  more than 64 cores.

1.2.0
=====

*2013-11-20*

**Enhancements**

- 439_: assume ``os.getpid()`` if no argument is passed to `Process`_ class
  constructor.
- 440_: new `wait_procs()`_ utility function which waits for multiple
  processes to terminate.

**Bug fixes**

- 348_, [Windows]: fix "ImportError: DLL load failed" occurring on module
  import on Windows XP / Vista.

1.1.3
=====

*2013-11-07*

**Bug fixes**

- 442_, [Linux], **[critical]**: psutil won't compile on certain version of
  Linux because of missing ``prlimit(2)`` syscall.

1.1.2
=====

*2013-10-22*

**Bug fixes**

- 442_, [Linux], **[critical]**: psutil won't compile on Debian 6.0 because of
  missing ``prlimit(2)`` syscall.

1.1.1
=====

*2013-10-08*

**Bug fixes**

- 442_, [Linux], **[critical]**: psutil won't compile on kernels < 2.6.36 due
  to missing ``prlimit(2)`` syscall.

1.1.0
=====

*2013-09-28*

**Enhancements**

- 410_: host tar.gz and Windows binary files are on PyPI.
- 412_, [Linux]: get/set process resource limits (`Process.rlimit()`_).
- 415_, [Windows]: `Process.children()`_ is an order of magnitude faster.
- 426_, [Windows]: `Process.name()`_ is an order of magnitude faster.
- 431_, [POSIX]: `Process.name()`_ is slightly faster because it unnecessarily
  retrieved also `Process.cmdline()`_.

**Bug fixes**

- 391_, [Windows]: `cpu_times_percent()`_ returns negative percentages.
- 408_: ``STATUS_*`` and ``CONN_*`` constants don't properly serialize on JSON.
- 411_, [Windows]: `disk_usage.py`_ may pop-up a GUI error.
- 413_, [Windows]: `Process.memory_info()`_ leaks memory.
- 414_, [Windows]: `Process.exe()`_ on Windows XP may raise ``ERROR_INVALID_PARAMETER``.
- 416_: `disk_usage()`_ doesn't work well with unicode path names.
- 430_, [Linux]: `Process.io_counters()`_ report wrong number of r/w syscalls.
- 435_, [Linux]: `net_io_counters()`_ might report erreneous NIC names.
- 436_, [Linux]: `net_io_counters()`_ reports a wrong ``dropin`` value.

**API changes**

- 408_: turn ``STATUS_*`` and ``CONN_*`` constants into plain Python strings.

1.0.1
=====

*2013-07-12*

**Bug fixes**

- 405_: `net_io_counters()`_ ``pernic=True`` no longer works as intended in 1.0.0.

1.0.0
=====

*2013-07-10*

**Enhancements**

- 18_, [SunOS]: add Solaris support (yay!)  (thanks Justin Venus)
- 367_: `Process.connections()`_ ``status`` strings are now constants.
- 380_: test suite exits with non-zero on failure.  (patch by floppymaster)
- 391_: introduce unittest2 facilities and provide workarounds if unittest2
  is not installed (Python < 2.7).

**Bug fixes**

- 374_, [Windows]: negative memory usage reported if process uses a lot of
  memory.
- 379_, [Linux]: `Process.memory_maps()`_ may raise ``ValueError``.
- 394_, [macOS]: mapped memory regions of `Process.memory_maps()`_ report
  incorrect file name.
- 404_, [Linux]: ``sched_*affinity()`` are implicitly declared. (patch by Arfrever)

**API changes**

- `Process.connections()`_ ``status`` field is no longer a string but a
  constant object (``psutil.CONN_*``).
- `Process.connections()`_ ``local_address`` and ``remote_address`` fields
  renamed to ``laddr`` and ``raddr``.
- psutil.network_io_counters() renamed to `net_io_counters()`_.

0.7.1
=====

*2013-05-03*

**Bug fixes**

- 325_, [BSD], **[critical]**: `virtual_memory()`_ can raise ``SystemError``.
  (patch by Jan Beich)
- 370_, [BSD]: `Process.connections()`_ requires root.  (patch by John Baldwin)
- 372_, [BSD]: different process methods raise `NoSuchProcess`_ instead of
  `AccessDenied`_.

0.7.0
=====

*2013-04-12*

**Enhancements**

- 233_: code migrated to Mercurial (yay!)
- 246_: psutil.error module is deprecated and scheduled for removal.
- 328_, [Windows]: `Process.ionice()`_ support.
- 359_: add `boot_time()`_ as a substitute of ``psutil.BOOT_TIME`` since the
  latter cannot reflect system clock updates.
- 361_, [Linux]: `cpu_times()`_ now includes new ``steal``, ``guest`` and
  ``guest_nice`` fields available on recent Linux kernels. Also, `cpu_percent()`_
  is more accurate.
- 362_: add `cpu_times_percent()`_ (per-CPU-time utilization as a percentage).

**Bug fixes**

- 234_, [Windows]: `disk_io_counters()`_ fails to list certain disks.
- 264_, [Windows]: use of `disk_partitions()`_ may cause a message box to
  appear.
- 313_, [Linux], **[critical]**: `virtual_memory()`_ and `swap_memory()`_ can
  crash on certain exotic Linux flavors having an incomplete ``/proc`` interface.
  If that's the case we now set the unretrievable stats to ``0`` and raise
  ``RuntimeWarning`` instead.
- 315_, [macOS]: fix some compilation warnings.
- 317_, [Windows]: cannot set process CPU affinity above 31 cores.
- 319_, [Linux]: `Process.memory_maps()`_ raises ``KeyError`` 'Anonymous' on Debian
  squeeze.
- 321_, [POSIX]: `Process.ppid()`_ property is no longer cached as the kernel may set
  the PPID to 1 in case of a zombie process.
- 323_, [macOS]: `disk_io_counters()`_ ``read_time`` and ``write_time``
  parameters were reporting microseconds not milliseconds.  (patch by Gregory Szorc)
- 331_: `Process.cmdline()`_ is no longer cached after first access as it may
  change.
- 333_, [macOS]: leak of Mach ports (patch by rsesek@google.com)
- 337_, [Linux], **[critical]**: `Process`_ methods not working because of a
  poor ``/proc`` implementation will raise ``NotImplementedError`` rather than
  ``RuntimeError`` and `Process.as_dict()`_ will not blow up.
  (patch by Curtin1060)
- 338_, [Linux]: `disk_io_counters()`_ fails to find some disks.
- 339_, [FreeBSD]: ``get_pid_list()`` can allocate all the memory on system.
- 341_, [Linux], **[critical]**: psutil might crash on import due to error in
  retrieving system terminals map.
- 344_, [FreeBSD]: `swap_memory()`_ might return incorrect results due to
  ``kvm_open(3)`` not being called. (patch by Jean Sebastien)
- 338_, [Linux]: `disk_io_counters()`_ fails to find some disks.
- 351_, [Windows]: if psutil is compiled with MinGW32 (provided installers for
  py2.4 and py2.5 are) `disk_io_counters()`_ will fail. (Patch by m.malycha)
- 353_, [macOS]: `users()`_ returns an empty list on macOS 10.8.
- 356_: `Process.parent()`_ now checks whether parent PID has been reused in which
  case returns ``None``.
- 365_: `Process.nice()`_ (set) should check PID has not been reused by another
  process.
- 366_, [FreeBSD], **[critical]**: `Process.memory_maps()`_, `Process.num_fds()`_,
  `Process.open_files()`_ and `Process.cwd()`_ methods raise ``RuntimeError``
  instead of `AccessDenied`_.

**API changes**

- `Process.cmdline()`_ property is no longer cached after first access.
- `Process.ppid()`_ property is no longer cached after first access.
- [Linux] `Process`_ methods not working because of a poor ``/proc``
  implementation will raise ``NotImplementedError`` instead of ``RuntimeError``.
- ``psutil.error`` module is deprecated and scheduled for removal.

0.6.1
=====

*2012-08-16*

**Enhancements**

- 316_: `Process.cmdline()`_ property now makes a better job at guessing the
  process executable from the cmdline.

**Bug fixes**

- 316_: `Process.exe()`_ was resolved in case it was a symlink.
- 318_, **[critical]**: Python 2.4 compatibility was broken.

**API changes**

- `Process.exe()`_ can now return an empty string instead of raising `AccessDenied`_.
- `Process.exe()`_ is no longer resolved in case it's a symlink.

0.6.0
=====

*2012-08-13*

**Enhancements**

- 216_, [POSIX]: `Process.connections()`_ UNIX sockets support.
- 220_, [FreeBSD]: ``get_connections()`` has been rewritten in C and no longer
  requires ``lsof``.
- 222_, [macOS]: add support for `Process.cwd()`_.
- 261_: per-process extended memory info (`Process.memory_info_ex()`_).
- 295_, [macOS]: `Process.exe()`_ path is now determined by asking the OS
  instead of being guessed from `Process.cmdline()`_.
- 297_, [macOS]: the `Process`_ methods below were always raising `AccessDenied`_
  for any process except the current one. Now this is no longer true. Also
  they are 2.5x faster. `Process.name()`_, `Process.memory_info()`_,
  `Process.memory_percent()`_, `Process.cpu_times()`_, `Process.cpu_percent()`_,
  `Process.num_threads()`_.
- 300_: add `pmap.py`_ script.
- 301_: `process_iter()`_ now yields processes sorted by their PIDs.
- 302_: per-process number of voluntary and involuntary context switches
  (`Process.num_ctx_switches()`_).
- 303_, [Windows]: the `Process`_ methods below were always raising `AccessDenied`_
  for any process not owned by current user. Now this is no longer true:
  `Process.create_time()`_, `Process.cpu_times()`_, `Process.cpu_percent()`_,
  `Process.memory_info()`_, `Process.memory_percent()`_, `Process.num_handles()`_,
  `Process.io_counters()`_.
- 305_: add `netstat.py`_ script.
- 311_: system memory functions has been refactorized and rewritten and now
  provide a more detailed and consistent representation of the system
  memory. Added new `virtual_memory()`_ and `swap_memory()`_ functions.
  All old memory-related functions are deprecated. Also two new example scripts
  were added:  `free.py`_ and `meminfo.py`_.
- 312_: ``net_io_counters()`` namedtuple includes 4 new fields:
  ``errin``, ``errout``, ``dropin`` and ``dropout``, reflecting the number of
  packets dropped and with errors.

**Bug fixes**

- 298_, [macOS], [BSD]: memory leak in `Process.num_fds()`_.
- 299_: potential memory leak every time ``PyList_New(0)`` is used.
- 303_, [Windows], **[critical]**: potential heap corruption in
  `Process.num_threads()`_ and `Process.status()`_ methods.
- 305_, [FreeBSD], **[critical]**: can't compile on FreeBSD 9 due to removal of
  ``utmp.h``.
- 306_, **[critical]**: at C level, errors are not checked when invoking ``Py*``
  functions which create or manipulate Python objects leading to potential
  memory related errors and/or segmentation faults.
- 307_, [FreeBSD]: values returned by `net_io_counters()`_ are wrong.
- 308_, [BSD], [Windows]: ``psutil.virtmem_usage()`` wasn't actually returning
  information about swap memory usage as it was supposed to do. It does now.
- 309_: `Process.open_files()`_ might not return files which can not be accessed
  due to limited permissions. `AccessDenied`_ is now raised instead.

**API changes**

- ``psutil.phymem_usage()`` is deprecated (use `virtual_memory()`_)
- ``psutil.virtmem_usage()`` is deprecated (use `swap_memory()`_)
- [Linux]: ``psutil.phymem_buffers()`` is deprecated (use `virtual_memory()`_)
- [Linux]: ``psutil.cached_phymem()`` is deprecated (use `virtual_memory()`_)
- [Windows], [BSD]: ``psutil.virtmem_usage()`` now returns information about
  swap memory instead of virtual memory.

0.5.1
=====

*2012-06-29*

**Enhancements**

- 293_, [Windows]: `Process.exe()`_ path is now determined by asking the OS
  instead of being guessed from `Process.cmdline()`_.

**Bug fixes**

- 292_, [Linux]: race condition in process `Process.open_files()`_,
  `Process.connections()`_, `Process.threads()`_.
- 294_, [Windows]: `Process.cpu_affinity()`_ is only able to set CPU #0.

0.5.0
=====

*2012-06-27*

**Enhancements**

- 195_, [Windows]: number of handles opened by process (`Process.num_handles()`_).
- 209_: `disk_partitions()`_ now provides also mount options.
- 229_: list users currently connected on the system (`users()`_).
- 238_, [Linux], [Windows]: process CPU affinity (get and set,
  `Process.cpu_affinity()`_).
- 242_: add ``recursive=True`` to `Process.children()`_: return all process
  descendants.
- 245_, [POSIX]: `Process.wait()`_ incrementally consumes less CPU cycles.
- 257_, [Windows]: removed Windows 2000 support.
- 258_, [Linux]: `Process.memory_info()`_ is now 0.5x faster.
- 260_: process's mapped memory regions. (Windows patch by wj32.64, macOS patch
  by Jeremy Whitlock)
- 262_, [Windows]: `disk_partitions()`_ was slow due to inspecting the
  floppy disk drive also when parameter is ``all=False``.
- 273_: ``psutil.get_process_list()`` is deprecated.
- 274_: psutil no longer requires ``2to3`` at installation time in order to work
  with Python 3.
- 278_: new `Process.as_dict()`_ method.
- 281_: `Process.ppid()`_, `Process.name()`_, `Process.exe()`_,
  `Process.cmdline()`_ and `Process.create_time()`_ properties of `Process`_ class
  are now cached after being accessed.
- 282_: ``psutil.STATUS_*`` constants can now be compared by using their string
  representation.
- 283_: speedup `Process.is_running()`_ by caching its return value in case the
  process is terminated.
- 284_, [POSIX]: per-process number of opened file descriptors
  (`Process.num_fds()`_).
- 287_: `process_iter()`_ now caches `Process`_ instances between calls.
- 290_: `Process.nice()`_ property is deprecated in favor of new ``get_nice()``
  and ``set_nice()`` methods.

**Bug fixes**

- 193_: `psutil.Popen`_ constructor can throw an exception if the spawned process
  terminates quickly.
- 240_, [macOS]: incorrect use of ``free()`` for `Process.connections()`_.
- 244_, [POSIX]: `Process.wait()`_ can hog CPU resources if called against a
  process which is not our children.
- 248_, [Linux]: `net_io_counters()`_ might return erroneous NIC names.
- 252_, [Windows]: `Process.cwd()`_ erroneously raise `NoSuchProcess`_ for
  processes owned by another user.  It now raises `AccessDenied`_ instead.
- 266_, [Windows]: ``psutil.get_pid_list()`` only shows 1024 processes.
  (patch by Amoser)
- 267_, [macOS]: `Process.connections()`_ returns wrong remote address.
  (Patch by Amoser)
- 272_, [Linux]: `Process.open_files()`_ potential race condition can lead to
  unexpected `NoSuchProcess`_ exception. Also, we can get incorrect reports
  of not absolutized path names.
- 275_, [Linux]: ``Process.io_counters()`` erroneously raise `NoSuchProcess`_ on
  old Linux versions. Where not available it now raises ``NotImplementedError``.
- 286_: `Process.is_running()`_ doesn't actually check whether PID has been
  reused.
- 314_: `Process.children()`_ can sometimes return non-children.

**API changes**

- ``Process.nice`` property is deprecated in favor of new ``get_nice()`` and
  ``set_nice()`` methods.
- ``psutil.get_process_list()`` is deprecated.
- `Process.ppid()`_, `Process.name()`_, `Process.exe()`_, `Process.cmdline()`_
  and `Process.create_time()`_ properties of `Process`_ class are now cached after
  being accessed, meaning `NoSuchProcess`_ will no longer be raised in case the
  process is gone in the meantime.
- ``psutil.STATUS_*`` constants can now be compared by using their string
  representation.

0.4.1
=====

*2011-12-14*

**Bug fixes**

- 228_: some example scripts were not working with Python 3.
- 230_, [Windows], [macOS]: fix memory leak in `Process.connections()`_.
- 232_, [Linux]: ``psutil.phymem_usage()`` can report erroneous values which are
  different than ``free`` command.
- 236_, [Windows]: fix memory/handle leak in `Process.memory_info()`_,
  `Process.suspend()`_ and `Process.resume()`_ methods.

0.4.0
=====

*2011-10-29*

**Enhancements**

- 150_: network I/O counters (`net_io_counters()`_). (macOS and Windows patch
  by Jeremy Whitlock)
- 154_, [FreeBSD]: add support for `Process.cwd()`_.
- 157_, [Windows]: provide installer for Python 3.2 64-bit.
- 198_: `Process.wait()`_ with ``timeout=0`` can now be used to make the
  function return immediately.
- 206_: disk I/O counters (`disk_io_counters()`_). (macOS and Windows patch by
  Jeremy Whitlock)
- 213_: add `iotop.py`_ script.
- 217_: `Process.connections()`_ now has a ``kind`` argument to filter
  for connections with different criteria.
- 221_, [FreeBSD]: `Process.open_files()`_ has been rewritten in C and no longer
  relies on ``lsof``.
- 223_: add `top.py`_ script.
- 227_: add `nettop.py`_ script.

**Bug fixes**

- 135_, [macOS]: psutil cannot create `Process`_ object.
- 144_, [Linux]: no longer support 0 special PID.
- 188_, [Linux]: psutil import error on Linux ARM architectures.
- 194_, [POSIX]: `Process.cpu_percent()`_ now reports a percentage over
  100 on multicore processors.
- 197_, [Linux]: `Process.connections()`_ is broken on platforms not
  supporting IPv6.
- 200_, [Linux], **[critical]**: ``psutil.NUM_CPUS`` not working on armel and
  sparc architectures and causing crash on module import.
- 201_, [Linux]: `Process.connections()`_ is broken on big-endian
  architectures.
- 211_: `Process`_ instance can unexpectedly raise `NoSuchProcess`_ if tested
  for equality with another object.
- 218_, [Linux], **[critical]**: crash at import time on Debian 64-bit because
  of a missing line in ``/proc/meminfo``.
- 226_, [FreeBSD], **[critical]**: crash at import time on FreeBSD 7 and minor.

0.3.0
=====

*2011-07-08*

**Enhancements**

- 125_: system per-cpu percentage utilization and times (`Process.cpu_times()`_,
  `Process.cpu_percent()`_).
- 163_: per-process associated terminal / TTY (`Process.terminal()`_).
- 171_: added ``get_phymem()`` and ``get_virtmem()`` functions returning system
  memory information (``total``, ``used``, ``free``) and memory percent usage.
  ``total_*``, ``avail_*`` and ``used_*`` memory functions are deprecated.
- 172_: disk usage statistics (`disk_usage()`_).
- 174_: mounted disk partitions (`disk_partitions()`_).
- 179_: setuptools is now used in setup.py

**Bug fixes**

- 159_, [Windows]: ``SetSeDebug()`` does not close handles or unset
  impersonation on return.
- 164_, [Windows]: wait function raises a ``TimeoutException`` when a process
  returns ``-1``.
- 165_: `Process.status()`_ raises an unhandled exception.
- 166_: `Process.memory_info()`_ leaks handles hogging system resources.
- 168_: `cpu_percent()`_ returns erroneous results when used in
  non-blocking mode.  (patch by Philip Roberts)
- 178_, [macOS]: `Process.threads()`_ leaks memory.
- 180_, [Windows]: `Process.num_threads()`_ and `Process.threads()`_ methods
  can raise `NoSuchProcess`_ exception while process still exists.

0.2.1
=====

*2011-03-20*

**Enhancements**

- 64_: per-process I/O counters (`Process.io_counters()`_).
- 116_: per-process `Process.wait()`_ (wait for process to terminate and return
  its exit code).
- 134_: per-process threads (`Process.threads()`_).
- 136_: `Process.exe()`_ path on FreeBSD is now determined by asking the
  kernel instead of guessing it from cmdline[0].
- 137_: per-process real, effective and saved user and group ids
  (`Process.gids()`_).
- 140_: system boot time (`boot_time()`_).
- 142_: per-process get and set niceness (priority) (`Process.nice()`_).
- 143_: per-process status (`Process.status()`_).
- 147_ [Linux]: per-process I/O niceness / priority (`Process.ionice()`_).
- 148_: `psutil.Popen`_ class which tidies up ``subprocess.Popen`` and `Process`_
  class in a single interface.
- 152_, [macOS]: `Process.open_files()`_ implementation has been rewritten
  in C and no longer relies on ``lsof`` resulting in a 3x speedup.
- 153_, [macOS]: `Process.connections()`_ implementation has been rewritten
  in C and no longer relies on ``lsof`` resulting in a 3x speedup.

**Bug fixes**

- 83_, [macOS]:  `Process.cmdline()`_ is empty on macOS 64-bit.
- 130_, [Linux]: a race condition can cause ``IOError`` exception be raised on
  if process disappears between ``open()`` and the subsequent ``read()`` call.
- 145_, [Windows], **[critical]**: ``WindowsError`` was raised instead of
  `AccessDenied`_ when using `Process.resume()`_ or `Process.suspend()`_.
- 146_, [Linux]: `Process.exe()`_ property can raise ``TypeError`` if path
  contains NULL bytes.
- 151_, [Linux]: `Process.exe()`_ and `Process.cwd()`_ for PID 0 return
  inconsistent data.

**API changes**

- `Process`_ ``uid`` and ``gid`` properties are deprecated in favor of ``uids``
  and ``gids`` properties.

0.2.0
=====

*2010-11-13*

**Enhancements**

- 79_: per-process open files (`Process.open_files()`_).
- 88_: total system physical cached memory.
- 88_: total system physical memory buffers used by the kernel.
- 91_: add `Process.send_signal()`_ and `Process.terminate()`_ methods.
- 95_: `NoSuchProcess`_ and `AccessDenied`_ exception classes now provide
  ``pid``, ``name`` and ``msg`` attributes.
- 97_: per-process children (`Process.children()`_).
- 98_: `Process.cpu_times()`_ and `Process.memory_info()`_ now return
  a namedtuple instead of a tuple.
- 103_: per-process opened TCP and UDP connections (`Process.connections()`_).
- 107_, [Windows]: add support for Windows 64 bit. (patch by cjgohlke)
- 111_: per-process executable name (`Process.exe()`_).
- 113_: exception messages now include `Process.name()`_ and `Process.pid`_.
- 114_, [Windows]: `Process.username()`_ has been rewritten in pure C and no
  longer uses WMI resulting in a big speedup. Also, pywin32 is no longer
  required as a third-party dependency. (patch by wj32)
- 117_, [Windows]: added support for Windows 2000.
- 123_: `cpu_percent()`_ and `Process.cpu_percent()`_ accept a
  new ``interval`` parameter.
- 129_: per-process threads (`Process.threads()`_).

**Bug fixes**

- 80_: fixed warnings when installing psutil with easy_install.
- 81_, [Windows]: psutil fails to compile with Visual Studio.
- 94_: `Process.suspend()`_ raises ``OSError`` instead of `AccessDenied`_.
- 86_, [FreeBSD]: psutil didn't compile against FreeBSD 6.x.
- 102_, [Windows]: orphaned process handles obtained by using ``OpenProcess``
  in C were left behind every time `Process`_ class was instantiated.
- 111_, [POSIX]: ``path`` and ``name`` `Process`_ properties report truncated
  or erroneous values on POSIX.
- 120_, [macOS]: `cpu_percent()`_ always returning 100%.
- 112_: ``uid`` and ``gid`` properties don't change if process changes effective
  user/group id at some point.
- 126_: `Process.ppid()`_, `Process.uids()`_, `Process.gids()`_, `Process.name()`_,
  `Process.exe()`_, `Process.cmdline()`_ and `Process.create_time()`_
  properties are no longer cached and correctly raise `NoSuchProcess`_ exception
  if the process disappears.

**API changes**

- ``psutil.Process.path`` property is deprecated and works as an alias for
  ``psutil.Process.exe`` property.
- `Process.kill()`_: signal argument was removed - to send a signal to the
  process use `Process.send_signal()`_ method instead.
- `Process.memory_info()`_ returns a nametuple instead of a tuple.
- `cpu_times()`_ returns a nametuple instead of a tuple.
- New `Process`_ methods: `Process.open_files()`_, `Process.connections()`_,
  `Process.send_signal()`_ and `Process.terminate()`_.
- `Process.ppid()`_, `Process.uids()`_, `Process.gids()`_, `Process.name()`_,
  `Process.exe()`_, `Process.cmdline()`_ and `Process.create_time()`_
  properties are no longer cached and raise `NoSuchProcess`_ exception if process
  disappears.
- `cpu_percent()`_ no longer returns immediately (see issue 123).
- `Process.cpu_percent()`_ and `cpu_percent()`_ no longer returns immediately
  by default (see issue 123_).

0.1.3
=====

*2010-03-02*

**Enhancements**

- 14_: `Process.username()`_.
- 51_, [Linux], [Windows]: per-process current working directory (`Process.cwd()`_).
- 59_: `Process.is_running()`_ is now 10 times faster.
- 61_, [FreeBSD]: added supoprt for FreeBSD 64 bit.
- 71_: per-process suspend and resume (`Process.suspend()`_ and `Process.resume()`_).
- 75_: Python 3 support.

**Bug fixes**

- 36_: `Process.cpu_times()`_ and `Process.memory_info()`_ functions succeeded.
  also for dead processes while a `NoSuchProcess`_ exception is supposed to be raised.
- 48_, [FreeBSD]: incorrect size for MIB array defined in ``getcmdargs``.
- 49_, [FreeBSD]: possible memory leak due to missing ``free()`` on error
  condition in ``getcmdpath()``.
- 50_, [BSD]: fixed ``getcmdargs()`` memory fragmentation.
- 55_, [Windows]: ``test_pid_4`` was failing on Windows Vista.
- 57_: some unit tests were failing on systems where no swap memory is
  available.
- 58_: `Process.is_running()`_ is now called before `Process.kill()`_ to make
  sure we are going to kill the correct process.
- 73_, [macOS]: virtual memory size reported on includes shared library size.
- 77_: `NoSuchProcess`_ wasn't raised on `Process.create_time()`_ if `Process.kill()`_
  was used first.

0.1.2
=====

*2009-05-06*

**Enhancements**

- 32_: Per-process CPU user/kernel times (`Process.cpu_times()`_).
- 33_: Per-process create time (`Process.create_time()`_).
- 34_: Per-process CPU utilization percentage (`Process.cpu_percent()`_).
- 38_: Per-process memory usage (bytes) (`Process.memory_info()`_).
- 41_: Per-process memory percent (`Process.memory_percent()`_).
- 39_: System uptime (`boot_time()`_).
- 43_: Total system virtual memory.
- 46_: Total system physical memory.
- 44_: Total system used/free virtual and physical memory.

**Bug fixes**

- 36_, [Windows]: `NoSuchProcess`_ not raised when accessing timing methods.
- 40_, [FreeBSD], [macOS]: fix ``test_get_cpu_times`` failures.
- 42_, [Windows]: `Process.memory_percent()`_ raises `AccessDenied`_.

0.1.1
=====

*2009-03-06*

**Enhancements**

- 4_, [FreeBSD]: support for all functions of psutil.
- 9_, [macOS], [Windows]: add ``Process.uid`` and ``Process.gid``, returning
  process UID and GID.
- 11_: per-process parent object: `Process.parent()`_ property returns a
  `Process`_ object representing the parent process, and `Process.ppid()`_
  returns the parent PID.
- 12_, 15_:
  `NoSuchProcess`_ exception now raised when creating an object
  for a nonexistent process, or when retrieving information about a process
  that has gone away.
- 21_, [Windows]: `AccessDenied`_ exception created for raising access denied
  errors from ``OSError`` or ``WindowsError`` on individual platforms.
- 26_: `process_iter()`_ function to iterate over processes as
  `Process`_ objects with a generator.
- `Process`_ objects can now also be compared with == operator for equality
  (PID, name, command line are compared).

**Bug fixes**

- 16_, [Windows]: Special case for "System Idle Process" (PID 0) which
  otherwise would return an "invalid parameter" exception.
- 17_: get_process_list() ignores `NoSuchProcess`_ and `AccessDenied`_
  exceptions during building of the list.
- 22_, [Windows]: `Process.kill()`_ for PID 0 was failing with an unset exception.
- 23_, [Linux], [macOS]: create special case for `pid_exists()`_ with PID 0.
- 24_, [Windows], **[critical]**: `Process.kill()`_ for PID 0 now raises
  `AccessDenied`_ exception instead of ``WindowsError``.
- 30_: psutil.get_pid_list() was returning two 0 PIDs.


.. _`PROCFS_PATH`: https://psutil.readthedocs.io/en/latest/#psutil.PROCFS_PATH

.. _`boot_time()`: https://psutil.readthedocs.io/en/latest/#psutil.boot_time
.. _`cpu_count()`: https://psutil.readthedocs.io/en/latest/#psutil.cpu_count
.. _`cpu_freq()`: https://psutil.readthedocs.io/en/latest/#psutil.cpu_freq
.. _`cpu_percent()`: https://psutil.readthedocs.io/en/latest/#psutil.cpu_percent
.. _`cpu_stats()`: https://psutil.readthedocs.io/en/latest/#psutil.cpu_stats
.. _`cpu_times()`: https://psutil.readthedocs.io/en/latest/#psutil.cpu_times
.. _`cpu_times_percent()`: https://psutil.readthedocs.io/en/latest/#psutil.cpu_times_percent
.. _`disk_io_counters()`: https://psutil.readthedocs.io/en/latest/#psutil.disk_io_counters
.. _`disk_partitions()`: https://psutil.readthedocs.io/en/latest/#psutil.disk_partitions
.. _`disk_usage()`: https://psutil.readthedocs.io/en/latest/#psutil.disk_usage
.. _`getloadavg()`: https://psutil.readthedocs.io/en/latest/#psutil.getloadavg
.. _`net_connections()`: https://psutil.readthedocs.io/en/latest/#psutil.net_connections
.. _`net_if_addrs()`: https://psutil.readthedocs.io/en/latest/#psutil.net_if_addrs
.. _`net_if_stats()`: https://psutil.readthedocs.io/en/latest/#psutil.net_if_stats
.. _`net_io_counters()`: https://psutil.readthedocs.io/en/latest/#psutil.net_io_counters
.. _`pid_exists()`: https://psutil.readthedocs.io/en/latest/#psutil.pid_exists
.. _`pids()`: https://psutil.readthedocs.io/en/latest/#psutil.pids
.. _`process_iter()`: https://psutil.readthedocs.io/en/latest/#psutil.process_iter
.. _`sensors_battery()`: https://psutil.readthedocs.io/en/latest/#psutil.sensors_battery
.. _`sensors_fans()`: https://psutil.readthedocs.io/en/latest/#psutil.sensors_fans
.. _`sensors_temperatures()`: https://psutil.readthedocs.io/en/latest/#psutil.sensors_temperatures
.. _`swap_memory()`: https://psutil.readthedocs.io/en/latest/#psutil.swap_memory
.. _`users()`: https://psutil.readthedocs.io/en/latest/#psutil.users
.. _`virtual_memory()`: https://psutil.readthedocs.io/en/latest/#psutil.virtual_memory
.. _`wait_procs()`: https://psutil.readthedocs.io/en/latest/#psutil.wait_procs
.. _`win_service_get()`: https://psutil.readthedocs.io/en/latest/#psutil.win_service_get
.. _`win_service_iter()`: https://psutil.readthedocs.io/en/latest/#psutil.win_service_iter


.. _`Process`: https://psutil.readthedocs.io/en/latest/#psutil.Process
.. _`psutil.Popen`: https://psutil.readthedocs.io/en/latest/#psutil.Popen

.. _`AccessDenied`: https://psutil.readthedocs.io/en/latest/#psutil.AccessDenied
.. _`NoSuchProcess`: https://psutil.readthedocs.io/en/latest/#psutil.NoSuchProcess
.. _`TimeoutExpired`: https://psutil.readthedocs.io/en/latest/#psutil.TimeoutExpired
.. _`ZombieProcess`: https://psutil.readthedocs.io/en/latest/#psutil.ZombieProcess


.. _`Process.as_dict()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.as_dict
.. _`Process.children()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.children
.. _`Process.cmdline()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.connections
.. _`Process.connections()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.connections
.. _`Process.cpu_affinity()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_affinity
.. _`Process.cpu_num()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_num
.. _`Process.cpu_percent()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_percent
.. _`Process.cpu_times()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.cpu_times
.. _`Process.create_time()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.create_time
.. _`Process.cwd()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.cwd
.. _`Process.environ()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.environ
.. _`Process.exe()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.exe
.. _`Process.gids()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.gids
.. _`Process.io_counters()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.io_counters
.. _`Process.ionice()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.ionice
.. _`Process.is_running()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.is_running
.. _`Process.kill()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.kill
.. _`Process.memory_full_info()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_full_info
.. _`Process.memory_info()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_info
.. _`Process.memory_info_ex()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_info_ex
.. _`Process.memory_maps()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_maps
.. _`Process.memory_percent()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.memory_percent
.. _`Process.name()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.name
.. _`Process.net_connections()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.net_connections
.. _`Process.nice()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.nice
.. _`Process.num_ctx_switches()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.num_ctx_switches
.. _`Process.num_fds()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.num_fds
.. _`Process.num_handles()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.num_handles
.. _`Process.num_threads()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.num_threads
.. _`Process.oneshot()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.oneshot
.. _`Process.open_files()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.open_files
.. _`Process.parent()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.parent
.. _`Process.parents()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.parents
.. _`Process.pid`: https://psutil.readthedocs.io/en/latest/#psutil.Process.pid
.. _`Process.ppid()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.ppid
.. _`Process.resume()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.resume
.. _`Process.rlimit()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.rlimit
.. _`Process.send_signal()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.send_signal
.. _`Process.status()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.status
.. _`Process.suspend()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.suspend
.. _`Process.terminal()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.terminal
.. _`Process.terminate()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.terminate
.. _`Process.threads()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.threads
.. _`Process.uids()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.uids
.. _`Process.username()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.username
.. _`Process.wait()`: https://psutil.readthedocs.io/en/latest/#psutil.Process.wait


.. _`cpu_distribution.py`: https://github.com/giampaolo/psutil/blob/master/scripts/cpu_distribution.py
.. _`disk_usage.py`: https://github.com/giampaolo/psutil/blob/master/scripts/disk_usage.py
.. _`free.py`: https://github.com/giampaolo/psutil/blob/master/scripts/free.py
.. _`iotop.py`: https://github.com/giampaolo/psutil/blob/master/scripts/iotop.py
.. _`meminfo.py`: https://github.com/giampaolo/psutil/blob/master/scripts/meminfo.py
.. _`netstat.py`: https://github.com/giampaolo/psutil/blob/master/scripts/netstat.py
.. _`nettop.py`: https://github.com/giampaolo/psutil/blob/master/scripts/nettop.py
.. _`pidof.py`: https://github.com/giampaolo/psutil/blob/master/scripts/pidof.py
.. _`pmap.py`: https://github.com/giampaolo/psutil/blob/master/scripts/pmap.py
.. _`procinfo.py`: https://github.com/giampaolo/psutil/blob/master/scripts/procinfo.py
.. _`procsmem.py`: https://github.com/giampaolo/psutil/blob/master/scripts/procsmem.py
.. _`ps.py`: https://github.com/giampaolo/psutil/blob/master/scripts/ps.py
.. _`pstree.py`: https://github.com/giampaolo/psutil/blob/master/scripts/pstree.py
.. _`top.py`: https://github.com/giampaolo/psutil/blob/master/scripts/top.py


.. _1: https://github.com/giampaolo/psutil/issues/1
.. _2: https://github.com/giampaolo/psutil/issues/2
.. _3: https://github.com/giampaolo/psutil/issues/3
.. _4: https://github.com/giampaolo/psutil/issues/4
.. _5: https://github.com/giampaolo/psutil/issues/5
.. _6: https://github.com/giampaolo/psutil/issues/6
.. _7: https://github.com/giampaolo/psutil/issues/7
.. _8: https://github.com/giampaolo/psutil/issues/8
.. _9: https://github.com/giampaolo/psutil/issues/9
.. _10: https://github.com/giampaolo/psutil/issues/10
.. _11: https://github.com/giampaolo/psutil/issues/11
.. _12: https://github.com/giampaolo/psutil/issues/12
.. _13: https://github.com/giampaolo/psutil/issues/13
.. _14: https://github.com/giampaolo/psutil/issues/14
.. _15: https://github.com/giampaolo/psutil/issues/15
.. _16: https://github.com/giampaolo/psutil/issues/16
.. _17: https://github.com/giampaolo/psutil/issues/17
.. _18: https://github.com/giampaolo/psutil/issues/18
.. _19: https://github.com/giampaolo/psutil/issues/19
.. _20: https://github.com/giampaolo/psutil/issues/20
.. _21: https://github.com/giampaolo/psutil/issues/21
.. _22: https://github.com/giampaolo/psutil/issues/22
.. _23: https://github.com/giampaolo/psutil/issues/23
.. _24: https://github.com/giampaolo/psutil/issues/24
.. _25: https://github.com/giampaolo/psutil/issues/25
.. _26: https://github.com/giampaolo/psutil/issues/26
.. _27: https://github.com/giampaolo/psutil/issues/27
.. _28: https://github.com/giampaolo/psutil/issues/28
.. _29: https://github.com/giampaolo/psutil/issues/29
.. _30: https://github.com/giampaolo/psutil/issues/30
.. _31: https://github.com/giampaolo/psutil/issues/31
.. _32: https://github.com/giampaolo/psutil/issues/32
.. _33: https://github.com/giampaolo/psutil/issues/33
.. _34: https://github.com/giampaolo/psutil/issues/34
.. _35: https://github.com/giampaolo/psutil/issues/35
.. _36: https://github.com/giampaolo/psutil/issues/36
.. _37: https://github.com/giampaolo/psutil/issues/37
.. _38: https://github.com/giampaolo/psutil/issues/38
.. _39: https://github.com/giampaolo/psutil/issues/39
.. _40: https://github.com/giampaolo/psutil/issues/40
.. _41: https://github.com/giampaolo/psutil/issues/41
.. _42: https://github.com/giampaolo/psutil/issues/42
.. _43: https://github.com/giampaolo/psutil/issues/43
.. _44: https://github.com/giampaolo/psutil/issues/44
.. _45: https://github.com/giampaolo/psutil/issues/45
.. _46: https://github.com/giampaolo/psutil/issues/46
.. _47: https://github.com/giampaolo/psutil/issues/47
.. _48: https://github.com/giampaolo/psutil/issues/48
.. _49: https://github.com/giampaolo/psutil/issues/49
.. _50: https://github.com/giampaolo/psutil/issues/50
.. _51: https://github.com/giampaolo/psutil/issues/51
.. _52: https://github.com/giampaolo/psutil/issues/52
.. _53: https://github.com/giampaolo/psutil/issues/53
.. _54: https://github.com/giampaolo/psutil/issues/54
.. _55: https://github.com/giampaolo/psutil/issues/55
.. _56: https://github.com/giampaolo/psutil/issues/56
.. _57: https://github.com/giampaolo/psutil/issues/57
.. _58: https://github.com/giampaolo/psutil/issues/58
.. _59: https://github.com/giampaolo/psutil/issues/59
.. _60: https://github.com/giampaolo/psutil/issues/60
.. _61: https://github.com/giampaolo/psutil/issues/61
.. _62: https://github.com/giampaolo/psutil/issues/62
.. _63: https://github.com/giampaolo/psutil/issues/63
.. _64: https://github.com/giampaolo/psutil/issues/64
.. _65: https://github.com/giampaolo/psutil/issues/65
.. _66: https://github.com/giampaolo/psutil/issues/66
.. _67: https://github.com/giampaolo/psutil/issues/67
.. _68: https://github.com/giampaolo/psutil/issues/68
.. _69: https://github.com/giampaolo/psutil/issues/69
.. _70: https://github.com/giampaolo/psutil/issues/70
.. _71: https://github.com/giampaolo/psutil/issues/71
.. _72: https://github.com/giampaolo/psutil/issues/72
.. _73: https://github.com/giampaolo/psutil/issues/73
.. _74: https://github.com/giampaolo/psutil/issues/74
.. _75: https://github.com/giampaolo/psutil/issues/75
.. _76: https://github.com/giampaolo/psutil/issues/76
.. _77: https://github.com/giampaolo/psutil/issues/77
.. _78: https://github.com/giampaolo/psutil/issues/78
.. _79: https://github.com/giampaolo/psutil/issues/79
.. _80: https://github.com/giampaolo/psutil/issues/80
.. _81: https://github.com/giampaolo/psutil/issues/81
.. _82: https://github.com/giampaolo/psutil/issues/82
.. _83: https://github.com/giampaolo/psutil/issues/83
.. _84: https://github.com/giampaolo/psutil/issues/84
.. _85: https://github.com/giampaolo/psutil/issues/85
.. _86: https://github.com/giampaolo/psutil/issues/86
.. _87: https://github.com/giampaolo/psutil/issues/87
.. _88: https://github.com/giampaolo/psutil/issues/88
.. _89: https://github.com/giampaolo/psutil/issues/89
.. _90: https://github.com/giampaolo/psutil/issues/90
.. _91: https://github.com/giampaolo/psutil/issues/91
.. _92: https://github.com/giampaolo/psutil/issues/92
.. _93: https://github.com/giampaolo/psutil/issues/93
.. _94: https://github.com/giampaolo/psutil/issues/94
.. _95: https://github.com/giampaolo/psutil/issues/95
.. _96: https://github.com/giampaolo/psutil/issues/96
.. _97: https://github.com/giampaolo/psutil/issues/97
.. _98: https://github.com/giampaolo/psutil/issues/98
.. _99: https://github.com/giampaolo/psutil/issues/99
.. _100: https://github.com/giampaolo/psutil/issues/100
.. _101: https://github.com/giampaolo/psutil/issues/101
.. _102: https://github.com/giampaolo/psutil/issues/102
.. _103: https://github.com/giampaolo/psutil/issues/103
.. _104: https://github.com/giampaolo/psutil/issues/104
.. _105: https://github.com/giampaolo/psutil/issues/105
.. _106: https://github.com/giampaolo/psutil/issues/106
.. _107: https://github.com/giampaolo/psutil/issues/107
.. _108: https://github.com/giampaolo/psutil/issues/108
.. _109: https://github.com/giampaolo/psutil/issues/109
.. _110: https://github.com/giampaolo/psutil/issues/110
.. _111: https://github.com/giampaolo/psutil/issues/111
.. _112: https://github.com/giampaolo/psutil/issues/112
.. _113: https://github.com/giampaolo/psutil/issues/113
.. _114: https://github.com/giampaolo/psutil/issues/114
.. _115: https://github.com/giampaolo/psutil/issues/115
.. _116: https://github.com/giampaolo/psutil/issues/116
.. _117: https://github.com/giampaolo/psutil/issues/117
.. _118: https://github.com/giampaolo/psutil/issues/118
.. _119: https://github.com/giampaolo/psutil/issues/119
.. _120: https://github.com/giampaolo/psutil/issues/120
.. _121: https://github.com/giampaolo/psutil/issues/121
.. _122: https://github.com/giampaolo/psutil/issues/122
.. _123: https://github.com/giampaolo/psutil/issues/123
.. _124: https://github.com/giampaolo/psutil/issues/124
.. _125: https://github.com/giampaolo/psutil/issues/125
.. _126: https://github.com/giampaolo/psutil/issues/126
.. _127: https://github.com/giampaolo/psutil/issues/127
.. _128: https://github.com/giampaolo/psutil/issues/128
.. _129: https://github.com/giampaolo/psutil/issues/129
.. _130: https://github.com/giampaolo/psutil/issues/130
.. _131: https://github.com/giampaolo/psutil/issues/131
.. _132: https://github.com/giampaolo/psutil/issues/132
.. _133: https://github.com/giampaolo/psutil/issues/133
.. _134: https://github.com/giampaolo/psutil/issues/134
.. _135: https://github.com/giampaolo/psutil/issues/135
.. _136: https://github.com/giampaolo/psutil/issues/136
.. _137: https://github.com/giampaolo/psutil/issues/137
.. _138: https://github.com/giampaolo/psutil/issues/138
.. _139: https://github.com/giampaolo/psutil/issues/139
.. _140: https://github.com/giampaolo/psutil/issues/140
.. _141: https://github.com/giampaolo/psutil/issues/141
.. _142: https://github.com/giampaolo/psutil/issues/142
.. _143: https://github.com/giampaolo/psutil/issues/143
.. _144: https://github.com/giampaolo/psutil/issues/144
.. _145: https://github.com/giampaolo/psutil/issues/145
.. _146: https://github.com/giampaolo/psutil/issues/146
.. _147: https://github.com/giampaolo/psutil/issues/147
.. _148: https://github.com/giampaolo/psutil/issues/148
.. _149: https://github.com/giampaolo/psutil/issues/149
.. _150: https://github.com/giampaolo/psutil/issues/150
.. _151: https://github.com/giampaolo/psutil/issues/151
.. _152: https://github.com/giampaolo/psutil/issues/152
.. _153: https://github.com/giampaolo/psutil/issues/153
.. _154: https://github.com/giampaolo/psutil/issues/154
.. _155: https://github.com/giampaolo/psutil/issues/155
.. _156: https://github.com/giampaolo/psutil/issues/156
.. _157: https://github.com/giampaolo/psutil/issues/157
.. _158: https://github.com/giampaolo/psutil/issues/158
.. _159: https://github.com/giampaolo/psutil/issues/159
.. _160: https://github.com/giampaolo/psutil/issues/160
.. _161: https://github.com/giampaolo/psutil/issues/161
.. _162: https://github.com/giampaolo/psutil/issues/162
.. _163: https://github.com/giampaolo/psutil/issues/163
.. _164: https://github.com/giampaolo/psutil/issues/164
.. _165: https://github.com/giampaolo/psutil/issues/165
.. _166: https://github.com/giampaolo/psutil/issues/166
.. _167: https://github.com/giampaolo/psutil/issues/167
.. _168: https://github.com/giampaolo/psutil/issues/168
.. _169: https://github.com/giampaolo/psutil/issues/169
.. _170: https://github.com/giampaolo/psutil/issues/170
.. _171: https://github.com/giampaolo/psutil/issues/171
.. _172: https://github.com/giampaolo/psutil/issues/172
.. _173: https://github.com/giampaolo/psutil/issues/173
.. _174: https://github.com/giampaolo/psutil/issues/174
.. _175: https://github.com/giampaolo/psutil/issues/175
.. _176: https://github.com/giampaolo/psutil/issues/176
.. _177: https://github.com/giampaolo/psutil/issues/177
.. _178: https://github.com/giampaolo/psutil/issues/178
.. _179: https://github.com/giampaolo/psutil/issues/179
.. _180: https://github.com/giampaolo/psutil/issues/180
.. _181: https://github.com/giampaolo/psutil/issues/181
.. _182: https://github.com/giampaolo/psutil/issues/182
.. _183: https://github.com/giampaolo/psutil/issues/183
.. _184: https://github.com/giampaolo/psutil/issues/184
.. _185: https://github.com/giampaolo/psutil/issues/185
.. _186: https://github.com/giampaolo/psutil/issues/186
.. _187: https://github.com/giampaolo/psutil/issues/187
.. _188: https://github.com/giampaolo/psutil/issues/188
.. _189: https://github.com/giampaolo/psutil/issues/189
.. _190: https://github.com/giampaolo/psutil/issues/190
.. _191: https://github.com/giampaolo/psutil/issues/191
.. _192: https://github.com/giampaolo/psutil/issues/192
.. _193: https://github.com/giampaolo/psutil/issues/193
.. _194: https://github.com/giampaolo/psutil/issues/194
.. _195: https://github.com/giampaolo/psutil/issues/195
.. _196: https://github.com/giampaolo/psutil/issues/196
.. _197: https://github.com/giampaolo/psutil/issues/197
.. _198: https://github.com/giampaolo/psutil/issues/198
.. _199: https://github.com/giampaolo/psutil/issues/199
.. _200: https://github.com/giampaolo/psutil/issues/200
.. _201: https://github.com/giampaolo/psutil/issues/201
.. _202: https://github.com/giampaolo/psutil/issues/202
.. _203: https://github.com/giampaolo/psutil/issues/203
.. _204: https://github.com/giampaolo/psutil/issues/204
.. _205: https://github.com/giampaolo/psutil/issues/205
.. _206: https://github.com/giampaolo/psutil/issues/206
.. _207: https://github.com/giampaolo/psutil/issues/207
.. _208: https://github.com/giampaolo/psutil/issues/208
.. _209: https://github.com/giampaolo/psutil/issues/209
.. _210: https://github.com/giampaolo/psutil/issues/210
.. _211: https://github.com/giampaolo/psutil/issues/211
.. _212: https://github.com/giampaolo/psutil/issues/212
.. _213: https://github.com/giampaolo/psutil/issues/213
.. _214: https://github.com/giampaolo/psutil/issues/214
.. _215: https://github.com/giampaolo/psutil/issues/215
.. _216: https://github.com/giampaolo/psutil/issues/216
.. _217: https://github.com/giampaolo/psutil/issues/217
.. _218: https://github.com/giampaolo/psutil/issues/218
.. _219: https://github.com/giampaolo/psutil/issues/219
.. _220: https://github.com/giampaolo/psutil/issues/220
.. _221: https://github.com/giampaolo/psutil/issues/221
.. _222: https://github.com/giampaolo/psutil/issues/222
.. _223: https://github.com/giampaolo/psutil/issues/223
.. _224: https://github.com/giampaolo/psutil/issues/224
.. _225: https://github.com/giampaolo/psutil/issues/225
.. _226: https://github.com/giampaolo/psutil/issues/226
.. _227: https://github.com/giampaolo/psutil/issues/227
.. _228: https://github.com/giampaolo/psutil/issues/228
.. _229: https://github.com/giampaolo/psutil/issues/229
.. _230: https://github.com/giampaolo/psutil/issues/230
.. _231: https://github.com/giampaolo/psutil/issues/231
.. _232: https://github.com/giampaolo/psutil/issues/232
.. _233: https://github.com/giampaolo/psutil/issues/233
.. _234: https://github.com/giampaolo/psutil/issues/234
.. _235: https://github.com/giampaolo/psutil/issues/235
.. _236: https://github.com/giampaolo/psutil/issues/236
.. _237: https://github.com/giampaolo/psutil/issues/237
.. _238: https://github.com/giampaolo/psutil/issues/238
.. _239: https://github.com/giampaolo/psutil/issues/239
.. _240: https://github.com/giampaolo/psutil/issues/240
.. _241: https://github.com/giampaolo/psutil/issues/241
.. _242: https://github.com/giampaolo/psutil/issues/242
.. _243: https://github.com/giampaolo/psutil/issues/243
.. _244: https://github.com/giampaolo/psutil/issues/244
.. _245: https://github.com/giampaolo/psutil/issues/245
.. _246: https://github.com/giampaolo/psutil/issues/246
.. _247: https://github.com/giampaolo/psutil/issues/247
.. _248: https://github.com/giampaolo/psutil/issues/248
.. _249: https://github.com/giampaolo/psutil/issues/249
.. _250: https://github.com/giampaolo/psutil/issues/250
.. _251: https://github.com/giampaolo/psutil/issues/251
.. _252: https://github.com/giampaolo/psutil/issues/252
.. _253: https://github.com/giampaolo/psutil/issues/253
.. _254: https://github.com/giampaolo/psutil/issues/254
.. _255: https://github.com/giampaolo/psutil/issues/255
.. _256: https://github.com/giampaolo/psutil/issues/256
.. _257: https://github.com/giampaolo/psutil/issues/257
.. _258: https://github.com/giampaolo/psutil/issues/258
.. _259: https://github.com/giampaolo/psutil/issues/259
.. _260: https://github.com/giampaolo/psutil/issues/260
.. _261: https://github.com/giampaolo/psutil/issues/261
.. _262: https://github.com/giampaolo/psutil/issues/262
.. _263: https://github.com/giampaolo/psutil/issues/263
.. _264: https://github.com/giampaolo/psutil/issues/264
.. _265: https://github.com/giampaolo/psutil/issues/265
.. _266: https://github.com/giampaolo/psutil/issues/266
.. _267: https://github.com/giampaolo/psutil/issues/267
.. _268: https://github.com/giampaolo/psutil/issues/268
.. _269: https://github.com/giampaolo/psutil/issues/269
.. _270: https://github.com/giampaolo/psutil/issues/270
.. _271: https://github.com/giampaolo/psutil/issues/271
.. _272: https://github.com/giampaolo/psutil/issues/272
.. _273: https://github.com/giampaolo/psutil/issues/273
.. _274: https://github.com/giampaolo/psutil/issues/274
.. _275: https://github.com/giampaolo/psutil/issues/275
.. _276: https://github.com/giampaolo/psutil/issues/276
.. _277: https://github.com/giampaolo/psutil/issues/277
.. _278: https://github.com/giampaolo/psutil/issues/278
.. _279: https://github.com/giampaolo/psutil/issues/279
.. _280: https://github.com/giampaolo/psutil/issues/280
.. _281: https://github.com/giampaolo/psutil/issues/281
.. _282: https://github.com/giampaolo/psutil/issues/282
.. _283: https://github.com/giampaolo/psutil/issues/283
.. _284: https://github.com/giampaolo/psutil/issues/284
.. _285: https://github.com/giampaolo/psutil/issues/285
.. _286: https://github.com/giampaolo/psutil/issues/286
.. _287: https://github.com/giampaolo/psutil/issues/287
.. _288: https://github.com/giampaolo/psutil/issues/288
.. _289: https://github.com/giampaolo/psutil/issues/289
.. _290: https://github.com/giampaolo/psutil/issues/290
.. _291: https://github.com/giampaolo/psutil/issues/291
.. _292: https://github.com/giampaolo/psutil/issues/292
.. _293: https://github.com/giampaolo/psutil/issues/293
.. _294: https://github.com/giampaolo/psutil/issues/294
.. _295: https://github.com/giampaolo/psutil/issues/295
.. _296: https://github.com/giampaolo/psutil/issues/296
.. _297: https://github.com/giampaolo/psutil/issues/297
.. _298: https://github.com/giampaolo/psutil/issues/298
.. _299: https://github.com/giampaolo/psutil/issues/299
.. _300: https://github.com/giampaolo/psutil/issues/300
.. _301: https://github.com/giampaolo/psutil/issues/301
.. _302: https://github.com/giampaolo/psutil/issues/302
.. _303: https://github.com/giampaolo/psutil/issues/303
.. _304: https://github.com/giampaolo/psutil/issues/304
.. _305: https://github.com/giampaolo/psutil/issues/305
.. _306: https://github.com/giampaolo/psutil/issues/306
.. _307: https://github.com/giampaolo/psutil/issues/307
.. _308: https://github.com/giampaolo/psutil/issues/308
.. _309: https://github.com/giampaolo/psutil/issues/309
.. _310: https://github.com/giampaolo/psutil/issues/310
.. _311: https://github.com/giampaolo/psutil/issues/311
.. _312: https://github.com/giampaolo/psutil/issues/312
.. _313: https://github.com/giampaolo/psutil/issues/313
.. _314: https://github.com/giampaolo/psutil/issues/314
.. _315: https://github.com/giampaolo/psutil/issues/315
.. _316: https://github.com/giampaolo/psutil/issues/316
.. _317: https://github.com/giampaolo/psutil/issues/317
.. _318: https://github.com/giampaolo/psutil/issues/318
.. _319: https://github.com/giampaolo/psutil/issues/319
.. _320: https://github.com/giampaolo/psutil/issues/320
.. _321: https://github.com/giampaolo/psutil/issues/321
.. _322: https://github.com/giampaolo/psutil/issues/322
.. _323: https://github.com/giampaolo/psutil/issues/323
.. _324: https://github.com/giampaolo/psutil/issues/324
.. _325: https://github.com/giampaolo/psutil/issues/325
.. _326: https://github.com/giampaolo/psutil/issues/326
.. _327: https://github.com/giampaolo/psutil/issues/327
.. _328: https://github.com/giampaolo/psutil/issues/328
.. _329: https://github.com/giampaolo/psutil/issues/329
.. _330: https://github.com/giampaolo/psutil/issues/330
.. _331: https://github.com/giampaolo/psutil/issues/331
.. _332: https://github.com/giampaolo/psutil/issues/332
.. _333: https://github.com/giampaolo/psutil/issues/333
.. _334: https://github.com/giampaolo/psutil/issues/334
.. _335: https://github.com/giampaolo/psutil/issues/335
.. _336: https://github.com/giampaolo/psutil/issues/336
.. _337: https://github.com/giampaolo/psutil/issues/337
.. _338: https://github.com/giampaolo/psutil/issues/338
.. _339: https://github.com/giampaolo/psutil/issues/339
.. _340: https://github.com/giampaolo/psutil/issues/340
.. _341: https://github.com/giampaolo/psutil/issues/341
.. _342: https://github.com/giampaolo/psutil/issues/342
.. _343: https://github.com/giampaolo/psutil/issues/343
.. _344: https://github.com/giampaolo/psutil/issues/344
.. _345: https://github.com/giampaolo/psutil/issues/345
.. _346: https://github.com/giampaolo/psutil/issues/346
.. _347: https://github.com/giampaolo/psutil/issues/347
.. _348: https://github.com/giampaolo/psutil/issues/348
.. _349: https://github.com/giampaolo/psutil/issues/349
.. _350: https://github.com/giampaolo/psutil/issues/350
.. _351: https://github.com/giampaolo/psutil/issues/351
.. _352: https://github.com/giampaolo/psutil/issues/352
.. _353: https://github.com/giampaolo/psutil/issues/353
.. _354: https://github.com/giampaolo/psutil/issues/354
.. _355: https://github.com/giampaolo/psutil/issues/355
.. _356: https://github.com/giampaolo/psutil/issues/356
.. _357: https://github.com/giampaolo/psutil/issues/357
.. _358: https://github.com/giampaolo/psutil/issues/358
.. _359: https://github.com/giampaolo/psutil/issues/359
.. _360: https://github.com/giampaolo/psutil/issues/360
.. _361: https://github.com/giampaolo/psutil/issues/361
.. _362: https://github.com/giampaolo/psutil/issues/362
.. _363: https://github.com/giampaolo/psutil/issues/363
.. _364: https://github.com/giampaolo/psutil/issues/364
.. _365: https://github.com/giampaolo/psutil/issues/365
.. _366: https://github.com/giampaolo/psutil/issues/366
.. _367: https://github.com/giampaolo/psutil/issues/367
.. _368: https://github.com/giampaolo/psutil/issues/368
.. _369: https://github.com/giampaolo/psutil/issues/369
.. _370: https://github.com/giampaolo/psutil/issues/370
.. _371: https://github.com/giampaolo/psutil/issues/371
.. _372: https://github.com/giampaolo/psutil/issues/372
.. _373: https://github.com/giampaolo/psutil/issues/373
.. _374: https://github.com/giampaolo/psutil/issues/374
.. _375: https://github.com/giampaolo/psutil/issues/375
.. _376: https://github.com/giampaolo/psutil/issues/376
.. _377: https://github.com/giampaolo/psutil/issues/377
.. _378: https://github.com/giampaolo/psutil/issues/378
.. _379: https://github.com/giampaolo/psutil/issues/379
.. _380: https://github.com/giampaolo/psutil/issues/380
.. _381: https://github.com/giampaolo/psutil/issues/381
.. _382: https://github.com/giampaolo/psutil/issues/382
.. _383: https://github.com/giampaolo/psutil/issues/383
.. _384: https://github.com/giampaolo/psutil/issues/384
.. _385: https://github.com/giampaolo/psutil/issues/385
.. _386: https://github.com/giampaolo/psutil/issues/386
.. _387: https://github.com/giampaolo/psutil/issues/387
.. _388: https://github.com/giampaolo/psutil/issues/388
.. _389: https://github.com/giampaolo/psutil/issues/389
.. _390: https://github.com/giampaolo/psutil/issues/390
.. _391: https://github.com/giampaolo/psutil/issues/391
.. _392: https://github.com/giampaolo/psutil/issues/392
.. _393: https://github.com/giampaolo/psutil/issues/393
.. _394: https://github.com/giampaolo/psutil/issues/394
.. _395: https://github.com/giampaolo/psutil/issues/395
.. _396: https://github.com/giampaolo/psutil/issues/396
.. _397: https://github.com/giampaolo/psutil/issues/397
.. _398: https://github.com/giampaolo/psutil/issues/398
.. _399: https://github.com/giampaolo/psutil/issues/399
.. _400: https://github.com/giampaolo/psutil/issues/400
.. _401: https://github.com/giampaolo/psutil/issues/401
.. _402: https://github.com/giampaolo/psutil/issues/402
.. _403: https://github.com/giampaolo/psutil/issues/403
.. _404: https://github.com/giampaolo/psutil/issues/404
.. _405: https://github.com/giampaolo/psutil/issues/405
.. _406: https://github.com/giampaolo/psutil/issues/406
.. _407: https://github.com/giampaolo/psutil/issues/407
.. _408: https://github.com/giampaolo/psutil/issues/408
.. _409: https://github.com/giampaolo/psutil/issues/409
.. _410: https://github.com/giampaolo/psutil/issues/410
.. _411: https://github.com/giampaolo/psutil/issues/411
.. _412: https://github.com/giampaolo/psutil/issues/412
.. _413: https://github.com/giampaolo/psutil/issues/413
.. _414: https://github.com/giampaolo/psutil/issues/414
.. _415: https://github.com/giampaolo/psutil/issues/415
.. _416: https://github.com/giampaolo/psutil/issues/416
.. _417: https://github.com/giampaolo/psutil/issues/417
.. _418: https://github.com/giampaolo/psutil/issues/418
.. _419: https://github.com/giampaolo/psutil/issues/419
.. _420: https://github.com/giampaolo/psutil/issues/420
.. _421: https://github.com/giampaolo/psutil/issues/421
.. _422: https://github.com/giampaolo/psutil/issues/422
.. _423: https://github.com/giampaolo/psutil/issues/423
.. _424: https://github.com/giampaolo/psutil/issues/424
.. _425: https://github.com/giampaolo/psutil/issues/425
.. _426: https://github.com/giampaolo/psutil/issues/426
.. _427: https://github.com/giampaolo/psutil/issues/427
.. _428: https://github.com/giampaolo/psutil/issues/428
.. _429: https://github.com/giampaolo/psutil/issues/429
.. _430: https://github.com/giampaolo/psutil/issues/430
.. _431: https://github.com/giampaolo/psutil/issues/431
.. _432: https://github.com/giampaolo/psutil/issues/432
.. _433: https://github.com/giampaolo/psutil/issues/433
.. _434: https://github.com/giampaolo/psutil/issues/434
.. _435: https://github.com/giampaolo/psutil/issues/435
.. _436: https://github.com/giampaolo/psutil/issues/436
.. _437: https://github.com/giampaolo/psutil/issues/437
.. _438: https://github.com/giampaolo/psutil/issues/438
.. _439: https://github.com/giampaolo/psutil/issues/439
.. _440: https://github.com/giampaolo/psutil/issues/440
.. _441: https://github.com/giampaolo/psutil/issues/441
.. _442: https://github.com/giampaolo/psutil/issues/442
.. _443: https://github.com/giampaolo/psutil/issues/443
.. _444: https://github.com/giampaolo/psutil/issues/444
.. _445: https://github.com/giampaolo/psutil/issues/445
.. _446: https://github.com/giampaolo/psutil/issues/446
.. _447: https://github.com/giampaolo/psutil/issues/447
.. _448: https://github.com/giampaolo/psutil/issues/448
.. _449: https://github.com/giampaolo/psutil/issues/449
.. _450: https://github.com/giampaolo/psutil/issues/450
.. _451: https://github.com/giampaolo/psutil/issues/451
.. _452: https://github.com/giampaolo/psutil/issues/452
.. _453: https://github.com/giampaolo/psutil/issues/453
.. _454: https://github.com/giampaolo/psutil/issues/454
.. _455: https://github.com/giampaolo/psutil/issues/455
.. _456: https://github.com/giampaolo/psutil/issues/456
.. _457: https://github.com/giampaolo/psutil/issues/457
.. _458: https://github.com/giampaolo/psutil/issues/458
.. _459: https://github.com/giampaolo/psutil/issues/459
.. _460: https://github.com/giampaolo/psutil/issues/460
.. _461: https://github.com/giampaolo/psutil/issues/461
.. _462: https://github.com/giampaolo/psutil/issues/462
.. _463: https://github.com/giampaolo/psutil/issues/463
.. _464: https://github.com/giampaolo/psutil/issues/464
.. _465: https://github.com/giampaolo/psutil/issues/465
.. _466: https://github.com/giampaolo/psutil/issues/466
.. _467: https://github.com/giampaolo/psutil/issues/467
.. _468: https://github.com/giampaolo/psutil/issues/468
.. _469: https://github.com/giampaolo/psutil/issues/469
.. _470: https://github.com/giampaolo/psutil/issues/470
.. _471: https://github.com/giampaolo/psutil/issues/471
.. _472: https://github.com/giampaolo/psutil/issues/472
.. _473: https://github.com/giampaolo/psutil/issues/473
.. _474: https://github.com/giampaolo/psutil/issues/474
.. _475: https://github.com/giampaolo/psutil/issues/475
.. _476: https://github.com/giampaolo/psutil/issues/476
.. _477: https://github.com/giampaolo/psutil/issues/477
.. _478: https://github.com/giampaolo/psutil/issues/478
.. _479: https://github.com/giampaolo/psutil/issues/479
.. _480: https://github.com/giampaolo/psutil/issues/480
.. _481: https://github.com/giampaolo/psutil/issues/481
.. _482: https://github.com/giampaolo/psutil/issues/482
.. _483: https://github.com/giampaolo/psutil/issues/483
.. _484: https://github.com/giampaolo/psutil/issues/484
.. _485: https://github.com/giampaolo/psutil/issues/485
.. _486: https://github.com/giampaolo/psutil/issues/486
.. _487: https://github.com/giampaolo/psutil/issues/487
.. _488: https://github.com/giampaolo/psutil/issues/488
.. _489: https://github.com/giampaolo/psutil/issues/489
.. _490: https://github.com/giampaolo/psutil/issues/490
.. _491: https://github.com/giampaolo/psutil/issues/491
.. _492: https://github.com/giampaolo/psutil/issues/492
.. _493: https://github.com/giampaolo/psutil/issues/493
.. _494: https://github.com/giampaolo/psutil/issues/494
.. _495: https://github.com/giampaolo/psutil/issues/495
.. _496: https://github.com/giampaolo/psutil/issues/496
.. _497: https://github.com/giampaolo/psutil/issues/497
.. _498: https://github.com/giampaolo/psutil/issues/498
.. _499: https://github.com/giampaolo/psutil/issues/499
.. _500: https://github.com/giampaolo/psutil/issues/500
.. _501: https://github.com/giampaolo/psutil/issues/501
.. _502: https://github.com/giampaolo/psutil/issues/502
.. _503: https://github.com/giampaolo/psutil/issues/503
.. _504: https://github.com/giampaolo/psutil/issues/504
.. _505: https://github.com/giampaolo/psutil/issues/505
.. _506: https://github.com/giampaolo/psutil/issues/506
.. _507: https://github.com/giampaolo/psutil/issues/507
.. _508: https://github.com/giampaolo/psutil/issues/508
.. _509: https://github.com/giampaolo/psutil/issues/509
.. _510: https://github.com/giampaolo/psutil/issues/510
.. _511: https://github.com/giampaolo/psutil/issues/511
.. _512: https://github.com/giampaolo/psutil/issues/512
.. _513: https://github.com/giampaolo/psutil/issues/513
.. _514: https://github.com/giampaolo/psutil/issues/514
.. _515: https://github.com/giampaolo/psutil/issues/515
.. _516: https://github.com/giampaolo/psutil/issues/516
.. _517: https://github.com/giampaolo/psutil/issues/517
.. _518: https://github.com/giampaolo/psutil/issues/518
.. _519: https://github.com/giampaolo/psutil/issues/519
.. _520: https://github.com/giampaolo/psutil/issues/520
.. _521: https://github.com/giampaolo/psutil/issues/521
.. _522: https://github.com/giampaolo/psutil/issues/522
.. _523: https://github.com/giampaolo/psutil/issues/523
.. _524: https://github.com/giampaolo/psutil/issues/524
.. _525: https://github.com/giampaolo/psutil/issues/525
.. _526: https://github.com/giampaolo/psutil/issues/526
.. _527: https://github.com/giampaolo/psutil/issues/527
.. _528: https://github.com/giampaolo/psutil/issues/528
.. _529: https://github.com/giampaolo/psutil/issues/529
.. _530: https://github.com/giampaolo/psutil/issues/530
.. _531: https://github.com/giampaolo/psutil/issues/531
.. _532: https://github.com/giampaolo/psutil/issues/532
.. _533: https://github.com/giampaolo/psutil/issues/533
.. _534: https://github.com/giampaolo/psutil/issues/534
.. _535: https://github.com/giampaolo/psutil/issues/535
.. _536: https://github.com/giampaolo/psutil/issues/536
.. _537: https://github.com/giampaolo/psutil/issues/537
.. _538: https://github.com/giampaolo/psutil/issues/538
.. _539: https://github.com/giampaolo/psutil/issues/539
.. _540: https://github.com/giampaolo/psutil/issues/540
.. _541: https://github.com/giampaolo/psutil/issues/541
.. _542: https://github.com/giampaolo/psutil/issues/542
.. _543: https://github.com/giampaolo/psutil/issues/543
.. _544: https://github.com/giampaolo/psutil/issues/544
.. _545: https://github.com/giampaolo/psutil/issues/545
.. _546: https://github.com/giampaolo/psutil/issues/546
.. _547: https://github.com/giampaolo/psutil/issues/547
.. _548: https://github.com/giampaolo/psutil/issues/548
.. _549: https://github.com/giampaolo/psutil/issues/549
.. _550: https://github.com/giampaolo/psutil/issues/550
.. _551: https://github.com/giampaolo/psutil/issues/551
.. _552: https://github.com/giampaolo/psutil/issues/552
.. _553: https://github.com/giampaolo/psutil/issues/553
.. _554: https://github.com/giampaolo/psutil/issues/554
.. _555: https://github.com/giampaolo/psutil/issues/555
.. _556: https://github.com/giampaolo/psutil/issues/556
.. _557: https://github.com/giampaolo/psutil/issues/557
.. _558: https://github.com/giampaolo/psutil/issues/558
.. _559: https://github.com/giampaolo/psutil/issues/559
.. _560: https://github.com/giampaolo/psutil/issues/560
.. _561: https://github.com/giampaolo/psutil/issues/561
.. _562: https://github.com/giampaolo/psutil/issues/562
.. _563: https://github.com/giampaolo/psutil/issues/563
.. _564: https://github.com/giampaolo/psutil/issues/564
.. _565: https://github.com/giampaolo/psutil/issues/565
.. _566: https://github.com/giampaolo/psutil/issues/566
.. _567: https://github.com/giampaolo/psutil/issues/567
.. _568: https://github.com/giampaolo/psutil/issues/568
.. _569: https://github.com/giampaolo/psutil/issues/569
.. _570: https://github.com/giampaolo/psutil/issues/570
.. _571: https://github.com/giampaolo/psutil/issues/571
.. _572: https://github.com/giampaolo/psutil/issues/572
.. _573: https://github.com/giampaolo/psutil/issues/573
.. _574: https://github.com/giampaolo/psutil/issues/574
.. _575: https://github.com/giampaolo/psutil/issues/575
.. _576: https://github.com/giampaolo/psutil/issues/576
.. _577: https://github.com/giampaolo/psutil/issues/577
.. _578: https://github.com/giampaolo/psutil/issues/578
.. _579: https://github.com/giampaolo/psutil/issues/579
.. _580: https://github.com/giampaolo/psutil/issues/580
.. _581: https://github.com/giampaolo/psutil/issues/581
.. _582: https://github.com/giampaolo/psutil/issues/582
.. _583: https://github.com/giampaolo/psutil/issues/583
.. _584: https://github.com/giampaolo/psutil/issues/584
.. _585: https://github.com/giampaolo/psutil/issues/585
.. _586: https://github.com/giampaolo/psutil/issues/586
.. _587: https://github.com/giampaolo/psutil/issues/587
.. _588: https://github.com/giampaolo/psutil/issues/588
.. _589: https://github.com/giampaolo/psutil/issues/589
.. _590: https://github.com/giampaolo/psutil/issues/590
.. _591: https://github.com/giampaolo/psutil/issues/591
.. _592: https://github.com/giampaolo/psutil/issues/592
.. _593: https://github.com/giampaolo/psutil/issues/593
.. _594: https://github.com/giampaolo/psutil/issues/594
.. _595: https://github.com/giampaolo/psutil/issues/595
.. _596: https://github.com/giampaolo/psutil/issues/596
.. _597: https://github.com/giampaolo/psutil/issues/597
.. _598: https://github.com/giampaolo/psutil/issues/598
.. _599: https://github.com/giampaolo/psutil/issues/599
.. _600: https://github.com/giampaolo/psutil/issues/600
.. _601: https://github.com/giampaolo/psutil/issues/601
.. _602: https://github.com/giampaolo/psutil/issues/602
.. _603: https://github.com/giampaolo/psutil/issues/603
.. _604: https://github.com/giampaolo/psutil/issues/604
.. _605: https://github.com/giampaolo/psutil/issues/605
.. _606: https://github.com/giampaolo/psutil/issues/606
.. _607: https://github.com/giampaolo/psutil/issues/607
.. _608: https://github.com/giampaolo/psutil/issues/608
.. _609: https://github.com/giampaolo/psutil/issues/609
.. _610: https://github.com/giampaolo/psutil/issues/610
.. _611: https://github.com/giampaolo/psutil/issues/611
.. _612: https://github.com/giampaolo/psutil/issues/612
.. _613: https://github.com/giampaolo/psutil/issues/613
.. _614: https://github.com/giampaolo/psutil/issues/614
.. _615: https://github.com/giampaolo/psutil/issues/615
.. _616: https://github.com/giampaolo/psutil/issues/616
.. _617: https://github.com/giampaolo/psutil/issues/617
.. _618: https://github.com/giampaolo/psutil/issues/618
.. _619: https://github.com/giampaolo/psutil/issues/619
.. _620: https://github.com/giampaolo/psutil/issues/620
.. _621: https://github.com/giampaolo/psutil/issues/621
.. _622: https://github.com/giampaolo/psutil/issues/622
.. _623: https://github.com/giampaolo/psutil/issues/623
.. _624: https://github.com/giampaolo/psutil/issues/624
.. _625: https://github.com/giampaolo/psutil/issues/625
.. _626: https://github.com/giampaolo/psutil/issues/626
.. _627: https://github.com/giampaolo/psutil/issues/627
.. _628: https://github.com/giampaolo/psutil/issues/628
.. _629: https://github.com/giampaolo/psutil/issues/629
.. _630: https://github.com/giampaolo/psutil/issues/630
.. _631: https://github.com/giampaolo/psutil/issues/631
.. _632: https://github.com/giampaolo/psutil/issues/632
.. _633: https://github.com/giampaolo/psutil/issues/633
.. _634: https://github.com/giampaolo/psutil/issues/634
.. _635: https://github.com/giampaolo/psutil/issues/635
.. _636: https://github.com/giampaolo/psutil/issues/636
.. _637: https://github.com/giampaolo/psutil/issues/637
.. _638: https://github.com/giampaolo/psutil/issues/638
.. _639: https://github.com/giampaolo/psutil/issues/639
.. _640: https://github.com/giampaolo/psutil/issues/640
.. _641: https://github.com/giampaolo/psutil/issues/641
.. _642: https://github.com/giampaolo/psutil/issues/642
.. _643: https://github.com/giampaolo/psutil/issues/643
.. _644: https://github.com/giampaolo/psutil/issues/644
.. _645: https://github.com/giampaolo/psutil/issues/645
.. _646: https://github.com/giampaolo/psutil/issues/646
.. _647: https://github.com/giampaolo/psutil/issues/647
.. _648: https://github.com/giampaolo/psutil/issues/648
.. _649: https://github.com/giampaolo/psutil/issues/649
.. _650: https://github.com/giampaolo/psutil/issues/650
.. _651: https://github.com/giampaolo/psutil/issues/651
.. _652: https://github.com/giampaolo/psutil/issues/652
.. _653: https://github.com/giampaolo/psutil/issues/653
.. _654: https://github.com/giampaolo/psutil/issues/654
.. _655: https://github.com/giampaolo/psutil/issues/655
.. _656: https://github.com/giampaolo/psutil/issues/656
.. _657: https://github.com/giampaolo/psutil/issues/657
.. _658: https://github.com/giampaolo/psutil/issues/658
.. _659: https://github.com/giampaolo/psutil/issues/659
.. _660: https://github.com/giampaolo/psutil/issues/660
.. _661: https://github.com/giampaolo/psutil/issues/661
.. _662: https://github.com/giampaolo/psutil/issues/662
.. _663: https://github.com/giampaolo/psutil/issues/663
.. _664: https://github.com/giampaolo/psutil/issues/664
.. _665: https://github.com/giampaolo/psutil/issues/665
.. _666: https://github.com/giampaolo/psutil/issues/666
.. _667: https://github.com/giampaolo/psutil/issues/667
.. _668: https://github.com/giampaolo/psutil/issues/668
.. _669: https://github.com/giampaolo/psutil/issues/669
.. _670: https://github.com/giampaolo/psutil/issues/670
.. _671: https://github.com/giampaolo/psutil/issues/671
.. _672: https://github.com/giampaolo/psutil/issues/672
.. _673: https://github.com/giampaolo/psutil/issues/673
.. _674: https://github.com/giampaolo/psutil/issues/674
.. _675: https://github.com/giampaolo/psutil/issues/675
.. _676: https://github.com/giampaolo/psutil/issues/676
.. _677: https://github.com/giampaolo/psutil/issues/677
.. _678: https://github.com/giampaolo/psutil/issues/678
.. _679: https://github.com/giampaolo/psutil/issues/679
.. _680: https://github.com/giampaolo/psutil/issues/680
.. _681: https://github.com/giampaolo/psutil/issues/681
.. _682: https://github.com/giampaolo/psutil/issues/682
.. _683: https://github.com/giampaolo/psutil/issues/683
.. _684: https://github.com/giampaolo/psutil/issues/684
.. _685: https://github.com/giampaolo/psutil/issues/685
.. _686: https://github.com/giampaolo/psutil/issues/686
.. _687: https://github.com/giampaolo/psutil/issues/687
.. _688: https://github.com/giampaolo/psutil/issues/688
.. _689: https://github.com/giampaolo/psutil/issues/689
.. _690: https://github.com/giampaolo/psutil/issues/690
.. _691: https://github.com/giampaolo/psutil/issues/691
.. _692: https://github.com/giampaolo/psutil/issues/692
.. _693: https://github.com/giampaolo/psutil/issues/693
.. _694: https://github.com/giampaolo/psutil/issues/694
.. _695: https://github.com/giampaolo/psutil/issues/695
.. _696: https://github.com/giampaolo/psutil/issues/696
.. _697: https://github.com/giampaolo/psutil/issues/697
.. _698: https://github.com/giampaolo/psutil/issues/698
.. _699: https://github.com/giampaolo/psutil/issues/699
.. _700: https://github.com/giampaolo/psutil/issues/700
.. _701: https://github.com/giampaolo/psutil/issues/701
.. _702: https://github.com/giampaolo/psutil/issues/702
.. _703: https://github.com/giampaolo/psutil/issues/703
.. _704: https://github.com/giampaolo/psutil/issues/704
.. _705: https://github.com/giampaolo/psutil/issues/705
.. _706: https://github.com/giampaolo/psutil/issues/706
.. _707: https://github.com/giampaolo/psutil/issues/707
.. _708: https://github.com/giampaolo/psutil/issues/708
.. _709: https://github.com/giampaolo/psutil/issues/709
.. _710: https://github.com/giampaolo/psutil/issues/710
.. _711: https://github.com/giampaolo/psutil/issues/711
.. _712: https://github.com/giampaolo/psutil/issues/712
.. _713: https://github.com/giampaolo/psutil/issues/713
.. _714: https://github.com/giampaolo/psutil/issues/714
.. _715: https://github.com/giampaolo/psutil/issues/715
.. _716: https://github.com/giampaolo/psutil/issues/716
.. _717: https://github.com/giampaolo/psutil/issues/717
.. _718: https://github.com/giampaolo/psutil/issues/718
.. _719: https://github.com/giampaolo/psutil/issues/719
.. _720: https://github.com/giampaolo/psutil/issues/720
.. _721: https://github.com/giampaolo/psutil/issues/721
.. _722: https://github.com/giampaolo/psutil/issues/722
.. _723: https://github.com/giampaolo/psutil/issues/723
.. _724: https://github.com/giampaolo/psutil/issues/724
.. _725: https://github.com/giampaolo/psutil/issues/725
.. _726: https://github.com/giampaolo/psutil/issues/726
.. _727: https://github.com/giampaolo/psutil/issues/727
.. _728: https://github.com/giampaolo/psutil/issues/728
.. _729: https://github.com/giampaolo/psutil/issues/729
.. _730: https://github.com/giampaolo/psutil/issues/730
.. _731: https://github.com/giampaolo/psutil/issues/731
.. _732: https://github.com/giampaolo/psutil/issues/732
.. _733: https://github.com/giampaolo/psutil/issues/733
.. _734: https://github.com/giampaolo/psutil/issues/734
.. _735: https://github.com/giampaolo/psutil/issues/735
.. _736: https://github.com/giampaolo/psutil/issues/736
.. _737: https://github.com/giampaolo/psutil/issues/737
.. _738: https://github.com/giampaolo/psutil/issues/738
.. _739: https://github.com/giampaolo/psutil/issues/739
.. _740: https://github.com/giampaolo/psutil/issues/740
.. _741: https://github.com/giampaolo/psutil/issues/741
.. _742: https://github.com/giampaolo/psutil/issues/742
.. _743: https://github.com/giampaolo/psutil/issues/743
.. _744: https://github.com/giampaolo/psutil/issues/744
.. _745: https://github.com/giampaolo/psutil/issues/745
.. _746: https://github.com/giampaolo/psutil/issues/746
.. _747: https://github.com/giampaolo/psutil/issues/747
.. _748: https://github.com/giampaolo/psutil/issues/748
.. _749: https://github.com/giampaolo/psutil/issues/749
.. _750: https://github.com/giampaolo/psutil/issues/750
.. _751: https://github.com/giampaolo/psutil/issues/751
.. _752: https://github.com/giampaolo/psutil/issues/752
.. _753: https://github.com/giampaolo/psutil/issues/753
.. _754: https://github.com/giampaolo/psutil/issues/754
.. _755: https://github.com/giampaolo/psutil/issues/755
.. _756: https://github.com/giampaolo/psutil/issues/756
.. _757: https://github.com/giampaolo/psutil/issues/757
.. _758: https://github.com/giampaolo/psutil/issues/758
.. _759: https://github.com/giampaolo/psutil/issues/759
.. _760: https://github.com/giampaolo/psutil/issues/760
.. _761: https://github.com/giampaolo/psutil/issues/761
.. _762: https://github.com/giampaolo/psutil/issues/762
.. _763: https://github.com/giampaolo/psutil/issues/763
.. _764: https://github.com/giampaolo/psutil/issues/764
.. _765: https://github.com/giampaolo/psutil/issues/765
.. _766: https://github.com/giampaolo/psutil/issues/766
.. _767: https://github.com/giampaolo/psutil/issues/767
.. _768: https://github.com/giampaolo/psutil/issues/768
.. _769: https://github.com/giampaolo/psutil/issues/769
.. _770: https://github.com/giampaolo/psutil/issues/770
.. _771: https://github.com/giampaolo/psutil/issues/771
.. _772: https://github.com/giampaolo/psutil/issues/772
.. _773: https://github.com/giampaolo/psutil/issues/773
.. _774: https://github.com/giampaolo/psutil/issues/774
.. _775: https://github.com/giampaolo/psutil/issues/775
.. _776: https://github.com/giampaolo/psutil/issues/776
.. _777: https://github.com/giampaolo/psutil/issues/777
.. _778: https://github.com/giampaolo/psutil/issues/778
.. _779: https://github.com/giampaolo/psutil/issues/779
.. _780: https://github.com/giampaolo/psutil/issues/780
.. _781: https://github.com/giampaolo/psutil/issues/781
.. _782: https://github.com/giampaolo/psutil/issues/782
.. _783: https://github.com/giampaolo/psutil/issues/783
.. _784: https://github.com/giampaolo/psutil/issues/784
.. _785: https://github.com/giampaolo/psutil/issues/785
.. _786: https://github.com/giampaolo/psutil/issues/786
.. _787: https://github.com/giampaolo/psutil/issues/787
.. _788: https://github.com/giampaolo/psutil/issues/788
.. _789: https://github.com/giampaolo/psutil/issues/789
.. _790: https://github.com/giampaolo/psutil/issues/790
.. _791: https://github.com/giampaolo/psutil/issues/791
.. _792: https://github.com/giampaolo/psutil/issues/792
.. _793: https://github.com/giampaolo/psutil/issues/793
.. _794: https://github.com/giampaolo/psutil/issues/794
.. _795: https://github.com/giampaolo/psutil/issues/795
.. _796: https://github.com/giampaolo/psutil/issues/796
.. _797: https://github.com/giampaolo/psutil/issues/797
.. _798: https://github.com/giampaolo/psutil/issues/798
.. _799: https://github.com/giampaolo/psutil/issues/799
.. _800: https://github.com/giampaolo/psutil/issues/800
.. _801: https://github.com/giampaolo/psutil/issues/801
.. _802: https://github.com/giampaolo/psutil/issues/802
.. _803: https://github.com/giampaolo/psutil/issues/803
.. _804: https://github.com/giampaolo/psutil/issues/804
.. _805: https://github.com/giampaolo/psutil/issues/805
.. _806: https://github.com/giampaolo/psutil/issues/806
.. _807: https://github.com/giampaolo/psutil/issues/807
.. _808: https://github.com/giampaolo/psutil/issues/808
.. _809: https://github.com/giampaolo/psutil/issues/809
.. _810: https://github.com/giampaolo/psutil/issues/810
.. _811: https://github.com/giampaolo/psutil/issues/811
.. _812: https://github.com/giampaolo/psutil/issues/812
.. _813: https://github.com/giampaolo/psutil/issues/813
.. _814: https://github.com/giampaolo/psutil/issues/814
.. _815: https://github.com/giampaolo/psutil/issues/815
.. _816: https://github.com/giampaolo/psutil/issues/816
.. _817: https://github.com/giampaolo/psutil/issues/817
.. _818: https://github.com/giampaolo/psutil/issues/818
.. _819: https://github.com/giampaolo/psutil/issues/819
.. _820: https://github.com/giampaolo/psutil/issues/820
.. _821: https://github.com/giampaolo/psutil/issues/821
.. _822: https://github.com/giampaolo/psutil/issues/822
.. _823: https://github.com/giampaolo/psutil/issues/823
.. _824: https://github.com/giampaolo/psutil/issues/824
.. _825: https://github.com/giampaolo/psutil/issues/825
.. _826: https://github.com/giampaolo/psutil/issues/826
.. _827: https://github.com/giampaolo/psutil/issues/827
.. _828: https://github.com/giampaolo/psutil/issues/828
.. _829: https://github.com/giampaolo/psutil/issues/829
.. _830: https://github.com/giampaolo/psutil/issues/830
.. _831: https://github.com/giampaolo/psutil/issues/831
.. _832: https://github.com/giampaolo/psutil/issues/832
.. _833: https://github.com/giampaolo/psutil/issues/833
.. _834: https://github.com/giampaolo/psutil/issues/834
.. _835: https://github.com/giampaolo/psutil/issues/835
.. _836: https://github.com/giampaolo/psutil/issues/836
.. _837: https://github.com/giampaolo/psutil/issues/837
.. _838: https://github.com/giampaolo/psutil/issues/838
.. _839: https://github.com/giampaolo/psutil/issues/839
.. _840: https://github.com/giampaolo/psutil/issues/840
.. _841: https://github.com/giampaolo/psutil/issues/841
.. _842: https://github.com/giampaolo/psutil/issues/842
.. _843: https://github.com/giampaolo/psutil/issues/843
.. _844: https://github.com/giampaolo/psutil/issues/844
.. _845: https://github.com/giampaolo/psutil/issues/845
.. _846: https://github.com/giampaolo/psutil/issues/846
.. _847: https://github.com/giampaolo/psutil/issues/847
.. _848: https://github.com/giampaolo/psutil/issues/848
.. _849: https://github.com/giampaolo/psutil/issues/849
.. _850: https://github.com/giampaolo/psutil/issues/850
.. _851: https://github.com/giampaolo/psutil/issues/851
.. _852: https://github.com/giampaolo/psutil/issues/852
.. _853: https://github.com/giampaolo/psutil/issues/853
.. _854: https://github.com/giampaolo/psutil/issues/854
.. _855: https://github.com/giampaolo/psutil/issues/855
.. _856: https://github.com/giampaolo/psutil/issues/856
.. _857: https://github.com/giampaolo/psutil/issues/857
.. _858: https://github.com/giampaolo/psutil/issues/858
.. _859: https://github.com/giampaolo/psutil/issues/859
.. _860: https://github.com/giampaolo/psutil/issues/860
.. _861: https://github.com/giampaolo/psutil/issues/861
.. _862: https://github.com/giampaolo/psutil/issues/862
.. _863: https://github.com/giampaolo/psutil/issues/863
.. _864: https://github.com/giampaolo/psutil/issues/864
.. _865: https://github.com/giampaolo/psutil/issues/865
.. _866: https://github.com/giampaolo/psutil/issues/866
.. _867: https://github.com/giampaolo/psutil/issues/867
.. _868: https://github.com/giampaolo/psutil/issues/868
.. _869: https://github.com/giampaolo/psutil/issues/869
.. _870: https://github.com/giampaolo/psutil/issues/870
.. _871: https://github.com/giampaolo/psutil/issues/871
.. _872: https://github.com/giampaolo/psutil/issues/872
.. _873: https://github.com/giampaolo/psutil/issues/873
.. _874: https://github.com/giampaolo/psutil/issues/874
.. _875: https://github.com/giampaolo/psutil/issues/875
.. _876: https://github.com/giampaolo/psutil/issues/876
.. _877: https://github.com/giampaolo/psutil/issues/877
.. _878: https://github.com/giampaolo/psutil/issues/878
.. _879: https://github.com/giampaolo/psutil/issues/879
.. _880: https://github.com/giampaolo/psutil/issues/880
.. _881: https://github.com/giampaolo/psutil/issues/881
.. _882: https://github.com/giampaolo/psutil/issues/882
.. _883: https://github.com/giampaolo/psutil/issues/883
.. _884: https://github.com/giampaolo/psutil/issues/884
.. _885: https://github.com/giampaolo/psutil/issues/885
.. _886: https://github.com/giampaolo/psutil/issues/886
.. _887: https://github.com/giampaolo/psutil/issues/887
.. _888: https://github.com/giampaolo/psutil/issues/888
.. _889: https://github.com/giampaolo/psutil/issues/889
.. _890: https://github.com/giampaolo/psutil/issues/890
.. _891: https://github.com/giampaolo/psutil/issues/891
.. _892: https://github.com/giampaolo/psutil/issues/892
.. _893: https://github.com/giampaolo/psutil/issues/893
.. _894: https://github.com/giampaolo/psutil/issues/894
.. _895: https://github.com/giampaolo/psutil/issues/895
.. _896: https://github.com/giampaolo/psutil/issues/896
.. _897: https://github.com/giampaolo/psutil/issues/897
.. _898: https://github.com/giampaolo/psutil/issues/898
.. _899: https://github.com/giampaolo/psutil/issues/899
.. _900: https://github.com/giampaolo/psutil/issues/900
.. _901: https://github.com/giampaolo/psutil/issues/901
.. _902: https://github.com/giampaolo/psutil/issues/902
.. _903: https://github.com/giampaolo/psutil/issues/903
.. _904: https://github.com/giampaolo/psutil/issues/904
.. _905: https://github.com/giampaolo/psutil/issues/905
.. _906: https://github.com/giampaolo/psutil/issues/906
.. _907: https://github.com/giampaolo/psutil/issues/907
.. _908: https://github.com/giampaolo/psutil/issues/908
.. _909: https://github.com/giampaolo/psutil/issues/909
.. _910: https://github.com/giampaolo/psutil/issues/910
.. _911: https://github.com/giampaolo/psutil/issues/911
.. _912: https://github.com/giampaolo/psutil/issues/912
.. _913: https://github.com/giampaolo/psutil/issues/913
.. _914: https://github.com/giampaolo/psutil/issues/914
.. _915: https://github.com/giampaolo/psutil/issues/915
.. _916: https://github.com/giampaolo/psutil/issues/916
.. _917: https://github.com/giampaolo/psutil/issues/917
.. _918: https://github.com/giampaolo/psutil/issues/918
.. _919: https://github.com/giampaolo/psutil/issues/919
.. _920: https://github.com/giampaolo/psutil/issues/920
.. _921: https://github.com/giampaolo/psutil/issues/921
.. _922: https://github.com/giampaolo/psutil/issues/922
.. _923: https://github.com/giampaolo/psutil/issues/923
.. _924: https://github.com/giampaolo/psutil/issues/924
.. _925: https://github.com/giampaolo/psutil/issues/925
.. _926: https://github.com/giampaolo/psutil/issues/926
.. _927: https://github.com/giampaolo/psutil/issues/927
.. _928: https://github.com/giampaolo/psutil/issues/928
.. _929: https://github.com/giampaolo/psutil/issues/929
.. _930: https://github.com/giampaolo/psutil/issues/930
.. _931: https://github.com/giampaolo/psutil/issues/931
.. _932: https://github.com/giampaolo/psutil/issues/932
.. _933: https://github.com/giampaolo/psutil/issues/933
.. _934: https://github.com/giampaolo/psutil/issues/934
.. _935: https://github.com/giampaolo/psutil/issues/935
.. _936: https://github.com/giampaolo/psutil/issues/936
.. _937: https://github.com/giampaolo/psutil/issues/937
.. _938: https://github.com/giampaolo/psutil/issues/938
.. _939: https://github.com/giampaolo/psutil/issues/939
.. _940: https://github.com/giampaolo/psutil/issues/940
.. _941: https://github.com/giampaolo/psutil/issues/941
.. _942: https://github.com/giampaolo/psutil/issues/942
.. _943: https://github.com/giampaolo/psutil/issues/943
.. _944: https://github.com/giampaolo/psutil/issues/944
.. _945: https://github.com/giampaolo/psutil/issues/945
.. _946: https://github.com/giampaolo/psutil/issues/946
.. _947: https://github.com/giampaolo/psutil/issues/947
.. _948: https://github.com/giampaolo/psutil/issues/948
.. _949: https://github.com/giampaolo/psutil/issues/949
.. _950: https://github.com/giampaolo/psutil/issues/950
.. _951: https://github.com/giampaolo/psutil/issues/951
.. _952: https://github.com/giampaolo/psutil/issues/952
.. _953: https://github.com/giampaolo/psutil/issues/953
.. _954: https://github.com/giampaolo/psutil/issues/954
.. _955: https://github.com/giampaolo/psutil/issues/955
.. _956: https://github.com/giampaolo/psutil/issues/956
.. _957: https://github.com/giampaolo/psutil/issues/957
.. _958: https://github.com/giampaolo/psutil/issues/958
.. _959: https://github.com/giampaolo/psutil/issues/959
.. _960: https://github.com/giampaolo/psutil/issues/960
.. _961: https://github.com/giampaolo/psutil/issues/961
.. _962: https://github.com/giampaolo/psutil/issues/962
.. _963: https://github.com/giampaolo/psutil/issues/963
.. _964: https://github.com/giampaolo/psutil/issues/964
.. _965: https://github.com/giampaolo/psutil/issues/965
.. _966: https://github.com/giampaolo/psutil/issues/966
.. _967: https://github.com/giampaolo/psutil/issues/967
.. _968: https://github.com/giampaolo/psutil/issues/968
.. _969: https://github.com/giampaolo/psutil/issues/969
.. _970: https://github.com/giampaolo/psutil/issues/970
.. _971: https://github.com/giampaolo/psutil/issues/971
.. _972: https://github.com/giampaolo/psutil/issues/972
.. _973: https://github.com/giampaolo/psutil/issues/973
.. _974: https://github.com/giampaolo/psutil/issues/974
.. _975: https://github.com/giampaolo/psutil/issues/975
.. _976: https://github.com/giampaolo/psutil/issues/976
.. _977: https://github.com/giampaolo/psutil/issues/977
.. _978: https://github.com/giampaolo/psutil/issues/978
.. _979: https://github.com/giampaolo/psutil/issues/979
.. _980: https://github.com/giampaolo/psutil/issues/980
.. _981: https://github.com/giampaolo/psutil/issues/981
.. _982: https://github.com/giampaolo/psutil/issues/982
.. _983: https://github.com/giampaolo/psutil/issues/983
.. _984: https://github.com/giampaolo/psutil/issues/984
.. _985: https://github.com/giampaolo/psutil/issues/985
.. _986: https://github.com/giampaolo/psutil/issues/986
.. _987: https://github.com/giampaolo/psutil/issues/987
.. _988: https://github.com/giampaolo/psutil/issues/988
.. _989: https://github.com/giampaolo/psutil/issues/989
.. _990: https://github.com/giampaolo/psutil/issues/990
.. _991: https://github.com/giampaolo/psutil/issues/991
.. _992: https://github.com/giampaolo/psutil/issues/992
.. _993: https://github.com/giampaolo/psutil/issues/993
.. _994: https://github.com/giampaolo/psutil/issues/994
.. _995: https://github.com/giampaolo/psutil/issues/995
.. _996: https://github.com/giampaolo/psutil/issues/996
.. _997: https://github.com/giampaolo/psutil/issues/997
.. _998: https://github.com/giampaolo/psutil/issues/998
.. _999: https://github.com/giampaolo/psutil/issues/999
.. _1000: https://github.com/giampaolo/psutil/issues/1000
.. _1001: https://github.com/giampaolo/psutil/issues/1001
.. _1002: https://github.com/giampaolo/psutil/issues/1002
.. _1003: https://github.com/giampaolo/psutil/issues/1003
.. _1004: https://github.com/giampaolo/psutil/issues/1004
.. _1005: https://github.com/giampaolo/psutil/issues/1005
.. _1006: https://github.com/giampaolo/psutil/issues/1006
.. _1007: https://github.com/giampaolo/psutil/issues/1007
.. _1008: https://github.com/giampaolo/psutil/issues/1008
.. _1009: https://github.com/giampaolo/psutil/issues/1009
.. _1010: https://github.com/giampaolo/psutil/issues/1010
.. _1011: https://github.com/giampaolo/psutil/issues/1011
.. _1012: https://github.com/giampaolo/psutil/issues/1012
.. _1013: https://github.com/giampaolo/psutil/issues/1013
.. _1014: https://github.com/giampaolo/psutil/issues/1014
.. _1015: https://github.com/giampaolo/psutil/issues/1015
.. _1016: https://github.com/giampaolo/psutil/issues/1016
.. _1017: https://github.com/giampaolo/psutil/issues/1017
.. _1018: https://github.com/giampaolo/psutil/issues/1018
.. _1019: https://github.com/giampaolo/psutil/issues/1019
.. _1020: https://github.com/giampaolo/psutil/issues/1020
.. _1021: https://github.com/giampaolo/psutil/issues/1021
.. _1022: https://github.com/giampaolo/psutil/issues/1022
.. _1023: https://github.com/giampaolo/psutil/issues/1023
.. _1024: https://github.com/giampaolo/psutil/issues/1024
.. _1025: https://github.com/giampaolo/psutil/issues/1025
.. _1026: https://github.com/giampaolo/psutil/issues/1026
.. _1027: https://github.com/giampaolo/psutil/issues/1027
.. _1028: https://github.com/giampaolo/psutil/issues/1028
.. _1029: https://github.com/giampaolo/psutil/issues/1029
.. _1030: https://github.com/giampaolo/psutil/issues/1030
.. _1031: https://github.com/giampaolo/psutil/issues/1031
.. _1032: https://github.com/giampaolo/psutil/issues/1032
.. _1033: https://github.com/giampaolo/psutil/issues/1033
.. _1034: https://github.com/giampaolo/psutil/issues/1034
.. _1035: https://github.com/giampaolo/psutil/issues/1035
.. _1036: https://github.com/giampaolo/psutil/issues/1036
.. _1037: https://github.com/giampaolo/psutil/issues/1037
.. _1038: https://github.com/giampaolo/psutil/issues/1038
.. _1039: https://github.com/giampaolo/psutil/issues/1039
.. _1040: https://github.com/giampaolo/psutil/issues/1040
.. _1041: https://github.com/giampaolo/psutil/issues/1041
.. _1042: https://github.com/giampaolo/psutil/issues/1042
.. _1043: https://github.com/giampaolo/psutil/issues/1043
.. _1044: https://github.com/giampaolo/psutil/issues/1044
.. _1045: https://github.com/giampaolo/psutil/issues/1045
.. _1046: https://github.com/giampaolo/psutil/issues/1046
.. _1047: https://github.com/giampaolo/psutil/issues/1047
.. _1048: https://github.com/giampaolo/psutil/issues/1048
.. _1049: https://github.com/giampaolo/psutil/issues/1049
.. _1050: https://github.com/giampaolo/psutil/issues/1050
.. _1051: https://github.com/giampaolo/psutil/issues/1051
.. _1052: https://github.com/giampaolo/psutil/issues/1052
.. _1053: https://github.com/giampaolo/psutil/issues/1053
.. _1054: https://github.com/giampaolo/psutil/issues/1054
.. _1055: https://github.com/giampaolo/psutil/issues/1055
.. _1056: https://github.com/giampaolo/psutil/issues/1056
.. _1057: https://github.com/giampaolo/psutil/issues/1057
.. _1058: https://github.com/giampaolo/psutil/issues/1058
.. _1059: https://github.com/giampaolo/psutil/issues/1059
.. _1060: https://github.com/giampaolo/psutil/issues/1060
.. _1061: https://github.com/giampaolo/psutil/issues/1061
.. _1062: https://github.com/giampaolo/psutil/issues/1062
.. _1063: https://github.com/giampaolo/psutil/issues/1063
.. _1064: https://github.com/giampaolo/psutil/issues/1064
.. _1065: https://github.com/giampaolo/psutil/issues/1065
.. _1066: https://github.com/giampaolo/psutil/issues/1066
.. _1067: https://github.com/giampaolo/psutil/issues/1067
.. _1068: https://github.com/giampaolo/psutil/issues/1068
.. _1069: https://github.com/giampaolo/psutil/issues/1069
.. _1070: https://github.com/giampaolo/psutil/issues/1070
.. _1071: https://github.com/giampaolo/psutil/issues/1071
.. _1072: https://github.com/giampaolo/psutil/issues/1072
.. _1073: https://github.com/giampaolo/psutil/issues/1073
.. _1074: https://github.com/giampaolo/psutil/issues/1074
.. _1075: https://github.com/giampaolo/psutil/issues/1075
.. _1076: https://github.com/giampaolo/psutil/issues/1076
.. _1077: https://github.com/giampaolo/psutil/issues/1077
.. _1078: https://github.com/giampaolo/psutil/issues/1078
.. _1079: https://github.com/giampaolo/psutil/issues/1079
.. _1080: https://github.com/giampaolo/psutil/issues/1080
.. _1081: https://github.com/giampaolo/psutil/issues/1081
.. _1082: https://github.com/giampaolo/psutil/issues/1082
.. _1083: https://github.com/giampaolo/psutil/issues/1083
.. _1084: https://github.com/giampaolo/psutil/issues/1084
.. _1085: https://github.com/giampaolo/psutil/issues/1085
.. _1086: https://github.com/giampaolo/psutil/issues/1086
.. _1087: https://github.com/giampaolo/psutil/issues/1087
.. _1088: https://github.com/giampaolo/psutil/issues/1088
.. _1089: https://github.com/giampaolo/psutil/issues/1089
.. _1090: https://github.com/giampaolo/psutil/issues/1090
.. _1091: https://github.com/giampaolo/psutil/issues/1091
.. _1092: https://github.com/giampaolo/psutil/issues/1092
.. _1093: https://github.com/giampaolo/psutil/issues/1093
.. _1094: https://github.com/giampaolo/psutil/issues/1094
.. _1095: https://github.com/giampaolo/psutil/issues/1095
.. _1096: https://github.com/giampaolo/psutil/issues/1096
.. _1097: https://github.com/giampaolo/psutil/issues/1097
.. _1098: https://github.com/giampaolo/psutil/issues/1098
.. _1099: https://github.com/giampaolo/psutil/issues/1099
.. _1100: https://github.com/giampaolo/psutil/issues/1100
.. _1101: https://github.com/giampaolo/psutil/issues/1101
.. _1102: https://github.com/giampaolo/psutil/issues/1102
.. _1103: https://github.com/giampaolo/psutil/issues/1103
.. _1104: https://github.com/giampaolo/psutil/issues/1104
.. _1105: https://github.com/giampaolo/psutil/issues/1105
.. _1106: https://github.com/giampaolo/psutil/issues/1106
.. _1107: https://github.com/giampaolo/psutil/issues/1107
.. _1108: https://github.com/giampaolo/psutil/issues/1108
.. _1109: https://github.com/giampaolo/psutil/issues/1109
.. _1110: https://github.com/giampaolo/psutil/issues/1110
.. _1111: https://github.com/giampaolo/psutil/issues/1111
.. _1112: https://github.com/giampaolo/psutil/issues/1112
.. _1113: https://github.com/giampaolo/psutil/issues/1113
.. _1114: https://github.com/giampaolo/psutil/issues/1114
.. _1115: https://github.com/giampaolo/psutil/issues/1115
.. _1116: https://github.com/giampaolo/psutil/issues/1116
.. _1117: https://github.com/giampaolo/psutil/issues/1117
.. _1118: https://github.com/giampaolo/psutil/issues/1118
.. _1119: https://github.com/giampaolo/psutil/issues/1119
.. _1120: https://github.com/giampaolo/psutil/issues/1120
.. _1121: https://github.com/giampaolo/psutil/issues/1121
.. _1122: https://github.com/giampaolo/psutil/issues/1122
.. _1123: https://github.com/giampaolo/psutil/issues/1123
.. _1124: https://github.com/giampaolo/psutil/issues/1124
.. _1125: https://github.com/giampaolo/psutil/issues/1125
.. _1126: https://github.com/giampaolo/psutil/issues/1126
.. _1127: https://github.com/giampaolo/psutil/issues/1127
.. _1128: https://github.com/giampaolo/psutil/issues/1128
.. _1129: https://github.com/giampaolo/psutil/issues/1129
.. _1130: https://github.com/giampaolo/psutil/issues/1130
.. _1131: https://github.com/giampaolo/psutil/issues/1131
.. _1132: https://github.com/giampaolo/psutil/issues/1132
.. _1133: https://github.com/giampaolo/psutil/issues/1133
.. _1134: https://github.com/giampaolo/psutil/issues/1134
.. _1135: https://github.com/giampaolo/psutil/issues/1135
.. _1136: https://github.com/giampaolo/psutil/issues/1136
.. _1137: https://github.com/giampaolo/psutil/issues/1137
.. _1138: https://github.com/giampaolo/psutil/issues/1138
.. _1139: https://github.com/giampaolo/psutil/issues/1139
.. _1140: https://github.com/giampaolo/psutil/issues/1140
.. _1141: https://github.com/giampaolo/psutil/issues/1141
.. _1142: https://github.com/giampaolo/psutil/issues/1142
.. _1143: https://github.com/giampaolo/psutil/issues/1143
.. _1144: https://github.com/giampaolo/psutil/issues/1144
.. _1145: https://github.com/giampaolo/psutil/issues/1145
.. _1146: https://github.com/giampaolo/psutil/issues/1146
.. _1147: https://github.com/giampaolo/psutil/issues/1147
.. _1148: https://github.com/giampaolo/psutil/issues/1148
.. _1149: https://github.com/giampaolo/psutil/issues/1149
.. _1150: https://github.com/giampaolo/psutil/issues/1150
.. _1151: https://github.com/giampaolo/psutil/issues/1151
.. _1152: https://github.com/giampaolo/psutil/issues/1152
.. _1153: https://github.com/giampaolo/psutil/issues/1153
.. _1154: https://github.com/giampaolo/psutil/issues/1154
.. _1155: https://github.com/giampaolo/psutil/issues/1155
.. _1156: https://github.com/giampaolo/psutil/issues/1156
.. _1157: https://github.com/giampaolo/psutil/issues/1157
.. _1158: https://github.com/giampaolo/psutil/issues/1158
.. _1159: https://github.com/giampaolo/psutil/issues/1159
.. _1160: https://github.com/giampaolo/psutil/issues/1160
.. _1161: https://github.com/giampaolo/psutil/issues/1161
.. _1162: https://github.com/giampaolo/psutil/issues/1162
.. _1163: https://github.com/giampaolo/psutil/issues/1163
.. _1164: https://github.com/giampaolo/psutil/issues/1164
.. _1165: https://github.com/giampaolo/psutil/issues/1165
.. _1166: https://github.com/giampaolo/psutil/issues/1166
.. _1167: https://github.com/giampaolo/psutil/issues/1167
.. _1168: https://github.com/giampaolo/psutil/issues/1168
.. _1169: https://github.com/giampaolo/psutil/issues/1169
.. _1170: https://github.com/giampaolo/psutil/issues/1170
.. _1171: https://github.com/giampaolo/psutil/issues/1171
.. _1172: https://github.com/giampaolo/psutil/issues/1172
.. _1173: https://github.com/giampaolo/psutil/issues/1173
.. _1174: https://github.com/giampaolo/psutil/issues/1174
.. _1175: https://github.com/giampaolo/psutil/issues/1175
.. _1176: https://github.com/giampaolo/psutil/issues/1176
.. _1177: https://github.com/giampaolo/psutil/issues/1177
.. _1178: https://github.com/giampaolo/psutil/issues/1178
.. _1179: https://github.com/giampaolo/psutil/issues/1179
.. _1180: https://github.com/giampaolo/psutil/issues/1180
.. _1181: https://github.com/giampaolo/psutil/issues/1181
.. _1182: https://github.com/giampaolo/psutil/issues/1182
.. _1183: https://github.com/giampaolo/psutil/issues/1183
.. _1184: https://github.com/giampaolo/psutil/issues/1184
.. _1185: https://github.com/giampaolo/psutil/issues/1185
.. _1186: https://github.com/giampaolo/psutil/issues/1186
.. _1187: https://github.com/giampaolo/psutil/issues/1187
.. _1188: https://github.com/giampaolo/psutil/issues/1188
.. _1189: https://github.com/giampaolo/psutil/issues/1189
.. _1190: https://github.com/giampaolo/psutil/issues/1190
.. _1191: https://github.com/giampaolo/psutil/issues/1191
.. _1192: https://github.com/giampaolo/psutil/issues/1192
.. _1193: https://github.com/giampaolo/psutil/issues/1193
.. _1194: https://github.com/giampaolo/psutil/issues/1194
.. _1195: https://github.com/giampaolo/psutil/issues/1195
.. _1196: https://github.com/giampaolo/psutil/issues/1196
.. _1197: https://github.com/giampaolo/psutil/issues/1197
.. _1198: https://github.com/giampaolo/psutil/issues/1198
.. _1199: https://github.com/giampaolo/psutil/issues/1199
.. _1200: https://github.com/giampaolo/psutil/issues/1200
.. _1201: https://github.com/giampaolo/psutil/issues/1201
.. _1202: https://github.com/giampaolo/psutil/issues/1202
.. _1203: https://github.com/giampaolo/psutil/issues/1203
.. _1204: https://github.com/giampaolo/psutil/issues/1204
.. _1205: https://github.com/giampaolo/psutil/issues/1205
.. _1206: https://github.com/giampaolo/psutil/issues/1206
.. _1207: https://github.com/giampaolo/psutil/issues/1207
.. _1208: https://github.com/giampaolo/psutil/issues/1208
.. _1209: https://github.com/giampaolo/psutil/issues/1209
.. _1210: https://github.com/giampaolo/psutil/issues/1210
.. _1211: https://github.com/giampaolo/psutil/issues/1211
.. _1212: https://github.com/giampaolo/psutil/issues/1212
.. _1213: https://github.com/giampaolo/psutil/issues/1213
.. _1214: https://github.com/giampaolo/psutil/issues/1214
.. _1215: https://github.com/giampaolo/psutil/issues/1215
.. _1216: https://github.com/giampaolo/psutil/issues/1216
.. _1217: https://github.com/giampaolo/psutil/issues/1217
.. _1218: https://github.com/giampaolo/psutil/issues/1218
.. _1219: https://github.com/giampaolo/psutil/issues/1219
.. _1220: https://github.com/giampaolo/psutil/issues/1220
.. _1221: https://github.com/giampaolo/psutil/issues/1221
.. _1222: https://github.com/giampaolo/psutil/issues/1222
.. _1223: https://github.com/giampaolo/psutil/issues/1223
.. _1224: https://github.com/giampaolo/psutil/issues/1224
.. _1225: https://github.com/giampaolo/psutil/issues/1225
.. _1226: https://github.com/giampaolo/psutil/issues/1226
.. _1227: https://github.com/giampaolo/psutil/issues/1227
.. _1228: https://github.com/giampaolo/psutil/issues/1228
.. _1229: https://github.com/giampaolo/psutil/issues/1229
.. _1230: https://github.com/giampaolo/psutil/issues/1230
.. _1231: https://github.com/giampaolo/psutil/issues/1231
.. _1232: https://github.com/giampaolo/psutil/issues/1232
.. _1233: https://github.com/giampaolo/psutil/issues/1233
.. _1234: https://github.com/giampaolo/psutil/issues/1234
.. _1235: https://github.com/giampaolo/psutil/issues/1235
.. _1236: https://github.com/giampaolo/psutil/issues/1236
.. _1237: https://github.com/giampaolo/psutil/issues/1237
.. _1238: https://github.com/giampaolo/psutil/issues/1238
.. _1239: https://github.com/giampaolo/psutil/issues/1239
.. _1240: https://github.com/giampaolo/psutil/issues/1240
.. _1241: https://github.com/giampaolo/psutil/issues/1241
.. _1242: https://github.com/giampaolo/psutil/issues/1242
.. _1243: https://github.com/giampaolo/psutil/issues/1243
.. _1244: https://github.com/giampaolo/psutil/issues/1244
.. _1245: https://github.com/giampaolo/psutil/issues/1245
.. _1246: https://github.com/giampaolo/psutil/issues/1246
.. _1247: https://github.com/giampaolo/psutil/issues/1247
.. _1248: https://github.com/giampaolo/psutil/issues/1248
.. _1249: https://github.com/giampaolo/psutil/issues/1249
.. _1250: https://github.com/giampaolo/psutil/issues/1250
.. _1251: https://github.com/giampaolo/psutil/issues/1251
.. _1252: https://github.com/giampaolo/psutil/issues/1252
.. _1253: https://github.com/giampaolo/psutil/issues/1253
.. _1254: https://github.com/giampaolo/psutil/issues/1254
.. _1255: https://github.com/giampaolo/psutil/issues/1255
.. _1256: https://github.com/giampaolo/psutil/issues/1256
.. _1257: https://github.com/giampaolo/psutil/issues/1257
.. _1258: https://github.com/giampaolo/psutil/issues/1258
.. _1259: https://github.com/giampaolo/psutil/issues/1259
.. _1260: https://github.com/giampaolo/psutil/issues/1260
.. _1261: https://github.com/giampaolo/psutil/issues/1261
.. _1262: https://github.com/giampaolo/psutil/issues/1262
.. _1263: https://github.com/giampaolo/psutil/issues/1263
.. _1264: https://github.com/giampaolo/psutil/issues/1264
.. _1265: https://github.com/giampaolo/psutil/issues/1265
.. _1266: https://github.com/giampaolo/psutil/issues/1266
.. _1267: https://github.com/giampaolo/psutil/issues/1267
.. _1268: https://github.com/giampaolo/psutil/issues/1268
.. _1269: https://github.com/giampaolo/psutil/issues/1269
.. _1270: https://github.com/giampaolo/psutil/issues/1270
.. _1271: https://github.com/giampaolo/psutil/issues/1271
.. _1272: https://github.com/giampaolo/psutil/issues/1272
.. _1273: https://github.com/giampaolo/psutil/issues/1273
.. _1274: https://github.com/giampaolo/psutil/issues/1274
.. _1275: https://github.com/giampaolo/psutil/issues/1275
.. _1276: https://github.com/giampaolo/psutil/issues/1276
.. _1277: https://github.com/giampaolo/psutil/issues/1277
.. _1278: https://github.com/giampaolo/psutil/issues/1278
.. _1279: https://github.com/giampaolo/psutil/issues/1279
.. _1280: https://github.com/giampaolo/psutil/issues/1280
.. _1281: https://github.com/giampaolo/psutil/issues/1281
.. _1282: https://github.com/giampaolo/psutil/issues/1282
.. _1283: https://github.com/giampaolo/psutil/issues/1283
.. _1284: https://github.com/giampaolo/psutil/issues/1284
.. _1285: https://github.com/giampaolo/psutil/issues/1285
.. _1286: https://github.com/giampaolo/psutil/issues/1286
.. _1287: https://github.com/giampaolo/psutil/issues/1287
.. _1288: https://github.com/giampaolo/psutil/issues/1288
.. _1289: https://github.com/giampaolo/psutil/issues/1289
.. _1290: https://github.com/giampaolo/psutil/issues/1290
.. _1291: https://github.com/giampaolo/psutil/issues/1291
.. _1292: https://github.com/giampaolo/psutil/issues/1292
.. _1293: https://github.com/giampaolo/psutil/issues/1293
.. _1294: https://github.com/giampaolo/psutil/issues/1294
.. _1295: https://github.com/giampaolo/psutil/issues/1295
.. _1296: https://github.com/giampaolo/psutil/issues/1296
.. _1297: https://github.com/giampaolo/psutil/issues/1297
.. _1298: https://github.com/giampaolo/psutil/issues/1298
.. _1299: https://github.com/giampaolo/psutil/issues/1299
.. _1300: https://github.com/giampaolo/psutil/issues/1300
.. _1301: https://github.com/giampaolo/psutil/issues/1301
.. _1302: https://github.com/giampaolo/psutil/issues/1302
.. _1303: https://github.com/giampaolo/psutil/issues/1303
.. _1304: https://github.com/giampaolo/psutil/issues/1304
.. _1305: https://github.com/giampaolo/psutil/issues/1305
.. _1306: https://github.com/giampaolo/psutil/issues/1306
.. _1307: https://github.com/giampaolo/psutil/issues/1307
.. _1308: https://github.com/giampaolo/psutil/issues/1308
.. _1309: https://github.com/giampaolo/psutil/issues/1309
.. _1310: https://github.com/giampaolo/psutil/issues/1310
.. _1311: https://github.com/giampaolo/psutil/issues/1311
.. _1312: https://github.com/giampaolo/psutil/issues/1312
.. _1313: https://github.com/giampaolo/psutil/issues/1313
.. _1314: https://github.com/giampaolo/psutil/issues/1314
.. _1315: https://github.com/giampaolo/psutil/issues/1315
.. _1316: https://github.com/giampaolo/psutil/issues/1316
.. _1317: https://github.com/giampaolo/psutil/issues/1317
.. _1318: https://github.com/giampaolo/psutil/issues/1318
.. _1319: https://github.com/giampaolo/psutil/issues/1319
.. _1320: https://github.com/giampaolo/psutil/issues/1320
.. _1321: https://github.com/giampaolo/psutil/issues/1321
.. _1322: https://github.com/giampaolo/psutil/issues/1322
.. _1323: https://github.com/giampaolo/psutil/issues/1323
.. _1324: https://github.com/giampaolo/psutil/issues/1324
.. _1325: https://github.com/giampaolo/psutil/issues/1325
.. _1326: https://github.com/giampaolo/psutil/issues/1326
.. _1327: https://github.com/giampaolo/psutil/issues/1327
.. _1328: https://github.com/giampaolo/psutil/issues/1328
.. _1329: https://github.com/giampaolo/psutil/issues/1329
.. _1330: https://github.com/giampaolo/psutil/issues/1330
.. _1331: https://github.com/giampaolo/psutil/issues/1331
.. _1332: https://github.com/giampaolo/psutil/issues/1332
.. _1333: https://github.com/giampaolo/psutil/issues/1333
.. _1334: https://github.com/giampaolo/psutil/issues/1334
.. _1335: https://github.com/giampaolo/psutil/issues/1335
.. _1336: https://github.com/giampaolo/psutil/issues/1336
.. _1337: https://github.com/giampaolo/psutil/issues/1337
.. _1338: https://github.com/giampaolo/psutil/issues/1338
.. _1339: https://github.com/giampaolo/psutil/issues/1339
.. _1340: https://github.com/giampaolo/psutil/issues/1340
.. _1341: https://github.com/giampaolo/psutil/issues/1341
.. _1342: https://github.com/giampaolo/psutil/issues/1342
.. _1343: https://github.com/giampaolo/psutil/issues/1343
.. _1344: https://github.com/giampaolo/psutil/issues/1344
.. _1345: https://github.com/giampaolo/psutil/issues/1345
.. _1346: https://github.com/giampaolo/psutil/issues/1346
.. _1347: https://github.com/giampaolo/psutil/issues/1347
.. _1348: https://github.com/giampaolo/psutil/issues/1348
.. _1349: https://github.com/giampaolo/psutil/issues/1349
.. _1350: https://github.com/giampaolo/psutil/issues/1350
.. _1351: https://github.com/giampaolo/psutil/issues/1351
.. _1352: https://github.com/giampaolo/psutil/issues/1352
.. _1353: https://github.com/giampaolo/psutil/issues/1353
.. _1354: https://github.com/giampaolo/psutil/issues/1354
.. _1355: https://github.com/giampaolo/psutil/issues/1355
.. _1356: https://github.com/giampaolo/psutil/issues/1356
.. _1357: https://github.com/giampaolo/psutil/issues/1357
.. _1358: https://github.com/giampaolo/psutil/issues/1358
.. _1359: https://github.com/giampaolo/psutil/issues/1359
.. _1360: https://github.com/giampaolo/psutil/issues/1360
.. _1361: https://github.com/giampaolo/psutil/issues/1361
.. _1362: https://github.com/giampaolo/psutil/issues/1362
.. _1363: https://github.com/giampaolo/psutil/issues/1363
.. _1364: https://github.com/giampaolo/psutil/issues/1364
.. _1365: https://github.com/giampaolo/psutil/issues/1365
.. _1366: https://github.com/giampaolo/psutil/issues/1366
.. _1367: https://github.com/giampaolo/psutil/issues/1367
.. _1368: https://github.com/giampaolo/psutil/issues/1368
.. _1369: https://github.com/giampaolo/psutil/issues/1369
.. _1370: https://github.com/giampaolo/psutil/issues/1370
.. _1371: https://github.com/giampaolo/psutil/issues/1371
.. _1372: https://github.com/giampaolo/psutil/issues/1372
.. _1373: https://github.com/giampaolo/psutil/issues/1373
.. _1374: https://github.com/giampaolo/psutil/issues/1374
.. _1375: https://github.com/giampaolo/psutil/issues/1375
.. _1376: https://github.com/giampaolo/psutil/issues/1376
.. _1377: https://github.com/giampaolo/psutil/issues/1377
.. _1378: https://github.com/giampaolo/psutil/issues/1378
.. _1379: https://github.com/giampaolo/psutil/issues/1379
.. _1380: https://github.com/giampaolo/psutil/issues/1380
.. _1381: https://github.com/giampaolo/psutil/issues/1381
.. _1382: https://github.com/giampaolo/psutil/issues/1382
.. _1383: https://github.com/giampaolo/psutil/issues/1383
.. _1384: https://github.com/giampaolo/psutil/issues/1384
.. _1385: https://github.com/giampaolo/psutil/issues/1385
.. _1386: https://github.com/giampaolo/psutil/issues/1386
.. _1387: https://github.com/giampaolo/psutil/issues/1387
.. _1388: https://github.com/giampaolo/psutil/issues/1388
.. _1389: https://github.com/giampaolo/psutil/issues/1389
.. _1390: https://github.com/giampaolo/psutil/issues/1390
.. _1391: https://github.com/giampaolo/psutil/issues/1391
.. _1392: https://github.com/giampaolo/psutil/issues/1392
.. _1393: https://github.com/giampaolo/psutil/issues/1393
.. _1394: https://github.com/giampaolo/psutil/issues/1394
.. _1395: https://github.com/giampaolo/psutil/issues/1395
.. _1396: https://github.com/giampaolo/psutil/issues/1396
.. _1397: https://github.com/giampaolo/psutil/issues/1397
.. _1398: https://github.com/giampaolo/psutil/issues/1398
.. _1399: https://github.com/giampaolo/psutil/issues/1399
.. _1400: https://github.com/giampaolo/psutil/issues/1400
.. _1401: https://github.com/giampaolo/psutil/issues/1401
.. _1402: https://github.com/giampaolo/psutil/issues/1402
.. _1403: https://github.com/giampaolo/psutil/issues/1403
.. _1404: https://github.com/giampaolo/psutil/issues/1404
.. _1405: https://github.com/giampaolo/psutil/issues/1405
.. _1406: https://github.com/giampaolo/psutil/issues/1406
.. _1407: https://github.com/giampaolo/psutil/issues/1407
.. _1408: https://github.com/giampaolo/psutil/issues/1408
.. _1409: https://github.com/giampaolo/psutil/issues/1409
.. _1410: https://github.com/giampaolo/psutil/issues/1410
.. _1411: https://github.com/giampaolo/psutil/issues/1411
.. _1412: https://github.com/giampaolo/psutil/issues/1412
.. _1413: https://github.com/giampaolo/psutil/issues/1413
.. _1414: https://github.com/giampaolo/psutil/issues/1414
.. _1415: https://github.com/giampaolo/psutil/issues/1415
.. _1416: https://github.com/giampaolo/psutil/issues/1416
.. _1417: https://github.com/giampaolo/psutil/issues/1417
.. _1418: https://github.com/giampaolo/psutil/issues/1418
.. _1419: https://github.com/giampaolo/psutil/issues/1419
.. _1420: https://github.com/giampaolo/psutil/issues/1420
.. _1421: https://github.com/giampaolo/psutil/issues/1421
.. _1422: https://github.com/giampaolo/psutil/issues/1422
.. _1423: https://github.com/giampaolo/psutil/issues/1423
.. _1424: https://github.com/giampaolo/psutil/issues/1424
.. _1425: https://github.com/giampaolo/psutil/issues/1425
.. _1426: https://github.com/giampaolo/psutil/issues/1426
.. _1427: https://github.com/giampaolo/psutil/issues/1427
.. _1428: https://github.com/giampaolo/psutil/issues/1428
.. _1429: https://github.com/giampaolo/psutil/issues/1429
.. _1430: https://github.com/giampaolo/psutil/issues/1430
.. _1431: https://github.com/giampaolo/psutil/issues/1431
.. _1432: https://github.com/giampaolo/psutil/issues/1432
.. _1433: https://github.com/giampaolo/psutil/issues/1433
.. _1434: https://github.com/giampaolo/psutil/issues/1434
.. _1435: https://github.com/giampaolo/psutil/issues/1435
.. _1436: https://github.com/giampaolo/psutil/issues/1436
.. _1437: https://github.com/giampaolo/psutil/issues/1437
.. _1438: https://github.com/giampaolo/psutil/issues/1438
.. _1439: https://github.com/giampaolo/psutil/issues/1439
.. _1440: https://github.com/giampaolo/psutil/issues/1440
.. _1441: https://github.com/giampaolo/psutil/issues/1441
.. _1442: https://github.com/giampaolo/psutil/issues/1442
.. _1443: https://github.com/giampaolo/psutil/issues/1443
.. _1444: https://github.com/giampaolo/psutil/issues/1444
.. _1445: https://github.com/giampaolo/psutil/issues/1445
.. _1446: https://github.com/giampaolo/psutil/issues/1446
.. _1447: https://github.com/giampaolo/psutil/issues/1447
.. _1448: https://github.com/giampaolo/psutil/issues/1448
.. _1449: https://github.com/giampaolo/psutil/issues/1449
.. _1450: https://github.com/giampaolo/psutil/issues/1450
.. _1451: https://github.com/giampaolo/psutil/issues/1451
.. _1452: https://github.com/giampaolo/psutil/issues/1452
.. _1453: https://github.com/giampaolo/psutil/issues/1453
.. _1454: https://github.com/giampaolo/psutil/issues/1454
.. _1455: https://github.com/giampaolo/psutil/issues/1455
.. _1456: https://github.com/giampaolo/psutil/issues/1456
.. _1457: https://github.com/giampaolo/psutil/issues/1457
.. _1458: https://github.com/giampaolo/psutil/issues/1458
.. _1459: https://github.com/giampaolo/psutil/issues/1459
.. _1460: https://github.com/giampaolo/psutil/issues/1460
.. _1461: https://github.com/giampaolo/psutil/issues/1461
.. _1462: https://github.com/giampaolo/psutil/issues/1462
.. _1463: https://github.com/giampaolo/psutil/issues/1463
.. _1464: https://github.com/giampaolo/psutil/issues/1464
.. _1465: https://github.com/giampaolo/psutil/issues/1465
.. _1466: https://github.com/giampaolo/psutil/issues/1466
.. _1467: https://github.com/giampaolo/psutil/issues/1467
.. _1468: https://github.com/giampaolo/psutil/issues/1468
.. _1469: https://github.com/giampaolo/psutil/issues/1469
.. _1470: https://github.com/giampaolo/psutil/issues/1470
.. _1471: https://github.com/giampaolo/psutil/issues/1471
.. _1472: https://github.com/giampaolo/psutil/issues/1472
.. _1473: https://github.com/giampaolo/psutil/issues/1473
.. _1474: https://github.com/giampaolo/psutil/issues/1474
.. _1475: https://github.com/giampaolo/psutil/issues/1475
.. _1476: https://github.com/giampaolo/psutil/issues/1476
.. _1477: https://github.com/giampaolo/psutil/issues/1477
.. _1478: https://github.com/giampaolo/psutil/issues/1478
.. _1479: https://github.com/giampaolo/psutil/issues/1479
.. _1480: https://github.com/giampaolo/psutil/issues/1480
.. _1481: https://github.com/giampaolo/psutil/issues/1481
.. _1482: https://github.com/giampaolo/psutil/issues/1482
.. _1483: https://github.com/giampaolo/psutil/issues/1483
.. _1484: https://github.com/giampaolo/psutil/issues/1484
.. _1485: https://github.com/giampaolo/psutil/issues/1485
.. _1486: https://github.com/giampaolo/psutil/issues/1486
.. _1487: https://github.com/giampaolo/psutil/issues/1487
.. _1488: https://github.com/giampaolo/psutil/issues/1488
.. _1489: https://github.com/giampaolo/psutil/issues/1489
.. _1490: https://github.com/giampaolo/psutil/issues/1490
.. _1491: https://github.com/giampaolo/psutil/issues/1491
.. _1492: https://github.com/giampaolo/psutil/issues/1492
.. _1493: https://github.com/giampaolo/psutil/issues/1493
.. _1494: https://github.com/giampaolo/psutil/issues/1494
.. _1495: https://github.com/giampaolo/psutil/issues/1495
.. _1496: https://github.com/giampaolo/psutil/issues/1496
.. _1497: https://github.com/giampaolo/psutil/issues/1497
.. _1498: https://github.com/giampaolo/psutil/issues/1498
.. _1499: https://github.com/giampaolo/psutil/issues/1499
.. _1500: https://github.com/giampaolo/psutil/issues/1500
.. _1501: https://github.com/giampaolo/psutil/issues/1501
.. _1502: https://github.com/giampaolo/psutil/issues/1502
.. _1503: https://github.com/giampaolo/psutil/issues/1503
.. _1504: https://github.com/giampaolo/psutil/issues/1504
.. _1505: https://github.com/giampaolo/psutil/issues/1505
.. _1506: https://github.com/giampaolo/psutil/issues/1506
.. _1507: https://github.com/giampaolo/psutil/issues/1507
.. _1508: https://github.com/giampaolo/psutil/issues/1508
.. _1509: https://github.com/giampaolo/psutil/issues/1509
.. _1510: https://github.com/giampaolo/psutil/issues/1510
.. _1511: https://github.com/giampaolo/psutil/issues/1511
.. _1512: https://github.com/giampaolo/psutil/issues/1512
.. _1513: https://github.com/giampaolo/psutil/issues/1513
.. _1514: https://github.com/giampaolo/psutil/issues/1514
.. _1515: https://github.com/giampaolo/psutil/issues/1515
.. _1516: https://github.com/giampaolo/psutil/issues/1516
.. _1517: https://github.com/giampaolo/psutil/issues/1517
.. _1518: https://github.com/giampaolo/psutil/issues/1518
.. _1519: https://github.com/giampaolo/psutil/issues/1519
.. _1520: https://github.com/giampaolo/psutil/issues/1520
.. _1521: https://github.com/giampaolo/psutil/issues/1521
.. _1522: https://github.com/giampaolo/psutil/issues/1522
.. _1523: https://github.com/giampaolo/psutil/issues/1523
.. _1524: https://github.com/giampaolo/psutil/issues/1524
.. _1525: https://github.com/giampaolo/psutil/issues/1525
.. _1526: https://github.com/giampaolo/psutil/issues/1526
.. _1527: https://github.com/giampaolo/psutil/issues/1527
.. _1528: https://github.com/giampaolo/psutil/issues/1528
.. _1529: https://github.com/giampaolo/psutil/issues/1529
.. _1530: https://github.com/giampaolo/psutil/issues/1530
.. _1531: https://github.com/giampaolo/psutil/issues/1531
.. _1532: https://github.com/giampaolo/psutil/issues/1532
.. _1533: https://github.com/giampaolo/psutil/issues/1533
.. _1534: https://github.com/giampaolo/psutil/issues/1534
.. _1535: https://github.com/giampaolo/psutil/issues/1535
.. _1536: https://github.com/giampaolo/psutil/issues/1536
.. _1537: https://github.com/giampaolo/psutil/issues/1537
.. _1538: https://github.com/giampaolo/psutil/issues/1538
.. _1539: https://github.com/giampaolo/psutil/issues/1539
.. _1540: https://github.com/giampaolo/psutil/issues/1540
.. _1541: https://github.com/giampaolo/psutil/issues/1541
.. _1542: https://github.com/giampaolo/psutil/issues/1542
.. _1543: https://github.com/giampaolo/psutil/issues/1543
.. _1544: https://github.com/giampaolo/psutil/issues/1544
.. _1545: https://github.com/giampaolo/psutil/issues/1545
.. _1546: https://github.com/giampaolo/psutil/issues/1546
.. _1547: https://github.com/giampaolo/psutil/issues/1547
.. _1548: https://github.com/giampaolo/psutil/issues/1548
.. _1549: https://github.com/giampaolo/psutil/issues/1549
.. _1550: https://github.com/giampaolo/psutil/issues/1550
.. _1551: https://github.com/giampaolo/psutil/issues/1551
.. _1552: https://github.com/giampaolo/psutil/issues/1552
.. _1553: https://github.com/giampaolo/psutil/issues/1553
.. _1554: https://github.com/giampaolo/psutil/issues/1554
.. _1555: https://github.com/giampaolo/psutil/issues/1555
.. _1556: https://github.com/giampaolo/psutil/issues/1556
.. _1557: https://github.com/giampaolo/psutil/issues/1557
.. _1558: https://github.com/giampaolo/psutil/issues/1558
.. _1559: https://github.com/giampaolo/psutil/issues/1559
.. _1560: https://github.com/giampaolo/psutil/issues/1560
.. _1561: https://github.com/giampaolo/psutil/issues/1561
.. _1562: https://github.com/giampaolo/psutil/issues/1562
.. _1563: https://github.com/giampaolo/psutil/issues/1563
.. _1564: https://github.com/giampaolo/psutil/issues/1564
.. _1565: https://github.com/giampaolo/psutil/issues/1565
.. _1566: https://github.com/giampaolo/psutil/issues/1566
.. _1567: https://github.com/giampaolo/psutil/issues/1567
.. _1568: https://github.com/giampaolo/psutil/issues/1568
.. _1569: https://github.com/giampaolo/psutil/issues/1569
.. _1570: https://github.com/giampaolo/psutil/issues/1570
.. _1571: https://github.com/giampaolo/psutil/issues/1571
.. _1572: https://github.com/giampaolo/psutil/issues/1572
.. _1573: https://github.com/giampaolo/psutil/issues/1573
.. _1574: https://github.com/giampaolo/psutil/issues/1574
.. _1575: https://github.com/giampaolo/psutil/issues/1575
.. _1576: https://github.com/giampaolo/psutil/issues/1576
.. _1577: https://github.com/giampaolo/psutil/issues/1577
.. _1578: https://github.com/giampaolo/psutil/issues/1578
.. _1579: https://github.com/giampaolo/psutil/issues/1579
.. _1580: https://github.com/giampaolo/psutil/issues/1580
.. _1581: https://github.com/giampaolo/psutil/issues/1581
.. _1582: https://github.com/giampaolo/psutil/issues/1582
.. _1583: https://github.com/giampaolo/psutil/issues/1583
.. _1584: https://github.com/giampaolo/psutil/issues/1584
.. _1585: https://github.com/giampaolo/psutil/issues/1585
.. _1586: https://github.com/giampaolo/psutil/issues/1586
.. _1587: https://github.com/giampaolo/psutil/issues/1587
.. _1588: https://github.com/giampaolo/psutil/issues/1588
.. _1589: https://github.com/giampaolo/psutil/issues/1589
.. _1590: https://github.com/giampaolo/psutil/issues/1590
.. _1591: https://github.com/giampaolo/psutil/issues/1591
.. _1592: https://github.com/giampaolo/psutil/issues/1592
.. _1593: https://github.com/giampaolo/psutil/issues/1593
.. _1594: https://github.com/giampaolo/psutil/issues/1594
.. _1595: https://github.com/giampaolo/psutil/issues/1595
.. _1596: https://github.com/giampaolo/psutil/issues/1596
.. _1597: https://github.com/giampaolo/psutil/issues/1597
.. _1598: https://github.com/giampaolo/psutil/issues/1598
.. _1599: https://github.com/giampaolo/psutil/issues/1599
.. _1600: https://github.com/giampaolo/psutil/issues/1600
.. _1601: https://github.com/giampaolo/psutil/issues/1601
.. _1602: https://github.com/giampaolo/psutil/issues/1602
.. _1603: https://github.com/giampaolo/psutil/issues/1603
.. _1604: https://github.com/giampaolo/psutil/issues/1604
.. _1605: https://github.com/giampaolo/psutil/issues/1605
.. _1606: https://github.com/giampaolo/psutil/issues/1606
.. _1607: https://github.com/giampaolo/psutil/issues/1607
.. _1608: https://github.com/giampaolo/psutil/issues/1608
.. _1609: https://github.com/giampaolo/psutil/issues/1609
.. _1610: https://github.com/giampaolo/psutil/issues/1610
.. _1611: https://github.com/giampaolo/psutil/issues/1611
.. _1612: https://github.com/giampaolo/psutil/issues/1612
.. _1613: https://github.com/giampaolo/psutil/issues/1613
.. _1614: https://github.com/giampaolo/psutil/issues/1614
.. _1615: https://github.com/giampaolo/psutil/issues/1615
.. _1616: https://github.com/giampaolo/psutil/issues/1616
.. _1617: https://github.com/giampaolo/psutil/issues/1617
.. _1618: https://github.com/giampaolo/psutil/issues/1618
.. _1619: https://github.com/giampaolo/psutil/issues/1619
.. _1620: https://github.com/giampaolo/psutil/issues/1620
.. _1621: https://github.com/giampaolo/psutil/issues/1621
.. _1622: https://github.com/giampaolo/psutil/issues/1622
.. _1623: https://github.com/giampaolo/psutil/issues/1623
.. _1624: https://github.com/giampaolo/psutil/issues/1624
.. _1625: https://github.com/giampaolo/psutil/issues/1625
.. _1626: https://github.com/giampaolo/psutil/issues/1626
.. _1627: https://github.com/giampaolo/psutil/issues/1627
.. _1628: https://github.com/giampaolo/psutil/issues/1628
.. _1629: https://github.com/giampaolo/psutil/issues/1629
.. _1630: https://github.com/giampaolo/psutil/issues/1630
.. _1631: https://github.com/giampaolo/psutil/issues/1631
.. _1632: https://github.com/giampaolo/psutil/issues/1632
.. _1633: https://github.com/giampaolo/psutil/issues/1633
.. _1634: https://github.com/giampaolo/psutil/issues/1634
.. _1635: https://github.com/giampaolo/psutil/issues/1635
.. _1636: https://github.com/giampaolo/psutil/issues/1636
.. _1637: https://github.com/giampaolo/psutil/issues/1637
.. _1638: https://github.com/giampaolo/psutil/issues/1638
.. _1639: https://github.com/giampaolo/psutil/issues/1639
.. _1640: https://github.com/giampaolo/psutil/issues/1640
.. _1641: https://github.com/giampaolo/psutil/issues/1641
.. _1642: https://github.com/giampaolo/psutil/issues/1642
.. _1643: https://github.com/giampaolo/psutil/issues/1643
.. _1644: https://github.com/giampaolo/psutil/issues/1644
.. _1645: https://github.com/giampaolo/psutil/issues/1645
.. _1646: https://github.com/giampaolo/psutil/issues/1646
.. _1647: https://github.com/giampaolo/psutil/issues/1647
.. _1648: https://github.com/giampaolo/psutil/issues/1648
.. _1649: https://github.com/giampaolo/psutil/issues/1649
.. _1650: https://github.com/giampaolo/psutil/issues/1650
.. _1651: https://github.com/giampaolo/psutil/issues/1651
.. _1652: https://github.com/giampaolo/psutil/issues/1652
.. _1653: https://github.com/giampaolo/psutil/issues/1653
.. _1654: https://github.com/giampaolo/psutil/issues/1654
.. _1655: https://github.com/giampaolo/psutil/issues/1655
.. _1656: https://github.com/giampaolo/psutil/issues/1656
.. _1657: https://github.com/giampaolo/psutil/issues/1657
.. _1658: https://github.com/giampaolo/psutil/issues/1658
.. _1659: https://github.com/giampaolo/psutil/issues/1659
.. _1660: https://github.com/giampaolo/psutil/issues/1660
.. _1661: https://github.com/giampaolo/psutil/issues/1661
.. _1662: https://github.com/giampaolo/psutil/issues/1662
.. _1663: https://github.com/giampaolo/psutil/issues/1663
.. _1664: https://github.com/giampaolo/psutil/issues/1664
.. _1665: https://github.com/giampaolo/psutil/issues/1665
.. _1666: https://github.com/giampaolo/psutil/issues/1666
.. _1667: https://github.com/giampaolo/psutil/issues/1667
.. _1668: https://github.com/giampaolo/psutil/issues/1668
.. _1669: https://github.com/giampaolo/psutil/issues/1669
.. _1670: https://github.com/giampaolo/psutil/issues/1670
.. _1671: https://github.com/giampaolo/psutil/issues/1671
.. _1672: https://github.com/giampaolo/psutil/issues/1672
.. _1673: https://github.com/giampaolo/psutil/issues/1673
.. _1674: https://github.com/giampaolo/psutil/issues/1674
.. _1675: https://github.com/giampaolo/psutil/issues/1675
.. _1676: https://github.com/giampaolo/psutil/issues/1676
.. _1677: https://github.com/giampaolo/psutil/issues/1677
.. _1678: https://github.com/giampaolo/psutil/issues/1678
.. _1679: https://github.com/giampaolo/psutil/issues/1679
.. _1680: https://github.com/giampaolo/psutil/issues/1680
.. _1681: https://github.com/giampaolo/psutil/issues/1681
.. _1682: https://github.com/giampaolo/psutil/issues/1682
.. _1683: https://github.com/giampaolo/psutil/issues/1683
.. _1684: https://github.com/giampaolo/psutil/issues/1684
.. _1685: https://github.com/giampaolo/psutil/issues/1685
.. _1686: https://github.com/giampaolo/psutil/issues/1686
.. _1687: https://github.com/giampaolo/psutil/issues/1687
.. _1688: https://github.com/giampaolo/psutil/issues/1688
.. _1689: https://github.com/giampaolo/psutil/issues/1689
.. _1690: https://github.com/giampaolo/psutil/issues/1690
.. _1691: https://github.com/giampaolo/psutil/issues/1691
.. _1692: https://github.com/giampaolo/psutil/issues/1692
.. _1693: https://github.com/giampaolo/psutil/issues/1693
.. _1694: https://github.com/giampaolo/psutil/issues/1694
.. _1695: https://github.com/giampaolo/psutil/issues/1695
.. _1696: https://github.com/giampaolo/psutil/issues/1696
.. _1697: https://github.com/giampaolo/psutil/issues/1697
.. _1698: https://github.com/giampaolo/psutil/issues/1698
.. _1699: https://github.com/giampaolo/psutil/issues/1699
.. _1700: https://github.com/giampaolo/psutil/issues/1700
.. _1701: https://github.com/giampaolo/psutil/issues/1701
.. _1702: https://github.com/giampaolo/psutil/issues/1702
.. _1703: https://github.com/giampaolo/psutil/issues/1703
.. _1704: https://github.com/giampaolo/psutil/issues/1704
.. _1705: https://github.com/giampaolo/psutil/issues/1705
.. _1706: https://github.com/giampaolo/psutil/issues/1706
.. _1707: https://github.com/giampaolo/psutil/issues/1707
.. _1708: https://github.com/giampaolo/psutil/issues/1708
.. _1709: https://github.com/giampaolo/psutil/issues/1709
.. _1710: https://github.com/giampaolo/psutil/issues/1710
.. _1711: https://github.com/giampaolo/psutil/issues/1711
.. _1712: https://github.com/giampaolo/psutil/issues/1712
.. _1713: https://github.com/giampaolo/psutil/issues/1713
.. _1714: https://github.com/giampaolo/psutil/issues/1714
.. _1715: https://github.com/giampaolo/psutil/issues/1715
.. _1716: https://github.com/giampaolo/psutil/issues/1716
.. _1717: https://github.com/giampaolo/psutil/issues/1717
.. _1718: https://github.com/giampaolo/psutil/issues/1718
.. _1719: https://github.com/giampaolo/psutil/issues/1719
.. _1720: https://github.com/giampaolo/psutil/issues/1720
.. _1721: https://github.com/giampaolo/psutil/issues/1721
.. _1722: https://github.com/giampaolo/psutil/issues/1722
.. _1723: https://github.com/giampaolo/psutil/issues/1723
.. _1724: https://github.com/giampaolo/psutil/issues/1724
.. _1725: https://github.com/giampaolo/psutil/issues/1725
.. _1726: https://github.com/giampaolo/psutil/issues/1726
.. _1727: https://github.com/giampaolo/psutil/issues/1727
.. _1728: https://github.com/giampaolo/psutil/issues/1728
.. _1729: https://github.com/giampaolo/psutil/issues/1729
.. _1730: https://github.com/giampaolo/psutil/issues/1730
.. _1731: https://github.com/giampaolo/psutil/issues/1731
.. _1732: https://github.com/giampaolo/psutil/issues/1732
.. _1733: https://github.com/giampaolo/psutil/issues/1733
.. _1734: https://github.com/giampaolo/psutil/issues/1734
.. _1735: https://github.com/giampaolo/psutil/issues/1735
.. _1736: https://github.com/giampaolo/psutil/issues/1736
.. _1737: https://github.com/giampaolo/psutil/issues/1737
.. _1738: https://github.com/giampaolo/psutil/issues/1738
.. _1739: https://github.com/giampaolo/psutil/issues/1739
.. _1740: https://github.com/giampaolo/psutil/issues/1740
.. _1741: https://github.com/giampaolo/psutil/issues/1741
.. _1742: https://github.com/giampaolo/psutil/issues/1742
.. _1743: https://github.com/giampaolo/psutil/issues/1743
.. _1744: https://github.com/giampaolo/psutil/issues/1744
.. _1745: https://github.com/giampaolo/psutil/issues/1745
.. _1746: https://github.com/giampaolo/psutil/issues/1746
.. _1747: https://github.com/giampaolo/psutil/issues/1747
.. _1748: https://github.com/giampaolo/psutil/issues/1748
.. _1749: https://github.com/giampaolo/psutil/issues/1749
.. _1750: https://github.com/giampaolo/psutil/issues/1750
.. _1751: https://github.com/giampaolo/psutil/issues/1751
.. _1752: https://github.com/giampaolo/psutil/issues/1752
.. _1753: https://github.com/giampaolo/psutil/issues/1753
.. _1754: https://github.com/giampaolo/psutil/issues/1754
.. _1755: https://github.com/giampaolo/psutil/issues/1755
.. _1756: https://github.com/giampaolo/psutil/issues/1756
.. _1757: https://github.com/giampaolo/psutil/issues/1757
.. _1758: https://github.com/giampaolo/psutil/issues/1758
.. _1759: https://github.com/giampaolo/psutil/issues/1759
.. _1760: https://github.com/giampaolo/psutil/issues/1760
.. _1761: https://github.com/giampaolo/psutil/issues/1761
.. _1762: https://github.com/giampaolo/psutil/issues/1762
.. _1763: https://github.com/giampaolo/psutil/issues/1763
.. _1764: https://github.com/giampaolo/psutil/issues/1764
.. _1765: https://github.com/giampaolo/psutil/issues/1765
.. _1766: https://github.com/giampaolo/psutil/issues/1766
.. _1767: https://github.com/giampaolo/psutil/issues/1767
.. _1768: https://github.com/giampaolo/psutil/issues/1768
.. _1769: https://github.com/giampaolo/psutil/issues/1769
.. _1770: https://github.com/giampaolo/psutil/issues/1770
.. _1771: https://github.com/giampaolo/psutil/issues/1771
.. _1772: https://github.com/giampaolo/psutil/issues/1772
.. _1773: https://github.com/giampaolo/psutil/issues/1773
.. _1774: https://github.com/giampaolo/psutil/issues/1774
.. _1775: https://github.com/giampaolo/psutil/issues/1775
.. _1776: https://github.com/giampaolo/psutil/issues/1776
.. _1777: https://github.com/giampaolo/psutil/issues/1777
.. _1778: https://github.com/giampaolo/psutil/issues/1778
.. _1779: https://github.com/giampaolo/psutil/issues/1779
.. _1780: https://github.com/giampaolo/psutil/issues/1780
.. _1781: https://github.com/giampaolo/psutil/issues/1781
.. _1782: https://github.com/giampaolo/psutil/issues/1782
.. _1783: https://github.com/giampaolo/psutil/issues/1783
.. _1784: https://github.com/giampaolo/psutil/issues/1784
.. _1785: https://github.com/giampaolo/psutil/issues/1785
.. _1786: https://github.com/giampaolo/psutil/issues/1786
.. _1787: https://github.com/giampaolo/psutil/issues/1787
.. _1788: https://github.com/giampaolo/psutil/issues/1788
.. _1789: https://github.com/giampaolo/psutil/issues/1789
.. _1790: https://github.com/giampaolo/psutil/issues/1790
.. _1791: https://github.com/giampaolo/psutil/issues/1791
.. _1792: https://github.com/giampaolo/psutil/issues/1792
.. _1793: https://github.com/giampaolo/psutil/issues/1793
.. _1794: https://github.com/giampaolo/psutil/issues/1794
.. _1795: https://github.com/giampaolo/psutil/issues/1795
.. _1796: https://github.com/giampaolo/psutil/issues/1796
.. _1797: https://github.com/giampaolo/psutil/issues/1797
.. _1798: https://github.com/giampaolo/psutil/issues/1798
.. _1799: https://github.com/giampaolo/psutil/issues/1799
.. _1800: https://github.com/giampaolo/psutil/issues/1800
.. _1801: https://github.com/giampaolo/psutil/issues/1801
.. _1802: https://github.com/giampaolo/psutil/issues/1802
.. _1803: https://github.com/giampaolo/psutil/issues/1803
.. _1804: https://github.com/giampaolo/psutil/issues/1804
.. _1805: https://github.com/giampaolo/psutil/issues/1805
.. _1806: https://github.com/giampaolo/psutil/issues/1806
.. _1807: https://github.com/giampaolo/psutil/issues/1807
.. _1808: https://github.com/giampaolo/psutil/issues/1808
.. _1809: https://github.com/giampaolo/psutil/issues/1809
.. _1810: https://github.com/giampaolo/psutil/issues/1810
.. _1811: https://github.com/giampaolo/psutil/issues/1811
.. _1812: https://github.com/giampaolo/psutil/issues/1812
.. _1813: https://github.com/giampaolo/psutil/issues/1813
.. _1814: https://github.com/giampaolo/psutil/issues/1814
.. _1815: https://github.com/giampaolo/psutil/issues/1815
.. _1816: https://github.com/giampaolo/psutil/issues/1816
.. _1817: https://github.com/giampaolo/psutil/issues/1817
.. _1818: https://github.com/giampaolo/psutil/issues/1818
.. _1819: https://github.com/giampaolo/psutil/issues/1819
.. _1820: https://github.com/giampaolo/psutil/issues/1820
.. _1821: https://github.com/giampaolo/psutil/issues/1821
.. _1822: https://github.com/giampaolo/psutil/issues/1822
.. _1823: https://github.com/giampaolo/psutil/issues/1823
.. _1824: https://github.com/giampaolo/psutil/issues/1824
.. _1825: https://github.com/giampaolo/psutil/issues/1825
.. _1826: https://github.com/giampaolo/psutil/issues/1826
.. _1827: https://github.com/giampaolo/psutil/issues/1827
.. _1828: https://github.com/giampaolo/psutil/issues/1828
.. _1829: https://github.com/giampaolo/psutil/issues/1829
.. _1830: https://github.com/giampaolo/psutil/issues/1830
.. _1831: https://github.com/giampaolo/psutil/issues/1831
.. _1832: https://github.com/giampaolo/psutil/issues/1832
.. _1833: https://github.com/giampaolo/psutil/issues/1833
.. _1834: https://github.com/giampaolo/psutil/issues/1834
.. _1835: https://github.com/giampaolo/psutil/issues/1835
.. _1836: https://github.com/giampaolo/psutil/issues/1836
.. _1837: https://github.com/giampaolo/psutil/issues/1837
.. _1838: https://github.com/giampaolo/psutil/issues/1838
.. _1839: https://github.com/giampaolo/psutil/issues/1839
.. _1840: https://github.com/giampaolo/psutil/issues/1840
.. _1841: https://github.com/giampaolo/psutil/issues/1841
.. _1842: https://github.com/giampaolo/psutil/issues/1842
.. _1843: https://github.com/giampaolo/psutil/issues/1843
.. _1844: https://github.com/giampaolo/psutil/issues/1844
.. _1845: https://github.com/giampaolo/psutil/issues/1845
.. _1846: https://github.com/giampaolo/psutil/issues/1846
.. _1847: https://github.com/giampaolo/psutil/issues/1847
.. _1848: https://github.com/giampaolo/psutil/issues/1848
.. _1849: https://github.com/giampaolo/psutil/issues/1849
.. _1850: https://github.com/giampaolo/psutil/issues/1850
.. _1851: https://github.com/giampaolo/psutil/issues/1851
.. _1852: https://github.com/giampaolo/psutil/issues/1852
.. _1853: https://github.com/giampaolo/psutil/issues/1853
.. _1854: https://github.com/giampaolo/psutil/issues/1854
.. _1855: https://github.com/giampaolo/psutil/issues/1855
.. _1856: https://github.com/giampaolo/psutil/issues/1856
.. _1857: https://github.com/giampaolo/psutil/issues/1857
.. _1858: https://github.com/giampaolo/psutil/issues/1858
.. _1859: https://github.com/giampaolo/psutil/issues/1859
.. _1860: https://github.com/giampaolo/psutil/issues/1860
.. _1861: https://github.com/giampaolo/psutil/issues/1861
.. _1862: https://github.com/giampaolo/psutil/issues/1862
.. _1863: https://github.com/giampaolo/psutil/issues/1863
.. _1864: https://github.com/giampaolo/psutil/issues/1864
.. _1865: https://github.com/giampaolo/psutil/issues/1865
.. _1866: https://github.com/giampaolo/psutil/issues/1866
.. _1867: https://github.com/giampaolo/psutil/issues/1867
.. _1868: https://github.com/giampaolo/psutil/issues/1868
.. _1869: https://github.com/giampaolo/psutil/issues/1869
.. _1870: https://github.com/giampaolo/psutil/issues/1870
.. _1871: https://github.com/giampaolo/psutil/issues/1871
.. _1872: https://github.com/giampaolo/psutil/issues/1872
.. _1873: https://github.com/giampaolo/psutil/issues/1873
.. _1874: https://github.com/giampaolo/psutil/issues/1874
.. _1875: https://github.com/giampaolo/psutil/issues/1875
.. _1876: https://github.com/giampaolo/psutil/issues/1876
.. _1877: https://github.com/giampaolo/psutil/issues/1877
.. _1878: https://github.com/giampaolo/psutil/issues/1878
.. _1879: https://github.com/giampaolo/psutil/issues/1879
.. _1880: https://github.com/giampaolo/psutil/issues/1880
.. _1881: https://github.com/giampaolo/psutil/issues/1881
.. _1882: https://github.com/giampaolo/psutil/issues/1882
.. _1883: https://github.com/giampaolo/psutil/issues/1883
.. _1884: https://github.com/giampaolo/psutil/issues/1884
.. _1885: https://github.com/giampaolo/psutil/issues/1885
.. _1886: https://github.com/giampaolo/psutil/issues/1886
.. _1887: https://github.com/giampaolo/psutil/issues/1887
.. _1888: https://github.com/giampaolo/psutil/issues/1888
.. _1889: https://github.com/giampaolo/psutil/issues/1889
.. _1890: https://github.com/giampaolo/psutil/issues/1890
.. _1891: https://github.com/giampaolo/psutil/issues/1891
.. _1892: https://github.com/giampaolo/psutil/issues/1892
.. _1893: https://github.com/giampaolo/psutil/issues/1893
.. _1894: https://github.com/giampaolo/psutil/issues/1894
.. _1895: https://github.com/giampaolo/psutil/issues/1895
.. _1896: https://github.com/giampaolo/psutil/issues/1896
.. _1897: https://github.com/giampaolo/psutil/issues/1897
.. _1898: https://github.com/giampaolo/psutil/issues/1898
.. _1899: https://github.com/giampaolo/psutil/issues/1899
.. _1900: https://github.com/giampaolo/psutil/issues/1900
.. _1901: https://github.com/giampaolo/psutil/issues/1901
.. _1902: https://github.com/giampaolo/psutil/issues/1902
.. _1903: https://github.com/giampaolo/psutil/issues/1903
.. _1904: https://github.com/giampaolo/psutil/issues/1904
.. _1905: https://github.com/giampaolo/psutil/issues/1905
.. _1906: https://github.com/giampaolo/psutil/issues/1906
.. _1907: https://github.com/giampaolo/psutil/issues/1907
.. _1908: https://github.com/giampaolo/psutil/issues/1908
.. _1909: https://github.com/giampaolo/psutil/issues/1909
.. _1910: https://github.com/giampaolo/psutil/issues/1910
.. _1911: https://github.com/giampaolo/psutil/issues/1911
.. _1912: https://github.com/giampaolo/psutil/issues/1912
.. _1913: https://github.com/giampaolo/psutil/issues/1913
.. _1914: https://github.com/giampaolo/psutil/issues/1914
.. _1915: https://github.com/giampaolo/psutil/issues/1915
.. _1916: https://github.com/giampaolo/psutil/issues/1916
.. _1917: https://github.com/giampaolo/psutil/issues/1917
.. _1918: https://github.com/giampaolo/psutil/issues/1918
.. _1919: https://github.com/giampaolo/psutil/issues/1919
.. _1920: https://github.com/giampaolo/psutil/issues/1920
.. _1921: https://github.com/giampaolo/psutil/issues/1921
.. _1922: https://github.com/giampaolo/psutil/issues/1922
.. _1923: https://github.com/giampaolo/psutil/issues/1923
.. _1924: https://github.com/giampaolo/psutil/issues/1924
.. _1925: https://github.com/giampaolo/psutil/issues/1925
.. _1926: https://github.com/giampaolo/psutil/issues/1926
.. _1927: https://github.com/giampaolo/psutil/issues/1927
.. _1928: https://github.com/giampaolo/psutil/issues/1928
.. _1929: https://github.com/giampaolo/psutil/issues/1929
.. _1930: https://github.com/giampaolo/psutil/issues/1930
.. _1931: https://github.com/giampaolo/psutil/issues/1931
.. _1932: https://github.com/giampaolo/psutil/issues/1932
.. _1933: https://github.com/giampaolo/psutil/issues/1933
.. _1934: https://github.com/giampaolo/psutil/issues/1934
.. _1935: https://github.com/giampaolo/psutil/issues/1935
.. _1936: https://github.com/giampaolo/psutil/issues/1936
.. _1937: https://github.com/giampaolo/psutil/issues/1937
.. _1938: https://github.com/giampaolo/psutil/issues/1938
.. _1939: https://github.com/giampaolo/psutil/issues/1939
.. _1940: https://github.com/giampaolo/psutil/issues/1940
.. _1941: https://github.com/giampaolo/psutil/issues/1941
.. _1942: https://github.com/giampaolo/psutil/issues/1942
.. _1943: https://github.com/giampaolo/psutil/issues/1943
.. _1944: https://github.com/giampaolo/psutil/issues/1944
.. _1945: https://github.com/giampaolo/psutil/issues/1945
.. _1946: https://github.com/giampaolo/psutil/issues/1946
.. _1947: https://github.com/giampaolo/psutil/issues/1947
.. _1948: https://github.com/giampaolo/psutil/issues/1948
.. _1949: https://github.com/giampaolo/psutil/issues/1949
.. _1950: https://github.com/giampaolo/psutil/issues/1950
.. _1951: https://github.com/giampaolo/psutil/issues/1951
.. _1952: https://github.com/giampaolo/psutil/issues/1952
.. _1953: https://github.com/giampaolo/psutil/issues/1953
.. _1954: https://github.com/giampaolo/psutil/issues/1954
.. _1955: https://github.com/giampaolo/psutil/issues/1955
.. _1956: https://github.com/giampaolo/psutil/issues/1956
.. _1957: https://github.com/giampaolo/psutil/issues/1957
.. _1958: https://github.com/giampaolo/psutil/issues/1958
.. _1959: https://github.com/giampaolo/psutil/issues/1959
.. _1960: https://github.com/giampaolo/psutil/issues/1960
.. _1961: https://github.com/giampaolo/psutil/issues/1961
.. _1962: https://github.com/giampaolo/psutil/issues/1962
.. _1963: https://github.com/giampaolo/psutil/issues/1963
.. _1964: https://github.com/giampaolo/psutil/issues/1964
.. _1965: https://github.com/giampaolo/psutil/issues/1965
.. _1966: https://github.com/giampaolo/psutil/issues/1966
.. _1967: https://github.com/giampaolo/psutil/issues/1967
.. _1968: https://github.com/giampaolo/psutil/issues/1968
.. _1969: https://github.com/giampaolo/psutil/issues/1969
.. _1970: https://github.com/giampaolo/psutil/issues/1970
.. _1971: https://github.com/giampaolo/psutil/issues/1971
.. _1972: https://github.com/giampaolo/psutil/issues/1972
.. _1973: https://github.com/giampaolo/psutil/issues/1973
.. _1974: https://github.com/giampaolo/psutil/issues/1974
.. _1975: https://github.com/giampaolo/psutil/issues/1975
.. _1976: https://github.com/giampaolo/psutil/issues/1976
.. _1977: https://github.com/giampaolo/psutil/issues/1977
.. _1978: https://github.com/giampaolo/psutil/issues/1978
.. _1979: https://github.com/giampaolo/psutil/issues/1979
.. _1980: https://github.com/giampaolo/psutil/issues/1980
.. _1981: https://github.com/giampaolo/psutil/issues/1981
.. _1982: https://github.com/giampaolo/psutil/issues/1982
.. _1983: https://github.com/giampaolo/psutil/issues/1983
.. _1984: https://github.com/giampaolo/psutil/issues/1984
.. _1985: https://github.com/giampaolo/psutil/issues/1985
.. _1986: https://github.com/giampaolo/psutil/issues/1986
.. _1987: https://github.com/giampaolo/psutil/issues/1987
.. _1988: https://github.com/giampaolo/psutil/issues/1988
.. _1989: https://github.com/giampaolo/psutil/issues/1989
.. _1990: https://github.com/giampaolo/psutil/issues/1990
.. _1991: https://github.com/giampaolo/psutil/issues/1991
.. _1992: https://github.com/giampaolo/psutil/issues/1992
.. _1993: https://github.com/giampaolo/psutil/issues/1993
.. _1994: https://github.com/giampaolo/psutil/issues/1994
.. _1995: https://github.com/giampaolo/psutil/issues/1995
.. _1996: https://github.com/giampaolo/psutil/issues/1996
.. _1997: https://github.com/giampaolo/psutil/issues/1997
.. _1998: https://github.com/giampaolo/psutil/issues/1998
.. _1999: https://github.com/giampaolo/psutil/issues/1999
.. _2000: https://github.com/giampaolo/psutil/issues/2000
.. _2001: https://github.com/giampaolo/psutil/issues/2001
.. _2002: https://github.com/giampaolo/psutil/issues/2002
.. _2003: https://github.com/giampaolo/psutil/issues/2003
.. _2004: https://github.com/giampaolo/psutil/issues/2004
.. _2005: https://github.com/giampaolo/psutil/issues/2005
.. _2006: https://github.com/giampaolo/psutil/issues/2006
.. _2007: https://github.com/giampaolo/psutil/issues/2007
.. _2008: https://github.com/giampaolo/psutil/issues/2008
.. _2009: https://github.com/giampaolo/psutil/issues/2009
.. _2010: https://github.com/giampaolo/psutil/issues/2010
.. _2011: https://github.com/giampaolo/psutil/issues/2011
.. _2012: https://github.com/giampaolo/psutil/issues/2012
.. _2013: https://github.com/giampaolo/psutil/issues/2013
.. _2014: https://github.com/giampaolo/psutil/issues/2014
.. _2015: https://github.com/giampaolo/psutil/issues/2015
.. _2016: https://github.com/giampaolo/psutil/issues/2016
.. _2017: https://github.com/giampaolo/psutil/issues/2017
.. _2018: https://github.com/giampaolo/psutil/issues/2018
.. _2019: https://github.com/giampaolo/psutil/issues/2019
.. _2020: https://github.com/giampaolo/psutil/issues/2020
.. _2021: https://github.com/giampaolo/psutil/issues/2021
.. _2022: https://github.com/giampaolo/psutil/issues/2022
.. _2023: https://github.com/giampaolo/psutil/issues/2023
.. _2024: https://github.com/giampaolo/psutil/issues/2024
.. _2025: https://github.com/giampaolo/psutil/issues/2025
.. _2026: https://github.com/giampaolo/psutil/issues/2026
.. _2027: https://github.com/giampaolo/psutil/issues/2027
.. _2028: https://github.com/giampaolo/psutil/issues/2028
.. _2029: https://github.com/giampaolo/psutil/issues/2029
.. _2030: https://github.com/giampaolo/psutil/issues/2030
.. _2031: https://github.com/giampaolo/psutil/issues/2031
.. _2032: https://github.com/giampaolo/psutil/issues/2032
.. _2033: https://github.com/giampaolo/psutil/issues/2033
.. _2034: https://github.com/giampaolo/psutil/issues/2034
.. _2035: https://github.com/giampaolo/psutil/issues/2035
.. _2036: https://github.com/giampaolo/psutil/issues/2036
.. _2037: https://github.com/giampaolo/psutil/issues/2037
.. _2038: https://github.com/giampaolo/psutil/issues/2038
.. _2039: https://github.com/giampaolo/psutil/issues/2039
.. _2040: https://github.com/giampaolo/psutil/issues/2040
.. _2041: https://github.com/giampaolo/psutil/issues/2041
.. _2042: https://github.com/giampaolo/psutil/issues/2042
.. _2043: https://github.com/giampaolo/psutil/issues/2043
.. _2044: https://github.com/giampaolo/psutil/issues/2044
.. _2045: https://github.com/giampaolo/psutil/issues/2045
.. _2046: https://github.com/giampaolo/psutil/issues/2046
.. _2047: https://github.com/giampaolo/psutil/issues/2047
.. _2048: https://github.com/giampaolo/psutil/issues/2048
.. _2049: https://github.com/giampaolo/psutil/issues/2049
.. _2050: https://github.com/giampaolo/psutil/issues/2050
.. _2051: https://github.com/giampaolo/psutil/issues/2051
.. _2052: https://github.com/giampaolo/psutil/issues/2052
.. _2053: https://github.com/giampaolo/psutil/issues/2053
.. _2054: https://github.com/giampaolo/psutil/issues/2054
.. _2055: https://github.com/giampaolo/psutil/issues/2055
.. _2056: https://github.com/giampaolo/psutil/issues/2056
.. _2057: https://github.com/giampaolo/psutil/issues/2057
.. _2058: https://github.com/giampaolo/psutil/issues/2058
.. _2059: https://github.com/giampaolo/psutil/issues/2059
.. _2060: https://github.com/giampaolo/psutil/issues/2060
.. _2061: https://github.com/giampaolo/psutil/issues/2061
.. _2062: https://github.com/giampaolo/psutil/issues/2062
.. _2063: https://github.com/giampaolo/psutil/issues/2063
.. _2064: https://github.com/giampaolo/psutil/issues/2064
.. _2065: https://github.com/giampaolo/psutil/issues/2065
.. _2066: https://github.com/giampaolo/psutil/issues/2066
.. _2067: https://github.com/giampaolo/psutil/issues/2067
.. _2068: https://github.com/giampaolo/psutil/issues/2068
.. _2069: https://github.com/giampaolo/psutil/issues/2069
.. _2070: https://github.com/giampaolo/psutil/issues/2070
.. _2071: https://github.com/giampaolo/psutil/issues/2071
.. _2072: https://github.com/giampaolo/psutil/issues/2072
.. _2073: https://github.com/giampaolo/psutil/issues/2073
.. _2074: https://github.com/giampaolo/psutil/issues/2074
.. _2075: https://github.com/giampaolo/psutil/issues/2075
.. _2076: https://github.com/giampaolo/psutil/issues/2076
.. _2077: https://github.com/giampaolo/psutil/issues/2077
.. _2078: https://github.com/giampaolo/psutil/issues/2078
.. _2079: https://github.com/giampaolo/psutil/issues/2079
.. _2080: https://github.com/giampaolo/psutil/issues/2080
.. _2081: https://github.com/giampaolo/psutil/issues/2081
.. _2082: https://github.com/giampaolo/psutil/issues/2082
.. _2083: https://github.com/giampaolo/psutil/issues/2083
.. _2084: https://github.com/giampaolo/psutil/issues/2084
.. _2085: https://github.com/giampaolo/psutil/issues/2085
.. _2086: https://github.com/giampaolo/psutil/issues/2086
.. _2087: https://github.com/giampaolo/psutil/issues/2087
.. _2088: https://github.com/giampaolo/psutil/issues/2088
.. _2089: https://github.com/giampaolo/psutil/issues/2089
.. _2090: https://github.com/giampaolo/psutil/issues/2090
.. _2091: https://github.com/giampaolo/psutil/issues/2091
.. _2092: https://github.com/giampaolo/psutil/issues/2092
.. _2093: https://github.com/giampaolo/psutil/issues/2093
.. _2094: https://github.com/giampaolo/psutil/issues/2094
.. _2095: https://github.com/giampaolo/psutil/issues/2095
.. _2096: https://github.com/giampaolo/psutil/issues/2096
.. _2097: https://github.com/giampaolo/psutil/issues/2097
.. _2098: https://github.com/giampaolo/psutil/issues/2098
.. _2099: https://github.com/giampaolo/psutil/issues/2099
.. _2100: https://github.com/giampaolo/psutil/issues/2100
.. _2101: https://github.com/giampaolo/psutil/issues/2101
.. _2102: https://github.com/giampaolo/psutil/issues/2102
.. _2103: https://github.com/giampaolo/psutil/issues/2103
.. _2104: https://github.com/giampaolo/psutil/issues/2104
.. _2105: https://github.com/giampaolo/psutil/issues/2105
.. _2106: https://github.com/giampaolo/psutil/issues/2106
.. _2107: https://github.com/giampaolo/psutil/issues/2107
.. _2108: https://github.com/giampaolo/psutil/issues/2108
.. _2109: https://github.com/giampaolo/psutil/issues/2109
.. _2110: https://github.com/giampaolo/psutil/issues/2110
.. _2111: https://github.com/giampaolo/psutil/issues/2111
.. _2112: https://github.com/giampaolo/psutil/issues/2112
.. _2113: https://github.com/giampaolo/psutil/issues/2113
.. _2114: https://github.com/giampaolo/psutil/issues/2114
.. _2115: https://github.com/giampaolo/psutil/issues/2115
.. _2116: https://github.com/giampaolo/psutil/issues/2116
.. _2117: https://github.com/giampaolo/psutil/issues/2117
.. _2118: https://github.com/giampaolo/psutil/issues/2118
.. _2119: https://github.com/giampaolo/psutil/issues/2119
.. _2120: https://github.com/giampaolo/psutil/issues/2120
.. _2121: https://github.com/giampaolo/psutil/issues/2121
.. _2122: https://github.com/giampaolo/psutil/issues/2122
.. _2123: https://github.com/giampaolo/psutil/issues/2123
.. _2124: https://github.com/giampaolo/psutil/issues/2124
.. _2125: https://github.com/giampaolo/psutil/issues/2125
.. _2126: https://github.com/giampaolo/psutil/issues/2126
.. _2127: https://github.com/giampaolo/psutil/issues/2127
.. _2128: https://github.com/giampaolo/psutil/issues/2128
.. _2129: https://github.com/giampaolo/psutil/issues/2129
.. _2130: https://github.com/giampaolo/psutil/issues/2130
.. _2131: https://github.com/giampaolo/psutil/issues/2131
.. _2132: https://github.com/giampaolo/psutil/issues/2132
.. _2133: https://github.com/giampaolo/psutil/issues/2133
.. _2134: https://github.com/giampaolo/psutil/issues/2134
.. _2135: https://github.com/giampaolo/psutil/issues/2135
.. _2136: https://github.com/giampaolo/psutil/issues/2136
.. _2137: https://github.com/giampaolo/psutil/issues/2137
.. _2138: https://github.com/giampaolo/psutil/issues/2138
.. _2139: https://github.com/giampaolo/psutil/issues/2139
.. _2140: https://github.com/giampaolo/psutil/issues/2140
.. _2141: https://github.com/giampaolo/psutil/issues/2141
.. _2142: https://github.com/giampaolo/psutil/issues/2142
.. _2143: https://github.com/giampaolo/psutil/issues/2143
.. _2144: https://github.com/giampaolo/psutil/issues/2144
.. _2145: https://github.com/giampaolo/psutil/issues/2145
.. _2146: https://github.com/giampaolo/psutil/issues/2146
.. _2147: https://github.com/giampaolo/psutil/issues/2147
.. _2148: https://github.com/giampaolo/psutil/issues/2148
.. _2149: https://github.com/giampaolo/psutil/issues/2149
.. _2150: https://github.com/giampaolo/psutil/issues/2150
.. _2151: https://github.com/giampaolo/psutil/issues/2151
.. _2152: https://github.com/giampaolo/psutil/issues/2152
.. _2153: https://github.com/giampaolo/psutil/issues/2153
.. _2154: https://github.com/giampaolo/psutil/issues/2154
.. _2155: https://github.com/giampaolo/psutil/issues/2155
.. _2156: https://github.com/giampaolo/psutil/issues/2156
.. _2157: https://github.com/giampaolo/psutil/issues/2157
.. _2158: https://github.com/giampaolo/psutil/issues/2158
.. _2159: https://github.com/giampaolo/psutil/issues/2159
.. _2160: https://github.com/giampaolo/psutil/issues/2160
.. _2161: https://github.com/giampaolo/psutil/issues/2161
.. _2162: https://github.com/giampaolo/psutil/issues/2162
.. _2163: https://github.com/giampaolo/psutil/issues/2163
.. _2164: https://github.com/giampaolo/psutil/issues/2164
.. _2165: https://github.com/giampaolo/psutil/issues/2165
.. _2166: https://github.com/giampaolo/psutil/issues/2166
.. _2167: https://github.com/giampaolo/psutil/issues/2167
.. _2168: https://github.com/giampaolo/psutil/issues/2168
.. _2169: https://github.com/giampaolo/psutil/issues/2169
.. _2170: https://github.com/giampaolo/psutil/issues/2170
.. _2171: https://github.com/giampaolo/psutil/issues/2171
.. _2172: https://github.com/giampaolo/psutil/issues/2172
.. _2173: https://github.com/giampaolo/psutil/issues/2173
.. _2174: https://github.com/giampaolo/psutil/issues/2174
.. _2175: https://github.com/giampaolo/psutil/issues/2175
.. _2176: https://github.com/giampaolo/psutil/issues/2176
.. _2177: https://github.com/giampaolo/psutil/issues/2177
.. _2178: https://github.com/giampaolo/psutil/issues/2178
.. _2179: https://github.com/giampaolo/psutil/issues/2179
.. _2180: https://github.com/giampaolo/psutil/issues/2180
.. _2181: https://github.com/giampaolo/psutil/issues/2181
.. _2182: https://github.com/giampaolo/psutil/issues/2182
.. _2183: https://github.com/giampaolo/psutil/issues/2183
.. _2184: https://github.com/giampaolo/psutil/issues/2184
.. _2185: https://github.com/giampaolo/psutil/issues/2185
.. _2186: https://github.com/giampaolo/psutil/issues/2186
.. _2187: https://github.com/giampaolo/psutil/issues/2187
.. _2188: https://github.com/giampaolo/psutil/issues/2188
.. _2189: https://github.com/giampaolo/psutil/issues/2189
.. _2190: https://github.com/giampaolo/psutil/issues/2190
.. _2191: https://github.com/giampaolo/psutil/issues/2191
.. _2192: https://github.com/giampaolo/psutil/issues/2192
.. _2193: https://github.com/giampaolo/psutil/issues/2193
.. _2194: https://github.com/giampaolo/psutil/issues/2194
.. _2195: https://github.com/giampaolo/psutil/issues/2195
.. _2196: https://github.com/giampaolo/psutil/issues/2196
.. _2197: https://github.com/giampaolo/psutil/issues/2197
.. _2198: https://github.com/giampaolo/psutil/issues/2198
.. _2199: https://github.com/giampaolo/psutil/issues/2199
.. _2200: https://github.com/giampaolo/psutil/issues/2200
.. _2201: https://github.com/giampaolo/psutil/issues/2201
.. _2202: https://github.com/giampaolo/psutil/issues/2202
.. _2203: https://github.com/giampaolo/psutil/issues/2203
.. _2204: https://github.com/giampaolo/psutil/issues/2204
.. _2205: https://github.com/giampaolo/psutil/issues/2205
.. _2206: https://github.com/giampaolo/psutil/issues/2206
.. _2207: https://github.com/giampaolo/psutil/issues/2207
.. _2208: https://github.com/giampaolo/psutil/issues/2208
.. _2209: https://github.com/giampaolo/psutil/issues/2209
.. _2210: https://github.com/giampaolo/psutil/issues/2210
.. _2211: https://github.com/giampaolo/psutil/issues/2211
.. _2212: https://github.com/giampaolo/psutil/issues/2212
.. _2213: https://github.com/giampaolo/psutil/issues/2213
.. _2214: https://github.com/giampaolo/psutil/issues/2214
.. _2215: https://github.com/giampaolo/psutil/issues/2215
.. _2216: https://github.com/giampaolo/psutil/issues/2216
.. _2217: https://github.com/giampaolo/psutil/issues/2217
.. _2218: https://github.com/giampaolo/psutil/issues/2218
.. _2219: https://github.com/giampaolo/psutil/issues/2219
.. _2220: https://github.com/giampaolo/psutil/issues/2220
.. _2221: https://github.com/giampaolo/psutil/issues/2221
.. _2222: https://github.com/giampaolo/psutil/issues/2222
.. _2223: https://github.com/giampaolo/psutil/issues/2223
.. _2224: https://github.com/giampaolo/psutil/issues/2224
.. _2225: https://github.com/giampaolo/psutil/issues/2225
.. _2226: https://github.com/giampaolo/psutil/issues/2226
.. _2227: https://github.com/giampaolo/psutil/issues/2227
.. _2228: https://github.com/giampaolo/psutil/issues/2228
.. _2229: https://github.com/giampaolo/psutil/issues/2229
.. _2230: https://github.com/giampaolo/psutil/issues/2230
.. _2231: https://github.com/giampaolo/psutil/issues/2231
.. _2232: https://github.com/giampaolo/psutil/issues/2232
.. _2233: https://github.com/giampaolo/psutil/issues/2233
.. _2234: https://github.com/giampaolo/psutil/issues/2234
.. _2235: https://github.com/giampaolo/psutil/issues/2235
.. _2236: https://github.com/giampaolo/psutil/issues/2236
.. _2237: https://github.com/giampaolo/psutil/issues/2237
.. _2238: https://github.com/giampaolo/psutil/issues/2238
.. _2239: https://github.com/giampaolo/psutil/issues/2239
.. _2240: https://github.com/giampaolo/psutil/issues/2240
.. _2241: https://github.com/giampaolo/psutil/issues/2241
.. _2242: https://github.com/giampaolo/psutil/issues/2242
.. _2243: https://github.com/giampaolo/psutil/issues/2243
.. _2244: https://github.com/giampaolo/psutil/issues/2244
.. _2245: https://github.com/giampaolo/psutil/issues/2245
.. _2246: https://github.com/giampaolo/psutil/issues/2246
.. _2247: https://github.com/giampaolo/psutil/issues/2247
.. _2248: https://github.com/giampaolo/psutil/issues/2248
.. _2249: https://github.com/giampaolo/psutil/issues/2249
.. _2250: https://github.com/giampaolo/psutil/issues/2250
.. _2251: https://github.com/giampaolo/psutil/issues/2251
.. _2252: https://github.com/giampaolo/psutil/issues/2252
.. _2253: https://github.com/giampaolo/psutil/issues/2253
.. _2254: https://github.com/giampaolo/psutil/issues/2254
.. _2255: https://github.com/giampaolo/psutil/issues/2255
.. _2256: https://github.com/giampaolo/psutil/issues/2256
.. _2257: https://github.com/giampaolo/psutil/issues/2257
.. _2258: https://github.com/giampaolo/psutil/issues/2258
.. _2259: https://github.com/giampaolo/psutil/issues/2259
.. _2260: https://github.com/giampaolo/psutil/issues/2260
.. _2261: https://github.com/giampaolo/psutil/issues/2261
.. _2262: https://github.com/giampaolo/psutil/issues/2262
.. _2263: https://github.com/giampaolo/psutil/issues/2263
.. _2264: https://github.com/giampaolo/psutil/issues/2264
.. _2265: https://github.com/giampaolo/psutil/issues/2265
.. _2266: https://github.com/giampaolo/psutil/issues/2266
.. _2267: https://github.com/giampaolo/psutil/issues/2267
.. _2268: https://github.com/giampaolo/psutil/issues/2268
.. _2269: https://github.com/giampaolo/psutil/issues/2269
.. _2270: https://github.com/giampaolo/psutil/issues/2270
.. _2271: https://github.com/giampaolo/psutil/issues/2271
.. _2272: https://github.com/giampaolo/psutil/issues/2272
.. _2273: https://github.com/giampaolo/psutil/issues/2273
.. _2274: https://github.com/giampaolo/psutil/issues/2274
.. _2275: https://github.com/giampaolo/psutil/issues/2275
.. _2276: https://github.com/giampaolo/psutil/issues/2276
.. _2277: https://github.com/giampaolo/psutil/issues/2277
.. _2278: https://github.com/giampaolo/psutil/issues/2278
.. _2279: https://github.com/giampaolo/psutil/issues/2279
.. _2280: https://github.com/giampaolo/psutil/issues/2280
.. _2281: https://github.com/giampaolo/psutil/issues/2281
.. _2282: https://github.com/giampaolo/psutil/issues/2282
.. _2283: https://github.com/giampaolo/psutil/issues/2283
.. _2284: https://github.com/giampaolo/psutil/issues/2284
.. _2285: https://github.com/giampaolo/psutil/issues/2285
.. _2286: https://github.com/giampaolo/psutil/issues/2286
.. _2287: https://github.com/giampaolo/psutil/issues/2287
.. _2288: https://github.com/giampaolo/psutil/issues/2288
.. _2289: https://github.com/giampaolo/psutil/issues/2289
.. _2290: https://github.com/giampaolo/psutil/issues/2290
.. _2291: https://github.com/giampaolo/psutil/issues/2291
.. _2292: https://github.com/giampaolo/psutil/issues/2292
.. _2293: https://github.com/giampaolo/psutil/issues/2293
.. _2294: https://github.com/giampaolo/psutil/issues/2294
.. _2295: https://github.com/giampaolo/psutil/issues/2295
.. _2296: https://github.com/giampaolo/psutil/issues/2296
.. _2297: https://github.com/giampaolo/psutil/issues/2297
.. _2298: https://github.com/giampaolo/psutil/issues/2298
.. _2299: https://github.com/giampaolo/psutil/issues/2299
.. _2300: https://github.com/giampaolo/psutil/issues/2300
.. _2301: https://github.com/giampaolo/psutil/issues/2301
.. _2302: https://github.com/giampaolo/psutil/issues/2302
.. _2303: https://github.com/giampaolo/psutil/issues/2303
.. _2304: https://github.com/giampaolo/psutil/issues/2304
.. _2305: https://github.com/giampaolo/psutil/issues/2305
.. _2306: https://github.com/giampaolo/psutil/issues/2306
.. _2307: https://github.com/giampaolo/psutil/issues/2307
.. _2308: https://github.com/giampaolo/psutil/issues/2308
.. _2309: https://github.com/giampaolo/psutil/issues/2309
.. _2310: https://github.com/giampaolo/psutil/issues/2310
.. _2311: https://github.com/giampaolo/psutil/issues/2311
.. _2312: https://github.com/giampaolo/psutil/issues/2312
.. _2313: https://github.com/giampaolo/psutil/issues/2313
.. _2314: https://github.com/giampaolo/psutil/issues/2314
.. _2315: https://github.com/giampaolo/psutil/issues/2315
.. _2316: https://github.com/giampaolo/psutil/issues/2316
.. _2317: https://github.com/giampaolo/psutil/issues/2317
.. _2318: https://github.com/giampaolo/psutil/issues/2318
.. _2319: https://github.com/giampaolo/psutil/issues/2319
.. _2320: https://github.com/giampaolo/psutil/issues/2320
.. _2321: https://github.com/giampaolo/psutil/issues/2321
.. _2322: https://github.com/giampaolo/psutil/issues/2322
.. _2323: https://github.com/giampaolo/psutil/issues/2323
.. _2324: https://github.com/giampaolo/psutil/issues/2324
.. _2325: https://github.com/giampaolo/psutil/issues/2325
.. _2326: https://github.com/giampaolo/psutil/issues/2326
.. _2327: https://github.com/giampaolo/psutil/issues/2327
.. _2328: https://github.com/giampaolo/psutil/issues/2328
.. _2329: https://github.com/giampaolo/psutil/issues/2329
.. _2330: https://github.com/giampaolo/psutil/issues/2330
.. _2331: https://github.com/giampaolo/psutil/issues/2331
.. _2332: https://github.com/giampaolo/psutil/issues/2332
.. _2333: https://github.com/giampaolo/psutil/issues/2333
.. _2334: https://github.com/giampaolo/psutil/issues/2334
.. _2335: https://github.com/giampaolo/psutil/issues/2335
.. _2336: https://github.com/giampaolo/psutil/issues/2336
.. _2337: https://github.com/giampaolo/psutil/issues/2337
.. _2338: https://github.com/giampaolo/psutil/issues/2338
.. _2339: https://github.com/giampaolo/psutil/issues/2339
.. _2340: https://github.com/giampaolo/psutil/issues/2340
.. _2341: https://github.com/giampaolo/psutil/issues/2341
.. _2342: https://github.com/giampaolo/psutil/issues/2342
.. _2343: https://github.com/giampaolo/psutil/issues/2343
.. _2344: https://github.com/giampaolo/psutil/issues/2344
.. _2345: https://github.com/giampaolo/psutil/issues/2345
.. _2346: https://github.com/giampaolo/psutil/issues/2346
.. _2347: https://github.com/giampaolo/psutil/issues/2347
.. _2348: https://github.com/giampaolo/psutil/issues/2348
.. _2349: https://github.com/giampaolo/psutil/issues/2349
.. _2350: https://github.com/giampaolo/psutil/issues/2350
.. _2351: https://github.com/giampaolo/psutil/issues/2351
.. _2352: https://github.com/giampaolo/psutil/issues/2352
.. _2353: https://github.com/giampaolo/psutil/issues/2353
.. _2354: https://github.com/giampaolo/psutil/issues/2354
.. _2355: https://github.com/giampaolo/psutil/issues/2355
.. _2356: https://github.com/giampaolo/psutil/issues/2356
.. _2357: https://github.com/giampaolo/psutil/issues/2357
.. _2358: https://github.com/giampaolo/psutil/issues/2358
.. _2359: https://github.com/giampaolo/psutil/issues/2359
.. _2360: https://github.com/giampaolo/psutil/issues/2360
.. _2361: https://github.com/giampaolo/psutil/issues/2361
.. _2362: https://github.com/giampaolo/psutil/issues/2362
.. _2363: https://github.com/giampaolo/psutil/issues/2363
.. _2364: https://github.com/giampaolo/psutil/issues/2364
.. _2365: https://github.com/giampaolo/psutil/issues/2365
.. _2366: https://github.com/giampaolo/psutil/issues/2366
.. _2367: https://github.com/giampaolo/psutil/issues/2367
.. _2368: https://github.com/giampaolo/psutil/issues/2368
.. _2369: https://github.com/giampaolo/psutil/issues/2369
.. _2370: https://github.com/giampaolo/psutil/issues/2370
.. _2371: https://github.com/giampaolo/psutil/issues/2371
.. _2372: https://github.com/giampaolo/psutil/issues/2372
.. _2373: https://github.com/giampaolo/psutil/issues/2373
.. _2374: https://github.com/giampaolo/psutil/issues/2374
.. _2375: https://github.com/giampaolo/psutil/issues/2375
.. _2376: https://github.com/giampaolo/psutil/issues/2376
.. _2377: https://github.com/giampaolo/psutil/issues/2377
.. _2378: https://github.com/giampaolo/psutil/issues/2378
.. _2379: https://github.com/giampaolo/psutil/issues/2379
.. _2380: https://github.com/giampaolo/psutil/issues/2380
.. _2381: https://github.com/giampaolo/psutil/issues/2381
.. _2382: https://github.com/giampaolo/psutil/issues/2382
.. _2383: https://github.com/giampaolo/psutil/issues/2383
.. _2384: https://github.com/giampaolo/psutil/issues/2384
.. _2385: https://github.com/giampaolo/psutil/issues/2385
.. _2386: https://github.com/giampaolo/psutil/issues/2386
.. _2387: https://github.com/giampaolo/psutil/issues/2387
.. _2388: https://github.com/giampaolo/psutil/issues/2388
.. _2389: https://github.com/giampaolo/psutil/issues/2389
.. _2390: https://github.com/giampaolo/psutil/issues/2390
.. _2391: https://github.com/giampaolo/psutil/issues/2391
.. _2392: https://github.com/giampaolo/psutil/issues/2392
.. _2393: https://github.com/giampaolo/psutil/issues/2393
.. _2394: https://github.com/giampaolo/psutil/issues/2394
.. _2395: https://github.com/giampaolo/psutil/issues/2395
.. _2396: https://github.com/giampaolo/psutil/issues/2396
.. _2397: https://github.com/giampaolo/psutil/issues/2397
.. _2398: https://github.com/giampaolo/psutil/issues/2398
.. _2399: https://github.com/giampaolo/psutil/issues/2399
.. _2400: https://github.com/giampaolo/psutil/issues/2400
.. _2401: https://github.com/giampaolo/psutil/issues/2401
.. _2402: https://github.com/giampaolo/psutil/issues/2402
.. _2403: https://github.com/giampaolo/psutil/issues/2403
.. _2404: https://github.com/giampaolo/psutil/issues/2404
.. _2405: https://github.com/giampaolo/psutil/issues/2405
.. _2406: https://github.com/giampaolo/psutil/issues/2406
.. _2407: https://github.com/giampaolo/psutil/issues/2407
.. _2408: https://github.com/giampaolo/psutil/issues/2408
.. _2409: https://github.com/giampaolo/psutil/issues/2409
.. _2410: https://github.com/giampaolo/psutil/issues/2410
.. _2411: https://github.com/giampaolo/psutil/issues/2411
.. _2412: https://github.com/giampaolo/psutil/issues/2412
.. _2413: https://github.com/giampaolo/psutil/issues/2413
.. _2414: https://github.com/giampaolo/psutil/issues/2414
.. _2415: https://github.com/giampaolo/psutil/issues/2415
.. _2416: https://github.com/giampaolo/psutil/issues/2416
.. _2417: https://github.com/giampaolo/psutil/issues/2417
.. _2418: https://github.com/giampaolo/psutil/issues/2418
.. _2419: https://github.com/giampaolo/psutil/issues/2419
.. _2420: https://github.com/giampaolo/psutil/issues/2420
.. _2421: https://github.com/giampaolo/psutil/issues/2421
.. _2422: https://github.com/giampaolo/psutil/issues/2422
.. _2423: https://github.com/giampaolo/psutil/issues/2423
.. _2424: https://github.com/giampaolo/psutil/issues/2424
.. _2425: https://github.com/giampaolo/psutil/issues/2425
.. _2426: https://github.com/giampaolo/psutil/issues/2426
.. _2427: https://github.com/giampaolo/psutil/issues/2427
.. _2428: https://github.com/giampaolo/psutil/issues/2428
.. _2429: https://github.com/giampaolo/psutil/issues/2429
.. _2430: https://github.com/giampaolo/psutil/issues/2430
.. _2431: https://github.com/giampaolo/psutil/issues/2431
.. _2432: https://github.com/giampaolo/psutil/issues/2432
.. _2433: https://github.com/giampaolo/psutil/issues/2433
.. _2434: https://github.com/giampaolo/psutil/issues/2434
.. _2435: https://github.com/giampaolo/psutil/issues/2435
.. _2436: https://github.com/giampaolo/psutil/issues/2436
.. _2437: https://github.com/giampaolo/psutil/issues/2437
.. _2438: https://github.com/giampaolo/psutil/issues/2438
.. _2439: https://github.com/giampaolo/psutil/issues/2439
.. _2440: https://github.com/giampaolo/psutil/issues/2440
.. _2441: https://github.com/giampaolo/psutil/issues/2441
.. _2442: https://github.com/giampaolo/psutil/issues/2442
.. _2443: https://github.com/giampaolo/psutil/issues/2443
.. _2444: https://github.com/giampaolo/psutil/issues/2444
.. _2445: https://github.com/giampaolo/psutil/issues/2445
.. _2446: https://github.com/giampaolo/psutil/issues/2446
.. _2447: https://github.com/giampaolo/psutil/issues/2447
.. _2448: https://github.com/giampaolo/psutil/issues/2448
.. _2449: https://github.com/giampaolo/psutil/issues/2449
.. _2450: https://github.com/giampaolo/psutil/issues/2450
.. _2451: https://github.com/giampaolo/psutil/issues/2451
.. _2452: https://github.com/giampaolo/psutil/issues/2452
.. _2453: https://github.com/giampaolo/psutil/issues/2453
.. _2454: https://github.com/giampaolo/psutil/issues/2454
.. _2455: https://github.com/giampaolo/psutil/issues/2455
.. _2456: https://github.com/giampaolo/psutil/issues/2456
.. _2457: https://github.com/giampaolo/psutil/issues/2457
.. _2458: https://github.com/giampaolo/psutil/issues/2458
.. _2459: https://github.com/giampaolo/psutil/issues/2459
.. _2460: https://github.com/giampaolo/psutil/issues/2460
.. _2461: https://github.com/giampaolo/psutil/issues/2461
.. _2462: https://github.com/giampaolo/psutil/issues/2462
.. _2463: https://github.com/giampaolo/psutil/issues/2463
.. _2464: https://github.com/giampaolo/psutil/issues/2464
.. _2465: https://github.com/giampaolo/psutil/issues/2465
.. _2466: https://github.com/giampaolo/psutil/issues/2466
.. _2467: https://github.com/giampaolo/psutil/issues/2467
.. _2468: https://github.com/giampaolo/psutil/issues/2468
.. _2469: https://github.com/giampaolo/psutil/issues/2469
.. _2470: https://github.com/giampaolo/psutil/issues/2470
.. _2471: https://github.com/giampaolo/psutil/issues/2471
.. _2472: https://github.com/giampaolo/psutil/issues/2472
.. _2473: https://github.com/giampaolo/psutil/issues/2473
.. _2474: https://github.com/giampaolo/psutil/issues/2474
.. _2475: https://github.com/giampaolo/psutil/issues/2475
.. _2476: https://github.com/giampaolo/psutil/issues/2476
.. _2477: https://github.com/giampaolo/psutil/issues/2477
.. _2478: https://github.com/giampaolo/psutil/issues/2478
.. _2479: https://github.com/giampaolo/psutil/issues/2479
.. _2480: https://github.com/giampaolo/psutil/issues/2480
.. _2481: https://github.com/giampaolo/psutil/issues/2481
.. _2482: https://github.com/giampaolo/psutil/issues/2482
.. _2483: https://github.com/giampaolo/psutil/issues/2483
.. _2484: https://github.com/giampaolo/psutil/issues/2484
.. _2485: https://github.com/giampaolo/psutil/issues/2485
.. _2486: https://github.com/giampaolo/psutil/issues/2486
.. _2487: https://github.com/giampaolo/psutil/issues/2487
.. _2488: https://github.com/giampaolo/psutil/issues/2488
.. _2489: https://github.com/giampaolo/psutil/issues/2489
.. _2490: https://github.com/giampaolo/psutil/issues/2490
.. _2491: https://github.com/giampaolo/psutil/issues/2491
.. _2492: https://github.com/giampaolo/psutil/issues/2492
.. _2493: https://github.com/giampaolo/psutil/issues/2493
.. _2494: https://github.com/giampaolo/psutil/issues/2494
.. _2495: https://github.com/giampaolo/psutil/issues/2495
.. _2496: https://github.com/giampaolo/psutil/issues/2496
.. _2497: https://github.com/giampaolo/psutil/issues/2497
.. _2498: https://github.com/giampaolo/psutil/issues/2498
.. _2499: https://github.com/giampaolo/psutil/issues/2499
.. _2500: https://github.com/giampaolo/psutil/issues/2500
.. _2501: https://github.com/giampaolo/psutil/issues/2501
.. _2502: https://github.com/giampaolo/psutil/issues/2502
.. _2503: https://github.com/giampaolo/psutil/issues/2503
.. _2504: https://github.com/giampaolo/psutil/issues/2504
.. _2505: https://github.com/giampaolo/psutil/issues/2505
.. _2506: https://github.com/giampaolo/psutil/issues/2506
.. _2507: https://github.com/giampaolo/psutil/issues/2507
.. _2508: https://github.com/giampaolo/psutil/issues/2508
.. _2509: https://github.com/giampaolo/psutil/issues/2509
.. _2510: https://github.com/giampaolo/psutil/issues/2510
.. _2511: https://github.com/giampaolo/psutil/issues/2511
.. _2512: https://github.com/giampaolo/psutil/issues/2512
.. _2513: https://github.com/giampaolo/psutil/issues/2513
.. _2514: https://github.com/giampaolo/psutil/issues/2514
.. _2515: https://github.com/giampaolo/psutil/issues/2515
.. _2516: https://github.com/giampaolo/psutil/issues/2516
.. _2517: https://github.com/giampaolo/psutil/issues/2517
.. _2518: https://github.com/giampaolo/psutil/issues/2518
.. _2519: https://github.com/giampaolo/psutil/issues/2519
.. _2520: https://github.com/giampaolo/psutil/issues/2520
.. _2521: https://github.com/giampaolo/psutil/issues/2521
.. _2522: https://github.com/giampaolo/psutil/issues/2522
.. _2523: https://github.com/giampaolo/psutil/issues/2523
.. _2524: https://github.com/giampaolo/psutil/issues/2524
.. _2525: https://github.com/giampaolo/psutil/issues/2525
.. _2526: https://github.com/giampaolo/psutil/issues/2526
.. _2527: https://github.com/giampaolo/psutil/issues/2527
.. _2528: https://github.com/giampaolo/psutil/issues/2528
.. _2529: https://github.com/giampaolo/psutil/issues/2529
.. _2530: https://github.com/giampaolo/psutil/issues/2530
.. _2531: https://github.com/giampaolo/psutil/issues/2531
.. _2532: https://github.com/giampaolo/psutil/issues/2532
.. _2533: https://github.com/giampaolo/psutil/issues/2533
.. _2534: https://github.com/giampaolo/psutil/issues/2534
.. _2535: https://github.com/giampaolo/psutil/issues/2535
.. _2536: https://github.com/giampaolo/psutil/issues/2536
.. _2537: https://github.com/giampaolo/psutil/issues/2537
.. _2538: https://github.com/giampaolo/psutil/issues/2538
.. _2539: https://github.com/giampaolo/psutil/issues/2539
.. _2540: https://github.com/giampaolo/psutil/issues/2540
.. _2541: https://github.com/giampaolo/psutil/issues/2541
.. _2542: https://github.com/giampaolo/psutil/issues/2542
.. _2543: https://github.com/giampaolo/psutil/issues/2543
.. _2544: https://github.com/giampaolo/psutil/issues/2544
.. _2545: https://github.com/giampaolo/psutil/issues/2545
.. _2546: https://github.com/giampaolo/psutil/issues/2546
.. _2547: https://github.com/giampaolo/psutil/issues/2547
.. _2548: https://github.com/giampaolo/psutil/issues/2548
.. _2549: https://github.com/giampaolo/psutil/issues/2549
.. _2550: https://github.com/giampaolo/psutil/issues/2550
.. _2551: https://github.com/giampaolo/psutil/issues/2551
.. _2552: https://github.com/giampaolo/psutil/issues/2552
.. _2553: https://github.com/giampaolo/psutil/issues/2553
.. _2554: https://github.com/giampaolo/psutil/issues/2554
.. _2555: https://github.com/giampaolo/psutil/issues/2555
.. _2556: https://github.com/giampaolo/psutil/issues/2556
.. _2557: https://github.com/giampaolo/psutil/issues/2557
.. _2558: https://github.com/giampaolo/psutil/issues/2558
.. _2559: https://github.com/giampaolo/psutil/issues/2559
.. _2560: https://github.com/giampaolo/psutil/issues/2560
.. _2561: https://github.com/giampaolo/psutil/issues/2561
.. _2562: https://github.com/giampaolo/psutil/issues/2562
.. _2563: https://github.com/giampaolo/psutil/issues/2563
.. _2564: https://github.com/giampaolo/psutil/issues/2564
.. _2565: https://github.com/giampaolo/psutil/issues/2565
.. _2566: https://github.com/giampaolo/psutil/issues/2566
.. _2567: https://github.com/giampaolo/psutil/issues/2567
.. _2568: https://github.com/giampaolo/psutil/issues/2568
.. _2569: https://github.com/giampaolo/psutil/issues/2569
.. _2570: https://github.com/giampaolo/psutil/issues/2570
.. _2571: https://github.com/giampaolo/psutil/issues/2571
.. _2572: https://github.com/giampaolo/psutil/issues/2572
.. _2573: https://github.com/giampaolo/psutil/issues/2573
.. _2574: https://github.com/giampaolo/psutil/issues/2574
.. _2575: https://github.com/giampaolo/psutil/issues/2575
.. _2576: https://github.com/giampaolo/psutil/issues/2576
.. _2577: https://github.com/giampaolo/psutil/issues/2577
.. _2578: https://github.com/giampaolo/psutil/issues/2578
.. _2579: https://github.com/giampaolo/psutil/issues/2579
.. _2580: https://github.com/giampaolo/psutil/issues/2580
.. _2581: https://github.com/giampaolo/psutil/issues/2581
.. _2582: https://github.com/giampaolo/psutil/issues/2582
.. _2583: https://github.com/giampaolo/psutil/issues/2583
.. _2584: https://github.com/giampaolo/psutil/issues/2584
.. _2585: https://github.com/giampaolo/psutil/issues/2585
.. _2586: https://github.com/giampaolo/psutil/issues/2586
.. _2587: https://github.com/giampaolo/psutil/issues/2587
.. _2588: https://github.com/giampaolo/psutil/issues/2588
.. _2589: https://github.com/giampaolo/psutil/issues/2589
.. _2590: https://github.com/giampaolo/psutil/issues/2590
.. _2591: https://github.com/giampaolo/psutil/issues/2591
.. _2592: https://github.com/giampaolo/psutil/issues/2592
.. _2593: https://github.com/giampaolo/psutil/issues/2593
.. _2594: https://github.com/giampaolo/psutil/issues/2594
.. _2595: https://github.com/giampaolo/psutil/issues/2595
.. _2596: https://github.com/giampaolo/psutil/issues/2596
.. _2597: https://github.com/giampaolo/psutil/issues/2597
.. _2598: https://github.com/giampaolo/psutil/issues/2598
.. _2599: https://github.com/giampaolo/psutil/issues/2599
.. _2600: https://github.com/giampaolo/psutil/issues/2600
.. _2601: https://github.com/giampaolo/psutil/issues/2601
.. _2602: https://github.com/giampaolo/psutil/issues/2602
.. _2603: https://github.com/giampaolo/psutil/issues/2603
.. _2604: https://github.com/giampaolo/psutil/issues/2604
.. _2605: https://github.com/giampaolo/psutil/issues/2605
.. _2606: https://github.com/giampaolo/psutil/issues/2606
.. _2607: https://github.com/giampaolo/psutil/issues/2607
.. _2608: https://github.com/giampaolo/psutil/issues/2608
.. _2609: https://github.com/giampaolo/psutil/issues/2609
.. _2610: https://github.com/giampaolo/psutil/issues/2610
.. _2611: https://github.com/giampaolo/psutil/issues/2611
.. _2612: https://github.com/giampaolo/psutil/issues/2612
.. _2613: https://github.com/giampaolo/psutil/issues/2613
.. _2614: https://github.com/giampaolo/psutil/issues/2614
.. _2615: https://github.com/giampaolo/psutil/issues/2615
.. _2616: https://github.com/giampaolo/psutil/issues/2616
.. _2617: https://github.com/giampaolo/psutil/issues/2617
.. _2618: https://github.com/giampaolo/psutil/issues/2618
.. _2619: https://github.com/giampaolo/psutil/issues/2619
.. _2620: https://github.com/giampaolo/psutil/issues/2620
.. _2621: https://github.com/giampaolo/psutil/issues/2621
.. _2622: https://github.com/giampaolo/psutil/issues/2622
.. _2623: https://github.com/giampaolo/psutil/issues/2623
.. _2624: https://github.com/giampaolo/psutil/issues/2624
.. _2625: https://github.com/giampaolo/psutil/issues/2625
.. _2626: https://github.com/giampaolo/psutil/issues/2626
.. _2627: https://github.com/giampaolo/psutil/issues/2627
.. _2628: https://github.com/giampaolo/psutil/issues/2628
.. _2629: https://github.com/giampaolo/psutil/issues/2629
.. _2630: https://github.com/giampaolo/psutil/issues/2630
.. _2631: https://github.com/giampaolo/psutil/issues/2631
.. _2632: https://github.com/giampaolo/psutil/issues/2632
.. _2633: https://github.com/giampaolo/psutil/issues/2633
.. _2634: https://github.com/giampaolo/psutil/issues/2634
.. _2635: https://github.com/giampaolo/psutil/issues/2635
.. _2636: https://github.com/giampaolo/psutil/issues/2636
.. _2637: https://github.com/giampaolo/psutil/issues/2637
.. _2638: https://github.com/giampaolo/psutil/issues/2638
.. _2639: https://github.com/giampaolo/psutil/issues/2639
.. _2640: https://github.com/giampaolo/psutil/issues/2640
.. _2641: https://github.com/giampaolo/psutil/issues/2641
.. _2642: https://github.com/giampaolo/psutil/issues/2642
.. _2643: https://github.com/giampaolo/psutil/issues/2643
.. _2644: https://github.com/giampaolo/psutil/issues/2644
.. _2645: https://github.com/giampaolo/psutil/issues/2645
.. _2646: https://github.com/giampaolo/psutil/issues/2646
.. _2647: https://github.com/giampaolo/psutil/issues/2647
.. _2648: https://github.com/giampaolo/psutil/issues/2648
.. _2649: https://github.com/giampaolo/psutil/issues/2649
.. _2650: https://github.com/giampaolo/psutil/issues/2650
.. _2651: https://github.com/giampaolo/psutil/issues/2651
.. _2652: https://github.com/giampaolo/psutil/issues/2652
.. _2653: https://github.com/giampaolo/psutil/issues/2653
.. _2654: https://github.com/giampaolo/psutil/issues/2654
.. _2655: https://github.com/giampaolo/psutil/issues/2655
.. _2656: https://github.com/giampaolo/psutil/issues/2656
.. _2657: https://github.com/giampaolo/psutil/issues/2657
.. _2658: https://github.com/giampaolo/psutil/issues/2658
.. _2659: https://github.com/giampaolo/psutil/issues/2659
.. _2660: https://github.com/giampaolo/psutil/issues/2660
.. _2661: https://github.com/giampaolo/psutil/issues/2661
.. _2662: https://github.com/giampaolo/psutil/issues/2662
.. _2663: https://github.com/giampaolo/psutil/issues/2663
.. _2664: https://github.com/giampaolo/psutil/issues/2664
.. _2665: https://github.com/giampaolo/psutil/issues/2665
.. _2666: https://github.com/giampaolo/psutil/issues/2666
.. _2667: https://github.com/giampaolo/psutil/issues/2667
.. _2668: https://github.com/giampaolo/psutil/issues/2668
.. _2669: https://github.com/giampaolo/psutil/issues/2669
.. _2670: https://github.com/giampaolo/psutil/issues/2670
.. _2671: https://github.com/giampaolo/psutil/issues/2671
.. _2672: https://github.com/giampaolo/psutil/issues/2672
.. _2673: https://github.com/giampaolo/psutil/issues/2673
.. _2674: https://github.com/giampaolo/psutil/issues/2674
.. _2675: https://github.com/giampaolo/psutil/issues/2675
.. _2676: https://github.com/giampaolo/psutil/issues/2676
.. _2677: https://github.com/giampaolo/psutil/issues/2677
.. _2678: https://github.com/giampaolo/psutil/issues/2678
.. _2679: https://github.com/giampaolo/psutil/issues/2679
.. _2680: https://github.com/giampaolo/psutil/issues/2680
.. _2681: https://github.com/giampaolo/psutil/issues/2681
.. _2682: https://github.com/giampaolo/psutil/issues/2682
.. _2683: https://github.com/giampaolo/psutil/issues/2683
.. _2684: https://github.com/giampaolo/psutil/issues/2684
.. _2685: https://github.com/giampaolo/psutil/issues/2685
.. _2686: https://github.com/giampaolo/psutil/issues/2686
.. _2687: https://github.com/giampaolo/psutil/issues/2687
.. _2688: https://github.com/giampaolo/psutil/issues/2688
.. _2689: https://github.com/giampaolo/psutil/issues/2689
.. _2690: https://github.com/giampaolo/psutil/issues/2690
.. _2691: https://github.com/giampaolo/psutil/issues/2691
.. _2692: https://github.com/giampaolo/psutil/issues/2692
.. _2693: https://github.com/giampaolo/psutil/issues/2693
.. _2694: https://github.com/giampaolo/psutil/issues/2694
.. _2695: https://github.com/giampaolo/psutil/issues/2695
.. _2696: https://github.com/giampaolo/psutil/issues/2696
.. _2697: https://github.com/giampaolo/psutil/issues/2697
.. _2698: https://github.com/giampaolo/psutil/issues/2698
.. _2699: https://github.com/giampaolo/psutil/issues/2699
.. _2700: https://github.com/giampaolo/psutil/issues/2700
.. _2701: https://github.com/giampaolo/psutil/issues/2701
.. _2702: https://github.com/giampaolo/psutil/issues/2702
.. _2703: https://github.com/giampaolo/psutil/issues/2703
.. _2704: https://github.com/giampaolo/psutil/issues/2704
.. _2705: https://github.com/giampaolo/psutil/issues/2705
.. _2706: https://github.com/giampaolo/psutil/issues/2706
.. _2707: https://github.com/giampaolo/psutil/issues/2707
.. _2708: https://github.com/giampaolo/psutil/issues/2708
.. _2709: https://github.com/giampaolo/psutil/issues/2709
.. _2710: https://github.com/giampaolo/psutil/issues/2710
.. _2711: https://github.com/giampaolo/psutil/issues/2711
.. _2712: https://github.com/giampaolo/psutil/issues/2712
.. _2713: https://github.com/giampaolo/psutil/issues/2713
.. _2714: https://github.com/giampaolo/psutil/issues/2714
.. _2715: https://github.com/giampaolo/psutil/issues/2715
.. _2716: https://github.com/giampaolo/psutil/issues/2716
.. _2717: https://github.com/giampaolo/psutil/issues/2717
.. _2718: https://github.com/giampaolo/psutil/issues/2718
.. _2719: https://github.com/giampaolo/psutil/issues/2719
.. _2720: https://github.com/giampaolo/psutil/issues/2720
.. _2721: https://github.com/giampaolo/psutil/issues/2721
.. _2722: https://github.com/giampaolo/psutil/issues/2722
.. _2723: https://github.com/giampaolo/psutil/issues/2723
.. _2724: https://github.com/giampaolo/psutil/issues/2724
.. _2725: https://github.com/giampaolo/psutil/issues/2725
.. _2726: https://github.com/giampaolo/psutil/issues/2726
.. _2727: https://github.com/giampaolo/psutil/issues/2727
.. _2728: https://github.com/giampaolo/psutil/issues/2728
.. _2729: https://github.com/giampaolo/psutil/issues/2729
.. _2730: https://github.com/giampaolo/psutil/issues/2730
.. _2731: https://github.com/giampaolo/psutil/issues/2731
.. _2732: https://github.com/giampaolo/psutil/issues/2732
.. _2733: https://github.com/giampaolo/psutil/issues/2733
.. _2734: https://github.com/giampaolo/psutil/issues/2734
.. _2735: https://github.com/giampaolo/psutil/issues/2735
.. _2736: https://github.com/giampaolo/psutil/issues/2736
.. _2737: https://github.com/giampaolo/psutil/issues/2737
.. _2738: https://github.com/giampaolo/psutil/issues/2738
.. _2739: https://github.com/giampaolo/psutil/issues/2739
.. _2740: https://github.com/giampaolo/psutil/issues/2740
.. _2741: https://github.com/giampaolo/psutil/issues/2741
.. _2742: https://github.com/giampaolo/psutil/issues/2742
.. _2743: https://github.com/giampaolo/psutil/issues/2743
.. _2744: https://github.com/giampaolo/psutil/issues/2744
.. _2745: https://github.com/giampaolo/psutil/issues/2745
.. _2746: https://github.com/giampaolo/psutil/issues/2746
.. _2747: https://github.com/giampaolo/psutil/issues/2747
.. _2748: https://github.com/giampaolo/psutil/issues/2748
.. _2749: https://github.com/giampaolo/psutil/issues/2749
.. _2750: https://github.com/giampaolo/psutil/issues/2750
.. _2751: https://github.com/giampaolo/psutil/issues/2751
.. _2752: https://github.com/giampaolo/psutil/issues/2752
.. _2753: https://github.com/giampaolo/psutil/issues/2753
.. _2754: https://github.com/giampaolo/psutil/issues/2754
.. _2755: https://github.com/giampaolo/psutil/issues/2755
.. _2756: https://github.com/giampaolo/psutil/issues/2756
.. _2757: https://github.com/giampaolo/psutil/issues/2757
.. _2758: https://github.com/giampaolo/psutil/issues/2758
.. _2759: https://github.com/giampaolo/psutil/issues/2759
.. _2760: https://github.com/giampaolo/psutil/issues/2760
.. _2761: https://github.com/giampaolo/psutil/issues/2761
.. _2762: https://github.com/giampaolo/psutil/issues/2762
.. _2763: https://github.com/giampaolo/psutil/issues/2763
.. _2764: https://github.com/giampaolo/psutil/issues/2764
.. _2765: https://github.com/giampaolo/psutil/issues/2765
.. _2766: https://github.com/giampaolo/psutil/issues/2766
.. _2767: https://github.com/giampaolo/psutil/issues/2767
.. _2768: https://github.com/giampaolo/psutil/issues/2768
.. _2769: https://github.com/giampaolo/psutil/issues/2769
.. _2770: https://github.com/giampaolo/psutil/issues/2770
.. _2771: https://github.com/giampaolo/psutil/issues/2771
.. _2772: https://github.com/giampaolo/psutil/issues/2772
.. _2773: https://github.com/giampaolo/psutil/issues/2773
.. _2774: https://github.com/giampaolo/psutil/issues/2774
.. _2775: https://github.com/giampaolo/psutil/issues/2775
.. _2776: https://github.com/giampaolo/psutil/issues/2776
.. _2777: https://github.com/giampaolo/psutil/issues/2777
.. _2778: https://github.com/giampaolo/psutil/issues/2778
.. _2779: https://github.com/giampaolo/psutil/issues/2779
.. _2780: https://github.com/giampaolo/psutil/issues/2780
.. _2781: https://github.com/giampaolo/psutil/issues/2781
.. _2782: https://github.com/giampaolo/psutil/issues/2782
.. _2783: https://github.com/giampaolo/psutil/issues/2783
.. _2784: https://github.com/giampaolo/psutil/issues/2784
.. _2785: https://github.com/giampaolo/psutil/issues/2785
.. _2786: https://github.com/giampaolo/psutil/issues/2786
.. _2787: https://github.com/giampaolo/psutil/issues/2787
.. _2788: https://github.com/giampaolo/psutil/issues/2788
.. _2789: https://github.com/giampaolo/psutil/issues/2789
.. _2790: https://github.com/giampaolo/psutil/issues/2790
.. _2791: https://github.com/giampaolo/psutil/issues/2791
.. _2792: https://github.com/giampaolo/psutil/issues/2792
.. _2793: https://github.com/giampaolo/psutil/issues/2793
.. _2794: https://github.com/giampaolo/psutil/issues/2794
.. _2795: https://github.com/giampaolo/psutil/issues/2795
.. _2796: https://github.com/giampaolo/psutil/issues/2796
.. _2797: https://github.com/giampaolo/psutil/issues/2797
.. _2798: https://github.com/giampaolo/psutil/issues/2798
.. _2799: https://github.com/giampaolo/psutil/issues/2799
.. _2800: https://github.com/giampaolo/psutil/issues/2800
.. _2801: https://github.com/giampaolo/psutil/issues/2801
.. _2802: https://github.com/giampaolo/psutil/issues/2802
.. _2803: https://github.com/giampaolo/psutil/issues/2803
.. _2804: https://github.com/giampaolo/psutil/issues/2804
.. _2805: https://github.com/giampaolo/psutil/issues/2805
.. _2806: https://github.com/giampaolo/psutil/issues/2806
.. _2807: https://github.com/giampaolo/psutil/issues/2807
.. _2808: https://github.com/giampaolo/psutil/issues/2808
.. _2809: https://github.com/giampaolo/psutil/issues/2809
.. _2810: https://github.com/giampaolo/psutil/issues/2810
.. _2811: https://github.com/giampaolo/psutil/issues/2811
.. _2812: https://github.com/giampaolo/psutil/issues/2812
.. _2813: https://github.com/giampaolo/psutil/issues/2813
.. _2814: https://github.com/giampaolo/psutil/issues/2814
.. _2815: https://github.com/giampaolo/psutil/issues/2815
.. _2816: https://github.com/giampaolo/psutil/issues/2816
.. _2817: https://github.com/giampaolo/psutil/issues/2817
.. _2818: https://github.com/giampaolo/psutil/issues/2818
.. _2819: https://github.com/giampaolo/psutil/issues/2819
.. _2820: https://github.com/giampaolo/psutil/issues/2820
.. _2821: https://github.com/giampaolo/psutil/issues/2821
.. _2822: https://github.com/giampaolo/psutil/issues/2822
.. _2823: https://github.com/giampaolo/psutil/issues/2823
.. _2824: https://github.com/giampaolo/psutil/issues/2824
.. _2825: https://github.com/giampaolo/psutil/issues/2825
.. _2826: https://github.com/giampaolo/psutil/issues/2826
.. _2827: https://github.com/giampaolo/psutil/issues/2827
.. _2828: https://github.com/giampaolo/psutil/issues/2828
.. _2829: https://github.com/giampaolo/psutil/issues/2829
.. _2830: https://github.com/giampaolo/psutil/issues/2830
.. _2831: https://github.com/giampaolo/psutil/issues/2831
.. _2832: https://github.com/giampaolo/psutil/issues/2832
.. _2833: https://github.com/giampaolo/psutil/issues/2833
.. _2834: https://github.com/giampaolo/psutil/issues/2834
.. _2835: https://github.com/giampaolo/psutil/issues/2835
.. _2836: https://github.com/giampaolo/psutil/issues/2836
.. _2837: https://github.com/giampaolo/psutil/issues/2837
.. _2838: https://github.com/giampaolo/psutil/issues/2838
.. _2839: https://github.com/giampaolo/psutil/issues/2839
.. _2840: https://github.com/giampaolo/psutil/issues/2840
.. _2841: https://github.com/giampaolo/psutil/issues/2841
.. _2842: https://github.com/giampaolo/psutil/issues/2842
.. _2843: https://github.com/giampaolo/psutil/issues/2843
.. _2844: https://github.com/giampaolo/psutil/issues/2844
.. _2845: https://github.com/giampaolo/psutil/issues/2845
.. _2846: https://github.com/giampaolo/psutil/issues/2846
.. _2847: https://github.com/giampaolo/psutil/issues/2847
.. _2848: https://github.com/giampaolo/psutil/issues/2848
.. _2849: https://github.com/giampaolo/psutil/issues/2849
.. _2850: https://github.com/giampaolo/psutil/issues/2850
.. _2851: https://github.com/giampaolo/psutil/issues/2851
.. _2852: https://github.com/giampaolo/psutil/issues/2852
.. _2853: https://github.com/giampaolo/psutil/issues/2853
.. _2854: https://github.com/giampaolo/psutil/issues/2854
.. _2855: https://github.com/giampaolo/psutil/issues/2855
.. _2856: https://github.com/giampaolo/psutil/issues/2856
.. _2857: https://github.com/giampaolo/psutil/issues/2857
.. _2858: https://github.com/giampaolo/psutil/issues/2858
.. _2859: https://github.com/giampaolo/psutil/issues/2859
.. _2860: https://github.com/giampaolo/psutil/issues/2860
.. _2861: https://github.com/giampaolo/psutil/issues/2861
.. _2862: https://github.com/giampaolo/psutil/issues/2862
.. _2863: https://github.com/giampaolo/psutil/issues/2863
.. _2864: https://github.com/giampaolo/psutil/issues/2864
.. _2865: https://github.com/giampaolo/psutil/issues/2865
.. _2866: https://github.com/giampaolo/psutil/issues/2866
.. _2867: https://github.com/giampaolo/psutil/issues/2867
.. _2868: https://github.com/giampaolo/psutil/issues/2868
.. _2869: https://github.com/giampaolo/psutil/issues/2869
.. _2870: https://github.com/giampaolo/psutil/issues/2870
.. _2871: https://github.com/giampaolo/psutil/issues/2871
.. _2872: https://github.com/giampaolo/psutil/issues/2872
.. _2873: https://github.com/giampaolo/psutil/issues/2873
.. _2874: https://github.com/giampaolo/psutil/issues/2874
.. _2875: https://github.com/giampaolo/psutil/issues/2875
.. _2876: https://github.com/giampaolo/psutil/issues/2876
.. _2877: https://github.com/giampaolo/psutil/issues/2877
.. _2878: https://github.com/giampaolo/psutil/issues/2878
.. _2879: https://github.com/giampaolo/psutil/issues/2879
.. _2880: https://github.com/giampaolo/psutil/issues/2880
.. _2881: https://github.com/giampaolo/psutil/issues/2881
.. _2882: https://github.com/giampaolo/psutil/issues/2882
.. _2883: https://github.com/giampaolo/psutil/issues/2883
.. _2884: https://github.com/giampaolo/psutil/issues/2884
.. _2885: https://github.com/giampaolo/psutil/issues/2885
.. _2886: https://github.com/giampaolo/psutil/issues/2886
.. _2887: https://github.com/giampaolo/psutil/issues/2887
.. _2888: https://github.com/giampaolo/psutil/issues/2888
.. _2889: https://github.com/giampaolo/psutil/issues/2889
.. _2890: https://github.com/giampaolo/psutil/issues/2890
.. _2891: https://github.com/giampaolo/psutil/issues/2891
.. _2892: https://github.com/giampaolo/psutil/issues/2892
.. _2893: https://github.com/giampaolo/psutil/issues/2893
.. _2894: https://github.com/giampaolo/psutil/issues/2894
.. _2895: https://github.com/giampaolo/psutil/issues/2895
.. _2896: https://github.com/giampaolo/psutil/issues/2896
.. _2897: https://github.com/giampaolo/psutil/issues/2897
.. _2898: https://github.com/giampaolo/psutil/issues/2898
.. _2899: https://github.com/giampaolo/psutil/issues/2899
.. _2900: https://github.com/giampaolo/psutil/issues/2900
.. _2901: https://github.com/giampaolo/psutil/issues/2901
.. _2902: https://github.com/giampaolo/psutil/issues/2902
.. _2903: https://github.com/giampaolo/psutil/issues/2903
.. _2904: https://github.com/giampaolo/psutil/issues/2904
.. _2905: https://github.com/giampaolo/psutil/issues/2905
.. _2906: https://github.com/giampaolo/psutil/issues/2906
.. _2907: https://github.com/giampaolo/psutil/issues/2907
.. _2908: https://github.com/giampaolo/psutil/issues/2908
.. _2909: https://github.com/giampaolo/psutil/issues/2909
.. _2910: https://github.com/giampaolo/psutil/issues/2910
.. _2911: https://github.com/giampaolo/psutil/issues/2911
.. _2912: https://github.com/giampaolo/psutil/issues/2912
.. _2913: https://github.com/giampaolo/psutil/issues/2913
.. _2914: https://github.com/giampaolo/psutil/issues/2914
.. _2915: https://github.com/giampaolo/psutil/issues/2915
.. _2916: https://github.com/giampaolo/psutil/issues/2916
.. _2917: https://github.com/giampaolo/psutil/issues/2917
.. _2918: https://github.com/giampaolo/psutil/issues/2918
.. _2919: https://github.com/giampaolo/psutil/issues/2919
.. _2920: https://github.com/giampaolo/psutil/issues/2920
.. _2921: https://github.com/giampaolo/psutil/issues/2921
.. _2922: https://github.com/giampaolo/psutil/issues/2922
.. _2923: https://github.com/giampaolo/psutil/issues/2923
.. _2924: https://github.com/giampaolo/psutil/issues/2924
.. _2925: https://github.com/giampaolo/psutil/issues/2925
.. _2926: https://github.com/giampaolo/psutil/issues/2926
.. _2927: https://github.com/giampaolo/psutil/issues/2927
.. _2928: https://github.com/giampaolo/psutil/issues/2928
.. _2929: https://github.com/giampaolo/psutil/issues/2929
.. _2930: https://github.com/giampaolo/psutil/issues/2930
.. _2931: https://github.com/giampaolo/psutil/issues/2931
.. _2932: https://github.com/giampaolo/psutil/issues/2932
.. _2933: https://github.com/giampaolo/psutil/issues/2933
.. _2934: https://github.com/giampaolo/psutil/issues/2934
.. _2935: https://github.com/giampaolo/psutil/issues/2935
.. _2936: https://github.com/giampaolo/psutil/issues/2936
.. _2937: https://github.com/giampaolo/psutil/issues/2937
.. _2938: https://github.com/giampaolo/psutil/issues/2938
.. _2939: https://github.com/giampaolo/psutil/issues/2939
.. _2940: https://github.com/giampaolo/psutil/issues/2940
.. _2941: https://github.com/giampaolo/psutil/issues/2941
.. _2942: https://github.com/giampaolo/psutil/issues/2942
.. _2943: https://github.com/giampaolo/psutil/issues/2943
.. _2944: https://github.com/giampaolo/psutil/issues/2944
.. _2945: https://github.com/giampaolo/psutil/issues/2945
.. _2946: https://github.com/giampaolo/psutil/issues/2946
.. _2947: https://github.com/giampaolo/psutil/issues/2947
.. _2948: https://github.com/giampaolo/psutil/issues/2948
.. _2949: https://github.com/giampaolo/psutil/issues/2949
.. _2950: https://github.com/giampaolo/psutil/issues/2950
.. _2951: https://github.com/giampaolo/psutil/issues/2951
.. _2952: https://github.com/giampaolo/psutil/issues/2952
.. _2953: https://github.com/giampaolo/psutil/issues/2953
.. _2954: https://github.com/giampaolo/psutil/issues/2954
.. _2955: https://github.com/giampaolo/psutil/issues/2955
.. _2956: https://github.com/giampaolo/psutil/issues/2956
.. _2957: https://github.com/giampaolo/psutil/issues/2957
.. _2958: https://github.com/giampaolo/psutil/issues/2958
.. _2959: https://github.com/giampaolo/psutil/issues/2959
.. _2960: https://github.com/giampaolo/psutil/issues/2960
.. _2961: https://github.com/giampaolo/psutil/issues/2961
.. _2962: https://github.com/giampaolo/psutil/issues/2962
.. _2963: https://github.com/giampaolo/psutil/issues/2963
.. _2964: https://github.com/giampaolo/psutil/issues/2964
.. _2965: https://github.com/giampaolo/psutil/issues/2965
.. _2966: https://github.com/giampaolo/psutil/issues/2966
.. _2967: https://github.com/giampaolo/psutil/issues/2967
.. _2968: https://github.com/giampaolo/psutil/issues/2968
.. _2969: https://github.com/giampaolo/psutil/issues/2969
.. _2970: https://github.com/giampaolo/psutil/issues/2970
.. _2971: https://github.com/giampaolo/psutil/issues/2971
.. _2972: https://github.com/giampaolo/psutil/issues/2972
.. _2973: https://github.com/giampaolo/psutil/issues/2973
.. _2974: https://github.com/giampaolo/psutil/issues/2974
.. _2975: https://github.com/giampaolo/psutil/issues/2975
.. _2976: https://github.com/giampaolo/psutil/issues/2976
.. _2977: https://github.com/giampaolo/psutil/issues/2977
.. _2978: https://github.com/giampaolo/psutil/issues/2978
.. _2979: https://github.com/giampaolo/psutil/issues/2979
.. _2980: https://github.com/giampaolo/psutil/issues/2980
.. _2981: https://github.com/giampaolo/psutil/issues/2981
.. _2982: https://github.com/giampaolo/psutil/issues/2982
.. _2983: https://github.com/giampaolo/psutil/issues/2983
.. _2984: https://github.com/giampaolo/psutil/issues/2984
.. _2985: https://github.com/giampaolo/psutil/issues/2985
.. _2986: https://github.com/giampaolo/psutil/issues/2986
.. _2987: https://github.com/giampaolo/psutil/issues/2987
.. _2988: https://github.com/giampaolo/psutil/issues/2988
.. _2989: https://github.com/giampaolo/psutil/issues/2989
.. _2990: https://github.com/giampaolo/psutil/issues/2990
.. _2991: https://github.com/giampaolo/psutil/issues/2991
.. _2992: https://github.com/giampaolo/psutil/issues/2992
.. _2993: https://github.com/giampaolo/psutil/issues/2993
.. _2994: https://github.com/giampaolo/psutil/issues/2994
.. _2995: https://github.com/giampaolo/psutil/issues/2995
.. _2996: https://github.com/giampaolo/psutil/issues/2996
.. _2997: https://github.com/giampaolo/psutil/issues/2997
.. _2998: https://github.com/giampaolo/psutil/issues/2998
.. _2999: https://github.com/giampaolo/psutil/issues/2999
.. _3000: https://github.com/giampaolo/psutil/issues/3000
