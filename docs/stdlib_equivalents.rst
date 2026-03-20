
.. currentmodule:: psutil

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
   * - :func:`cpu_times`
     - :func:`os.times`
     - :func:`os.times` returns only ``user``, ``system``, ``children_user``,
       ``children_system``, ``elapsed`` for the **current process**. psutil
       returns system-wide CPU times with more platform-specific fields
       (``iowait``, ``irq``, ``steal``, etc.).
   * - :func:`cpu_count`
     - :func:`os.cpu_count`,
       :func:`os.process_cpu_count`
     - :func:`os.cpu_count` returns logical CPUs (same as
       ``cpu_count(logical=True)``). :func:`os.process_cpu_count` (Python 3.13+)
       returns the number of CPUs the calling process is allowed to use (same
       as ``len(cpu_affinity())``). Neither can return physical core count.
   * - :func:`getloadavg`
     - :func:`os.getloadavg`
     - On POSIX, psutil delegates to :func:`os.getloadavg`, so results are
       identical. Unlike :func:`os.getloadavg`, psutil also works on Windows by
       spawning a background thread that computes load average every 5 seconds,
       mimicking UNIX behavior.

Disk
~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 17 24 100

   * - psutil
     - stdlib
     - notes
   * - :func:`disk_usage`
     - :func:`shutil.disk_usage`
     - Nearly identical. Both return ``(total, used, free)``. psutil also
       exposes a ``percent`` field and raises ``FileNotFoundError`` for
       non-existent paths consistently across platforms.

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
     - :func:`os.getpid` only returns the PID of the **current process**.
   * - :meth:`Process.ppid`
     - :func:`os.getppid`
     - :func:`os.getppid` only returns the PPID of the **current process**.
   * - :meth:`Process.cwd`
     - :func:`os.getcwd`
     - :func:`os.getcwd` only returns the cwd of the **current process**.
   * - :meth:`Process.environ`
     - :data:`os.environ`
     - :data:`os.environ` only exposes the **current process**'s environment.
       psutil reads ``/proc/PID/environ`` (Linux) or platform equivalents.
       Note: the environ of another process may differ from its original
       launch environment if it modified its own env at runtime.
   * - :meth:`Process.exe`
     - :data:`sys.executable`
     - :data:`sys.executable` is the path to the current Python interpreter only.
       For non-Python processes or other PIDs use psutil.
   * - :meth:`Process.cmdline`
     - :data:`sys.argv`
     - :data:`sys.argv` only reflects the **current process**'s command-line
       arguments, and only within Python. psutil reads the raw argument vector
       for any process.

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
     - The stdlib functions return real/effective/saved UIDs of the **current
       process** only. psutil works for any PID.
   * - :meth:`Process.gids`
     - :func:`os.getgid`,
       :func:`os.getegid`,
       :func:`os.getresgid`
     - Same as above for group IDs.
   * - :meth:`Process.username`
     - :func:`pwd.getpwuid`, :func:`os.getuid`
     - No direct stdlib equivalent. The stdlib combination only works for the
       current process.

CPU / scheduling
~~~~~~~~~~~~~~~~

.. list-table::
   :class: longtable
   :header-rows: 1
   :widths: 30 30 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`Process.cpu_times`
     - :func:`os.times`
     - :func:`os.times` returns CPU times for the **current process** only, with
       fewer fields. psutil works for any PID with platform-specific extras.
   * - :meth:`Process.nice() <Process.nice>`
     - :func:`os.getpriority`,
       :func:`os.setpriority`,
       :func:`os.nice`
     - :func:`os.getpriority` / :func:`os.setpriority` accept a PID and work like
       psutil (POSIX only). :func:`os.nice` only adjusts the **current
       process**'s nice value by a relative delta. psutil additionally supports
       Windows priority classes.
   * - :meth:`Process.cpu_affinity() <Process.cpu_affinity>`
     - :func:`os.sched_getaffinity`,
       :func:`os.sched_setaffinity`
     - Nearly equivalent. The stdlib functions accept a PID (``0`` for the
       current process) just like psutil. Linux only.
   * - :meth:`Process.rlimit() <Process.rlimit>`
     - :func:`resource.getrlimit`,
       :func:`resource.setrlimit`
     - The :mod:`resource` module only operates on the **current process**.
       psutil can get/set resource limits for any process (Linux only).

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
     - :func:`resource.getrusage` returns ``ru_maxrss`` (peak RSS) for the
       **current process** only. psutil returns current RSS, VMS, and
       additional platform-specific fields for any PID.

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
     - :func:`threading.active_count` counts only Python :mod:`threading` threads
       in the **current process**. psutil counts all OS-level threads for any
       PID.
   * - :meth:`Process.threads`
     - :func:`threading.enumerate`
     - :func:`threading.enumerate` returns Python :class:`threading.Thread`
       objects for the **current process** only. psutil returns OS-level thread
       IDs with CPU-time stats for any PID.

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
     - :func:`os.kill` is equivalent and works on any PID.
       :func:`signal.raise_signal` (Python 3.8+) only targets the **current
       process**. psutil wraps :func:`os.kill` with :exc:`NoSuchProcess` and
       :exc:`AccessDenied` exception handling.
   * - :meth:`Process.suspend`
     - :func:`os.kill` + ``signal.SIGSTOP``
     - Direct equivalent on POSIX.
   * - :meth:`Process.resume`
     - :func:`os.kill` + ``signal.SIGCONT``
     - Direct equivalent on POSIX.
   * - :meth:`Process.terminate`
     - :func:`os.kill` + ``signal.SIGTERM``
     - Direct equivalent on POSIX. On Windows psutil calls
       ``TerminateProcess()``; there is no ``SIGTERM`` equivalent.
   * - :meth:`Process.kill`
     - :func:`os.kill` + ``signal.SIGKILL``
     - Direct equivalent on POSIX. On Windows psutil calls
       ``TerminateProcess()`` unconditionally.
   * - :meth:`Process.wait`
     - :func:`os.waitpid`,
       :meth:`subprocess.Popen.wait`
     - :func:`os.waitpid` only works for **child** processes of the current
       process. psutil can wait for any PID (using polling on some platforms).
       :meth:`subprocess.Popen.wait` is the preferred stdlib choice when the
       process was spawned via :mod:`subprocess`.
