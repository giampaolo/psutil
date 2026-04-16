.. currentmodule:: psutil

Alternatives
============

This page describes Python tools and modules that overlap with psutil, to help
you pick the right tool for the job. See also :doc:`adoption` for notable
projects that use psutil.

Python standard library
-----------------------

.. seealso::
   :doc:`stdlib-equivalents` for a detailed function-by-function comparison.

os module
^^^^^^^^^

The :mod:`os` module provides a handful of process-related functions:
:func:`os.getpid`, :func:`os.getppid`, :func:`os.getuid`, :func:`os.cpu_count`,
:func:`os.getloadavg` (UNIX only). These are cheap wrappers around POSIX
syscalls and are perfectly fine when you only need information about the
*current* process and don't need cross-platform code.

psutil goes further in several directions. Its primary goal is to provide a
**single portable interface** for concepts that are traditionally UNIX-only.
Things like process CPU and memory usage, open file descriptors, network
connections, signals, nice levels, and I/O counters exist as first-class OS
primitives on Linux and macOS, but have no direct equivalent on Windows. psutil
implements all of them on Windows too (using Win32 APIs,
``NtQuerySystemInformation`` and WMI) so that code written against psutil runs
unmodified on every supported platform. Beyond portability, it also exposes the
same information for *any* process (not just the current one), and returns
structured named tuples instead of raw values.

resource module
^^^^^^^^^^^^^^^

:mod:`resource` (UNIX only) lets you read and set resource limits
(``RLIMIT_*``) and get basic usage counters (user/system time, page faults, I/O
ops) for the *current* process or its children via :func:`resource.getrusage`.
It is the right tool when you specifically want to enforce or inspect
``ulimit``-style limits.

psutil's :meth:`Process.rlimit` exposes the same interface but extends it to
all processes, not just the caller.

subprocess module
^^^^^^^^^^^^^^^^^

Calling tools like ``ps``, ``top``, ``netstat``, ``vmstat`` via
:mod:`subprocess` and parsing their output is fragile: output formats differ
across OS versions and locales, parsing is error-prone, and spawning a
subprocess per sample is slow. psutil reads the same kernel data sources
directly without spawning any external processes.

platform module
^^^^^^^^^^^^^^^

:mod:`platform` provides information about the OS and Python runtime, such as
OS name, kernel version, architecture, and machine type. It is useful for
identifying the environment, but does not expose runtime metrics or process
information like psutil. Overlaps with psutil's OS constants (:data:`LINUX`,
:data:`WINDOWS`, :data:`MACOS`, etc.).

/proc filesystem
^^^^^^^^^^^^^^^^

On Linux, ``/proc`` exposes process and system information as virtual files.
Reading ``/proc/pid/status`` or ``/proc/meminfo`` directly is fast and has no
dependencies, which is why some minimal containers or scripts do this. The
downsides are that it is Linux-only, the format may vary across kernel
versions, and you have to parse raw text yourself. psutil parses ``/proc``
internally, exposes the same information through a consistent cross-platform
API and handles edge cases (invalid format, compatibility with old kernels,
graceful fallbacks, etc.).

Third-party libraries
---------------------

Libraries that cover areas psutil does not, or that go deeper on a specific
platform or subsystem.

.. list-table::
   :header-rows: 1
   :widths: 5 25
   :class: longtable

   * - Library
     - Focus

   * - `distro <https://github.com/python-distro/distro>`_
     - Linux distro info (name, version, codename). psutil does not
       expose OS details.

   * - `GPUtil <https://github.com/anderskm/gputil>`_ /
       `pynvml <https://github.com/gpuopenanalytics/pynvml>`_
     - NVIDIA GPU utilization and VRAM usage.

   * - `ifaddr <https://github.com/ifaddr/ifaddr>`_
     - Network interface address enumeration.
       Overlaps with :func:`net_if_addrs`.

   * - `libvirt-python <https://github.com/libvirt/libvirt-python>`_
     - Manage KVM/QEMU/Xen VMs: enumerate guests, query
       CPU/memory allocation. Complements psutil's host-level view.

   * - `prometheus_client <https://github.com/prometheus/client_python>`_
     - Export metrics to Prometheus. Use *alongside* psutil.

   * - `py-cpuinfo <https://github.com/workhorsy/py-cpuinfo>`_
     - CPU brand string, micro architecture, feature flags.

   * - `pyroute2 <https://github.com/svinota/pyroute2>`_
     - Linux netlink (interfaces, routes, connections).
       Overlaps with :func:`net_if_addrs`, :func:`net_if_stats`,
       :func:`net_connections`.

   * - `pywifi <https://github.com/awkman/pywifi>`_
     - WiFi scanning, signal strength, SSID. Exposes wireless
       details that :func:`net_if_addrs` does not.

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

Other languages
---------------

Equivalent libraries in other languages providing cross-platform system and
process information.

.. list-table::
   :header-rows: 1
   :widths: 5 5 20
   :class: longtable

   * - Library
     - Language
     - Focus

   * - `gopsutil <https://github.com/shirou/gopsutil>`_
     - Go
     - CPU, memory, disk, network, processes. Directly inspired
       by psutil and follows a similar API.

   * - `heim <https://github.com/heim-rs/heim>`_
     - Rust
     - Async-first library covering CPU, memory, disk, network,
       processes and sensors.

   * - `Hardware.Info <https://github.com/Jinjinov/Hardware.Info>`_
     - C# / .NET
     - CPU, RAM, GPU, disk, network, battery.

   * - `hwinfo <https://github.com/lfreist/hwinfo>`_
     - C++
     - CPU, RAM, GPU, disks, mainboard. More hardware-focused.

   * - `OSHI <https://github.com/oshi/oshi>`_
     - Java
     - OS and hardware information: CPU, memory, disk, network,
       processes, sensors, USB devices.

   * - `rust-psutil <https://github.com/rust-psutil/rust-psutil>`_
     - Rust
     - Directly inspired by psutil and follows a similar API.

   * - `sysinfo <https://github.com/GuillaumeGomez/sysinfo>`_
     - Rust
     - CPU, memory, disk, network, processes, components.

   * - `systeminformation <https://github.com/sebhildebrandt/systeminformation>`_
     - Node.js
     - CPU, memory, disk, network, processes, battery, Docker.
