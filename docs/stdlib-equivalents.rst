.. currentmodule:: psutil
.. include:: _links.rst

Stdlib equivalents
==================

This page maps psutil's Python API to the closest equivalent in the Python
standard library. This is useful for understanding what psutil replaces and
how the two APIs differ. The most common difference is that stdlib functions
only operate on the **current process**, while psutil works on **any process**.

See also the :doc:`alternatives` page for a higher-level discussion of
how psutil compares to the standard library and third-party tools.

System-wide functions
---------------------

CPU
~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 17 37 100

   * - psutil
     - stdlib
     - notes
   * - :func:`cpu_count`
     - :func:`os.cpu_count`,
       :func:`multiprocessing.cpu_count`
     - Same as ``cpu_count(logical=True)``. Cannot return
       physical core count (``cpu_count(logical=False)``).
       See :ref:`FAQ <faq_cpu_count>`.
   * - :func:`cpu_count`
     - :func:`os.process_cpu_count`
     - CPUs the process is allowed to use (Python 3.13+).
       Equivalent to ``len(psutil.Process().cpu_affinity())``.
       See :ref:`FAQ <faq_cpu_count>`.
   * - :func:`getloadavg`
     - :func:`os.getloadavg`
     - Same as :func:`os.getloadavg` on POSIX, but psutil also offers
       Windows support (emulated).

Disk
~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 25 24 100

   * - psutil
     - stdlib
     - notes
   * - :func:`disk_usage`
     - :func:`shutil.disk_usage`
     - Identical except psutil adds a ``percent`` field.
       Backported to CPython 3.3 in BPO-12442_.
   * - :func:`disk_partitions`
     - :func:`os.listdrives`,
       :func:`os.listmounts`,
       :func:`os.listvolumes`
     - Windows only (Python 3.12+). These are low-level volume
       enumeration APIs: :func:`os.listdrives` returns drive
       letters, :func:`os.listvolumes` returns volume GUID
       paths, :func:`os.listmounts` returns mount points.
       psutil combines device, mountpoint, fstype and opts in a
       single cross-platform call.

Network
~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 25 30 100

   * - psutil
     - stdlib
     - notes
   * - :func:`net_if_addrs`
     - :func:`socket.if_nameindex`
     - Stdlib returns interface names only (no addresses).
       psutil returns addresses, netmasks, broadcast, and PTP
       for each NIC.

Process
~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 25 30 100

   * - psutil
     - stdlib
     - notes
   * - :func:`pid_exists`
     - ``os.kill(pid, 0)``
     - Common POSIX idiom. psutil also works on Windows.

Process methods
---------------

Identity
~~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 23 20 100

   * - psutil
     - stdlib
     - notes
   * - :attr:`Process.pid`
     - :func:`os.getpid`
     -
   * - :meth:`Process.ppid`
     - :func:`os.getppid`
     -
   * - :meth:`Process.cwd`
     - :func:`os.getcwd`
     -
   * - :meth:`Process.environ`
     - :data:`os.environ`
     - Another process's environ may differ from its launch
       environment if the process modified it at runtime.
   * - :meth:`Process.exe`
     - :data:`sys.executable`
     - Python interpreter path only.
   * - :meth:`Process.cmdline`
     - :data:`sys.argv`
     - Only within Python.

Credentials
~~~~~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 25 27 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.uids`
     - :func:`os.getuid`,
       :func:`os.geteuid`,
       :func:`os.getresuid`
     -
   * - :meth:`Process.gids`
     - :func:`os.getgid`,
       :func:`os.getegid`,
       :func:`os.getresgid`
     -
   * - :meth:`Process.username`
     - :func:`os.getlogin`, :func:`getpass.getuser`
     - Rough equivalents (just not per-process).

CPU / scheduling
~~~~~~~~~~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 35 35 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.cpu_times`
     - :func:`os.times`
     - :func:`os.times` also returns an ``elapsed`` field not
       present in psutil, which in turn adds platform-specific
       fields (``iowait``, ``irq``, ``steal``, etc.).
   * - :meth:`Process.cpu_times`
     - :func:`resource.getrusage`
     - ``ru_utime`` / ``ru_stime`` are the same, but with
       higher precision.
   * - :meth:`Process.num_ctx_switches`
     - :func:`resource.getrusage`
     - :func:`resource.getrusage` returns ``ru_nvcsw`` / ``ru_nivcsw``
       for the current process only. psutil works for any PID.
   * - :meth:`Process.nice() <Process.nice>`
     - :func:`os.getpriority`,
       :func:`os.setpriority`
     - Backported to CPython 3.3 in `BPO-10784`_. POSIX only; psutil also supports
       Windows.
   * - :meth:`Process.nice() <Process.nice>`
     - :func:`os.nice`
     - Stdlib is POSIX only. psutil also supports Windows.
   * - :meth:`Process.cpu_affinity() <Process.cpu_affinity>`
     - :func:`os.sched_getaffinity`,
       :func:`os.sched_setaffinity`
     - Nearly equivalent; both accept a PID. Linux only.
   * - :meth:`Process.rlimit() <Process.rlimit>`
     - :func:`resource.getrlimit`,
       :func:`resource.setrlimit`
     - psutil works for any PID (Linux only).

Memory
~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 28 27 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.memory_info`
     - :func:`resource.getrusage`
     - :func:`resource.getrusage` returns peak RSS (``ru_maxrss``) only.
       psutil returns current RSS, VMS, and more fields.
   * - :meth:`Process.page_faults`
     - :func:`resource.getrusage`
     - :func:`resource.getrusage` returns ``ru_majflt`` / ``ru_minflt``
       for the current process only.

I/O
~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 28 27 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.io_counters`
     - :func:`resource.getrusage`
     - :func:`resource.getrusage` returns ``ru_inblock`` /
       ``ru_oublock`` (block I/O operations only, current
       process only). psutil returns read/write bytes and
       counts for any PID.

Threads
~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 30 35 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.num_threads`
     - :func:`threading.active_count`
     - Counts only Python :mod:`threading` threads; psutil counts all
       OS-level threads.
   * - :meth:`Process.threads`
     - :func:`threading.enumerate`
     - Returns :class:`threading.Thread` objects; psutil returns raw OS-level
       thread IDs with CPU-time stats.

Signals
~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 33 45 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.send_signal`
     - :func:`os.kill`,
       :func:`signal.raise_signal`
     - Direct equivalent on POSIX (no Windows support).
       psutil adds :exc:`NoSuchProcess` and :exc:`AccessDenied` handling + it
       prevents killing a reused PID.
   * - :meth:`Process.suspend`
     - :func:`os.kill` + :data:`signal.SIGSTOP`
     - Same as above.
   * - :meth:`Process.resume`
     - :func:`os.kill` + :data:`signal.SIGCONT`
     - Same as above.
   * - :meth:`Process.terminate`
     - :func:`os.kill` + :data:`signal.SIGTERM`
     - Same as above. On Windows, psutil calls ``TerminateProcess()``
       (no ``SIGTERM``).
   * - :meth:`Process.kill`
     - :func:`os.kill` + :data:`signal.SIGKILL`
     - Same as above. On Windows, psutil calls ``TerminateProcess()``
       (no ``SIGKILL``).
   * - :meth:`Process.wait`
     - :func:`os.waitpid`
     - Works for child processes only. psutil waits for any PID.
   * - :meth:`Process.wait`
     - :meth:`subprocess.Popen.wait`
     - Equivalent, but on Linux and BSD psutil uses efficient OS-level
       waiting instead of busy polling. Backported to CPython 3.15
       in `BPO-144047`_.
