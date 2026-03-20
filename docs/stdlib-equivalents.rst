.. currentmodule:: psutil
.. include:: _links.rst

Stdlib equivalents
==================

This page maps psutil's Python API to the closest equivalent in the Python
standard library. This is useful for understanding what psutil replaces and
how the two APIs differ. The most common difference is that stdlib functions
only operate on the **current process**, while psutil works on **any process**.

System-wide functions
---------------------

CPU
~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 17 27 100

   * - psutil
     - stdlib
     - notes
   * - :func:`cpu_count`
     - :func:`os.cpu_count`
     - Exactly the same (logical CPUs). :func:`os.cpu_count` cannot return
       physical cores count (``psutil.cpu_count(logical=False)``).
   * - :func:`cpu_count`
     - :func:`os.process_cpu_count`
     - CPUs the calling process is allowed to use (Python 3.13+).
       No correspondance in psutil.
   * - :func:`getloadavg`
     - :func:`os.getloadavg`
     - Same as :func:`os.getloadavg` on POSIX but psutil offers Windows support
       (emulated).

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
     - Backported to CPython 3.3 in BPO-12442_.
       Identical except psutil adds a ``percent`` field.
   * - :func:`disk_partitions`
     - :func:`os.listdrives`,
       :func:`os.listmounts`,
       :func:`os.listvolumes`
     - Windows only (Python 3.12+). These are low-level volume
       enumeration APIs: :func:`os.listdrives` returns drive
       letters, :func:`os.listvolumes` volume GUID paths,
       :func:`os.listmounts` mount points. psutil combines device, mountpoint,
       fstype and opts in a single call.

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
     - Another process's environ may differ from its launch environment if it
       modified it at runtime.
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
     - :func:`os.times` also returns an ``elapsed`` field not present in
       psutil. psutil adds platform-specific fields (``iowait``, ``irq``,
       ``steal``, etc.).
   * - :meth:`Process.cpu_times`
     - :func:`resource.getrusage`
     - ``ru_utime`` / ``ru_stime`` are the same but more precise
   * - :meth:`Process.num_ctx_switches`
     - :func:`resource.getrusage`
     - :func:`resource.getrusage` returns ``ru_nvcsw`` / ``ru_nivcsw``
       for the current process only. psutil works for any PID.
   * - :meth:`Process.nice() <Process.nice>`
     - :func:`os.getpriority`,
       :func:`os.setpriority`
     - Backported to CPython 3.3 in `BPO-10784`_. Stdlib is POSIX only. psutil
       also supports Windows.
   * - :meth:`Process.nice() <Process.nice>`
     - :func:`os.nice`
     - Stdlib is POSIX only. psutil also supports Windows.
   * - :meth:`Process.cpu_affinity() <Process.cpu_affinity>`
     - :func:`os.sched_getaffinity`,
       :func:`os.sched_setaffinity`
     - Nearly equivalent. Both accept a PID. Linux only.
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
     - Returns :class:`threading.Thread` objects; psutil returns OS-level
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
     - Direct equivalent on POSIX. psutil adds :exc:`NoSuchProcess` and
       :exc:`AccessDenied` handling + it prevents killing a reused PID.
   * - :meth:`Process.suspend`
     - :func:`os.kill` + :data:`signal.SIGSTOP`
     - Same as above.
   * - :meth:`Process.resume`
     - :func:`os.kill` + :data:`signal.SIGCONT`
     - Same as above.
   * - :meth:`Process.terminate`
     - :func:`os.kill` + :data:`signal.SIGTERM`
     - On Windows, psutil calls ``TerminateProcess()`` (no ``SIGTERM``).
   * - :meth:`Process.kill`
     - :func:`os.kill` + :data:`signal.SIGKILL`
     - On Windows, psutil calls ``TerminateProcess()`` unconditionally.
   * - :meth:`Process.wait`
     - :func:`os.waitpid`,
       :meth:`subprocess.Popen.wait`
     - :func:`os.waitpid` works for child processes only. psutil waits for
       any PID. Prefer :meth:`subprocess.Popen.wait` for subprocesses.
