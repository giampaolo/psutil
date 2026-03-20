
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
   * - :func:`cpu_count`
     - :func:`os.cpu_count`,
       :func:`os.process_cpu_count`
     - :func:`os.cpu_count` is the same as ``cpu_count(logical=True)`` (logical CPUs).
       :func:`os.process_cpu_count`: returns the number of CPUs the calling process is
       allowed to use (same as ``len(cpu_affinity())``).
       Neither can return physical core count.
   * - :func:`getloadavg`
     - :func:`os.getloadavg`
     - Same as :func:`os.getloadavg` on POSIX but psutil offers Windows support
       (emulated).

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
     - Identical except psutil adds a ``percent`` field.

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
     - Current process only.
   * - :meth:`Process.ppid`
     - :func:`os.getppid`
     - Current process only.
   * - :meth:`Process.cwd`
     - :func:`os.getcwd`
     - Current process only.
   * - :meth:`Process.environ`
     - :data:`os.environ`
     - Current process only. Also, another process's environ may differ from
       its launch environment if it modified it at runtime.
   * - :meth:`Process.exe`
     - :data:`sys.executable`
     - Current Python interpreter only.
   * - :meth:`Process.cmdline`
     - :data:`sys.argv`
     - Current process only, and only within Python.

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
     - Current process only.
   * - :meth:`Process.gids`
     - :func:`os.getgid`,
       :func:`os.getegid`,
       :func:`os.getresgid`
     - Current process only.
   * - :meth:`Process.username`
     - :func:`pwd.getpwuid`, :func:`os.getuid`
     - No direct equivalent. Current process only.

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
     - :func:`os.times`: current process only + ``elapsed`` time field.
       :func:`cpu_times`: any process + additional fields (``iowait``,
       ``irq``, ``steal``, etc.).
   * - :meth:`Process.nice() <Process.nice>`
     - :func:`os.getpriority`,
       :func:`os.setpriority`,
       :func:`os.nice`
     - :func:`os.getpriority` / :func:`os.setpriority` accept a PID like
       psutil (POSIX only). :func:`os.nice` adjusts the current process by a
       relative delta only. psutil also supports Windows priority classes.
   * - :meth:`Process.cpu_affinity() <Process.cpu_affinity>`
     - :func:`os.sched_getaffinity`,
       :func:`os.sched_setaffinity`
     - Nearly equivalent. Both accept a PID. Linux only.
   * - :meth:`Process.rlimit() <Process.rlimit>`
     - :func:`resource.getrlimit`,
       :func:`resource.setrlimit`
     - Current process only. psutil works for any PID (Linux only).

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
     - :func:`resource.getrusage` returns peak RSS (``ru_maxrss``) for the
       current process only. psutil returns current RSS, VMS, and more fields
       for any PID.

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
     - Counts only Python :mod:`threading` threads in the current process.
       psutil counts all OS-level threads for any PID.
   * - :meth:`Process.threads`
     - :func:`threading.enumerate`
     - Returns :class:`threading.Thread` objects for the current process only.
       psutil returns OS-level thread IDs with CPU-time stats for any PID.

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
     - :func:`os.kill` + ``signal.SIGSTOP``
     - Same as above
   * - :meth:`Process.resume`
     - :func:`os.kill` + ``signal.SIGCONT``
     - Same as above
   * - :meth:`Process.terminate`
     - :func:`os.kill` + ``signal.SIGTERM``
     - On Windows, psutil calls ``TerminateProcess()`` (no ``SIGTERM``).
   * - :meth:`Process.kill`
     - :func:`os.kill` + ``signal.SIGKILL``
     - On Windows, psutil calls ``TerminateProcess()`` unconditionally.
   * - :meth:`Process.wait`
     - :func:`os.waitpid`,
       :meth:`subprocess.Popen.wait`
     - :func:`os.waitpid` works for child processes only. psutil waits for
       any PID. Prefer :meth:`subprocess.Popen.wait` for subprocesses.
