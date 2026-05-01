Stdlib equivalents
==================

This page maps psutil's Python API to the closest equivalent in the Python
standard library. This is useful for understanding what psutil replaces and how
the two APIs differ. The most common difference is that stdlib functions only
operate on the **current process**, while psutil works on **any process**
(PID).

.. seealso::
   - :doc:`shell-equivalents`
   - :doc:`alternatives`

System-wide functions
---------------------

CPU
~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 30 60 100

   * - psutil
     - stdlib
     - notes
   * - :func:`cpu_count`
     - :func:`os.cpu_count`,
       :func:`multiprocessing.cpu_count`
     - Same as ``cpu_count(logical=True)``; no support for
       physical cores (``logical=False``). See :ref:`FAQ <faq_cpu_count>`.
   * - :func:`cpu_count`
     - :func:`os.process_cpu_count`
     - CPUs the process is allowed to use (Python 3.13+).
       Equivalent to ``len(psutil.Process().cpu_affinity())``.
       See :ref:`FAQ <faq_cpu_count>`.
   * - :func:`getloadavg`
     - :func:`os.getloadavg`
     - Same on POSIX; psutil also supports Windows.

Disk
~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 45 100

   * - psutil
     - stdlib
     - notes
   * - :func:`disk_usage`
     - :func:`shutil.disk_usage`
     - Same as :func:`shutil.disk_usage`; psutil also adds
       :field:`percent`. Added to CPython 3.3 (BPO-12442_).
   * - :func:`disk_partitions`
     - :func:`os.listdrives`,
       :func:`os.listmounts`,
       :func:`os.listvolumes`
     - Windows only (Python 3.12+). Low-level APIs:
       drive letters, volume GUIDs, mount points. psutil
       combines them in one cross-platform call.

Network
~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 45 100

   * - psutil
     - stdlib
     - notes
   * - :func:`net_if_addrs`
     - :func:`socket.if_nameindex`
     - Stdlib returns :term:`NIC` names only; psutil also returns
       addresses, netmasks, broadcast, and PTP.

Process
~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 45 100

   * - psutil
     - stdlib
     - notes
   * - :func:`pid_exists`
     - ``os.kill(pid, 0)``
     - Common POSIX idiom; psutil also supports Windows.

Process methods
---------------

Assuming ``p = psutil.Process()``.

Identity
~~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 45 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.pid <Process.pid>`

     - :func:`os.getpid`
     -
   * - :meth:`p.ppid() <Process.ppid>`
     - :func:`os.getppid`
     -
   * - :meth:`p.cwd() <Process.cwd>`
     - :func:`os.getcwd`
     -
   * - :meth:`p.environ() <Process.environ>`
     - :data:`os.environ`
     - Will differ from launch environment if modified at runtime.
   * - :meth:`p.exe() <Process.exe>`
     - :data:`sys.executable`
     - Python interpreter path only.
   * - :meth:`p.cmdline() <Process.cmdline>`
     - :data:`sys.argv`
     - Python process only.

Credentials
~~~~~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 30 65 50

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.uids() <Process.uids>`
     - :func:`os.getuid`,
       :func:`os.geteuid`,
       :func:`os.getresuid`
     -
   * - :meth:`p.gids() <Process.gids>`
     - :func:`os.getgid`,
       :func:`os.getegid`,
       :func:`os.getresgid`
     -
   * - :meth:`p.username() <Process.username>`
     - :func:`os.getlogin`, :func:`getpass.getuser`
     - Rough equivalent; not per-process.

CPU / scheduling
~~~~~~~~~~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 60 60 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.cpu_times() <Process.cpu_times>`
     - :func:`os.times`
     - :func:`os.times` also has ``elapsed``; psutil adds
       :field:`iowait` (Linux).
   * - :meth:`p.cpu_times() <Process.cpu_times>`
     - :func:`resource.getrusage`
     - ``ru_utime`` / ``ru_stime`` match; have higher precision.
   * - :meth:`p.num_ctx_switches() <Process.num_ctx_switches>`
     - :func:`resource.getrusage`
     - Current process only; psutil works for any PID.
   * - :meth:`p.nice() <Process.nice>`
     - :func:`os.getpriority`,
       :func:`os.setpriority`
     - POSIX only; psutil also supports Windows.
       Added to CPython 3.3 (BPO-10784_).
   * - :meth:`p.nice() <Process.nice>`
     - :func:`os.nice`
     - POSIX only; psutil also supports Windows.
   * - *no equivalent*
     - :func:`os.sched_getscheduler`,
       :func:`os.sched_setscheduler`
     - Sets scheduling *policy* (``SCHED_*``). Unlike nice,
       which sets priority within ``SCHED_OTHER``. Real-time
       policies preempt normal processes.
   * - :meth:`p.cpu_affinity() <Process.cpu_affinity>`
     - :func:`os.sched_getaffinity`,
       :func:`os.sched_setaffinity`
     - Nearly equivalent; both accept a PID. Stdlib is
       Linux/BSD; psutil also supports Windows.
   * - :meth:`p.rlimit() <Process.rlimit>`
     - :func:`resource.getrlimit`,
       :func:`resource.setrlimit`
     - Same interface; psutil works for any PID (Linux only).

Memory
~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 45 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.memory_info() <Process.memory_info>`
     - :func:`resource.getrusage`
     - Only :term:`peak_rss` (``ru_maxrss``); psutil returns :term:`RSS`, :term:`VMS`, and more.
   * - :meth:`p.page_faults() <Process.page_faults>`
     - :func:`resource.getrusage`
     - Current process only.

I/O
~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 45 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.io_counters() <Process.io_counters>`
     - :func:`resource.getrusage`
     - Block I/O only (``ru_inblock`` / ``ru_oublock``),
       current process. psutil returns bytes and counts for any PID.

Threads
~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 50 55 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.num_threads() <Process.num_threads>`
     - :func:`threading.active_count`
     - Stdlib counts Python threads only; psutil counts all OS threads.
   * - :meth:`p.threads() <Process.threads>`
     - :func:`threading.enumerate`
     - Stdlib returns :class:`threading.Thread` objects; psutil
       returns OS thread IDs with CPU times.

Signals
~~~~~~~

.. list-table::
   :class: longtable wide-table
   :header-rows: 1
   :widths: 45 55 100

   * - psutil
     - stdlib
     - notes
   * - :meth:`p.send_signal() <Process.send_signal>`
     - :func:`os.kill`
     - Same on POSIX; limited on Windows. psutil adds
       :exc:`NoSuchProcess` / :exc:`AccessDenied` and avoids
       killing reused PIDs.
   * - :meth:`p.suspend() <Process.suspend>`
     - :func:`os.kill` + :data:`signal.SIGSTOP`
     - Same as above.
   * - :meth:`p.resume() <Process.resume>`
     - :func:`os.kill` + :data:`signal.SIGCONT`
     - Same as above.
   * - :meth:`p.terminate() <Process.terminate>`
     - :func:`os.kill` + :data:`signal.SIGTERM`
     - Same as above. On Windows uses ``TerminateProcess()``.
   * - :meth:`p.kill() <Process.kill>`
     - :func:`os.kill` + :data:`signal.SIGKILL`
     - Same as above. On Windows uses ``TerminateProcess()``.
   * - :meth:`p.wait() <Process.wait>`
     - :func:`os.waitpid`
     - Child processes only; psutil works for any PID.
   * - :meth:`p.wait() <Process.wait>`
     - :meth:`subprocess.Popen.wait`
     - Equivalent; psutil uses efficient OS-level waiting on
       Linux/BSD. Added to CPython 3.15 (GH-144047_).
