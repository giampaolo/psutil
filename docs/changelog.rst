.. currentmodule:: psutil

Changelog
=========

8.0.0 (IN DEVELOPMENT)
^^^^^^^^^^^^^^^^^^^^^^

**Compatibility notes**

 psutil 8.0 introduces breaking API changes and drops support for Python 3.6.
 See the :ref:`migration guide <migration-8.0>` if upgrading from 7.x.

**Enhancements**

Doc improvements (:gh:`2761`, :gh:`2757`, :gh:`2760`, :gh:`2745`, :gh:`2763`,
:gh:`2764`, :gh:`2767`, :gh:`2768`, :gh:`2769`, :gh:`2771`)

- Split docs from a single HTML file into multiple sections (API reference,
  install, etc.).

- Added new sections:

  - `/recipes <https://psutil.readthedocs.io/en/latest/credits.html>`__:
    show code samples
  - `/adoption <https://psutil.readthedocs.io/en/latest/adoption.html>`__:
    notable software using psutil
  - `/shell_equivalents <https://psutil.readthedocs.io/en/latest/shell_equivalents.html>`__:
    maps each psutil API to native CLI commands
  - `/install <https://psutil.readthedocs.io/en/latest/install.html>`__
    (was old ``INSTALL.rst`` in root dir)
  - `/credits <https://psutil.readthedocs.io/en/latest/credits.html>`__:
    list contributors and donors (was old ``CREDITS`` in root dir)
  - `/platform <https://psutil.readthedocs.io/en/latest/credits.html>`__:
    summary of OSes and architectures support
  - `/faq <https://psutil.readthedocs.io/en/latest/credits.html>`__:
    extended FAQ section.
  - `/migration <https://psutil.readthedocs.io/en/latest/migration.html>`__: a
    section explaining how to migrate to newer psutil versions that break
    backward compatibility.

- Usability:

  - Show a clickable COPY button to copy code snippets.
  - Show ``psutil.`` prefix for all APIs.
  - Use sphinx extension to validate Python code snippets syntax at build-time.

- Testing:

  - Replace ``rstcheck`` with ``sphinx-lint`` for RST linting.
  - Add custom script to detect dead reference links in ``.rst`` files.
  - Build doc as part of CI process.

- Greatly improved :func:`virtual_memory` doc.

Type hints / enums:

- :gh:`1946`: Add inline type hints to all public APIs in `psutil/__init__.py`.
  Type checkers (mypy, pyright, etc.) can now statically verify code that uses
  psutil. No runtime behavior is changed; the annotations are purely
  informational.
- :gh:`2751`: Convert all named tuples from ``collections.namedtuple`` to
  ``typing.NamedTuple`` classes with **type annotations**. This makes the
  classes self-documenting, effectively turning this module into a readable
  API reference.
- :gh:`2753`: Introduce enum classes (:class:`ProcessStatus`,
  :class:`ConnectionStatus`,
  :class:`ProcessIOPriority`, :class:`ProcessPriority`, :class:`ProcessRlimit`)
  grouping related constants. The individual top-level constants (e.g.
  ``psutil.STATUS_RUNNING``) remain the primary API, and are now aliases
  for the corresponding enum members.

- New APIs:

- :gh:`2729`: New :meth:`Process.page_faults` method, returning a ``(minor,
  major)`` namedtuple.
- Reorganization of process memory APIs (:gh:`2731`, :gh:`2736`, :gh:`2723`,
  :gh:`2733`).

  - Add new :meth:`Process.memory_info_ex` method, which extends
    :meth:`Process.memory_info` with platform-specific metrics:

    - Linux: *peak_rss*, *peak_vms*, *rss_anon*, *rss_file*, *rss_shmem*,
      *swap*, *hugetlb*
    - macOS: *peak_rss*, *rss_anon*, *rss_file*, *wired*, *compressed*,
      *phys_footprint*
    - Windows: *virtual*, *peak_virtual*

  - Add new :meth:`Process.memory_footprint` method, which returns *uss*,
    *pss* and *swap* metrics (what :meth:`Process.memory_full_info` used to
    return, which is now **deprecated**, see
    :ref:`migration guide <migration-8.0>`).

  - :meth:`Process.memory_info` named tuple changed:

    - BSD: added *peak_rss*.

    - Linux: *lib* and *dirty* removed (always 0 since Linux 2.6). Deprecated
      aliases returning 0 and emitting `DeprecationWarning` are kept.

    - macOS: *pfaults* and *pageins* removed with **no
      backward-compataliases**. Use :meth:`Process.page_faults` instead.

    - Windows: eliminated old aliases: *wset* → *rss*, *peak_wset* →
      *peak_rss*, *pagefile* / *private* → *vms*, *peak_pagefile* → *peak_vms*.
      At the same time *paged_pool*, *nonpaged_pool*, *peak_paged_pool*,
      *peak_nonpaged_pool* were moved to :meth:`Process.memory_info_ex`. All
      these old names still work but raise `DeprecationWarning`.
      See :ref:`migration guide <migration-8.0>`.

  - :meth:`Process.memory_full_info` is **deprecated**. Use the new
    :meth:`Process.memory_footprint` instead.
    See :ref:`migration guide <migration-8.0>`.

Others

- :gh:`2747`: the field order of the named tuple returned by :func:`cpu_times`
  has been normalized on all platforms, and the first 3 fields are now always
  ``user, system, idle``. See compatibility notes below.
- :gh:`2754`: standardize :func:`sensors_battery`'s `percent` so that it
  returns a `float` instead of `int` on all systems, not only Linux.
- :gh:`2765`: add a PR bot that uses Claude to summarize PR changes and update
  ``changelog.rst`` and ``credits.rst`` when commenting with /changelog.
- :gh:`2766`: remove remaining Python 2.7 compatibility shims from
  ``setup.py``, simplifying the build infrastructure.
- :gh:`2772`, [Windows]: :func:`cpu_times` ``interrupt`` field renamed to
  ``irq`` to match the field name used on Linux and BSD. ``interrupt`` still
  works but raises :exc:`DeprecationWarning`.
  See :ref:`migration guide <migration-8.0>`.

**Bug fixes**

- :gh:`2770`, [Linux]: fix :func:`cpu_count_cores` raising ``ValueError``
  on s390x architecture, where ``/proc/cpuinfo`` uses spaces before the
  colon separator instead of a tab.
- :gh:`2726`, [macOS]: :meth:`Process.num_ctx_switches` return an unusual
  high number due to a C type precision issue.
- :gh:`2411` [macOS]: :meth:`Process.cpu_times` and
  :meth:`Process.cpu_percent` calculation on macOS x86_64 (arm64 is fine) was
  highly inaccurate (41.67x lower).
- :gh:`2732`, [Linux]: net_if_duplex_speed: handle EBUSY from
  ioctl(SIOCETHTOOL).
- :gh:`2744`, [NetBSD]: fix possible double `free()` in :func:`swap_memory`.
- :gh:`2746`, [FreeBSD]: :meth:`Process.memory_maps`, `rss` and `private`
  fields, are erroneously reported in memory pages instead of bytes. Other
  platforms (Linux, macOS, Windows) return bytes.

7.2.3 — 2026-02-08
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`2715`, [Linux]: ``wait_pid_pidfd_open()`` (from :meth:`Process.wait`)
  crashes with ``EINVAL`` due to kernel race condition.

7.2.2 — 2026-01-28
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2705`: [Linux]: :meth:`Process.wait` now uses ``pidfd_open()`` +
  ``poll()`` for waiting, resulting in no busy loop and faster response times.
  Requires Linux >= 5.3 and Python >= 3.9. Falls back to traditional polling if
  unavailable.
- :gh:`2705`: [macOS], [BSD]: :meth:`Process.wait` now uses ``kqueue()`` for
  waiting, resulting in no busy loop and faster response times.

**Bug fixes**

- :gh:`2701`, [macOS]: fix compilation error on macOS < 10.7.  (patch by Sergey
  Fedorov)
- :gh:`2707`, [macOS]: fix potential memory leaks in error paths of
  `Process.memory_full_info()` and `Process.threads()`.
- :gh:`2708`, [macOS]: :meth:`Process.cmdline` and :meth:`Process.environ`
  may fail with ``OSError: [Errno 0] Undefined error`` (from
  ``sysctl(KERN_PROCARGS2)``). They now raise :exc:`AccessDenied` instead.

7.2.1 — 2025-12-29
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`2699`, [FreeBSD], [NetBSD]: :func:`heap_info` does not detect small
  allocations (<= 1K). In order to fix that, we now flush internal jemalloc
  cache before fetching the metrics.

7.2.0 — 2025-12-23
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1275`: new :func:`heap_info` and :func:`heap_trim` functions,
  providing direct access to the platform's native C heap allocator (glibc,
  mimalloc, libmalloc). Useful to create tools to detect memory leaks.
- :gh:`2403`, [Linux]: publish wheels for Linux musl.
- :gh:`2680`: unit tests are no longer installed / part of the distribution.
  They now live under `tests/` instead of `psutil/tests`.

**Bug fixes**

* :gh:`2684`, [FreeBSD], [critical]: compilation fails on FreeBSD 14 due to
  missing include.
* :gh:`2691`, [Windows]: fix memory leak in :func:`net_if_stats` due to
  missing ``Py_CLEAR``.

**Compatibility notes**

- :gh:`2680`: `import psutil.tests` no longer works (but it was never
  documented to begin with).

7.1.3 — 2025-11-02
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2667`: enforce `clang-format` on all C and header files. It is now the
  mandatory formatting style for all C sources.
- :gh:`2672`, [macOS], [BSD]: increase the chances to recognize zombie
  processes and raise the appropriate exception (:exc:`ZombieProcess`).
- :gh:`2676`, :gh:`2678`: replace unsafe `sprintf` / `snprintf` / `sprintf_s`
  calls with `str_format()`. Replace `strlcat` / `strlcpy` with safe `str_copy`
  / `str_append`. This unifies string handling across platforms and reduces
  unsafe usage of standard string functions, improving robustness.

**Bug fixes**

- :gh:`2674`, [Windows]: :func:`disk_usage` could truncate values on 32-bit
  platforms, potentially reporting incorrect total/free/used space for drives
  larger than 4GB.
- :gh:`2675`, [macOS]: :meth:`Process.status` incorrectly returns "running"
  for 99% of the processes.
- :gh:`2677`, [Windows]: fix MAC address string construction in
  :func:`net_if_addrs`. Previously, the MAC address buffer was incorrectly
  updated using a fixed increment and `sprintf_s`, which could overflow or
  misformat the string if the MAC length or formatting changed. Also, the
  final '\n' was inserted unnecessarily.
- :gh:`2679`, [OpenBSD], [NetBSD], [critical]: can't build due to C syntax
  error.

7.1.2 — 2025-10-25
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2657`: stop publishing prebuilt Linux and Windows wheels for 32-bit
  Python. 32-bit CPython is still supported, but psutil must now be built from
  source.
  :gh:`2565`: produce wheels for free-thread cPython 3.13 and 3.14 (patch by
  Lysandros Nikolaou)

**Bug fixes**

- :gh:`2650`, [macOS]: :meth:`Process.cmdline` and :meth:`Process.environ`
  may incorrectly raise :exc:`NoSuchProcess` instead of :exc:`ZombieProcess`.
- :gh:`2658`, [macOS]: double ``free()`` in :meth:`Process.environ` when it
  fails internally. This posed a risk of segfault.
- :gh:`2662`, [macOS]: massive C code cleanup to guard against possible
  segfaults which were (not so) sporadically spotted on CI.

**Compatibility notes**

- :gh:`2657`: stop publishing prebuilt Linux and Windows wheels for 32-bit
  Python.

7.1.1 — 2025-10-19
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2645`, [SunOS]: dropped support for SunOS 10.
- :gh:`2646`, [SunOS]: add CI test runner for SunOS.

**Bug fixes**

- :gh:`2641`, [SunOS]: cannot compile psutil from sources due to missing C
  include.
- :gh:`2357`, [SunOS]: :meth:`Process.cmdline` does not handle spaces
  properly. (patch by Ben Raz)

**Compatibility notes**

* :gh:`2645`: SunOS 10 is no longer supported.

7.1.0 — 2025-09-17
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2581`, [Windows]: publish ARM64 wheels.  (patch by Matthieu Darbois)
- :gh:`2571`, [FreeBSD]: Dropped support for FreeBSD 8 and earlier. FreeBSD 8
  was maintained from 2009 to 2013.
- :gh:`2575`: introduced `dprint` CLI tool to format .yml and .md files.

**Bug fixes**

- :gh:`2473`, [macOS]: Fix build issue on macOS 11 and lower.
- :gh:`2494`, [Windows]: All APIs dealing with paths, such as
  :meth:`Process.memory_maps`, :meth:`Process.exe` and
  :meth:`Process.open_files` does not properly handle UNC paths. Paths such
  as ``\\??\\C:\\Windows\\Temp`` and
  ``'\\Device\\HarddiskVolume1\\Windows\\Temp'`` are now converted to
  ``C:\\Windows\\Temp``.  (patch by Ben Peddell)
- :gh:`2506`, [Windows]: Windows service APIs had issues with unicode services
  using special characters in their name.
- :gh:`2514`, [Linux]: :meth:`Process.cwd` sometimes fail with
  `FileNotFoundError` due to a race condition.
- :gh:`2526`, [Linux]: :meth:`Process.create_time`, which is used to
  univocally identify a process over time, is subject to system clock updates,
  and as such can lead to :meth:`Process.is_running` returning a wrong
  result. A monotonic creation time is now used instead.  (patch by Jonathan
  Kohler)
- :gh:`2528`, [Linux]: :meth:`Process.children` may raise
  ``PermissionError``. It will now raise :exc:`AccessDenied` instead.
- :gh:`2540`, [macOS]: :func:`boot_time` is off by 45 seconds (C precision
  issue).
- :gh:`2541`, :gh:`2570`, :gh:`2578` [Linux], [macOS], [NetBSD]:
  :meth:`Process.create_time` does not reflect system clock updates.
- :gh:`2542`: if system clock is updated :meth:`Process.children` and
  :meth:`Process.parent` may not be able to return the right information.
- :gh:`2545`: [Illumos]: Fix handling of MIB2_UDP_ENTRY in
  :func:`net_connections`.
- :gh:`2552`, [Windows]: :func:`boot_time` didn't take into account the time
  spent during suspend / hibernation.
- :gh:`2560`, [Linux]: :meth:`Process.memory_maps` may crash with
  `IndexError` on RISCV64 due to a malformed `/proc/{PID}/smaps` file.  (patch
  by Julien Stephan)
- :gh:`2586`, [macOS], [CRITICAL]: fixed different places in C code which can
  trigger a segfault.
- :gh:`2604`, [Linux]: :func:`virtual_memory` "used" memory does not match
  recent versions of ``free`` CLI utility.  (patch by Isaac K. Ko)
- :gh:`2605`, [Linux]: :func:`sensors_battery` reports a negative amount for
  seconds left.
- :gh:`2607`, [Windows]: ``WindowsService.description()`` method may fail with
  ``ERROR_NOT_FOUND``. Now it returns an empty string instead.
- 2610:, [macOS], [CRITICAL]: fix :func:`cpu_freq` segfault on ARM
  architectures.

**Compatibility notes**

- :gh:`2571`: dropped support for FreeBSD 8 and earlier.

7.0.0 — 2025-02-13
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`669`, [Windows]: :func:`net_if_addrs` also returns the ``broadcast``
  address instead of ``None``.
- :gh:`2480`: Python 2.7 is no longer supported. Latest version supporting
  Python 2.7 is psutil 6.1.X. Install it with: ``pip2 install psutil==6.1.*``.
- :gh:`2490`: removed long deprecated ``Process.memory_info_ex()`` method. It
  was deprecated in psutil 4.0.0, released 8 years ago. Substitute is
  ``Process.memory_full_info()``.

**Bug fixes**

- :gh:`2496`, [Linux]: Avoid segfault (a cPython bug) on
  ``Process.memory_maps()`` for processes that use hundreds of GBs of memory.
- :gh:`2502`, [macOS]: :func:`virtual_memory` now relies on
  ``host_statistics64`` instead of ``host_statistics``. This is the same
  approach used by ``vm_stat`` CLI tool, and should grant more accurate
  results.

**Compatibility notes**

- :gh:`2480`: Python 2.7 is no longer supported.
- :gh:`2490`: removed long deprecated ``Process.memory_info_ex()`` method.

6.1.1 — 2024-12-19
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2471`: use Vulture CLI tool to detect dead code.

**Bug fixes**

- :gh:`2418`, [Linux]: fix race condition in case /proc/PID/stat does not
  exist, but /proc/PID does, resulting in FileNotFoundError.
- :gh:`2470`, [Linux]: :func:`users` may return "localhost" instead of the
  actual IP address of the user logged in.

6.1.0 — 2024-10-17
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2366`, [Windows]: drastically speedup :func:`process_iter`. We now
  determine process unique identity by using process "fast" create time method.
  This will considerably speedup those apps which use :func:`process_iter`
  only once, e.g. to look for a process with a certain name.
- :gh:`2446`: use pytest instead of unittest.
- :gh:`2448`: add ``make install-sysdeps`` target to install the necessary
  system dependencies (python-dev, gcc, etc.) on all supported UNIX flavors.
- :gh:`2449`: add ``make install-pydeps-test`` and ``make install-pydeps-dev``
  targets. They can be used to install dependencies meant for running tests and
  for local development. They can also be installed via ``pip install .[test]``
  and ``pip install .[dev]``.
- :gh:`2456`: allow to run tests via ``python3 -m psutil.tests`` even if
  ``pytest`` module is not installed. This is useful for production
  environments that don't have pytest installed, but still want to be able to
  test psutil installation.

**Bug fixes**

- :gh:`2427`: psutil (segfault) on import in the free-threaded (no GIL) version
  of Python 3.13.  (patch by Sam Gross)
- :gh:`2455`, [Linux]: ``IndexError`` may occur when reading /proc/pid/stat and
  field 40 (blkio_ticks) is missing.
- :gh:`2457`, [AIX]: significantly improve the speed of
  :meth:`Process.open_files` for some edge cases.
- :gh:`2460`, [OpenBSD]: :meth:`Process.num_fds` and
  :meth:`Process.open_files` may fail with :exc:`NoSuchProcess` for PID 0.
  Instead, we now return "null" values (0 and [] respectively).

6.0.0 — 2024-06-18
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2109`: ``maxfile`` and ``maxpath`` fields were removed from the
  namedtuple returned by :func:`disk_partitions`. Reason: on network
  filesystems (NFS) this can potentially take a very long time to complete.
- :gh:`2366`, [Windows]: log debug message when using slower process APIs.
- :gh:`2375`, [macOS]: provide arm64 wheels.  (patch by Matthieu Darbois)
- :gh:`2396`: :func:`process_iter` no longer pre-emptively checks whether
  PIDs have been reused. This makes :func:`process_iter` around 20x times
  faster.
- :gh:`2396`: a new ``psutil.process_iter.cache_clear()`` API can be used the
  clear
  :func:`process_iter` internal cache.
- :gh:`2401`, Support building with free-threaded CPython 3.13. (patch by Sam
  Gross)
- :gh:`2407`: :meth:`Process.connections` was renamed to
  :meth:`Process.net_connections`. The old name is still available, but it's
  deprecated (triggers a ``DeprecationWarning``) and will be removed in the
  future.
- :gh:`2425`: [Linux]: provide aarch64 wheels.  (patch by Matthieu Darbois /
  Ben Raz)

**Bug fixes**

- :gh:`2250`, [NetBSD]: :meth:`Process.cmdline` sometimes fail with EBUSY. It
  usually happens for long cmdlines with lots of arguments. In this case retry
  getting the cmdline for up to 50 times, and return an empty list as last
  resort.
- :gh:`2254`, [Linux]: offline cpus raise NotImplementedError in cpu_freq()
  (patch by Shade Gladden)
- :gh:`2272`: Add pickle support to psutil Exceptions.
- :gh:`2359`, [Windows], [CRITICAL]: :func:`pid_exists` disagrees with
  :class:`Process` on whether a pid exists when ERROR_ACCESS_DENIED.
- :gh:`2360`, [macOS]: can't compile on macOS < 10.13.  (patch by Ryan Schmidt)
- :gh:`2362`, [macOS]: can't compile on macOS 10.11.  (patch by Ryan Schmidt)
- :gh:`2365`, [macOS]: can't compile on macOS < 10.9.  (patch by Ryan Schmidt)
- :gh:`2395`, [OpenBSD]: :func:`pid_exists` erroneously return True if the
  argument is a thread ID (TID) instead of a PID (process ID).
- :gh:`2412`, [macOS]: can't compile on macOS 10.4 PowerPC due to missing
  `MNT_` constants.

**Porting notes**

Version 6.0.0 introduces some changes which affect backward compatibility:

- :gh:`2109`: the namedtuple returned by :func:`disk_partitions`' no longer
  has ``maxfile`` and ``maxpath`` fields.
- :gh:`2396`: :func:`process_iter` no longer pre-emptively checks whether
  PIDs have been reused. If you want to check for PID reusage you are supposed
  to use
  :meth:`Process.is_running` against the yielded :class:`Process` instances.
  That will also automatically remove reused PIDs from :func:`process_iter`
  internal cache.
- :gh:`2407`: :meth:`Process.connections` was renamed to
  :meth:`Process.net_connections`. The old name is still available, but it's
  deprecated (triggers a ``DeprecationWarning``) and will be removed in the
  future.

5.9.8 — 2024-01-19
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2343`, [FreeBSD]: filter :func:`net_connections` returned list in C
  instead of Python, and avoid to retrieve unnecessary connection types unless
  explicitly asked. E.g., on an IDLE system with few IPv6 connections this will
  run around 4 times faster. Before all connection types (TCP, UDP, UNIX) were
  retrieved internally, even if only a portion was returned.
- :gh:`2342`, [NetBSD]: same as above (#2343) but for NetBSD.
- :gh:`2349`: adopted black formatting style.

**Bug fixes**

- :gh:`930`, [NetBSD], [critical]: :func:`net_connections` implementation was
  broken. It could either leak memory or core dump.
- :gh:`2340`, [NetBSD]: if process is terminated, :meth:`Process.cwd` will
  return an empty string instead of raising :exc:`NoSuchProcess`.
- :gh:`2345`, [Linux]: fix compilation on older compiler missing
  DUPLEX_UNKNOWN.
- :gh:`2222`, [macOS]: `cpu_freq()` now returns fixed values for `min` and
  `max` frequencies in all Apple Silicon chips.

5.9.7 — 2023-12-17
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2324`: enforce Ruff rule `raw-string-in-exception`, which helps
  providing clearer tracebacks when exceptions are raised by psutil.

**Bug fixes**

- :gh:`2325`, [PyPy]: psutil did not compile on PyPy due to missing
  `PyErr_SetExcFromWindowsErrWithFilenameObject` cPython API.

5.9.6 — 2023-10-15
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1703`: :func:`cpu_percent` and :func:`cpu_times_percent` are now
  thread safe, meaning they can be called from different threads and still
  return meaningful and independent results. Before, if (say) 10 threads called
  ``cpu_percent(interval=None)`` at the same time, only 1 thread out of 10
  would get the right result.
- :gh:`2266`: if :class:`Process` class is passed a very high PID, raise
  :exc:`NoSuchProcess` instead of OverflowError.  (patch by Xuehai Pan)
- :gh:`2246`: drop python 3.4 & 3.5 support.  (patch by Matthieu Darbois)
- :gh:`2290`: PID reuse is now pre-emptively checked for :meth:`Process.ppid`
  and
  :meth:`Process.parents`.
- :gh:`2312`: use ``ruff`` Python linter instead of ``flake8 + isort``. It's an
  order of magnitude faster + it adds a ton of new code quality checks.

**Bug fixes**

- :gh:`2195`, [Linux]: no longer print exception at import time in case
  /proc/stat can't be read due to permission error. Redirect it to
  ``PSUTIL_DEBUG`` instead.
- :gh:`2241`, [NetBSD]: can't compile On NetBSD 10.99.3/amd64.  (patch by
  Thomas Klausner)
- :gh:`2245`, [Windows]: fix var unbound error on possibly in
  :func:`swap_memory` (patch by student_2333)
- :gh:`2268`: ``bytes2human()`` utility function was unable to properly
  represent negative values.
- :gh:`2252`, [Windows]: :func:`disk_usage` fails on Python 3.12+.  (patch by
  Matthieu Darbois)
- :gh:`2284`, [Linux]: :meth:`Process.memory_full_info` may incorrectly raise
  :exc:`ZombieProcess` if it's determined via ``/proc/pid/smaps_rollup``.
  Instead we now fallback on reading ``/proc/pid/smaps``.
- :gh:`2287`, [OpenBSD], [NetBSD]: :meth:`Process.is_running` erroneously
  return ``False`` for zombie processes, because creation time cannot be
  determined.
- :gh:`2288`, [Linux]: correctly raise :exc:`ZombieProcess` on
  :meth:`Process.exe`,
  :meth:`Process.cmdline` and :meth:`Process.memory_maps` instead of
  returning a "null" value.
- :gh:`2290`: differently from what stated in the doc, PID reuse is not
  pre-emptively checked for :meth:`Process.nice` (set),
  :meth:`Process.ionice`, (set), :meth:`Process.cpu_affinity` (set),
  :meth:`Process.rlimit` (set), :meth:`Process.parent`.
- :gh:`2308`, [OpenBSD]: :meth:`Process.threads` always fail with
  :exc:`AccessDenied` (also as root).

5.9.5 — 2023-04-17
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2196`: in case of exception, display a cleaner error traceback by hiding
  the `KeyError` bit deriving from a missed cache hit.
- :gh:`2217`: print the full traceback when a `DeprecationWarning` or
  `UserWarning` is raised.
- :gh:`2230`, [OpenBSD]: :func:`net_connections` implementation was rewritten
  from scratch:

  - We're now able to retrieve the path of AF_UNIX sockets (before it was an
    empty string)
  - The function is faster since it no longer iterates over all processes.
  - No longer produces duplicate connection entries.
- :gh:`2238`: there are cases where :meth:`Process.cwd` cannot be determined
  (e.g. directory no longer exists), in which case we returned either ``None``
  or an empty string. This was consolidated and we now return ``""`` on all
  platforms.
- :gh:`2239`, [UNIX]: if process is a zombie, and we can only determine part of
  the its truncated :meth:`Process.name` (15 chars), don't fail with
  :exc:`ZombieProcess` when we try to guess the full name from the
  :meth:`Process.cmdline`. Just return the truncated name.
- :gh:`2240`, [NetBSD], [OpenBSD]: add CI testing on every commit for NetBSD
  and OpenBSD platforms (python 3 only).

**Bug fixes**

- :gh:`1043`, [OpenBSD] :func:`net_connections` returns duplicate entries.
- :gh:`1915`, [Linux]: on certain kernels, ``"MemAvailable"`` field from
  ``/proc/meminfo`` returns ``0`` (possibly a kernel bug), in which case we
  calculate an approximation for ``available`` memory which matches "free" CLI
  utility.
- :gh:`2164`, [Linux]: compilation fails on kernels < 2.6.27 (e.g. CentOS 5).
- :gh:`2186`, [FreeBSD]: compilation fails with Clang 15.  (patch by Po-Chuan
  Hsieh)
- :gh:`2191`, [Linux]: :func:`disk_partitions`: do not unnecessarily read
  /proc/filesystems and raise :exc:`AccessDenied` unless user specified
  `all=False` argument.
- :gh:`2216`, [Windows]: fix tests when running in a virtual environment (patch
  by Matthieu Darbois)
- :gh:`2225`, [POSIX]: :func:`users` loses precision for ``started``
  attribute (off by 1 minute).
- :gh:`2229`, [OpenBSD]: unable to properly recognize zombie processes.
  :exc:`NoSuchProcess` may be raised instead of :exc:`ZombieProcess`.
- :gh:`2231`, [NetBSD]: *available*  :func:`virtual_memory` is higher than
  *total*.
- :gh:`2234`, [NetBSD]: :func:`virtual_memory` metrics are wrong: *available*
  and *used* are too high. We now match values shown by *htop* CLI utility.
- :gh:`2236`, [NetBSD]: :meth:`Process.num_threads` and
  :meth:`Process.threads` return threads that are already terminated.
- :gh:`2237`, [OpenBSD], [NetBSD]: :meth:`Process.cwd` may raise
  ``FileNotFoundError`` if cwd no longer exists. Return an empty string
  instead.

5.9.4 — 2022-11-07
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2102`: use Limited API when building wheels with CPython 3.6+ on Linux,
  macOS and Windows. This allows to use pre-built wheels in all future versions
  of cPython 3.  (patch by Matthieu Darbois)

**Bug fixes**

- :gh:`2077`, [Windows]: Use system-level values for :func:`virtual_memory`.
  (patch by Daniel Widdis)
- :gh:`2156`, [Linux]: compilation may fail on very old gcc compilers due to
  missing ``SPEED_UNKNOWN`` definition.  (patch by Amir Rossert)
- :gh:`2010`, [macOS]: on MacOS, arm64 ``IFM_1000_TX`` and ``IFM_1000_T`` are
  the same value, causing a build failure.  (patch by Lawrence D'Anna)
- :gh:`2160`, [Windows]: Get Windows percent swap usage from performance
  counters. (patch by Daniel Widdis)

5.9.3 — 2022-10-18
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`2040`, [macOS]: provide wheels for arm64 architecture.  (patch by
  Matthieu Darbois)

**Bug fixes**

- :gh:`2116`, [macOS], [critical]: :func:`net_connections` fails with
  RuntimeError.
- :gh:`2135`, [macOS]: :meth:`Process.environ` may contain garbage data. Fix
  out-of-bounds read around ``sysctl_procargs``.  (patch by Bernhard
  Urban-Forster)
- :gh:`2138`, [Linux], **[critical]**: can't compile psutil on Android due to
  undefined ``ethtool_cmd_speed`` symbol.
- :gh:`2142`, [POSIX]: :func:`net_if_stats` 's ``flags`` on Python 2 returned
  unicode instead of str.  (patch by Matthieu Darbois)
- :gh:`2147`, [macOS] Fix disk usage report on macOS 12+.  (patch by Matthieu
  Darbois)
- :gh:`2150`, [Linux] :meth:`Process.threads` may raise ``NoSuchProcess``.
  Fix race condition.  (patch by Daniel Li)
- :gh:`2153`, [macOS] Fix race condition in
  test_posix.TestProcess.test_cmdline. (patch by Matthieu Darbois)

5.9.2 — 2022-09-04
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`2093`, [FreeBSD], **[critical]**: :func:`pids` may fail with ENOMEM.
  Dynamically increase the ``malloc()`` buffer size until it's big enough.
- :gh:`2095`, [Linux]: :func:`net_if_stats` returns incorrect interface speed
  for 100GbE network cards.
- :gh:`2113`, [FreeBSD], **[critical]**: :func:`virtual_memory` may raise
  ENOMEM due to missing ``#include <sys/param.h>`` directive.  (patch by Peter
  Jeremy)
- :gh:`2128`, [NetBSD]: :func:`swap_memory` was miscalculated.  (patch by
  Thomas Klausner)

5.9.1 — 2022-05-20
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1053`: drop Python 2.6 support.  (patches by Matthieu Darbois and Hugo
  van Kemenade)
- :gh:`2037`: Add additional flags to net_if_stats.
- :gh:`2050`, [Linux]: increase ``read(2)`` buffer size from 1k to 32k when
  reading ``/proc`` pseudo files line by line. This should help having more
  consistent results.
- :gh:`2057`, [OpenBSD]: add support for :func:`cpu_freq`.
- :gh:`2107`, [Linux]: :meth:`Process.memory_full_info` (reporting process
  USS/PSS/Swap memory) now reads ``/proc/pid/smaps_rollup`` instead of
  ``/proc/pids/smaps``, which makes it 5 times faster.

**Bug fixes**

- :gh:`2048`: ``AttributeError`` is raised if ``psutil.Error`` class is raised
  manually and passed through ``str``.
- :gh:`2049`, [Linux]: :func:`cpu_freq` erroneously returns ``curr`` value in
  GHz while ``min`` and ``max`` are in MHz.
- :gh:`2050`, [Linux]: :func:`virtual_memory` may raise ``ValueError`` if
  running in a LCX container.

5.9.0 — 2021-12-29
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1851`, [Linux]: :func:`cpu_freq` is slow on systems with many CPUs.
  Read current frequency values for all CPUs from ``/proc/cpuinfo`` instead of
  opening many files in ``/sys`` fs.  (patch by marxin)
- :gh:`1992`: :exc:`NoSuchProcess` message now specifies if the PID has been
  reused.
- :gh:`1992`: error classes (:exc:`NoSuchProcess`, :exc:`AccessDenied`, etc.)
  now have a better formatted and separated ``__repr__`` and ``__str__``
  implementations.
- :gh:`1996`, [BSD]: add support for MidnightBSD.  (patch by Saeed Rasooli)
- :gh:`1999`, [Linux]: :func:`disk_partitions`: convert ``/dev/root`` device
  (an alias used on some Linux distros) to real root device path.
- :gh:`2005`: ``PSUTIL_DEBUG`` mode now prints file name and line number of the
  debug messages coming from C extension modules.
- :gh:`2042`: rewrite HISTORY.rst to use hyperlinks pointing to psutil API doc.

**Bug fixes**

- :gh:`1456`, [macOS], **[critical]**: :func:`cpu_freq` ``min`` and ``max``
  are set to 0 if can't be determined (instead of crashing).
- :gh:`1512`, [macOS]: sometimes :meth:`Process.connections` will crash with
  ``EOPNOTSUPP`` for one connection; this is now ignored.
- :gh:`1598`, [Windows]: :func:`disk_partitions` only returns mountpoints on
  drives where it first finds one.
- :gh:`1874`, [SunOS]: swap output error due to incorrect range.
- :gh:`1892`, [macOS]: :func:`cpu_freq` broken on Apple M1.
- :gh:`1901`, [macOS]: different functions, especially
  :meth:`Process.open_files` and
  :meth:`Process.connections`, could randomly raise :exc:`AccessDenied`
  because the internal buffer of ``proc_pidinfo(PROC_PIDLISTFDS)`` syscall
  was not big enough. We now dynamically increase the buffer size until
  it's big enough instead of giving up and raising :exc:`AccessDenied`,
  which was a fallback to avoid crashing.
- :gh:`1904`, [Windows]: ``OpenProcess`` fails with ``ERROR_SUCCESS`` due to
  ``GetLastError()`` called after ``sprintf()``.  (patch by alxchk)
- :gh:`1913`, [Linux]: :func:`wait_procs` should catch
  ``subprocess.TimeoutExpired`` exception.
- :gh:`1919`, [Linux]: :func:`sensors_battery` can raise ``TypeError`` on
  PureOS.
- :gh:`1921`, [Windows]: :func:`swap_memory` shows committed memory instead
  of swap.
- :gh:`1940`, [Linux]: psutil does not handle ``ENAMETOOLONG`` when accessing
  process file descriptors in procfs.  (patch by Nikita Radchenko)
- :gh:`1948`, **[critical]**: ``memoize_when_activated`` decorator is not
  thread-safe. (patch by Xuehai Pan)
- :gh:`1953`, [Windows], **[critical]**: :func:`disk_partitions` crashes due
  to insufficient buffer len. (patch by MaWe2019)
- :gh:`1965`, [Windows], **[critical]**: fix "Fatal Python error: deallocating
  None" when calling :func:`users` multiple times.
- :gh:`1980`, [Windows]: 32bit / WoW64 processes fails to read
  :meth:`Process.name` longer than 128 characters resulting in
  :exc:`AccessDenied`. This is now fixed.  (patch by PetrPospisil)
- :gh:`1991`, **[critical]**: :func:`process_iter` is not thread safe and can
  raise ``TypeError`` if invoked from multiple threads.
- :gh:`1956`, [macOS]: :meth:`Process.cpu_times` reports incorrect timings on
  M1 machines. (patch by Olivier Dormond)
- :gh:`2023`, [Linux]: :func:`cpu_freq` return order is wrong on systems with
  more than 9 CPUs.

5.8.0 — 2020-12-19
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1863`: :func:`disk_partitions` exposes 2 extra fields: ``maxfile`` and
  ``maxpath``, which are the maximum file name and path name length.
- :gh:`1872`, [Windows]: added support for PyPy 2.7.
- :gh:`1879`: provide pre-compiled wheels for Linux and macOS (yey!).
- :gh:`1880`: get rid of Travis and Cirrus CI services (they are no longer
  free). CI testing is now done by GitHub Actions on Linux, macOS and FreeBSD
  (yes). AppVeyor is still being used for Windows CI.

**Bug fixes**

- :gh:`1708`, [Linux]: get rid of :func:`sensors_temperatures` duplicates.
  (patch by Tim Schlueter).
- :gh:`1839`, [Windows], **[critical]**: always raise :exc:`AccessDenied`
  instead of ``WindowsError`` when failing to query 64 processes from 32 bit
  ones by using ``NtWoW64`` APIs.
- :gh:`1866`, [Windows], **[critical]**: :meth:`Process.exe`,
  :meth:`Process.cmdline`,
  :meth:`Process.environ` may raise "[WinError 998] Invalid access to memory
  location" on Python 3.9 / VS 2019.
- :gh:`1874`, [SunOS]: wrong swap output given when encrypted column is
  present.
- :gh:`1875`, [Windows], **[critical]**: :meth:`Process.username` may raise
  ``ERROR_NONE_MAPPED`` if the SID has no corresponding account name. In this
  case :exc:`AccessDenied` is now raised.
- :gh:`1886`, [macOS]: ``EIO`` error may be raised on :meth:`Process.cmdline`
  and :meth:`Process.environ`. Now it gets translated into
  :exc:`AccessDenied`.
- :gh:`1887`, [Windows], **[critical]**: ``OpenProcess`` may fail with
  "[WinError 0] The operation completed successfully"." Turn it into
  :exc:`AccessDenied` or :exc:`NoSuchProcess` depending on whether the PID is
  alive.
- :gh:`1891`, [macOS]: get rid of deprecated ``getpagesize()``.

5.7.3 — 2020-10-23
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`809`, [FreeBSD]: add support for :meth:`Process.rlimit`.
- :gh:`893`, [BSD]: add support for :meth:`Process.environ` (patch by Armin
  Gruner)
- :gh:`1830`, [POSIX]: :func:`net_if_stats` ``isup`` also checks whether the
  NIC is running (meaning Wi-Fi or ethernet cable is connected).  (patch by
  Chris Burger)
- :gh:`1837`, [Linux]: improved battery detection and charge ``secsleft``
  calculation (patch by aristocratos)

**Bug fixes**

- :gh:`1620`, [Linux]: :func:`cpu_count` with ``logical=False`` result is
  incorrect on systems with more than one CPU socket.  (patch by Vincent A.
  Arcila)
- :gh:`1738`, [macOS]: :meth:`Process.exe` may raise ``FileNotFoundError`` if
  process is still alive but the exe file which launched it got deleted.
- :gh:`1791`, [macOS]: fix missing include for ``getpagesize()``.
- :gh:`1823`, [Windows], **[critical]**: :meth:`Process.open_files` may cause
  a segfault due to a NULL pointer.
- :gh:`1838`, [Linux]: :func:`sensors_battery`: if `percent` can be
  determined but not the remaining values, still return a result instead of
  ``None``. (patch by aristocratos)

5.7.2 — 2020-07-15
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- wheels for 2.7 were inadvertently deleted.

5.7.1 — 2020-07-15
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1729`: parallel tests on POSIX (``make test-parallel``). They're twice
  as fast!
- :gh:`1741`, [POSIX]: ``make build`` now runs in parallel on Python >= 3.6 and
  it's about 15% faster.
- :gh:`1747`: :meth:`Process.wait` return value is cached so that the exit
  code can be retrieved on then next call.
- :gh:`1747`, [POSIX]: :meth:`Process.wait` on POSIX now returns an enum,
  showing the negative signal which was used to terminate the process. It
  returns something like ``<Negsignal.SIGTERM: -15>``.
- :gh:`1747`: :class:`Process` class provides more info about the process on
  ``str()`` and ``repr()`` (status and exit code).
- :gh:`1757`: memory leak tests are now stable.
- :gh:`1768`, [Windows]: added support for Windows Nano Server. (contributed by
  Julien Lebot)

**Bug fixes**

- :gh:`1726`, [Linux]: :func:`cpu_freq` parsing should use spaces instead of
  tabs on ia64. (patch by Michał Górny)
- :gh:`1760`, [Linux]: :meth:`Process.rlimit` does not handle long long type
  properly.
- :gh:`1766`, [macOS]: :exc:`NoSuchProcess` may be raised instead of
  :exc:`ZombieProcess`.
- :gh:`1781`, **[critical]**: :func:`getloadavg` can crash the Python
  interpreter. (patch by Ammar Askar)

5.7.0 — 2020-02-18
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1637`, [SunOS]: add partial support for old SunOS 5.10 Update 0 to 3.
- :gh:`1648`, [Linux]: :func:`sensors_temperatures` looks into an additional
  ``/sys/device/`` directory for additional data.  (patch by Javad Karabi)
- :gh:`1652`, [Windows]: dropped support for Windows XP and Windows Server
  2003. Minimum supported Windows version now is Windows Vista.
- :gh:`1671`, [FreeBSD]: add CI testing/service for FreeBSD (Cirrus CI).
- :gh:`1677`, [Windows]: :meth:`Process.exe` will succeed for all process
  PIDs (instead of raising :exc:`AccessDenied`).
- :gh:`1679`, [Windows]: :func:`net_connections` and
  :meth:`Process.connections` are 10% faster.
- :gh:`1682`, [PyPy]: added CI / test integration for PyPy via Travis.
- :gh:`1686`, [Windows]: added support for PyPy on Windows.
- :gh:`1693`, [Windows]: :func:`boot_time`, :meth:`Process.create_time` and
  :func:`users`'s login time now have 1 micro second precision (before the
  precision was of 1 second).

**Bug fixes**

- :gh:`1538`, [NetBSD]: :meth:`Process.cwd` may return ``ENOENT`` instead of
  :exc:`NoSuchProcess`.
- :gh:`1627`, [Linux]: :meth:`Process.memory_maps` can raise ``KeyError``.
- :gh:`1642`, [SunOS]: querying basic info for PID 0 results in
  ``FileNotFoundError``.
- :gh:`1646`, [FreeBSD], **[critical]**: many :class:`Process` methods may
  cause a segfault due to a backward incompatible change in a C type on FreeBSD
  12.0.
- :gh:`1656`, [Windows]: :meth:`Process.memory_full_info` raises
  :exc:`AccessDenied` even for the current user and os.getpid().
- :gh:`1660`, [Windows]: :meth:`Process.open_files` complete rewrite + check
  of errors.
- :gh:`1662`, [Windows], **[critical]**: :meth:`Process.exe` may raise
  "[WinError 0] The operation completed successfully".
- :gh:`1665`, [Linux]: :func:`disk_io_counters` does not take into account
  extra fields added to recent kernels.  (patch by Mike Hommey)
- :gh:`1672`: use the right C type when dealing with PIDs (int or long). Thus
  far (long) was almost always assumed, which is wrong on most platforms.
- :gh:`1673`, [OpenBSD]: :meth:`Process.connections`,
  :meth:`Process.num_fds` and
  :meth:`Process.threads` returned improper exception if process is gone.
- :gh:`1674`, [SunOS]: :func:`disk_partitions` may raise ``OSError``.
- :gh:`1684`, [Linux]: :func:`disk_io_counters` may raise ``ValueError`` on
  systems not having ``/proc/diskstats``.
- :gh:`1695`, [Linux]: could not compile on kernels <= 2.6.13 due to
  ``PSUTIL_HAS_IOPRIO`` not being defined.  (patch by Anselm Kruis)

5.6.7 — 2019-11-26
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1630`, [Windows], **[critical]**: can't compile source distribution due
  to C syntax error.

5.6.6 — 2019-11-25
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1179`, [Linux]: :meth:`Process.cmdline` now takes into account
  misbehaving processes renaming the command line and using inappropriate chars
  to separate args.
- :gh:`1616`, **[critical]**: use of ``Py_DECREF`` instead of ``Py_CLEAR`` will
  result in double ``free()`` and segfault (`CVE-2019-18874
  <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-18874>`__). (patch
  by Riccardo Schirone)
- :gh:`1619`, [OpenBSD], **[critical]**: compilation fails due to C syntax
  error. (patch by Nathan Houghton)

5.6.5 — 2019-11-06
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1615`: remove ``pyproject.toml`` as it was causing installation issues.

5.6.4 — 2019-11-04
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1527`, [Linux]: added :meth:`Process.cpu_times` ``iowait`` counter,
  which is the time spent waiting for blocking I/O to complete.
- :gh:`1565`: add PEP 517/8 build backend and requirements specification for
  better pip integration.  (patch by Bernát Gábor)

**Bug fixes**

- :gh:`875`, [Windows], **[critical]**: :meth:`Process.cmdline`,
  :meth:`Process.environ` or
  :meth:`Process.cwd` may occasionally fail with ``ERROR_PARTIAL_COPY`` which
  now gets translated to :exc:`AccessDenied`.
- :gh:`1126`, [Linux], **[critical]**: :meth:`Process.cpu_affinity` segfaults
  on CentOS 5 / manylinux. :meth:`Process.cpu_affinity` support for CentOS 5
  was removed.
- :gh:`1528`, [AIX], **[critical]**: compilation error on AIX 7.2 due to 32 vs
  64 bit differences. (patch by Arnon Yaari)
- :gh:`1535`: ``type`` and ``family`` fields returned by
  :func:`net_connections` are not always turned into enums.
- :gh:`1536`, [NetBSD]: :meth:`Process.cmdline` erroneously raise
  :exc:`ZombieProcess` error if cmdline has non encodable chars.
- :gh:`1546`: usage percent may be rounded to 0 on Python 2.
- :gh:`1552`, [Windows]: :func:`getloadavg` math for calculating 5 and 15
  mins values is incorrect.
- :gh:`1568`, [Linux]: use CC compiler env var if defined.
- :gh:`1570`, [Windows]: ``NtWow64*`` syscalls fail to raise the proper error
  code
- :gh:`1585`, [OSX]: avoid calling ``close()`` (in C) on possible negative
  integers. (patch by Athos Ribeiro)
- :gh:`1606`, [SunOS], **[critical]**: compilation fails on SunOS 5.10. (patch
  by vser1)

5.6.3 — 2019-06-11
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1494`, [AIX]: added support for :meth:`Process.environ`.  (patch by
  Arnon Yaari)

**Bug fixes**

- :gh:`1276`, [AIX]: can't get whole :meth:`Process.cmdline`.  (patch by
  Arnon Yaari)
- :gh:`1501`, [Windows]: :meth:`Process.cmdline` and :meth:`Process.exe`
  raise unhandled "WinError 1168 element not found" exceptions for "Registry"
  and "Memory Compression" pseudo processes on Windows 10.
- :gh:`1526`, [NetBSD], **[critical]**: :meth:`Process.cmdline` could raise
  ``MemoryError``.  (patch by Kamil Rytarowski)

5.6.2 — 2019-04-26
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`604`, [Windows]: add new :func:`getloadavg`, returning system load
  average calculation, including on Windows (emulated).  (patch by Ammar Askar)
- :gh:`1404`, [Linux]: :func:`cpu_count` with ``logical=False`` uses a second
  method (read from ``/sys/devices/system/cpu/cpu[0-9]/topology/core_id``) in
  order to determine the number of CPU cores in case ``/proc/cpuinfo`` does not
  provide this info.
- :gh:`1458`: provide coloured test output. Also show failures on
  ``KeyboardInterrupt``.
- :gh:`1464`: various docfixes (always point to Python 3 doc, fix links, etc.).
- :gh:`1476`, [Windows]: it is now possible to set process high I/O priority
  (:meth:`Process.ionice`). Also, I/O priority values are now exposed as 4
  new constants: ``IOPRIO_VERYLOW``, ``IOPRIO_LOW``, ``IOPRIO_NORMAL``,
  ``IOPRIO_HIGH``.
- :gh:`1478`: add make command to re-run tests failed on last run.

**Bug fixes**

- :gh:`1223`, [Windows]: :func:`boot_time` may return incorrect value on
  Windows XP.
- :gh:`1456`, [Linux]: :func:`cpu_freq` returns ``None`` instead of 0.0 when
  ``min`` and ``max`` fields can't be determined. (patch by Alex Manuskin)
- :gh:`1462`, [Linux]: (tests) make tests invariant to ``LANG`` setting (patch
  by Benjamin Drung)
- :gh:`1463`: `cpu_distribution.py`_ script was broken.
- :gh:`1470`, [Linux]: :func:`disk_partitions`: fix corner case when
  ``/etc/mtab`` doesn't exist.  (patch by Cedric Lamoriniere)
- :gh:`1471`, [SunOS]: :meth:`Process.name` and :meth:`Process.cmdline` can
  return ``SystemError``.  (patch by Daniel Beer)
- :gh:`1472`, [Linux]: :func:`cpu_freq` does not return all CPUs on
  Raspberry-pi 3.
- :gh:`1474`: fix formatting of ``psutil.tests()`` which mimics ``ps aux``
  output.
- :gh:`1475`, [Windows], **[critical]**: ``OSError.winerror`` attribute wasn't
  properly checked resulting in ``WindowsError(ERROR_ACCESS_DENIED)`` being
  raised instead of :exc:`AccessDenied`.
- :gh:`1477`, [Windows]: wrong or absent error handling for private
  ``NTSTATUS`` Windows APIs. Different process methods were affected by this.
- :gh:`1480`, [Windows], **[critical]**: :func:`cpu_count` with
  ``logical=False`` could cause a crash due to fixed read violation.  (patch by
  Samer Masterson)
- :gh:`1486`, [AIX], [SunOS]: ``AttributeError`` when interacting with
  :class:`Process` methods involved into :meth:`Process.oneshot` context.
- :gh:`1491`, [SunOS]: :func:`net_if_addrs`: use ``free()`` against ``ifap``
  struct on error.  (patch by Agnewee)
- :gh:`1493`, [Linux]: :func:`cpu_freq`: handle the case where
  ``/sys/devices/system/cpu/cpufreq/`` exists but it's empty.

5.6.1 — 2019-03-11
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1329`, [AIX]: psutil doesn't compile on AIX 6.1.  (patch by Arnon Yaari)
- :gh:`1448`, [Windows], **[critical]**: crash on import due to
  ``rtlIpv6AddressToStringA`` not available on Wine.
- :gh:`1451`, [Windows], **[critical]**: :meth:`Process.memory_full_info`
  segfaults. ``NtQueryVirtualMemory`` is now used instead of
  ``QueryWorkingSet`` to calculate USS memory.

5.6.0 — 2019-03-05
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1379`, [Windows]: :meth:`Process.suspend` and :meth:`Process.resume`
  now use ``NtSuspendProcess`` and ``NtResumeProcess`` instead of
  stopping/resuming all threads of a process. This is faster and more reliable
  (aka this is what ProcessHacker does).
- :gh:`1420`, [Windows]: in case of exception :func:`disk_usage` now also
  shows the path name.
- :gh:`1422`, [Windows]: Windows APIs requiring to be dynamically loaded from
  DLL libraries are now loaded only once on startup (instead of on per function
  call) significantly speeding up different functions and methods.
- :gh:`1426`, [Windows]: ``PAGESIZE`` and number of processors is now
  calculated on startup.
- :gh:`1428`: in case of error, the traceback message now shows the underlying
  C function called which failed.
- :gh:`1433`: new :meth:`Process.parents` method.  (idea by Ghislain Le Meur)
- :gh:`1437`: :func:`pids` are returned in sorted order.
- :gh:`1442`: Python 3 is now the default interpreter used by Makefile.

**Bug fixes**

- :gh:`1353`: :func:`process_iter` is now thread safe (it rarely raised
  ``TypeError``).
- :gh:`1394`, [Windows], **[critical]**: :meth:`Process.name` and
  :meth:`Process.exe` may erroneously return "Registry" or fail with "[Error
  0] The operation completed successfully". ``QueryFullProcessImageNameW``
  is now used instead of ``GetProcessImageFileNameW`` in order to prevent
  that.
- :gh:`1411`, [BSD]: lack of ``Py_DECREF`` could cause segmentation fault on
  process instantiation.
- :gh:`1419`, [Windows]: :meth:`Process.environ` raises
  ``NotImplementedError`` when querying a 64-bit process in 32-bit-WoW mode.
  Now it raises
  :exc:`AccessDenied`.
- :gh:`1427`, [OSX]: :meth:`Process.cmdline` and :meth:`Process.environ`
  may erroneously raise ``OSError`` on failed ``malloc()``.
- :gh:`1429`, [Windows]: ``SE DEBUG`` was not properly set for current process.
  It is now, and it should result in less :exc:`AccessDenied` exceptions for
  low PID processes.
- :gh:`1432`, [Windows]: :meth:`Process.memory_info_ex`'s USS memory is
  miscalculated because we're not using the actual system ``PAGESIZE``.
- :gh:`1439`, [NetBSD]: :meth:`Process.connections` may return incomplete
  results if using
  :meth:`Process.oneshot`.
- :gh:`1447`: original exception wasn't turned into :exc:`NoSuchProcess` /
  :exc:`AccessDenied` exceptions when using :meth:`Process.oneshot` context
  manager.

**Incompatible API changes**

- :gh:`1291`, [OSX], **[critical]**: :meth:`Process.memory_maps` was removed
  because inherently broken (segfault) for years.

5.5.1 — 2019-02-15
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1348`, [Windows]: on Windows >= 8.1 if :meth:`Process.cmdline` fails
  due to ``ERROR_ACCESS_DENIED`` attempt using ``NtQueryInformationProcess`` +
  ``ProcessCommandLineInformation``. (patch by EccoTheFlintstone)

**Bug fixes**

- :gh:`1394`, [Windows]: :meth:`Process.exe` returns "[Error 0] The operation
  completed successfully" when Python process runs in "Virtual Secure Mode".
- :gh:`1402`: psutil exceptions' ``repr()`` show the internal private module
  path.
- :gh:`1408`, [AIX], **[critical]**: psutil won't compile on AIX 7.1 due to
  missing header.  (patch by Arnon Yaari)

5.5.0 — 2019-01-23
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1350`, [FreeBSD]: added support for :func:`sensors_temperatures`.
  (patch by Alex Manuskin)
- :gh:`1352`, [FreeBSD]: added support for :func:`cpu_freq`.  (patch by Alex
  Manuskin)

**Bug fixes**

- :gh:`1111`: :meth:`Process.oneshot` is now thread safe.
- :gh:`1354`, [Linux]: :func:`disk_io_counters` fails on Linux kernel 4.18+.
- :gh:`1357`, [Linux]: :meth:`Process.memory_maps` and
  :meth:`Process.io_counters` methods are no longer exposed if not supported
  by the kernel.
- :gh:`1368`, [Windows]: fix :meth:`Process.ionice` mismatch.  (patch by
  EccoTheFlintstone)
- :gh:`1370`, [Windows]: improper usage of ``CloseHandle()`` may lead to
  override the original error code when raising an exception.
- :gh:`1373`, **[critical]**: incorrect handling of cache in
  :meth:`Process.oneshot` context causes :class:`Process` instances to return
  incorrect results.
- :gh:`1376`, [Windows]: ``OpenProcess`` now uses
  ``PROCESS_QUERY_LIMITED_INFORMATION`` access rights wherever possible,
  resulting in less :exc:`AccessDenied` exceptions being thrown for system
  processes.
- :gh:`1376`, [Windows]: check if variable is ``NULL`` before ``free()`` ing
  it. (patch by EccoTheFlintstone)

5.4.8 — 2018-10-30
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1197`, [Linux]: :func:`cpu_freq` is now implemented by parsing
  ``/proc/cpuinfo`` in case ``/sys/devices/system/cpu/*`` filesystem is not
  available.
- :gh:`1310`, [Linux]: :func:`sensors_temperatures` now parses
  ``/sys/class/thermal`` in case ``/sys/class/hwmon`` fs is not available (e.g.
  Raspberry Pi).  (patch by Alex Manuskin)
- :gh:`1320`, [POSIX]: better compilation support when using g++ instead of
  GCC. (patch by Jaime Fullaondo)

**Bug fixes**

- :gh:`715`: do not print exception on import time in case :func:`cpu_times`
  fails.
- :gh:`1004`, [Linux]: :meth:`Process.io_counters` may raise ``ValueError``.
- :gh:`1277`, [OSX]: available and used memory (:func:`virtual_memory`)
  metrics are not accurate.
- :gh:`1294`, [Windows]: :meth:`Process.connections` may sometimes fail with
  intermittent ``0xC0000001``.  (patch by Sylvain Duchesne)
- :gh:`1307`, [Linux]: :func:`disk_partitions` does not honour
  :data:`PROCFS_PATH`.
- :gh:`1320`, [AIX]: system CPU times (:func:`cpu_times`) were being reported
  with ticks unit as opposed to seconds.  (patch by Jaime Fullaondo)
- :gh:`1332`, [OSX]: psutil debug messages are erroneously printed all the
  time. (patch by Ilya Yanok)
- :gh:`1346`, [SunOS]: :func:`net_connections` returns an empty list.  (patch
  by Oleksii Shevchuk)

5.4.7 — 2018-08-14
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1286`, [macOS]: ``psutil.OSX`` constant is now deprecated in favor of
  new ``psutil.MACOS``.
- :gh:`1309`, [Linux]: added ``psutil.STATUS_PARKED`` constant for
  :meth:`Process.status`.
- :gh:`1321`, [Linux]: add :func:`disk_io_counters` dual implementation
  relying on ``/sys/block`` filesystem in case ``/proc/diskstats`` is not
  available. (patch by Lawrence Ye)

**Bug fixes**

- :gh:`1209`, [macOS]: :meth:`Process.memory_maps` may fail with ``EINVAL``
  due to poor ``task_for_pid()`` syscall. :exc:`AccessDenied` is now raised
  instead.
- :gh:`1278`, [macOS]: :meth:`Process.threads` incorrectly return
  microseconds instead of seconds. (patch by Nikhil Marathe)
- :gh:`1279`, [Linux], [macOS], [BSD]: :func:`net_if_stats` may return
  ``ENODEV``.
- :gh:`1294`, [Windows]: :meth:`Process.connections` may sometime fail with
  ``MemoryError``.  (patch by sylvainduchesne)
- :gh:`1305`, [Linux]: :func:`disk_io_counters` may report inflated r/w bytes
  values.
- :gh:`1309`, [Linux]: :meth:`Process.status` is unable to recognize
  ``"idle"`` and ``"parked"`` statuses (returns ``"?"``).
- :gh:`1313`, [Linux]: :func:`disk_io_counters` can report inflated values
  due to counting base disk device and its partition(s) twice.
- :gh:`1323`, [Linux]: :func:`sensors_temperatures` may fail with
  ``ValueError``.

5.4.6 — 2018-06-07
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1258`, [Windows], **[critical]**: :meth:`Process.username` may cause a
  segfault (Python interpreter crash).  (patch by Jean-Luc Migot)
- :gh:`1273`: :func:`net_if_addrs` namedtuple's name has been renamed from
  ``snic`` to ``snicaddr``.
- :gh:`1274`, [Linux]: there was a small chance :meth:`Process.children` may
  swallow
  :exc:`AccessDenied` exceptions.

5.4.5 — 2018-04-14
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1268`: setup.py's ``extra_require`` parameter requires latest setuptools
  version, breaking quite a lot of installations.

5.4.4 — 2018-04-13
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1239`, [Linux]: expose kernel ``slab`` memory field for
  :func:`virtual_memory`. (patch by Maxime Mouial)

**Bug fixes**

- :gh:`694`, [SunOS]: :meth:`Process.cmdline` could be truncated at the 15th
  character when reading it from ``/proc``. An extra effort is made by reading
  it from process address space first.  (patch by Georg Sauthoff)
- :gh:`771`, [Windows]: :func:`cpu_count` (both logical and cores) return a
  wrong (smaller) number on systems using process groups (> 64 cores).
- :gh:`771`, [Windows]: :func:`cpu_times` with ``percpu=True`` return fewer
  CPUs on systems using process groups (> 64 cores).
- :gh:`771`, [Windows]: :func:`cpu_stats` and :func:`cpu_freq` may return
  incorrect results on systems using process groups (> 64 cores).
- :gh:`1193`, [SunOS]: return uid/gid from ``/proc/pid/psinfo`` if there aren't
  enough permissions for ``/proc/pid/cred``.  (patch by Georg Sauthoff)
- :gh:`1194`, [SunOS]: return nice value from ``psinfo`` as ``getpriority()``
  doesn't support real-time processes.  (patch by Georg Sauthoff)
- :gh:`1194`, [SunOS]: fix double ``free()`` in :meth:`Process.cpu_num`.
  (patch by Georg Sauthoff)
- :gh:`1194`, [SunOS]: fix undefined behavior related to strict-aliasing rules
  and warnings.  (patch by Georg Sauthoff)
- :gh:`1210`, [Linux]: :func:`cpu_percent` steal time may remain stuck at
  100% due to Linux erroneously reporting a decreased steal time between calls.
  (patch by Arnon Yaari)
- :gh:`1216`: fix compatibility with Python 2.6 on Windows (patch by Dan
  Vinakovsky)
- :gh:`1222`, [Linux]: :meth:`Process.memory_full_info` was erroneously
  summing "Swap:" and "SwapPss:". Same for "Pss:" and "SwapPss". Not anymore.
- :gh:`1224`, [Windows]: :meth:`Process.wait` may erroneously raise
  :exc:`TimeoutExpired`.
- :gh:`1238`, [Linux]: :func:`sensors_battery` may return ``None`` in case
  battery is not listed as "BAT0" under ``/sys/class/power_supply``.
- :gh:`1240`, [Windows]: :func:`cpu_times` float loses accuracy in a long
  running system. (patch by stswandering)
- :gh:`1245`, [Linux]: :func:`sensors_temperatures` may fail with ``IOError``
  "no such file".
- :gh:`1255`, [FreeBSD]: :func:`swap_memory` stats were erroneously
  represented in KB. (patch by Denis Krienbühl)

**Backward compatibility**

- :gh:`771`, [Windows]: :func:`cpu_count` with ``logical=False`` on Windows
  XP and Vista is no longer supported and returns ``None``.

5.4.3 — 2018-01-01
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`775`: :func:`disk_partitions` on Windows return mount points.

**Bug fixes**

- :gh:`1193`: :func:`pids` may return ``False`` on macOS.

5.4.2 — 2017-12-07
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1173`: introduced ``PSUTIL_DEBUG`` environment variable which can be set
  in order to print useful debug messages on stderr (useful in case of nasty
  errors).
- :gh:`1177`, [macOS]: added support for :func:`sensors_battery`.  (patch by
  Arnon Yaari)
- :gh:`1183`: :meth:`Process.children` is 2x faster on POSIX and 2.4x faster
  on Linux.
- :gh:`1188`: deprecated method :meth:`Process.memory_info_ex` now warns by
  using ``FutureWarning`` instead of ``DeprecationWarning``.

**Bug fixes**

- :gh:`1152`, [Windows]: :func:`disk_io_counters` may return an empty dict.
- :gh:`1169`, [Linux]: :func:`users` ``hostname`` returns username instead.
  (patch by janderbrain)
- :gh:`1172`, [Windows]: ``make test`` does not work.
- :gh:`1179`, [Linux]: :meth:`Process.cmdline` is now able to split cmdline
  args for misbehaving processes which overwrite ``/proc/pid/cmdline`` and use
  spaces instead of null bytes as args separator.
- :gh:`1181`, [macOS]: :meth:`Process.memory_maps` may raise ``ENOENT``.
- :gh:`1187`, [macOS]: :func:`pids` does not return PID 0 on recent macOS
  versions.

5.4.1 — 2017-11-08
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1164`, [AIX]: add support for :meth:`Process.num_ctx_switches`.
  (patch by Arnon Yaari)
- :gh:`1053`: drop Python 3.3 support (psutil still works but it's no longer
  tested).

**Bug fixes**

- :gh:`1150`, [Windows]: when a process is terminated now the exit code is set
  to ``SIGTERM`` instead of ``0``.  (patch by Akos Kiss)
- :gh:`1151`: ``python -m psutil.tests`` fail.
- :gh:`1154`, [AIX], **[critical]**: psutil won't compile on AIX 6.1.0. (patch
  by Arnon Yaari)
- :gh:`1167`, [Windows]: :func:`net_io_counters` packets count now include
  also non-unicast packets.  (patch by Matthew Long)

5.4.0 — 2017-10-12
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1123`, [AIX]: added support for AIX platform.  (patch by Arnon Yaari)

**Bug fixes**

- :gh:`1009`, [Linux]: :func:`sensors_temperatures` may crash with
  ``IOError``.
- :gh:`1012`, [Windows]: :func:`disk_io_counters` ``read_time`` and
  ``write_time`` were expressed in tens of micro seconds instead of
  milliseconds.
- :gh:`1127`, [macOS], **[critical]**: invalid reference counting in
  :meth:`Process.open_files` may lead to segfault.  (patch by Jakub Bacic)
- :gh:`1129`, [Linux]: :func:`sensors_fans` may crash with ``IOError``.
  (patch by Sebastian Saip)
- :gh:`1131`, [SunOS]: fix compilation warnings.  (patch by Arnon Yaari)
- :gh:`1133`, [Windows]: can't compile on newer versions of Visual Studio 2017
  15.4. (patch by Max Bélanger)
- :gh:`1138`, [Linux]: can't compile on CentOS 5.0 and RedHat 5.0. (patch by
  Prodesire)

5.3.1 — 2017-09-10
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`1124`: documentation moved to http://psutil.readthedocs.io

**Bug fixes**

- :gh:`1105`, [FreeBSD]: psutil does not compile on FreeBSD 12.
- :gh:`1125`, [BSD]: :func:`net_connections` raises ``TypeError``.

**Compatibility notes**

- :gh:`1120`: ``.exe`` files for Windows are no longer uploaded on PyPI as per
  PEP-527. Only wheels are provided.

5.3.0 — 2017-09-01
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`802`: :func:`disk_io_counters` and :func:`net_io_counters` numbers
  no longer wrap (restart from 0). Introduced a new ``nowrap`` argument.
- :gh:`928`: :func:`net_connections` and :meth:`Process.connections`
  ``laddr`` and ``raddr`` are now named tuples.
- :gh:`1015`: :func:`swap_memory` now relies on ``/proc/meminfo`` instead of
  ``sysinfo()`` syscall so that it can be used in conjunction with
  :data:`PROCFS_PATH` in order to retrieve memory info about Linux containers
  such as Docker and Heroku.
- :gh:`1022`: :func:`users` provides a new ``pid`` field.
- :gh:`1025`: :func:`process_iter` accepts two new parameters in order to
  invoke
  :meth:`Process.as_dict`: ``attrs`` and ``ad_value``. With these you can
  iterate over all processes in one shot without needing to catch
  :exc:`NoSuchProcess` and do list/dict comprehensions.
- :gh:`1040`: implemented full unicode support.
- :gh:`1051`: :func:`disk_usage` on Python 3 is now able to accept bytes.
- :gh:`1058`: test suite now enables all warnings by default.
- :gh:`1060`: source distribution is dynamically generated so that it only
  includes relevant files.
- :gh:`1079`, [FreeBSD]: :func:`net_connections` ``fd`` number is now being
  set for real (instead of ``-1``).  (patch by Gleb Smirnoff)
- :gh:`1091`, [SunOS]: implemented :meth:`Process.environ`.  (patch by
  Oleksii Shevchuk)

**Bug fixes**

- :gh:`989`, [Windows]: :func:`boot_time` may return a negative value.
- :gh:`1007`, [Windows]: :func:`boot_time` can have a 1 sec fluctuation
  between calls. The value of the first call is now cached so that
  :func:`boot_time` always returns the same value if fluctuation is <= 1
  second.
- :gh:`1013`, [FreeBSD]: :func:`net_connections` may return incorrect PID.
  (patch by Gleb Smirnoff)
- :gh:`1014`, [Linux]: :class:`Process` class can mask legitimate ``ENOENT``
  exceptions as
  :exc:`NoSuchProcess`.
- :gh:`1016`: :func:`disk_io_counters` raises ``RuntimeError`` on a system
  with no disks.
- :gh:`1017`: :func:`net_io_counters` raises ``RuntimeError`` on a system
  with no network cards installed.
- :gh:`1021`, [Linux]: :meth:`Process.open_files` may erroneously raise
  :exc:`NoSuchProcess` instead of skipping a file which gets deleted while open
  files are retrieved.
- :gh:`1029`, [macOS], [FreeBSD]: :meth:`Process.connections` with
  ``family=unix`` on Python 3 doesn't properly handle unicode paths and may
  raise ``UnicodeDecodeError``.
- :gh:`1033`, [macOS], [FreeBSD]: memory leak for :func:`net_connections` and
  :meth:`Process.connections` when retrieving UNIX sockets (``kind='unix'``).
- :gh:`1040`: fixed many unicode related issues such as ``UnicodeDecodeError``
  on Python 3 + POSIX and invalid encoded data on Windows.
- :gh:`1042`, [FreeBSD], **[critical]**: psutil won't compile on FreeBSD 12.
- :gh:`1044`, [macOS]: different :class:`Process` methods incorrectly raise
  :exc:`AccessDenied` for zombie processes.
- :gh:`1046`, [Windows]: :func:`disk_partitions` on Windows overrides user's
  ``SetErrorMode``.
- :gh:`1047`, [Windows]: :meth:`Process.username`: memory leak in case
  exception is thrown.
- :gh:`1048`, [Windows]: :func:`users` ``host`` field report an invalid IP
  address.
- :gh:`1050`, [Windows]: :meth:`Process.memory_maps` leaks memory.
- :gh:`1055`: :func:`cpu_count` is no longer cached. This is useful on
  systems such as Linux where CPUs can be disabled at runtime. This also
  reflects on
  :meth:`Process.cpu_percent` which no longer uses the cache.
- :gh:`1058`: fixed Python warnings.
- :gh:`1062`: :func:`disk_io_counters` and :func:`net_io_counters` raise
  ``TypeError`` if no disks or NICs are installed on the system.
- :gh:`1063`, [NetBSD]: :func:`net_connections` may list incorrect sockets.
- :gh:`1064`, [NetBSD], **[critical]**: :func:`swap_memory` may segfault in
  case of error.
- :gh:`1065`, [OpenBSD], **[critical]**: :meth:`Process.cmdline` may raise
  ``SystemError``.
- :gh:`1067`, [NetBSD]: :meth:`Process.cmdline` leaks memory if process has
  terminated.
- :gh:`1069`, [FreeBSD]: :meth:`Process.cpu_num` may return 255 for certain
  kernel processes.
- :gh:`1071`, [Linux]: :func:`cpu_freq` may raise ``IOError`` on old RedHat
  distros.
- :gh:`1074`, [FreeBSD]: :func:`sensors_battery` raises ``OSError`` in case
  of no battery.
- :gh:`1075`, [Windows]: :func:`net_if_addrs`: ``inet_ntop()`` return value
  is not checked.
- :gh:`1077`, [SunOS]: :func:`net_if_addrs` shows garbage addresses on SunOS
  5.10. (patch by Oleksii Shevchuk)
- :gh:`1077`, [SunOS]: :func:`net_connections` does not work on SunOS 5.10.
  (patch by Oleksii Shevchuk)
- :gh:`1079`, [FreeBSD]: :func:`net_connections` didn't list locally
  connected sockets. (patch by Gleb Smirnoff)
- :gh:`1085`: :func:`cpu_count` return value is now checked and forced to
  ``None`` if <= 1.
- :gh:`1087`: :meth:`Process.cpu_percent` guard against :func:`cpu_count`
  returning ``None`` and assumes 1 instead.
- :gh:`1093`, [SunOS]: :meth:`Process.memory_maps` shows wrong 64 bit
  addresses.
- :gh:`1094`, [Windows]: :func:`pid_exists` may lie. Also, all process APIs
  relying on ``OpenProcess`` Windows API now check whether the PID is actually
  running.
- :gh:`1098`, [Windows]: :meth:`Process.wait` may erroneously return sooner,
  when the PID is still alive.
- :gh:`1099`, [Windows]: :meth:`Process.terminate` may raise
  :exc:`AccessDenied` even if the process already died.
- :gh:`1101`, [Linux]: :func:`sensors_temperatures` may raise ``ENODEV``.

**Porting notes**

- :gh:`1039`: returned types consolidation. 1) Windows /
  :meth:`Process.cpu_times`: fields #3 and #4 were int instead of float. 2)
  Linux / FreeBSD / OpenBSD:
  :meth:`Process.connections` ``raddr`` is now set to  ``""`` instead of
  ``None`` when retrieving UNIX sockets.
- :gh:`1040`: all strings are encoded by using OS fs encoding.
- :gh:`1040`: the following Windows APIs on Python 2 now return a string
  instead of unicode: ``Process.memory_maps().path``,
  ``WindowsService.bin_path()``, ``WindowsService.description()``,
  ``WindowsService.display_name()``, ``WindowsService.username()``.

5.2.2 — 2017-04-10
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`1000`: fixed some setup.py warnings.
- :gh:`1002`, [SunOS]: remove C macro which will not be available on new
  Solaris versions. (patch by Danek Duvall)
- :gh:`1004`, [Linux]: :meth:`Process.io_counters` may raise ``ValueError``.
- :gh:`1006`, [Linux]: :func:`cpu_freq` may return ``None`` on some Linux
  versions does not support the function. Let's not make the function available
  instead.
- :gh:`1009`, [Linux]: :func:`sensors_temperatures` may raise ``OSError``.
- :gh:`1010`, [Linux]: :func:`virtual_memory` may raise ``ValueError`` on
  Ubuntu 14.04.

5.2.1 — 2017-03-24
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`981`, [Linux]: :func:`cpu_freq` may return an empty list.
- :gh:`993`, [Windows]: :meth:`Process.memory_maps` on Python 3 may raise
  ``UnicodeDecodeError``.
- :gh:`996`, [Linux]: :func:`sensors_temperatures` may not show all
  temperatures.
- :gh:`997`, [FreeBSD]: :func:`virtual_memory` may fail due to missing
  ``sysctl`` parameter on FreeBSD 12.

5.2.0 — 2017-03-05
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`971`, [Linux]: Add :func:`sensors_fans` function.  (patch by Nicolas
  Hennion)
- :gh:`976`, [Windows]: :meth:`Process.io_counters` has 2 new fields:
  ``other_count`` and ``other_bytes``.
- :gh:`976`, [Linux]: :meth:`Process.io_counters` has 2 new fields:
  ``read_chars`` and ``write_chars``.

**Bug fixes**

- :gh:`872`, [Linux]: can now compile on Linux by using MUSL C library.
- :gh:`985`, [Windows]: Fix a crash in :meth:`Process.open_files` when the
  worker thread for ``NtQueryObject`` times out.
- :gh:`986`, [Linux]: :meth:`Process.cwd` may raise :exc:`NoSuchProcess`
  instead of :exc:`ZombieProcess`.

5.1.3
^^^^^

**Bug fixes**

- :gh:`971`, [Linux]: :func:`sensors_temperatures` didn't work on CentOS 7.
- :gh:`973`, **[critical]**: :func:`cpu_percent` may raise
  ``ZeroDivisionError``.

5.1.2 — 2017-02-03
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`966`, [Linux]: :func:`sensors_battery` ``power_plugged`` may
  erroneously return ``None`` on Python 3.
- :gh:`968`, [Linux]: :func:`disk_io_counters` raises ``TypeError`` on Python
  3.
- :gh:`970`, [Linux]: :func:`sensors_battery` ``name`` and ``label`` fields
  on Python 3 are bytes instead of str.

5.1.1 — 2017-02-03
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`966`, [Linux]: :func:`sensors_battery` ``percent`` is a float and is
  more precise.

**Bug fixes**

- :gh:`964`, [Windows]: :meth:`Process.username` and :func:`users` may
  return badly decoded character on Python 3.
- :gh:`965`, [Linux]: :func:`disk_io_counters` may miscalculate sector size
  and report the wrong number of bytes read and written.
- :gh:`966`, [Linux]: :func:`sensors_battery` may fail with
  ``FileNotFoundError``.
- :gh:`966`, [Linux]: :func:`sensors_battery` ``power_plugged`` may lie.

5.1.0 — 2017-02-01
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`357`: added :meth:`Process.cpu_num` (what CPU a process is on).
- :gh:`371`: added :func:`sensors_temperatures` (Linux only).
- :gh:`941`: added :func:`cpu_freq` (CPU frequency).
- :gh:`955`: added :func:`sensors_battery` (Linux, Windows, only).
- :gh:`956`: :meth:`Process.cpu_affinity` can now be passed ``[]`` argument
  as an alias to set affinity against all eligible CPUs.

**Bug fixes**

- :gh:`687`, [Linux]: :func:`pid_exists` no longer returns ``True`` if passed
  a process thread ID.
- :gh:`948`: cannot install psutil with ``PYTHONOPTIMIZE=2``.
- :gh:`950`, [Windows]: :meth:`Process.cpu_percent` was calculated
  incorrectly and showed higher number than real usage.
- :gh:`951`, [Windows]: the uploaded wheels for Python 3.6 64 bit didn't work.
- :gh:`959`: psutil exception objects could not be pickled.
- :gh:`960`: :class:`Popen` ``wait()`` did not return the correct negative exit
  status if process is killed by a signal.
- :gh:`961`, [Windows]: ``WindowsService.description()`` method may fail with
  ``ERROR_MUI_FILE_NOT_FOUND``.

5.0.1 — 2016-12-21
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`939`: tar.gz distribution went from 1.8M to 258K.
- :gh:`811`, [Windows]: provide a more meaningful error message if trying to
  use psutil on unsupported Windows XP.

**Bug fixes**

- :gh:`609`, [SunOS], **[critical]**: psutil does not compile on Solaris 10.
- :gh:`936`, [Windows]: fix compilation error on VS 2013 (patch by Max
  Bélanger).
- :gh:`940`, [Linux]: :func:`cpu_percent` and :func:`cpu_times_percent` was
  calculated incorrectly as ``iowait``, ``guest`` and ``guest_nice`` times were
  not properly taken into account.
- :gh:`944`, [OpenBSD]: :func:`pids` was omitting PID 0.

5.0.0 — 2016-11-06
^^^^^^^^^^^^^^^^^^

**Enhncements**

- :gh:`799`: new :meth:`Process.oneshot` context manager making
  :class:`Process` methods around +2x faster in general and from +2x to +6x
  faster on Windows.
- :gh:`943`: better error message in case of version conflict on import.

**Bug fixes**

- :gh:`932`, [NetBSD]: :func:`net_connections` and
  :meth:`Process.connections` may fail without raising an exception.
- :gh:`933`, [Windows]: memory leak in :func:`cpu_stats` and
  ``WindowsService.description()`` method.

4.4.2 — 2016-10-26
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`931`, **[critical]**: psutil no longer compiles on Solaris.

4.4.1 — 2016-10-25
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`927`, **[critical]**: :class:`Popen` ``__del__`` may cause maximum
  recursion depth error.

4.4.0 — 2016-10-23
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`874`, [Windows]: make :func:`net_if_addrs` also return the
  ``netmask``.
- :gh:`887`, [Linux]: :func:`virtual_memory` ``available`` and ``used``
  values are more precise and match ``free`` cmdline utility.  ``available``
  also takes into account LCX containers preventing ``available`` to overflow
  ``total``.
- :gh:`891`: `procinfo.py`_ script has been updated and provides a lot more
  info.

**Bug fixes**

- :gh:`514`, [macOS], **[critical]**: :meth:`Process.memory_maps` can
  segfault.
- :gh:`783`, [macOS]: :meth:`Process.status` may erroneously return
  ``"running"`` for zombie processes.
- :gh:`798`, [Windows]: :meth:`Process.open_files` returns and empty list on
  Windows 10.
- :gh:`825`, [Linux]: :meth:`Process.cpu_affinity`: fix possible double close
  and use of unopened socket.
- :gh:`880`, [Windows]: fix race condition inside :func:`net_connections`.
- :gh:`885`: ``ValueError`` is raised if a negative integer is passed to
  :func:`cpu_percent` functions.
- :gh:`892`, [Linux], **[critical]**: :meth:`Process.cpu_affinity` with
  ``[-1]`` as arg raises ``SystemError`` with no error set; now ``ValueError``
  is raised.
- :gh:`906`, [BSD]: :func:`disk_partitions` with ``all=False`` returned an
  empty list. Now the argument is ignored and all partitions are always
  returned.
- :gh:`907`, [FreeBSD]: :meth:`Process.exe` may fail with
  ``OSError(ENOENT)``.
- :gh:`908`, [macOS], [BSD]: different process methods could errounesuly mask
  the real error for high-privileged PIDs and raise :exc:`NoSuchProcess` and
  :exc:`AccessDenied` instead of ``OSError`` and ``RuntimeError``.
- :gh:`909`, [macOS]: :meth:`Process.open_files` and
  :meth:`Process.connections` methods may raise ``OSError`` with no exception
  set if process is gone.
- :gh:`916`, [macOS]: fix many compilation warnings.

4.3.1 — 2016-09-01
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`881`: ``make install`` now works also when using a virtual env.

**Bug fixes**

- :gh:`854`: :meth:`Process.as_dict` raises ``ValueError`` if passed an
  erroneous attrs name.
- :gh:`857`, [SunOS]: :meth:`Process.cpu_times`,
  :meth:`Process.cpu_percent`,
  :meth:`Process.threads` and :meth:`Process.memory_maps` may raise
  ``RuntimeError`` if attempting to query a 64bit process with a 32bit Python.
  "Null" values are returned as a fallback.
- :gh:`858`: :meth:`Process.as_dict` should not call
  :meth:`Process.memory_info_ex` because it's deprecated.
- :gh:`863`, [Windows]: :meth:`Process.memory_maps` truncates addresses above
  32 bits.
- :gh:`866`, [Windows]: :func:`win_service_iter` and services in general are
  not able to handle unicode service names / descriptions.
- :gh:`869`, [Windows]: :meth:`Process.wait` may raise :exc:`TimeoutExpired`
  with wrong timeout unit (ms instead of sec).
- :gh:`870`, [Windows]: handle leak inside ``psutil_get_process_data``.

4.3.0 — 2016-06-18
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`819`, [Linux]: different speedup improvements:
  :meth:`Process.ppid` +20% faster.
  :meth:`Process.status` +28% faster.
  :meth:`Process.name` +25% faster.
  :meth:`Process.num_threads` +20% faster on Python 3.

**Bug fixes**

- :gh:`810`, [Windows]: Windows wheels are incompatible with pip 7.1.2.
- :gh:`812`, [NetBSD], **[critical]**: fix compilation on NetBSD-5.x.
- :gh:`823`, [NetBSD]: :func:`virtual_memory` raises ``TypeError`` on Python
  3.
- :gh:`829`, [POSIX]: :func:`disk_usage` ``percent`` field takes root
  reserved space into account.
- :gh:`816`, [Windows]: fixed :func:`net_io_counters` values wrapping after
  4.3GB in Windows Vista (NT 6.0) and above using 64bit values from newer win
  APIs.

4.2.0 — 2016-05-14
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`795`, [Windows]: new APIs to deal with Windows services:
  :func:`win_service_iter` and :func:`win_service_get`.
- :gh:`800`, [Linux]: :func:`virtual_memory` returns a new ``shared`` memory
  field.
- :gh:`819`, [Linux]: speedup ``/proc`` parsing:
  :meth:`Process.ppid` +20% faster.
  :meth:`Process.status` +28% faster.
  :meth:`Process.name` +25% faster.
  :meth:`Process.num_threads` +20% faster on Python 3.

**Bug fixes**

- :gh:`797`, [Linux]: :func:`net_if_stats` may raise ``OSError`` for certain
  NIC cards.
- :gh:`813`: :meth:`Process.as_dict` should ignore extraneous attribute names
  which gets attached to the :class:`Process` instance.

4.1.0 — 2016-03-12
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`777`, [Linux]: :meth:`Process.open_files` on Linux return 3 new
  fields: ``position``, ``mode`` and ``flags``.
- :gh:`779`: :meth:`Process.cpu_times` returns two new fields,
  ``children_user`` and ``children_system`` (always set to 0 on macOS and
  Windows).
- :gh:`789`, [Windows]: :func:`cpu_times` return two new fields:
  ``interrupt`` and ``dpc``. Same for :func:`cpu_times_percent`.
- :gh:`792`: new :func:`cpu_stats` function returning number of CPU
  ``ctx_switches``, ``interrupts``, ``soft_interrupts`` and ``syscalls``.

**Bug fixes**

- :gh:`774`, [FreeBSD]: :func:`net_io_counters` dropout is no longer set to 0
  if the kernel provides it.
- :gh:`776`, [Linux]: :meth:`Process.cpu_affinity` may erroneously raise
  :exc:`NoSuchProcess`. (patch by wxwright)
- :gh:`780`, [macOS]: psutil does not compile with some GCC versions.
- :gh:`786`: :func:`net_if_addrs` may report incomplete MAC addresses.
- :gh:`788`, [NetBSD]: :func:`virtual_memory` ``buffers`` and ``shared``
  values were set to 0.
- :gh:`790`, [macOS], **[critical]**: psutil won't compile on macOS 10.4.

4.0.0 — 2016-02-17
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`523`, [Linux], [FreeBSD]: :func:`disk_io_counters` return a new
  ``busy_time`` field.
- :gh:`660`, [Windows]: make.bat is smarter in finding alternative VS install
  locations.  (patch by mpderbec)
- :gh:`732`: :meth:`Process.environ`.  (patch by Frank Benkstein)
- :gh:`753`, [Linux], [macOS], [Windows]: process USS and PSS (Linux) "real"
  memory stats. (patch by Eric Rahm)
- :gh:`755`: :meth:`Process.memory_percent` ``memtype`` parameter.
- :gh:`758`: tests now live in psutil namespace.
- :gh:`760`: expose OS constants (``psutil.LINUX``, ``psutil.OSX``, etc.)
- :gh:`756`, [Linux]: :func:`disk_io_counters` return 2 new fields:
  ``read_merged_count`` and ``write_merged_count``.
- :gh:`762`: new `procsmem.py`_ script.

**Bug fixes**

- :gh:`685`, [Linux]: :func:`virtual_memory` provides wrong results on
  systems with a lot of physical memory.
- :gh:`704`, [SunOS]: psutil does not compile on Solaris sparc.
- :gh:`734`: on Python 3 invalid UTF-8 data is not correctly handled for
  :meth:`Process.name`, :meth:`Process.cwd`, :meth:`Process.exe`,
  :meth:`Process.cmdline` and :meth:`Process.open_files` methods resulting
  in ``UnicodeDecodeError`` exceptions. ``'surrogateescape'`` error handler
  is now used as a workaround for replacing the corrupted data.
- :gh:`737`, [Windows]: when the bitness of psutil and the target process was
  different, :meth:`Process.cmdline` and :meth:`Process.cwd` could return a
  wrong result or incorrectly report an :exc:`AccessDenied` error.
- :gh:`741`, [OpenBSD]: psutil does not compile on mips64.
- :gh:`751`, [Linux]: fixed call to ``Py_DECREF`` on possible ``NULL`` object.
- :gh:`754`, [Linux]: :meth:`Process.cmdline` can be wrong in case of zombie
  process.
- :gh:`759`, [Linux]: :meth:`Process.memory_maps` may return paths ending
  with ``" (deleted)"``.
- :gh:`761`, [Windows]: :func:`boot_time` wraps to 0 after 49 days.
- :gh:`764`, [NetBSD]: fix compilation on NetBSD-6.x.
- :gh:`766`, [Linux]: :func:`net_connections` can't handle malformed
  ``/proc/net/unix`` file.
- :gh:`767`, [Linux]: :func:`disk_io_counters` may raise ``ValueError`` on
  2.6 kernels and it's broken on 2.4 kernels.
- :gh:`770`, [NetBSD]: :func:`disk_io_counters` metrics didn't update.

3.4.2 — 2016-01-20
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`728`, [SunOS]: exposed :data:`PROCFS_PATH` constant to change the
  default location of ``/proc`` filesystem.

**Bug fixes**

- :gh:`724`, [FreeBSD]: :func:`virtual_memory` ``total`` is incorrect.
- :gh:`730`, [FreeBSD], **[critical]**: :func:`virtual_memory` crashes with
  "OSError: [Errno 12] Cannot allocate memory".

3.4.1 — 2016-01-15
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`557`, [NetBSD]: added NetBSD support.  (contributed by Ryo Onodera and
  Thomas Klausner)
- :gh:`708`, [Linux]: :func:`net_connections` and
  :meth:`Process.connections` on Python 2 can be up to 3x faster in case of
  many connections. Also
  :meth:`Process.memory_maps` is slightly faster.
- :gh:`718`: :func:`process_iter` is now thread safe.

**Bug fixes**

- :gh:`714`, [OpenBSD]: :func:`virtual_memory` ``cached`` value was always
  set to 0.
- :gh:`715`, **[critical]**: don't crash at import time if :func:`cpu_times`
  fail for some reason.
- :gh:`717`, [Linux]: :meth:`Process.open_files` fails if deleted files still
  visible.
- :gh:`722`, [Linux]: :func:`swap_memory` no longer crashes if ``sin`` /
  ``sout`` can't be determined due to missing ``/proc/vmstat``.
- :gh:`724`, [FreeBSD]: :func:`virtual_memory` ``total`` is slightly
  incorrect.

3.3.0 — 2015-11-25
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`558`, [Linux]: exposed :data:`PROCFS_PATH` constant to change the
  default location of ``/proc`` filesystem.
- :gh:`615`, [OpenBSD]: added OpenBSD support.  (contributed by Landry Breuil)

**Bug fixes**

- :gh:`692`, [POSIX]: :meth:`Process.name` is no longer cached as it may
  change.

3.2.2 — 2015-10-04
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`517`, [SunOS]: :func:`net_io_counters` failed to detect network
  interfaces correctly on Solaris 10
- :gh:`541`, [FreeBSD]: :func:`disk_io_counters` r/w times were expressed in
  seconds instead of milliseconds.  (patch by dasumin)
- :gh:`610`, [SunOS]: fix build and tests on Solaris 10
- :gh:`623`, [Linux]: process or system connections raises ``ValueError`` if
  IPv6 is not supported by the system.
- :gh:`678`, [Linux], **[critical]**: can't install psutil due to bug in
  setup.py.
- :gh:`688`, [Windows]: compilation fails with MSVC 2015, Python 3.5. (patch by
  Mike Sarahan)

3.2.1 — 2015-09-03
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`677`, [Linux], **[critical]**: can't install psutil due to bug in
  setup.py.

3.2.0 — 2015-09-02
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`644`, [Windows]: added support for ``CTRL_C_EVENT`` and
  ``CTRL_BREAK_EVENT`` signals to use with :meth:`Process.send_signal`.
- :gh:`648`: CI test integration for macOS. (patch by Jeff Tang)
- :gh:`663`, [POSIX]: :func:`net_if_addrs` now returns point-to-point (VPNs)
  addresses.
- :gh:`655`, [Windows]: different issues regarding unicode handling were fixed.
  On Python 2 all APIs returning a string will now return an encoded version of
  it by using sys.getfilesystemencoding() codec. The APIs involved are:
  :func:`net_if_addrs`, :func:`net_if_stats`, :func:`net_io_counters`,
  :meth:`Process.cmdline`, :meth:`Process.name`,
  :meth:`Process.username`, :func:`users`.

**Bug fixes**

- :gh:`513`, [Linux]: fixed integer overflow for ``RLIM_INFINITY``.
- :gh:`641`, [Windows]: fixed many compilation warnings.  (patch by Jeff Tang)
- :gh:`652`, [Windows]: :func:`net_if_addrs` ``UnicodeDecodeError`` in case
  of non-ASCII NIC names.
- :gh:`655`, [Windows]: :func:`net_if_stats` ``UnicodeDecodeError`` in case
  of non-ASCII NIC names.
- :gh:`659`, [Linux]: compilation error on Suse 10. (patch by maozguttman)
- :gh:`664`, [Linux]: compilation error on Alpine Linux. (patch by Bart van
  Kleef)
- :gh:`670`, [Windows]: segfgault of :func:`net_if_addrs` in case of
  non-ASCII NIC names. (patch by sk6249)
- :gh:`672`, [Windows]: compilation fails if using Windows SDK v8.0. (patch by
  Steven Winfield)
- :gh:`675`, [Linux]: :func:`net_connections`: ``UnicodeDecodeError`` may
  occur when listing UNIX sockets.

3.1.1 — 2015-07-15
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`603`, [Linux]: :meth:`Process.ionice` set value range is incorrect.
  (patch by spacewander)
- :gh:`645`, [Linux]: :func:`cpu_times_percent` may produce negative results.
- :gh:`656`: ``from psutil import *`` does not work.

3.1.0 — 2015-07-15
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`534`, [Linux]: :func:`disk_partitions` added support for ZFS
  filesystems.
- :gh:`646`, [Windows]: continuous tests integration for Windows with
  https://ci.appveyor.com/project/giampaolo/psutil.
- :gh:`647`: new dev guide:
  https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst
- :gh:`651`: continuous code quality test integration with scrutinizer-ci.com

**Bug fixes**

- :gh:`340`, [Windows], **[critical]**: :meth:`Process.open_files` no longer
  hangs. Instead it uses a thread which times out and skips the file handle in
  case it's taking too long to be retrieved.  (patch by Jeff Tang)
- :gh:`627`, [Windows]: :meth:`Process.name` no longer raises
  :exc:`AccessDenied` for pids owned by another user.
- :gh:`636`, [Windows]: :meth:`Process.memory_info` raise
  :exc:`AccessDenied`.
- :gh:`637`, [POSIX]: raise exception if trying to send signal to PID 0 as it
  will affect ``os.getpid()`` 's process group and not PID 0.
- :gh:`639`, [Linux]: :meth:`Process.cmdline` can be truncated.
- :gh:`640`, [Linux]: ``*connections`` functions may swallow errors and return
  an incomplete list of connections.
- :gh:`642`: ``repr()`` of exceptions is incorrect.
- :gh:`653`, [Windows]: add ``inet_ntop()`` function for Windows XP to support
  IPv6.
- :gh:`641`, [Windows]: replace deprecated string functions with safe
  equivalents.

3.0.1 — 2015-06-18
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`632`, [Linux]: better error message if cannot parse process UNIX
  connections.
- :gh:`634`, [Linux]: :meth:`Process.cmdline` does not include empty string
  arguments.
- :gh:`635`, [POSIX], **[critical]**: crash on module import if ``enum``
  package is installed on Python < 3.4.

3.0.0 — 2015-06-13
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`250`: new :func:`net_if_stats` returning NIC statistics (``isup``,
  ``duplex``, ``speed``, ``mtu``).
- :gh:`376`: new :func:`net_if_addrs` returning all NIC addresses a-la
  ``ifconfig``.
- :gh:`469`: on Python >= 3.4 ``IOPRIO_CLASS_*`` and ``*_PRIORITY_CLASS``
  constants returned by :meth:`Process.ionice` and :meth:`Process.nice` are
  enums instead of plain integers.
- :gh:`581`: add ``.gitignore``. (patch by Gabi Davar)
- :gh:`582`: connection constants returned by :func:`net_connections` and
  :meth:`Process.connections` were turned from int to enums on Python > 3.4.
- :gh:`587`: move native extension into the package.
- :gh:`589`: :meth:`Process.cpu_affinity` accepts any kind of iterable (set,
  tuple, ...), not only lists.
- :gh:`594`: all deprecated APIs were removed.
- :gh:`599`, [Windows]: :meth:`Process.name` can now be determined for all
  processes even when running as a limited user.
- :gh:`602`: pre-commit GIT hook.
- :gh:`629`: enhanced support for ``pytest`` and ``nose`` test runners.
- :gh:`616`, [Windows]: add ``inet_ntop()`` function for Windows XP.

**Bug fixes**

- :gh:`428`, [POSIX], **[critical]**: correct handling of zombie processes on
  POSIX. Introduced new :exc:`ZombieProcess` exception class.
- :gh:`512`, [BSD], **[critical]**: fix segfault in :func:`net_connections`.
- :gh:`555`, [Linux]: :func:`users` correctly handles ``":0"`` as an alias
  for ``"localhost"``.
- :gh:`579`, [Windows]: fixed :meth:`Process.open_files` for PID > 64K.
- :gh:`579`, [Windows]: fixed many compiler warnings.
- :gh:`585`, [FreeBSD]: :func:`net_connections` may raise ``KeyError``.
- :gh:`586`, [FreeBSD], **[critical]**: :meth:`Process.cpu_affinity`
  segfaults on set in case an invalid CPU number is provided.
- :gh:`593`, [FreeBSD], **[critical]**: :meth:`Process.memory_maps`
  segfaults.
- :gh:`606`: :meth:`Process.parent` may swallow :exc:`NoSuchProcess`
  exceptions.
- :gh:`611`, [SunOS]: :func:`net_io_counters` has send and received swapped
- :gh:`614`, [Linux]:: :func:`cpu_count` with ``logical=False`` return the
  number of sockets instead of cores.
- :gh:`618`, [SunOS]: swap tests fail on Solaris when run as normal user.
- :gh:`628`, [Linux]: :meth:`Process.name` truncates string in case it
  contains spaces or parentheses.

2.2.1 — 2015-02-02
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`572`, [Linux]: fix "ValueError: ambiguous inode with multiple PIDs
  references" for :meth:`Process.connections`. (patch by Bruno Binet)

2.2.0 — 2015-01-06
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`521`: drop support for Python 2.4 and 2.5.
- :gh:`553`: new `pstree.py`_ script.
- :gh:`564`: C extension version mismatch in case the user messed up with
  psutil installation or with sys.path is now detected at import time.
- :gh:`568`: new `pidof.py`_ script.
- :gh:`569`, [FreeBSD]: add support for :meth:`Process.cpu_affinity` on
  FreeBSD.

**Bug fixes**

- :gh:`496`, [SunOS], **[critical]**: can't import psutil.
- :gh:`547`, [POSIX]: :meth:`Process.username` may raise ``KeyError`` if UID
  can't be resolved.
- :gh:`551`, [Windows]: get rid of the unicode hack for
  :func:`net_io_counters` NIC names.
- :gh:`556`, [Linux]: lots of file handles were left open.
- :gh:`561`, [Linux]: :func:`net_connections` might skip some legitimate UNIX
  sockets. (patch by spacewander)
- :gh:`565`, [Windows]: use proper encoding for :meth:`Process.username` and
  :func:`users`. (patch by Sylvain Mouquet)
- :gh:`567`, [Linux]: in the alternative implementation of
  :meth:`Process.cpu_affinity` ``PyList_Append`` and ``Py_BuildValue`` return
  values are not checked.
- :gh:`569`, [FreeBSD]: fix memory leak in :func:`cpu_count` with
  ``logical=False``.
- :gh:`571`, [Linux]: :meth:`Process.open_files` might swallow
  :exc:`AccessDenied` exceptions and return an incomplete list of open files.

2.1.3 — 2014-09-26
^^^^^^^^^^^^^^^^^^

- :gh:`536`, [Linux], **[critical]**: fix "undefined symbol: CPU_ALLOC"
  compilation error.

2.1.2 — 2014-09-21
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`407`: project moved from Google Code to Github; code moved from
  Mercurial to Git.
- :gh:`492`: use ``tox`` to run tests on multiple Python versions.  (patch by
  msabramo)
- :gh:`505`, [Windows]: distribution as wheel packages.
- :gh:`511`: add `ps.py`_ script.

**Bug fixes**

- :gh:`340`, [Windows]: :meth:`Process.open_files` no longer hangs.  (patch
  by Jeff Tang)
- :gh:`501`, [Windows]: :func:`disk_io_counters` may return negative values.
- :gh:`503`, [Linux]: in rare conditions :meth:`Process.exe`,
  :meth:`Process.open_files` and
  :meth:`Process.connections` can raise ``OSError(ESRCH)`` instead of
  :exc:`NoSuchProcess`.
- :gh:`504`, [Linux]: can't build RPM packages via setup.py
- :gh:`506`, [Linux], **[critical]**: Python 2.4 support was broken.
- :gh:`522`, [Linux]: :meth:`Process.cpu_affinity` might return ``EINVAL``.
  (patch by David Daeschler)
- :gh:`529`, [Windows]: :meth:`Process.exe` may raise unhandled
  ``WindowsError`` exception for PIDs 0 and 4.  (patch by Jeff Tang)
- :gh:`530`, [Linux]: :func:`disk_io_counters` may crash on old Linux distros
  (< 2.6.5)  (patch by Yaolong Huang)
- :gh:`533`, [Linux]: :meth:`Process.memory_maps` may raise ``TypeError`` on
  old Linux distros.

2.1.1 — 2014-04-30
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`446`, [Windows]: fix encoding error when using :func:`net_io_counters`
  on Python 3. (patch by Szigeti Gabor Niif)
- :gh:`460`, [Windows]: :func:`net_io_counters` wraps after 4G.
- :gh:`491`, [Linux]: :func:`net_connections` exceptions. (patch by Alexander
  Grothe)

2.1.0 — 2014-04-08
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`387`: system-wide open connections a-la ``netstat`` (add
  :func:`net_connections`).

**Bug fixes**

- :gh:`421`, [SunOS], **[critical]**: psutil does not compile on SunOS 5.10.
  (patch by Naveed Roudsari)
- :gh:`489`, [Linux]: :func:`disk_partitions` return an empty list.

2.0.0 — 2014-03-10
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`424`, [Windows]: installer for Python 3.X 64 bit.
- :gh:`427`: number of logical CPUs and physical cores (:func:`cpu_count`).
- :gh:`447`: :func:`wait_procs` ``timeout`` parameter is now optional.
- :gh:`452`: make :class:`Process` instances hashable and usable with ``set()``
  s.
- :gh:`453`: tests on Python < 2.7 require ``unittest2`` module.
- :gh:`459`: add a Makefile for running tests and other repetitive tasks (also
  on Windows).
- :gh:`463`: make timeout parameter of ``cpu_percent*`` functions default to
  ``0.0`` 'cause it's a common trap to introduce slowdowns.
- :gh:`468`: move documentation to readthedocs.com.
- :gh:`477`: :meth:`Process.cpu_percent` is about 30% faster.  (suggested by
  crusaderky)
- :gh:`478`, [Linux]: almost all APIs are about 30% faster on Python 3.X.
- :gh:`479`: long deprecated ``psutil.error`` module is gone; exception classes
  now live in psutil namespace only.

**Bug fixes**

- :gh:`193`: :class:`Popen` constructor can throw an exception if the spawned
  process terminates quickly.
- :gh:`340`, [Windows]: :meth:`Process.open_files` no longer hangs.  (patch
  by jtang@vahna.net)
- :gh:`443`, [Linux]: fix a potential overflow issue for
  :meth:`Process.cpu_affinity` (set) on systems with more than 64 CPUs.
- :gh:`448`, [Windows]: :meth:`Process.children` and :meth:`Process.ppid`
  memory leak (patch by Ulrich Klank).
- :gh:`457`, [POSIX]: :func:`pid_exists` always returns ``True`` for PID 0.
- :gh:`461`: namedtuples are not pickle-able.
- :gh:`466`, [Linux]: :meth:`Process.exe` improper null bytes handling.
  (patch by Gautam Singh)
- :gh:`470`: :func:`wait_procs` might not wait.  (patch by crusaderky)
- :gh:`471`, [Windows]: :meth:`Process.exe` improper unicode handling. (patch
  by alex@mroja.net)
- :gh:`473`: :class:`Popen` ``wait()`` method does not set returncode
  attribute.
- :gh:`474`, [Windows]: :meth:`Process.cpu_percent` is no longer capped at
  100%.
- :gh:`476`, [Linux]: encoding error for :meth:`Process.name` and
  :meth:`Process.cmdline`.

**API changes**

For the sake of consistency a lot of psutil APIs have been renamed. In most
cases accessing the old names will work but it will cause a
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

- All :class:`Process` ``get_*`` methods lost the ``get_`` prefix. E.g.
  ``get_ext_memory_info()`` was renamed to ``memory_info_ex()``. Assuming ``p =
  psutil.Process()``:

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

- All :class:`Process` ``set_*`` methods lost the ``set_`` prefix. Assuming ``p
  = psutil.Process()``:

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

- Except for ``pid``, all :class:`Process` class properties have been turned
  into methods. This is the only case which there are no aliases. Assuming ``p
  = psutil.Process()``:

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

- timeout parameter of ``cpu_percent*`` functions defaults to 0.0 instead of
  0.1.
- long deprecated ``psutil.error`` module is gone; exception classes now live
  in "psutil" namespace only.
- :class:`Process` instances' ``retcode`` attribute returned by
  :func:`wait_procs` has been renamed to ``returncode`` for consistency with
  ``subprocess.Popen``.

1.2.1 — 2013-11-25
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`348`, [Windows], **[critical]**: fixed "ImportError: DLL load failed"
  occurring on module import on Windows XP.
- :gh:`425`, [SunOS], **[critical]**: crash on import due to failure at
  determining ``BOOT_TIME``.
- :gh:`443`, [Linux]: :meth:`Process.cpu_affinity` can't set affinity on
  systems with more than 64 cores.

1.2.0 — 2013-11-20
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`439`: assume ``os.getpid()`` if no argument is passed to
  :class:`Process` class constructor.
- :gh:`440`: new :func:`wait_procs` utility function which waits for multiple
  processes to terminate.

**Bug fixes**

- :gh:`348`, [Windows]: fix "ImportError: DLL load failed" occurring on module
  import on Windows XP / Vista.

1.1.3 — 2013-11-07
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`442`, [Linux], **[critical]**: psutil won't compile on certain version
  of Linux because of missing ``prlimit(2)`` syscall.

1.1.2 — 2013-10-22
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`442`, [Linux], **[critical]**: psutil won't compile on Debian 6.0
  because of missing ``prlimit(2)`` syscall.

1.1.1 — 2013-10-08
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`442`, [Linux], **[critical]**: psutil won't compile on kernels < 2.6.36
  due to missing ``prlimit(2)`` syscall.

1.1.0 — 2013-09-28
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`410`: host tar.gz and Windows binary files are on PyPI.
- :gh:`412`, [Linux]: get/set process resource limits
  (:meth:`Process.rlimit`).
- :gh:`415`, [Windows]: :meth:`Process.children` is an order of magnitude
  faster.
- :gh:`426`, [Windows]: :meth:`Process.name` is an order of magnitude faster.
- :gh:`431`, [POSIX]: :meth:`Process.name` is slightly faster because it
  unnecessarily retrieved also :meth:`Process.cmdline`.

**Bug fixes**

- :gh:`391`, [Windows]: :func:`cpu_times_percent` returns negative
  percentages.
- :gh:`408`: ``STATUS_*`` and ``CONN_*`` constants don't properly serialize on
  JSON.
- :gh:`411`, [Windows]: `disk_usage.py`_ may pop-up a GUI error.
- :gh:`413`, [Windows]: :meth:`Process.memory_info` leaks memory.
- :gh:`414`, [Windows]: :meth:`Process.exe` on Windows XP may raise
  ``ERROR_INVALID_PARAMETER``.
- :gh:`416`: :func:`disk_usage` doesn't work well with unicode path names.
- :gh:`430`, [Linux]: :meth:`Process.io_counters` report wrong number of r/w
  syscalls.
- :gh:`435`, [Linux]: :func:`net_io_counters` might report erreneous NIC
  names.
- :gh:`436`, [Linux]: :func:`net_io_counters` reports a wrong ``dropin``
  value.

**API changes**

- :gh:`408`: turn ``STATUS_*`` and ``CONN_*`` constants into plain Python
  strings.

1.0.1 — 2013-07-12
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`405`: :func:`net_io_counters` ``pernic=True`` no longer works as
  intended in 1.0.0.

1.0.0 — 2013-07-10
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`18`, [SunOS]: add Solaris support (yay!)  (thanks Justin Venus)
- :gh:`367`: :meth:`Process.connections` ``status`` strings are now
  constants.
- :gh:`380`: test suite exits with non-zero on failure.  (patch by
  floppymaster)
- :gh:`391`: introduce unittest2 facilities and provide workarounds if
  unittest2 is not installed (Python < 2.7).

**Bug fixes**

- :gh:`374`, [Windows]: negative memory usage reported if process uses a lot of
  memory.
- :gh:`379`, [Linux]: :meth:`Process.memory_maps` may raise ``ValueError``.
- :gh:`394`, [macOS]: mapped memory regions of :meth:`Process.memory_maps`
  report incorrect file name.
- :gh:`404`, [Linux]: ``sched_*affinity()`` are implicitly declared. (patch by
  Arfrever)

**API changes**

- :meth:`Process.connections` ``status`` field is no longer a string but a
  constant object (``psutil.CONN_*``).
- :meth:`Process.connections` ``local_address`` and ``remote_address`` fields
  renamed to ``laddr`` and ``raddr``.
- psutil.network_io_counters() renamed to :func:`net_io_counters`.

0.7.1 — 2013-05-03
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`325`, [BSD], **[critical]**: :func:`virtual_memory` can raise
  ``SystemError``. (patch by Jan Beich)
- :gh:`370`, [BSD]: :meth:`Process.connections` requires root.  (patch by
  John Baldwin)
- :gh:`372`, [BSD]: different process methods raise :exc:`NoSuchProcess`
  instead of
  :exc:`AccessDenied`.

0.7.0 — 2013-04-12
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`233`: code migrated to Mercurial (yay!)
- :gh:`246`: psutil.error module is deprecated and scheduled for removal.
- :gh:`328`, [Windows]: :meth:`Process.ionice` support.
- :gh:`359`: add :func:`boot_time` as a substitute of ``psutil.BOOT_TIME``
  since the latter cannot reflect system clock updates.
- :gh:`361`, [Linux]: :func:`cpu_times` now includes new ``steal``, ``guest``
  and ``guest_nice`` fields available on recent Linux kernels. Also,
  :func:`cpu_percent` is more accurate.
- :gh:`362`: add :func:`cpu_times_percent` (per-CPU-time utilization as a
  percentage).

**Bug fixes**

- :gh:`234`, [Windows]: :func:`disk_io_counters` fails to list certain disks.
- :gh:`264`, [Windows]: use of :func:`disk_partitions` may cause a message
  box to appear.
- :gh:`313`, [Linux], **[critical]**: :func:`virtual_memory` and
  :func:`swap_memory` can crash on certain exotic Linux flavors having an
  incomplete ``/proc`` interface. If that's the case we now set the
  unretrievable stats to ``0`` and raise ``RuntimeWarning`` instead.
- :gh:`315`, [macOS]: fix some compilation warnings.
- :gh:`317`, [Windows]: cannot set process CPU affinity above 31 cores.
- :gh:`319`, [Linux]: :meth:`Process.memory_maps` raises ``KeyError``
  'Anonymous' on Debian squeeze.
- :gh:`321`, [POSIX]: :meth:`Process.ppid` property is no longer cached as
  the kernel may set the PPID to 1 in case of a zombie process.
- :gh:`323`, [macOS]: :func:`disk_io_counters` ``read_time`` and
  ``write_time`` parameters were reporting microseconds not milliseconds.
  (patch by Gregory Szorc)
- :gh:`331`: :meth:`Process.cmdline` is no longer cached after first access
  as it may change.
- :gh:`333`, [macOS]: leak of Mach ports (patch by rsesek@google.com)
- :gh:`337`, [Linux], **[critical]**: :class:`Process` methods not working
  because of a poor ``/proc`` implementation will raise ``NotImplementedError``
  rather than ``RuntimeError`` and :meth:`Process.as_dict` will not blow up.
  (patch by Curtin1060)
- :gh:`338`, [Linux]: :func:`disk_io_counters` fails to find some disks.
- :gh:`339`, [FreeBSD]: ``get_pid_list()`` can allocate all the memory on
  system.
- :gh:`341`, [Linux], **[critical]**: psutil might crash on import due to error
  in retrieving system terminals map.
- :gh:`344`, [FreeBSD]: :func:`swap_memory` might return incorrect results
  due to ``kvm_open(3)`` not being called. (patch by Jean Sebastien)
- :gh:`338`, [Linux]: :func:`disk_io_counters` fails to find some disks.
- :gh:`351`, [Windows]: if psutil is compiled with MinGW32 (provided installers
  for py2.4 and py2.5 are) :func:`disk_io_counters` will fail. (Patch by
  m.malycha)
- :gh:`353`, [macOS]: :func:`users` returns an empty list on macOS 10.8.
- :gh:`356`: :meth:`Process.parent` now checks whether parent PID has been
  reused in which case returns ``None``.
- :gh:`365`: :meth:`Process.nice` (set) should check PID has not been reused
  by another process.
- :gh:`366`, [FreeBSD], **[critical]**: :meth:`Process.memory_maps`,
  :meth:`Process.num_fds`,
  :meth:`Process.open_files` and :meth:`Process.cwd` methods raise
  ``RuntimeError`` instead of :exc:`AccessDenied`.

**API changes**

- :meth:`Process.cmdline` property is no longer cached after first access.
- :meth:`Process.ppid` property is no longer cached after first access.
- [Linux] :class:`Process` methods not working because of a poor ``/proc``
  implementation will raise ``NotImplementedError`` instead of
  ``RuntimeError``.
- ``psutil.error`` module is deprecated and scheduled for removal.

0.6.1 — 2012-08-16
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`316`: :meth:`Process.cmdline` property now makes a better job at
  guessing the process executable from the cmdline.

**Bug fixes**

- :gh:`316`: :meth:`Process.exe` was resolved in case it was a symlink.
- :gh:`318`, **[critical]**: Python 2.4 compatibility was broken.

**API changes**

- :meth:`Process.exe` can now return an empty string instead of raising
  :exc:`AccessDenied`.
- :meth:`Process.exe` is no longer resolved in case it's a symlink.

0.6.0 — 2012-08-13
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`216`, [POSIX]: :meth:`Process.connections` UNIX sockets support.
- :gh:`220`, [FreeBSD]: ``get_connections()`` has been rewritten in C and no
  longer requires ``lsof``.
- :gh:`222`, [macOS]: add support for :meth:`Process.cwd`.
- :gh:`261`: per-process extended memory info
  (:meth:`Process.memory_info_ex`).
- :gh:`295`, [macOS]: :meth:`Process.exe` path is now determined by asking
  the OS instead of being guessed from :meth:`Process.cmdline`.
- :gh:`297`, [macOS]: the :class:`Process` methods below were always raising
  :exc:`AccessDenied` for any process except the current one. Now this is no
  longer true. Also they are 2.5x faster. :meth:`Process.name`,
  :meth:`Process.memory_info`,
  :meth:`Process.memory_percent`, :meth:`Process.cpu_times`,
  :meth:`Process.cpu_percent`,
  :meth:`Process.num_threads`.
- :gh:`300`: add `pmap.py`_ script.
- :gh:`301`: :func:`process_iter` now yields processes sorted by their PIDs.
- :gh:`302`: per-process number of voluntary and involuntary context switches
  (:meth:`Process.num_ctx_switches`).
- :gh:`303`, [Windows]: the :class:`Process` methods below were always raising
  :exc:`AccessDenied` for any process not owned by current user. Now this is no
  longer true:
  :meth:`Process.create_time`, :meth:`Process.cpu_times`,
  :meth:`Process.cpu_percent`,
  :meth:`Process.memory_info`, :meth:`Process.memory_percent`,
  :meth:`Process.num_handles`,
  :meth:`Process.io_counters`.
- :gh:`305`: add `netstat.py`_ script.
- :gh:`311`: system memory functions has been refactorized and rewritten and
  now provide a more detailed and consistent representation of the system
  memory. Added new :func:`virtual_memory` and :func:`swap_memory`
  functions. All old memory-related functions are deprecated. Also two new
  example scripts were added:  `free.py`_ and `meminfo.py`_.
- :gh:`312`: ``net_io_counters()`` namedtuple includes 4 new fields: ``errin``,
  ``errout``, ``dropin`` and ``dropout``, reflecting the number of packets
  dropped and with errors.

**Bug fixes**

- :gh:`298`, [macOS], [BSD]: memory leak in :meth:`Process.num_fds`.
- :gh:`299`: potential memory leak every time ``PyList_New(0)`` is used.
- :gh:`303`, [Windows], **[critical]**: potential heap corruption in
  :meth:`Process.num_threads` and :meth:`Process.status` methods.
- :gh:`305`, [FreeBSD], **[critical]**: can't compile on FreeBSD 9 due to
  removal of ``utmp.h``.
- :gh:`306`, **[critical]**: at C level, errors are not checked when invoking
  ``Py*`` functions which create or manipulate Python objects leading to
  potential memory related errors and/or segmentation faults.
- :gh:`307`, [FreeBSD]: values returned by :func:`net_io_counters` are wrong.
- :gh:`308`, [BSD], [Windows]: ``psutil.virtmem_usage()`` wasn't actually
  returning information about swap memory usage as it was supposed to do. It
  does now.
- :gh:`309`: :meth:`Process.open_files` might not return files which can not
  be accessed due to limited permissions. :exc:`AccessDenied` is now raised
  instead.

**API changes**

- ``psutil.phymem_usage()`` is deprecated (use :func:`virtual_memory`)
- ``psutil.virtmem_usage()`` is deprecated (use :func:`swap_memory`)
- [Linux]: ``psutil.phymem_buffers()`` is deprecated (use
  :func:`virtual_memory`)
- [Linux]: ``psutil.cached_phymem()`` is deprecated (use
  :func:`virtual_memory`)
- [Windows], [BSD]: ``psutil.virtmem_usage()`` now returns information about
  swap memory instead of virtual memory.

0.5.1 — 2012-06-29
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`293`, [Windows]: :meth:`Process.exe` path is now determined by asking
  the OS instead of being guessed from :meth:`Process.cmdline`.

**Bug fixes**

- :gh:`292`, [Linux]: race condition in process :meth:`Process.open_files`,
  :meth:`Process.connections`, :meth:`Process.threads`.
- :gh:`294`, [Windows]: :meth:`Process.cpu_affinity` is only able to set CPU
  #0.

0.5.0 — 2012-06-27
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`195`, [Windows]: number of handles opened by process
  (:meth:`Process.num_handles`).
- :gh:`209`: :func:`disk_partitions` now provides also mount options.
- :gh:`229`: list users currently connected on the system (:func:`users`).
- :gh:`238`, [Linux], [Windows]: process CPU affinity (get and set,
  :meth:`Process.cpu_affinity`).
- :gh:`242`: add ``recursive=True`` to :meth:`Process.children`: return all
  process descendants.
- :gh:`245`, [POSIX]: :meth:`Process.wait` incrementally consumes less CPU
  cycles.
- :gh:`257`, [Windows]: removed Windows 2000 support.
- :gh:`258`, [Linux]: :meth:`Process.memory_info` is now 0.5x faster.
- :gh:`260`: process's mapped memory regions. (Windows patch by wj32.64, macOS
  patch by Jeremy Whitlock)
- :gh:`262`, [Windows]: :func:`disk_partitions` was slow due to inspecting
  the floppy disk drive also when parameter is ``all=False``.
- :gh:`273`: ``psutil.get_process_list()`` is deprecated.
- :gh:`274`: psutil no longer requires ``2to3`` at installation time in order
  to work with Python 3.
- :gh:`278`: new :meth:`Process.as_dict` method.
- :gh:`281`: :meth:`Process.ppid`, :meth:`Process.name`,
  :meth:`Process.exe`,
  :meth:`Process.cmdline` and :meth:`Process.create_time` properties of
  :class:`Process` class are now cached after being accessed.
- :gh:`282`: ``psutil.STATUS_*`` constants can now be compared by using their
  string representation.
- :gh:`283`: speedup :meth:`Process.is_running` by caching its return value
  in case the process is terminated.
- :gh:`284`, [POSIX]: per-process number of opened file descriptors
  (:meth:`Process.num_fds`).
- :gh:`287`: :func:`process_iter` now caches :class:`Process` instances
  between calls.
- :gh:`290`: :meth:`Process.nice` property is deprecated in favor of new
  ``get_nice()`` and ``set_nice()`` methods.

**Bug fixes**

- :gh:`193`: :class:`Popen` constructor can throw an exception if the spawned
  process terminates quickly.
- :gh:`240`, [macOS]: incorrect use of ``free()`` for
  :meth:`Process.connections`.
- :gh:`244`, [POSIX]: :meth:`Process.wait` can hog CPU resources if called
  against a process which is not our children.
- :gh:`248`, [Linux]: :func:`net_io_counters` might return erroneous NIC
  names.
- :gh:`252`, [Windows]: :meth:`Process.cwd` erroneously raise
  :exc:`NoSuchProcess` for processes owned by another user.  It now raises
  :exc:`AccessDenied` instead.
- :gh:`266`, [Windows]: ``psutil.get_pid_list()`` only shows 1024 processes.
  (patch by Amoser)
- :gh:`267`, [macOS]: :meth:`Process.connections` returns wrong remote
  address. (Patch by Amoser)
- :gh:`272`, [Linux]: :meth:`Process.open_files` potential race condition can
  lead to unexpected :exc:`NoSuchProcess` exception. Also, we can get incorrect
  reports of not absolutized path names.
- :gh:`275`, [Linux]: ``Process.io_counters()`` erroneously raise
  :exc:`NoSuchProcess` on old Linux versions. Where not available it now raises
  ``NotImplementedError``.
- :gh:`286`: :meth:`Process.is_running` doesn't actually check whether PID
  has been reused.
- :gh:`314`: :meth:`Process.children` can sometimes return non-children.

**API changes**

- ``Process.nice`` property is deprecated in favor of new ``get_nice()`` and
  ``set_nice()`` methods.
- ``psutil.get_process_list()`` is deprecated.
- :meth:`Process.ppid`, :meth:`Process.name`, :meth:`Process.exe`,
  :meth:`Process.cmdline` and :meth:`Process.create_time` properties of
  :class:`Process` class are now cached after being accessed, meaning
  :exc:`NoSuchProcess` will no longer be raised in case the process is gone in
  the meantime.
- ``psutil.STATUS_*`` constants can now be compared by using their string
  representation.

0.4.1 — 2011-12-14
^^^^^^^^^^^^^^^^^^

**Bug fixes**

- :gh:`228`: some example scripts were not working with Python 3.
- :gh:`230`, [Windows], [macOS]: fix memory leak in
  :meth:`Process.connections`.
- :gh:`232`, [Linux]: ``psutil.phymem_usage()`` can report erroneous values
  which are different than ``free`` command.
- :gh:`236`, [Windows]: fix memory/handle leak in
  :meth:`Process.memory_info`,
  :meth:`Process.suspend` and :meth:`Process.resume` methods.

0.4.0 — 2011-10-29
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`150`: network I/O counters (:func:`net_io_counters`). (macOS and
  Windows patch by Jeremy Whitlock)
- :gh:`154`, [FreeBSD]: add support for :meth:`Process.cwd`.
- :gh:`157`, [Windows]: provide installer for Python 3.2 64-bit.
- :gh:`198`: :meth:`Process.wait` with ``timeout=0`` can now be used to make
  the function return immediately.
- :gh:`206`: disk I/O counters (:func:`disk_io_counters`). (macOS and Windows
  patch by Jeremy Whitlock)
- :gh:`213`: add `iotop.py`_ script.
- :gh:`217`: :meth:`Process.connections` now has a ``kind`` argument to
  filter for connections with different criteria.
- :gh:`221`, [FreeBSD]: :meth:`Process.open_files` has been rewritten in C
  and no longer relies on ``lsof``.
- :gh:`223`: add `top.py`_ script.
- :gh:`227`: add `nettop.py`_ script.

**Bug fixes**

- :gh:`135`, [macOS]: psutil cannot create :class:`Process` object.
- :gh:`144`, [Linux]: no longer support 0 special PID.
- :gh:`188`, [Linux]: psutil import error on Linux ARM architectures.
- :gh:`194`, [POSIX]: :meth:`Process.cpu_percent` now reports a percentage
  over 100 on multicore processors.
- :gh:`197`, [Linux]: :meth:`Process.connections` is broken on platforms not
  supporting IPv6.
- :gh:`200`, [Linux], **[critical]**: ``psutil.NUM_CPUS`` not working on armel
  and sparc architectures and causing crash on module import.
- :gh:`201`, [Linux]: :meth:`Process.connections` is broken on big-endian
  architectures.
- :gh:`211`: :class:`Process` instance can unexpectedly raise
  :exc:`NoSuchProcess` if tested for equality with another object.
- :gh:`218`, [Linux], **[critical]**: crash at import time on Debian 64-bit
  because of a missing line in ``/proc/meminfo``.
- :gh:`226`, [FreeBSD], **[critical]**: crash at import time on FreeBSD 7 and
  minor.

0.3.0 — 2011-07-08
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`125`: system per-cpu percentage utilization and times
  (:meth:`Process.cpu_times`,
  :meth:`Process.cpu_percent`).
- :gh:`163`: per-process associated terminal / TTY
  (:meth:`Process.terminal`).
- :gh:`171`: added ``get_phymem()`` and ``get_virtmem()`` functions returning
  system memory information (``total``, ``used``, ``free``) and memory percent
  usage. ``total_*``, ``avail_*`` and ``used_*`` memory functions are
  deprecated.
- :gh:`172`: disk usage statistics (:func:`disk_usage`).
- :gh:`174`: mounted disk partitions (:func:`disk_partitions`).
- :gh:`179`: setuptools is now used in setup.py

**Bug fixes**

- :gh:`159`, [Windows]: ``SetSeDebug()`` does not close handles or unset
  impersonation on return.
- :gh:`164`, [Windows]: wait function raises a ``TimeoutException`` when a
  process returns ``-1``.
- :gh:`165`: :meth:`Process.status` raises an unhandled exception.
- :gh:`166`: :meth:`Process.memory_info` leaks handles hogging system
  resources.
- :gh:`168`: :func:`cpu_percent` returns erroneous results when used in
  non-blocking mode.  (patch by Philip Roberts)
- :gh:`178`, [macOS]: :meth:`Process.threads` leaks memory.
- :gh:`180`, [Windows]: :meth:`Process.num_threads` and
  :meth:`Process.threads` methods can raise :exc:`NoSuchProcess` exception
  while process still exists.

0.2.1 — 2011-03-20
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`64`: per-process I/O counters (:meth:`Process.io_counters`).
- :gh:`116`: per-process :meth:`Process.wait` (wait for process to terminate
  and return its exit code).
- :gh:`134`: per-process threads (:meth:`Process.threads`).
- :gh:`136`: :meth:`Process.exe` path on FreeBSD is now determined by asking
  the kernel instead of guessing it from cmdline[0].
- :gh:`137`: per-process real, effective and saved user and group ids
  (:meth:`Process.gids`).
- :gh:`140`: system boot time (:func:`boot_time`).
- :gh:`142`: per-process get and set niceness (priority)
  (:meth:`Process.nice`).
- :gh:`143`: per-process status (:meth:`Process.status`).
- :gh:`147` [Linux]: per-process I/O niceness / priority
  (:meth:`Process.ionice`).
- :gh:`148`: :class:`Popen` class which tidies up ``subprocess.Popen`` and
  :class:`Process` class in a single interface.
- :gh:`152`, [macOS]: :meth:`Process.open_files` implementation has been
  rewritten in C and no longer relies on ``lsof`` resulting in a 3x speedup.
- :gh:`153`, [macOS]: :meth:`Process.connections` implementation has been
  rewritten in C and no longer relies on ``lsof`` resulting in a 3x speedup.

**Bug fixes**

- :gh:`83`, [macOS]:  :meth:`Process.cmdline` is empty on macOS 64-bit.
- :gh:`130`, [Linux]: a race condition can cause ``IOError`` exception be
  raised on if process disappears between ``open()`` and the subsequent
  ``read()`` call.
- :gh:`145`, [Windows], **[critical]**: ``WindowsError`` was raised instead of
  :exc:`AccessDenied` when using :meth:`Process.resume` or
  :meth:`Process.suspend`.
- :gh:`146`, [Linux]: :meth:`Process.exe` property can raise ``TypeError`` if
  path contains NULL bytes.
- :gh:`151`, [Linux]: :meth:`Process.exe` and :meth:`Process.cwd` for PID 0
  return inconsistent data.

**API changes**

- :class:`Process` ``uid`` and ``gid`` properties are deprecated in favor of
  ``uids`` and ``gids`` properties.

0.2.0 — 2010-11-13
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`79`: per-process open files (:meth:`Process.open_files`).
- :gh:`88`: total system physical cached memory.
- :gh:`88`: total system physical memory buffers used by the kernel.
- :gh:`91`: add :meth:`Process.send_signal` and :meth:`Process.terminate`
  methods.
- :gh:`95`: :exc:`NoSuchProcess` and :exc:`AccessDenied` exception classes now
  provide ``pid``, ``name`` and ``msg`` attributes.
- :gh:`97`: per-process children (:meth:`Process.children`).
- :gh:`98`: :meth:`Process.cpu_times` and :meth:`Process.memory_info` now
  return a namedtuple instead of a tuple.
- :gh:`103`: per-process opened TCP and UDP connections
  (:meth:`Process.connections`).
- :gh:`107`, [Windows]: add support for Windows 64 bit. (patch by cjgohlke)
- :gh:`111`: per-process executable name (:meth:`Process.exe`).
- :gh:`113`: exception messages now include :meth:`Process.name` and
  :attr:`Process.pid`.
- :gh:`114`, [Windows]: :meth:`Process.username` has been rewritten in pure C
  and no longer uses WMI resulting in a big speedup. Also, pywin32 is no longer
  required as a third-party dependency. (patch by wj32)
- :gh:`117`, [Windows]: added support for Windows 2000.
- :gh:`123`: :func:`cpu_percent` and :meth:`Process.cpu_percent` accept a
  new ``interval`` parameter.
- :gh:`129`: per-process threads (:meth:`Process.threads`).

**Bug fixes**

- :gh:`80`: fixed warnings when installing psutil with easy_install.
- :gh:`81`, [Windows]: psutil fails to compile with Visual Studio.
- :gh:`94`: :meth:`Process.suspend` raises ``OSError`` instead of
  :exc:`AccessDenied`.
- :gh:`86`, [FreeBSD]: psutil didn't compile against FreeBSD 6.x.
- :gh:`102`, [Windows]: orphaned process handles obtained by using
  ``OpenProcess`` in C were left behind every time :class:`Process` class was
  instantiated.
- :gh:`111`, [POSIX]: ``path`` and ``name`` :class:`Process` properties report
  truncated or erroneous values on POSIX.
- :gh:`120`, [macOS]: :func:`cpu_percent` always returning 100%.
- :gh:`112`: ``uid`` and ``gid`` properties don't change if process changes
  effective user/group id at some point.
- :gh:`126`: :meth:`Process.ppid`, :meth:`Process.uids`,
  :meth:`Process.gids`,
  :meth:`Process.name`,
  :meth:`Process.exe`, :meth:`Process.cmdline` and
  :meth:`Process.create_time` properties are no longer cached and correctly
  raise :exc:`NoSuchProcess` exception if the process disappears.

**API changes**

- ``psutil.Process.path`` property is deprecated and works as an alias for
  ``psutil.Process.exe`` property.
- :meth:`Process.kill`: signal argument was removed - to send a signal to the
  process use :meth:`Process.send_signal` method instead.
- :meth:`Process.memory_info` returns a nametuple instead of a tuple.
- :func:`cpu_times` returns a nametuple instead of a tuple.
- New :class:`Process` methods: :meth:`Process.open_files`,
  :meth:`Process.connections`,
  :meth:`Process.send_signal` and :meth:`Process.terminate`.
- :meth:`Process.ppid`, :meth:`Process.uids`, :meth:`Process.gids`,
  :meth:`Process.name`,
  :meth:`Process.exe`, :meth:`Process.cmdline` and
  :meth:`Process.create_time` properties are no longer cached and raise
  :exc:`NoSuchProcess` exception if process disappears.
- :func:`cpu_percent` no longer returns immediately (see issue 123).
- :meth:`Process.cpu_percent` and :func:`cpu_percent` no longer returns
  immediately by default (see issue :gh:`123`).

0.1.3 — 2010-03-02
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`14`: :meth:`Process.username`.
- :gh:`51`, [Linux], [Windows]: per-process current working directory
  (:meth:`Process.cwd`).
- :gh:`59`: :meth:`Process.is_running` is now 10 times faster.
- :gh:`61`, [FreeBSD]: added supoprt for FreeBSD 64 bit.
- :gh:`71`: per-process suspend and resume (:meth:`Process.suspend` and
  :meth:`Process.resume`).
- :gh:`75`: Python 3 support.

**Bug fixes**

- :gh:`36`: :meth:`Process.cpu_times` and :meth:`Process.memory_info`
  functions succeeded. also for dead processes while a :exc:`NoSuchProcess`
  exception is supposed to be raised.
- :gh:`48`, [FreeBSD]: incorrect size for MIB array defined in ``getcmdargs``.
- :gh:`49`, [FreeBSD]: possible memory leak due to missing ``free()`` on error
  condition in ``getcmdpath()``.
- :gh:`50`, [BSD]: fixed ``getcmdargs()`` memory fragmentation.
- :gh:`55`, [Windows]: ``test_pid_4`` was failing on Windows Vista.
- :gh:`57`: some unit tests were failing on systems where no swap memory is
  available.
- :gh:`58`: :meth:`Process.is_running` is now called before
  :meth:`Process.kill` to make sure we are going to kill the correct process.
- :gh:`73`, [macOS]: virtual memory size reported on includes shared library
  size.
- :gh:`77`: :exc:`NoSuchProcess` wasn't raised on :meth:`Process.create_time`
  if
  :meth:`Process.kill` was used first.

0.1.2 — 2009-05-06
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`32`: Per-process CPU user/kernel times (:meth:`Process.cpu_times`).
- :gh:`33`: Per-process create time (:meth:`Process.create_time`).
- :gh:`34`: Per-process CPU utilization percentage
  (:meth:`Process.cpu_percent`).
- :gh:`38`: Per-process memory usage (bytes) (:meth:`Process.memory_info`).
- :gh:`41`: Per-process memory percent (:meth:`Process.memory_percent`).
- :gh:`39`: System uptime (:func:`boot_time`).
- :gh:`43`: Total system virtual memory.
- :gh:`46`: Total system physical memory.
- :gh:`44`: Total system used/free virtual and physical memory.

**Bug fixes**

- :gh:`36`, [Windows]: :exc:`NoSuchProcess` not raised when accessing timing
  methods.
- :gh:`40`, [FreeBSD], [macOS]: fix ``test_get_cpu_times`` failures.
- :gh:`42`, [Windows]: :meth:`Process.memory_percent` raises
  :exc:`AccessDenied`.

0.1.1 — 2009-03-06
^^^^^^^^^^^^^^^^^^

**Enhancements**

- :gh:`4`, [FreeBSD]: support for all functions of psutil.
- :gh:`9`, [macOS], [Windows]: add ``Process.uid`` and ``Process.gid``,
  returning process UID and GID.
- :gh:`11`: per-process parent object: :meth:`Process.parent` property
  returns a
  :class:`Process` object representing the parent process, and
  :meth:`Process.ppid` returns the parent PID.
- :gh:`12`, :gh:`15`:
  :exc:`NoSuchProcess` exception now raised when creating an object for a
  nonexistent process, or when retrieving information about a process that
  has gone away.
- :gh:`21`, [Windows]: :exc:`AccessDenied` exception created for raising access
  denied errors from ``OSError`` or ``WindowsError`` on individual platforms.
- :gh:`26`: :func:`process_iter` function to iterate over processes as
  :class:`Process` objects with a generator.
- :class:`Process` objects can now also be compared with == operator for
  equality (PID, name, command line are compared).

**Bug fixes**

- :gh:`16`, [Windows]: Special case for "System Idle Process" (PID 0) which
  otherwise would return an "invalid parameter" exception.
- :gh:`17`: get_process_list() ignores :exc:`NoSuchProcess` and
  :exc:`AccessDenied` exceptions during building of the list.
- :gh:`22`, [Windows]: :meth:`Process.kill` for PID 0 was failing with an
  unset exception.
- :gh:`23`, [Linux], [macOS]: create special case for :func:`pid_exists` with
  PID 0.
- :gh:`24`, [Windows], **[critical]**: :meth:`Process.kill` for PID 0 now
  raises
  :exc:`AccessDenied` exception instead of ``WindowsError``.
- :gh:`30`: psutil.get_pid_list() was returning two 0 PIDs.


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
