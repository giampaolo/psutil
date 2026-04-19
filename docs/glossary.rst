Glossary
========

.. glossary::
   :sorted:

   anonymous memory

      RAM used by the program that is not associated with any file (unlike the
      :term:`page cache`), such as the :term:`heap`, the stack, and other
      memory allocated directly by the program (e.g. via ``malloc()``).
      Anonymous pages have no on-disk counterpart and must be written to
      :term:`swap memory` if evicted. Exposed by psutil via the :field:`rss_anon`
      field of :meth:`Process.memory_info_ex` (total resident anonymous pages)
      and the :field:`anonymous` field of :meth:`Process.memory_maps` (per
      mapping). Anonymous regions are also visible in the :field:`path` column
      of :meth:`Process.memory_maps` as ``"[heap]"``, ``"[stack]"``, or an
      empty string.

   available memory

      The amount of RAM that can be given to processes without the system going
      into :term:`swap <swap memory>`. This is the right field to watch for
      memory pressure, not :field:`free`. :field:`free` is often deceptively low
      because the OS keeps recently freed pages as reclaimable cache; those pages
      are counted in :field:`available` but not in :field:`free`.
      A monitoring alert should fire on :field:`available` (or :field:`percent`)
      falling below a threshold, not on :field:`free`. See :func:`virtual_memory`.

   buffers

      Kernel memory used to cache filesystem metadata such as
      superblocks, inodes, and directory entries. Distinct from the
      :term:`page cache`, which caches file *contents*.
      Like the page cache, buffer memory is reclaimable: the OS can
      free it under memory pressure.
      Reported as the :field:`buffers` field of :func:`virtual_memory`
      (Linux, BSD).

   busy_time

      A :term:`cumulative counter` (milliseconds) tracking the time a disk
      device spent actually performing I/O, as reported in the :field:`busy_time`
      field of :func:`disk_io_counters` (Linux and FreeBSD only). To use it,
      sample twice and divide the delta by elapsed time to get a utilization
      percentage (analogous to CPU percent but for disks). A value close to
      100% means the disk is saturated.

      .. seealso:: :ref:`Real-time disk I/O percent recipe <recipe_disk_io_percent>`

   CPU affinity

      A property of a process (or thread) that restricts which
      :term:`logical CPUs <logical CPU>` it is allowed to run on. For example,
      pinning a process to CPU 0 and CPU 1 prevents the OS scheduler from
      moving it to other cores. This could be useful, e.g., for benchmarking.
      See :meth:`Process.cpu_affinity`.

   context switch

      Occurs when the CPU stops executing one process or thread for another.
      Frequent switching can indicate high system
      load or thread contention. See :meth:`Process.num_ctx_switches`
      and :func:`cpu_stats` (:field:`ctx_switches` field).
      A :field:`voluntary` context switch occurs when a process gives up the
      CPU, usually because it's waiting for something (I/O, a sleep, a mutex
      lock). High rates are normal for I/O-bound workloads (e.g. a web server)
      and usually point to I/O or locking as the bottleneck.
      An :field:`involuntary` context switch occurs when the OS forcibly takes
      the CPU from the process. High rates mean the process has more work to do
      but is being kicked off the core. This usually indicates too many active
      threads/processes competing for too few CPU cores.

   cumulative counter

      A field whose value only increases over time (since boot or process
      creation) and never resets. Examples include :func:`cpu_times`,
      :func:`disk_io_counters`, :func:`net_io_counters`,
      :meth:`Process.io_counters`, and :meth:`Process.num_ctx_switches`.
      The raw value is rarely useful on its own; divide the delta between
      two samples by the elapsed time to get a meaningful rate (e.g.
      bytes per second, context switches per second).

   file descriptor

      An integer handle used by UNIX processes to reference open files,
      sockets, pipes, and other I/O resources. On Windows the equivalent
      are :term:`handles <handle>`. Leaking file descriptors (opening without
      closing) eventually causes ``EMFILE`` / ``Too many open files`` errors.
      See :meth:`Process.num_fds` and :meth:`Process.open_files`.

   handle

      On Windows, an opaque reference to a kernel object such as a file,
      thread, process, event or mutex. Handles are the Windows equivalent of
      UNIX :term:`file descriptors <file descriptor>`. Each open handle
      consumes a small amount of kernel memory. Leaking / unclosed
      handles eventually causes ``ERROR_NO_MORE_FILES`` or similar errors. See
      :meth:`Process.num_handles`.

   hardware interrupt

      A signal sent by a hardware device (disk controller, :term:`NIC`, keyboard)
      to the CPU to request attention. Each interrupt briefly preempts
      whatever the CPU was doing. Reported as the :field:`interrupts` field of
      :func:`cpu_stats` and :field:`irq` field of :func:`cpu_times`.
      A very high rate may indicate a misbehaving device driver or a heavily
      loaded :term:`NIC`. Also see :term:`soft interrupt`.

   heap

      The memory region managed by the platform's native C allocator
      (e.g. glibc's ``malloc`` on Linux, ``jemalloc`` on FreeBSD,
      ``HeapAlloc`` on Windows). When a C extension calls ``malloc()``
      and never calls ``free()``, the leaked bytes show up here but
      are not always visible to Python's memory tracking tools
      (:mod:`tracemalloc`, :func:`sys.getsizeof`) or :term:`RSS` / :term:`VMS`.
      :func:`heap_info` exposes the current state of the heap, and
      :func:`heap_trim` asks the allocator to release unused portions
      of it. Together they provide a way to detect memory leaks in C
      extensions that standard process-level metrics would otherwise miss.

   involuntary context switch

      See :term:`context switch`.

   iowait

      A CPU time field (Linux, SunOS, AIX) measuring time spent by the CPU
      waiting for I/O operations to complete. High iowait indicates a
      disk or network bottleneck. It is reported as part of
      :func:`cpu_times` but is *not* included in the idle counter.
      To get it as a percentage: ``psutil.cpu_times_percent(interval=1).iowait``.
      Note that this is a CPU metric, not a disk metric: it measures how much
      CPU time is wasted waiting, not how busy the disk is. See also
      :term:`busy_time` for actual disk utilization.

   ionice

      An I/O scheduling priority that controls how much disk bandwidth a
      process receives. On Linux three scheduling classes are supported:
      :data:`IOPRIO_CLASS_RT` (real-time), :data:`IOPRIO_CLASS_BE`
      (best-effort, the default), and :data:`IOPRIO_CLASS_IDLE`. See
      :meth:`Process.ionice`.

   logical CPU

      A CPU as seen by the operating system scheduler. On systems with
      *hyper-threading* each physical core exposes two logical CPUs, so a
      4-core hyper-threaded chip has 8 logical CPUs. This is the count
      returned by :func:`cpu_count` (the default) and the number of
      entries returned by ``cpu_percent(percpu=True)``. See also
      :term:`physical CPU`.

   mapped memory

      A region of a process's virtual address space typically created via
      ``mmap()``. Mappings can be file-backed (e.g. shared libraries,
      memory-mapped files) or :term:`anonymous <anonymous memory>`.
      Each mapping has its own permissions and memory accounting fields
      (:term:`RSS`, :term:`PSS`, private / shared pages).
      See :meth:`Process.memory_maps`.

   NIC

      *Network Interface Card*, a hardware or virtual network interface.
      psutil uses this term when referring to per-interface network
      statistics. See :func:`net_if_addrs` and :func:`net_if_stats`.

   nice

      A process priority value that influences how much CPU time the OS
      scheduler gives to a process. Lower nice values mean higher priority. The
      range is −20 (highest priority) to 19 (lowest) on UNIX; on Windows the
      concept maps to :ref:`priority constants <const-proc-prio>`. See
      :meth:`Process.nice`.

   page cache

      RAM used to cache data of regular files on disk.
      When a process reads a file, the data stays in the page cache, and when
      it writes, the data is first stored in the cache before being written to
      disk. Subsequent reads or writes can be served from RAM without disk I/O,
      making access fast. The OS reclaims page cache automatically under memory
      pressure, so a large cache is healthy. Shown as the :field:`cached` field
      of :func:`virtual_memory` on Linux/BSD.

   page fault

      An event that occurs when a process accesses a virtual memory page that
      is not currently mapped in physical RAM. A :field:`minor` fault occurs
      when a page is already in physical RAM (e.g., in the :term:`page cache`
      or other :term:`shared memory`), but it's not yet mapped into the
      process's virtual address space, so no disk I/O is required (fast). A
      :field:`major` fault requires reading the page from disk, and is
      significantly more expensive. Many major faults may indicate memory
      pressure or excessive swapping. See :meth:`Process.page_faults`.

   peak_rss

      The highest :term:`RSS` value a process has ever reached since it
      started (memory high-water mark). Available via
      :meth:`Process.memory_info` (BSD, Windows) and
      :meth:`Process.memory_info_ex` (Linux, macOS). Useful for capacity
      planning and leak detection: if :field:`peak_rss` keeps growing across
      successive runs or over time, the process is likely leaking memory.
      See also :term:`peak_vms`.

   peak_vms

      The highest :term:`VMS` value a process has ever reached since it
      started. Available via :meth:`Process.memory_info_ex` (Linux) and
      :meth:`Process.memory_info` (Windows). On Windows this maps to
      ``PeakPagefileUsage`` (peak :term:`private <private memory>` committed
      memory), which is not the same as UNIX VMS. See also :term:`peak_rss`.

   physical CPU

      An actual hardware CPU core on the motherboard, as opposed to a
      :term:`logical CPU`. A single physical core may appear as multiple
      logical CPUs when hyper-threading is enabled. The physical count is
      returned by ``cpu_count(logical=False)``.

   private memory

      Memory pages not shared with any other process, such as the
      :term:`heap`, the stack, and other allocations made directly by the
      program, e.g. via ``malloc()``.
      :term:`USS`, returned by :meth:`Process.memory_footprint`, measures
      exactly the private memory of a process, that is the bytes that would be
      freed if the process exited. At a per-mapping level, the
      :field:`private_clean` and :field:`private_dirty` fields of
      :meth:`Process.memory_maps` (Linux) and the :field:`private` field (FreeBSD)
      break it down further.

   PSS

      *Proportional Set Size*, the amount of RAM used by a process,
      where :term:`shared memory` pages are divided proportionally among all
      processes that map them. PSS gives a fairer per-process memory estimate
      than :term:`RSS` when shared libraries are involved. Available on Linux
      via :meth:`Process.memory_footprint`.

   resource limit

      A per-process cap on a system resource enforced by the kernel (POSIX
      :data:`RLIMIT_* <psutil.RLIM_INFINITY>` constants).
      Each limit has a *soft* value (the current enforcement threshold, which
      the process may raise up to the hard limit) and a *hard* value
      (the ceiling, settable only by root).
      Common limits include :data:`RLIM_INFINITY` (open file descriptors),
      :data:`RLIMIT_AS` (virtual address space), and :data:`RLIMIT_CPU`
      (CPU time in seconds). See :meth:`Process.rlimit`.

   RSS

      *Resident Set Size*, the amount of physical RAM currently used by a
      process. This includes :term:`shared memory` pages. It is the most
      commonly reported memory metric (shown as ``RES`` in ``top``), but can be
      misleading because :term:`shared memory` is counted in full for each
      process that maps it.
      See :meth:`Process.memory_info`.

   soft interrupt

      Deferred work scheduled by a :term:`hardware interrupt` handler to
      run later in a less time-critical context (e.g. network packet
      processing, block I/O completion). Using soft interrupts lets the
      hardware interrupt return quickly while the heavier processing
      happens shortly after. Reported as the :field:`soft_interrupts` field of
      :func:`cpu_stats`. A high rate usually points to heavy network or
      disk I/O throughput rather than a hardware problem.

   shared memory

      Memory pages mapped by more than one process at the same time. The most
      common example is shared libraries (e.g. ``libc.so``): the OS loads them
      once and lets every process that needs them map the same physical pages,
      saving RAM. Shared pages are counted in full in :term:`RSS` for every
      process that maps them. :term:`PSS` corrects for this by splitting each
      shared page proportionally among the processes that use it.
      See also :term:`private memory`.

      Exposed by psutil as the :field:`shared` field of :func:`virtual_memory` and
      :meth:`Process.memory_info` (Linux), the :field:`rss_shmem` field of
      :meth:`Process.memory_info_ex` (Linux), and the :field:`shared_clean` /
      :field:`shared_dirty` fields of :meth:`Process.memory_maps` (Linux).

   swap-in

      Memory moved from disk (:term:`swap <swap memory>`) back into RAM.
      Reported as the :field:`sin` :term:`cumulative counter` of
      :func:`swap_memory`. A non-zero :field:`sin` rate usually means the system
      is bringing memory back into RAM for processes to use. See also
      :term:`swap-out`.

   swap-out

      Memory moved from RAM to disk (:term:`swap <swap memory>`).
      Reported as the :field:`sout` :term:`cumulative counter` of
      :func:`swap_memory`.  A non-zero :field:`sout` rate indicates memory
      pressure: the system is running low on RAM and must move data to disk,
      which can slow performance. See also :term:`swap-in`.

      .. seealso::
         - :ref:`swap activity recipe <recipe_swap_activity>`
         - :term:`thrashing`

   swap memory

      Disk space used as an extension of physical RAM. When the OS runs out of
      RAM, it moves memory to disk to free space (:term:`swap-out`), and moves
      it back into RAM (:term:`swap-in`) when a process needs it. If RAM is
      full, the OS may first swap out other pages to make room. Swap prevents
      out-of-memory crashes, but is much slower than RAM, so heavy swapping can
      significantly degrade performance. See :func:`swap_memory` and
      :ref:`swap activity recipe <recipe_swap_activity>`.

   thrashing

      A condition where the system spends more time moving memory between RAM
      and disk (:term:`swap <swap memory>`) than doing actual work, because memory
      demand exceeds available RAM. The symptom is high and sustained rates on
      both :field:`sin` and :field:`sout` from :func:`swap_memory`.
      As a result, the system becomes very slow or unresponsive. CPU utilization
      may look low while everything is waiting on disk I/O.

   USS

      *Unique Set Size*, the :term:`private memory` of a process, that belongs
      exclusively to it, and which would be freed if it exited. It excludes
      :term:`shared memory` pages entirely, making it the most accurate
      single-process memory metric. Available on Linux, macOS, and Windows via
      :meth:`Process.memory_footprint`.

   voluntary context switch

      See :term:`context switch`.

   VMS

      *Virtual Memory Size*, the total virtual address space reserved by a
      process, including mapped files, :term:`shared memory`, stack, and
      :term:`heap`, regardless of whether those pages are currently in RAM or
      in :term:`swap memory`. VMS is almost always much larger than :term:`RSS`
      because most virtual pages are never actually loaded into RAM. See
      :meth:`Process.memory_info`.

   zombie process

      A process that has exited but whose entry remains in the process
      table until its parent calls ``wait()``. Zombies hold a PID but consume
      no CPU or memory.

      .. seealso:: :ref:`faq_zombie_process`
