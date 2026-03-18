.. currentmodule:: psutil

Glossary
========

.. glossary::
   :sorted:

   CPU affinity
      A property of a process (or thread) that restricts which logical CPUs
      it is allowed to run on. For example, pinning a process to CPU 0 and
      CPU 1 prevents the OS scheduler from moving it to other cores. See
      :meth:`Process.cpu_affinity`.

   CPU percent
      The fraction of CPU time consumed by a process or the whole system
      over a measurement interval, expressed as a percentage. A value of
      100 % means one full logical CPU core was busy for the entire
      interval. Values above 100 % are possible on multi-core systems when
      multiple threads run in parallel. See :func:`cpu_percent` and
      :meth:`Process.cpu_percent`.

   CPU times
      Cumulative counters (in seconds) recording how much time a CPU or
      process spent in different modes: **user** (normal code), **system**
      (kernel code on behalf of the process), **idle**, **iowait**, etc.
      These always increase monotonically. See :func:`cpu_times` and
      :meth:`Process.cpu_times`.

   context switch
      A context switch occurs when the OS saves the state of a running
      process (or thread) and restores the state of another. Frequent
      context switching can indicate high system load or excessive thread
      contention. See :func:`cpu_stats` and :meth:`Process.num_ctx_switches`.

   file descriptor
      An integer handle used by UNIX processes to reference open files,
      sockets, pipes, and other I/O resources. On Windows the equivalent
      are *handles*. Leaking file descriptors (opening without closing)
      eventually causes ``EMFILE`` / ``Too many open files`` errors. See
      :meth:`Process.num_fds`, :meth:`Process.open_files`,
      :meth:`Process.num_handles`.

   handle
      On Windows, an opaque reference to a kernel object such as a file,
      thread, process, event, mutex, or registry key. Handles are the
      Windows equivalent of UNIX :term:`file descriptor`\s. Each open
      handle consumes a small amount of kernel memory; leaking handles
      eventually causes ``ERROR_NO_MORE_FILES`` or similar errors. See
      :meth:`Process.num_handles`.

   iowait
      A CPU time field (Linux, SunOS, AIX) measuring time spent by the CPU
      waiting for I/O operations to complete. High iowait indicates a
      disk or network bottleneck. It is reported as part of
      :func:`cpu_times` but is *not* included in the idle counter.

   ionice
      An I/O scheduling priority that controls how much disk bandwidth a
      process receives. On Linux three scheduling classes are supported:
      ``IOPRIO_CLASS_RT`` (real-time), ``IOPRIO_CLASS_BE`` (best-effort,
      the default), and ``IOPRIO_CLASS_IDLE``. See
      :meth:`Process.ionice`.

   logical CPU
      A CPU as seen by the operating system scheduler. On systems with
      *hyper-threading* each physical core exposes two logical CPUs, so a
      4-core hyper-threaded chip has 8 logical CPUs. This is the count
      returned by :func:`cpu_count` (the default) and the number of
      entries returned by ``cpu_percent(percpu=True)``. See also
      :term:`physical CPU`.

   load average
      Three floating-point values representing the average number of
      processes in a *runnable* or *uninterruptible* state over the last
      1, 5, and 15 minutes. A load average equal to the number of logical
      CPUs means the system is fully saturated. See :func:`getloadavg`.

   named tuple
      A :class:`collections.namedtuple` subclass, a tuple whose fields
      can be accessed by name as well as by index. Most psutil functions
      return named tuples (e.g. ``sswap``, ``pmem``, ``scputimes``).

   nice
      A process priority value that influences how much CPU time the OS
      scheduler gives to a process. Lower nice values mean higher priority.
      The range is −20 (highest priority) to 19 (lowest) on UNIX; on
      Windows the concept maps to priority classes. See
      :meth:`Process.nice`.

   NIC
      *Network Interface Card*, a hardware or virtual network interface.
      psutil uses this term when referring to per-interface network
      statistics. See :func:`net_if_addrs` and :func:`net_if_stats`.

   page fault
      An event that occurs when a process accesses a virtual memory page
      that is not currently mapped in physical RAM. A **minor** fault is
      resolved without disk I/O (e.g. the page is already in RAM but not
      yet mapped, or it is copy-on-write). A **major** fault requires
      reading the page from disk (e.g. from a memory-mapped file or the
      swap area) and is significantly more expensive. Many major faults
      may indicate memory pressure or excessive swapping. See
      :meth:`Process.page_faults`.

   physical CPU
      An actual hardware CPU core on the motherboard, as opposed to a
      :term:`logical CPU`. A single physical core may appear as multiple
      logical CPUs when hyper-threading is enabled. The physical count is
      returned by ``cpu_count(logical=False)``.

   PID
      *Process identifier*, a non-negative integer assigned by the OS to
      every running process. PIDs are unique at any instant but are
      recycled over time (:term:`PID reuse`). PID 0 is typically the
      idle/swapper process; PID 1 is ``init`` / ``systemd`` on UNIX.

   PID reuse
      When a process exits its PID is eventually recycled and assigned to
      a new process. A :class:`Process` object held across this boundary
      would silently refer to the wrong process. psutil detects reuse by
      comparing the recorded creation time against the live value, and
      raises :exc:`NoSuchProcess` if they differ.

   PSS
      *Proportional Set Size*, the amount of RAM used by a process,
      where shared pages are divided proportionally among all processes
      that map them. PSS gives a fairer per-process memory estimate than
      :term:`RSS` when shared libraries are involved. Available on Linux
      and via :meth:`Process.memory_full_info`.

   RSS
      *Resident Set Size*, the amount of physical RAM currently occupied
      by a process, including shared library pages. It is the most
      commonly reported memory metric (shown as ``RES`` in ``top``), but
      it can be misleading because shared pages are counted in full for
      every process that maps them. See :meth:`Process.memory_info`.

   status (process)
      The scheduling state of a process at a given instant. Common
      values are:

      - ``running``: actively executing on a CPU.
      - ``sleeping``: waiting for an event (interruptible sleep).
      - ``disk-sleep``: waiting for I/O (uninterruptible sleep).
      - ``stopped``: suspended via ``SIGSTOP`` or a debugger.
      - ``zombie``: exited but not yet reaped by its parent.
      - ``idle``: no work to do (common on BSD/macOS for kernel threads).

      See :meth:`Process.status` and the ``STATUS_*`` constants.

   swap memory
      Disk space used as an overflow extension of physical RAM. When the
      OS runs low on RAM it *swaps out* memory pages to disk and restores
      them on demand. Heavy swapping significantly degrades performance.
      See :func:`swap_memory`.

   USS
      *Unique Set Size*, the amount of RAM that belongs exclusively to a
      process and would be freed if it exited. It excludes shared pages
      entirely, making it the most accurate single-process memory metric.
      Available on Linux, macOS, and Windows via
      :meth:`Process.memory_full_info`.

   VMS
      *Virtual Memory Size*, the total virtual address space reserved by a
      process, including mapped files, shared libraries, stack, heap, and
      swap. VMS is almost always much larger than :term:`RSS` because most
      virtual pages are never actually loaded into RAM. See
      :meth:`Process.memory_info`.

   zombie process
      A process that has finished executing but whose exit status has not
      yet been collected by its parent (via ``wait()``). The OS keeps a
      minimal entry in the process table so the parent can retrieve the
      exit code. Zombies consume no CPU or memory but do occupy a PID and
      a process-table slot. On UNIX, long-lived zombies indicate a bug in
      the parent. See :attr:`STATUS_ZOMBIE` and :exc:`ZombieProcess`.
