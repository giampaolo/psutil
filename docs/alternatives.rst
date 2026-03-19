Alternatives
============

.. contents::
   :local:
   :depth: 2

This page describes Python tools and modules that overlap with psutil,
to help you pick the right tool for the job.

Python standard library
-----------------------

os module
^^^^^^^^^

The :mod:`os` module provides a handful of process-related functions:
:func:`os.getpid`, :func:`os.getppid`, :func:`os.getuid`,
:func:`os.cpu_count`, :func:`os.getloadavg` (UNIX only). These are
cheap wrappers around POSIX syscalls and are perfectly fine when you
only need information about the *current* process and don't need
cross-platform code.

psutil goes further in every direction. Its primary goal is to provide a
**single portable interface** for concepts that are natively UNIX-only. Things
like process CPU and memory usage, open file descriptors, network connections,
signals, nice levels, and I/O counters exist as first-class OS primitives on
Linux and macOS, but have no direct equivalent on Windows. psutil implements
all of them on Windows too (using Win32 APIs, ``NtQuerySystemInformation`` and
WMI) so that code written against psutil runs unmodified on every supported
platform. Beyond portability, it also exposes the same information for *any*
process (not just the current one), and returns structured named tuples instead
of raw integers.

resource module
^^^^^^^^^^^^^^^

:mod:`resource` (UNIX only) lets you read and set resource limits
(``RLIMIT_*``) and get basic usage counters (user/system time, page
faults, I/O ops) for the *current* process or its children via
:func:`resource.getrusage`. It is the right tool when you specifically
want to enforce or inspect ``ulimit``-style limits.

psutil's :meth:`Process.rlimit` exposes the same limit interface in a
cross-platform way and extends it to arbitrary processes, not just the
caller.

subprocess module
^^^^^^^^^^^^^^^^^

Calling ``ps``, ``top``, ``netstat``, ``vmstat`` via
:mod:`subprocess` and parsing the text output is fragile: output
formats differ across OS versions and locales, parsing is error-prone,
and spawning a subprocess per sample is slow. psutil reads the same
kernel data sources directly without spawning any external processes.

/proc filesystem
^^^^^^^^^^^^^^^^

On Linux, ``/proc`` exposes process and system information as virtual files.
Reading ``/proc/pid/status`` or ``/proc/meminfo`` directly is fast and has no
dependencies, which is why some minimal containers or scripts do this. The
downsides are that it is Linux-only, the format may varies across kernel
versions, and you have to parse raw text yourself. psutil parses ``/proc``
internally on Linux, adds a consistent cross-platform API on top, and handles
edge cases (numeric overflow, compatibility with old kernels, graceful
fallbacks, etc.) transparently.

Third-party libraries
---------------------

Libraries that cover areas psutil does not, or that go deeper on a
specific platform or subsystem.

.. list-table::
   :header-rows: 1
   :widths: 5 25
   :class: longtable

   * - Library
     - Focus

   * - `distro <https://github.com/python-distro/distro>`_
     - Linux distro info (name, version, codename).

   * - `GPUtil <https://github.com/anderskm/gputil>`_ /
       `pynvml <https://github.com/gpuopenanalytics/pynvml>`_
     - NVIDIA GPU utilization and VRAM usage.

   * - `ifaddr <https://github.com/ifaddr/ifaddr>`_
     - Network interface address enumeration.
       Overlaps with :func:`net_if_addrs`.

   * - `prometheus_client <https://github.com/prometheus/client_python>`_
     - Export metrics to Prometheus. Use *alongside* psutil.

   * - `py-cpuinfo <https://github.com/workhorsy/py-cpuinfo>`_
     - CPU brand string, microarchitecture, feature flags.

   * - `pyroute2 <https://github.com/svinota/pyroute2>`_
     - Linux netlink (interfaces, routes, connections).
       Overlaps with :func:`net_if_addrs`, :func:`net_if_stats`,
       :func:`net_connections`.

   * - `pySMART <https://github.com/truenas/py-SMART>`_
     - S.M.A.R.T. disk health data. Complements
       :func:`disk_io_counters`.

   * - `pywin32 <https://github.com/mhammond/pywin32>`_
     - Win32 API bindings (Windows only).

   * - `setproctitle <https://github.com/dvarrazzo/py-setproctitle>`_
     - Set process title shown by ``ps``/``top``. Writes what
       :meth:`Process.name` reads.

   * - `wmi <https://github.com/tjguk/wmi>`_
     - WMI interface (Windows only).
