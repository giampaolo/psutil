.. currentmodule:: psutil
.. include:: _links.rst

API reference
=============

.. note::
   psutil 8.0 introduces breaking API changes. See the
   :ref:`migration guide <migration-8.0>` if upgrading from 7.x.

.. important::
   do not rely on positional unpacking of named tuples.
   Always use attribute access (e.g. ``t.rss``).

.. contents::
   :local:
   :depth: 5

System related functions
------------------------

CPU
^^^

.. function:: cpu_times(percpu=False)

  Return system CPU times as a named tuple. All fields are
  :term:`cumulative counters <cumulative counter>` (seconds) representing time
  the CPU has spent in each mode since boot.
  The attributes availability varies depending on the platform.
  Cross-platform fields:

  - :field:`user`: time spent by processes executing in user mode; on
    Linux this also includes :field:`guest` time.

  - :field:`system`: time spent by processes executing in kernel mode.

  - :field:`idle`: time spent doing nothing.

  Platform-specific fields:

  - :field:`nice` *(Linux, macOS, BSD)*: time spent by :term:`niced <nice>`
    (lower-priority) processes executing in user mode; on Linux this also
    includes :field:`guest_nice` time.

  - :field:`iowait` *(Linux, SunOS, AIX)*: time spent waiting for I/O to complete
    (:term:`iowait`). This is *not* accounted in :field:`idle` time counter.

  - :field:`irq` *(Linux, Windows, BSD)*: time spent for servicing
    :term:`hardware interrupts <hardware interrupt>`.

  - :field:`softirq` *(Linux)*: time spent for servicing
    :term:`soft interrupts <soft interrupt>`.

  - :field:`steal` *(Linux)*: CPU time the virtual machine wanted to run, but was
    used by other virtual machines or the host.

  - :field:`guest` *(Linux)*: time the host CPU spent running a guest operating
    system (virtual machine). Already included in :field:`user` time.

  - :field:`guest_nice` *(Linux)*: like :field:`guest`, but for virtual CPUs
    running at a lower :term:`nice` priority. Already included in :field:`nice`
    time.

  - :field:`dpc` *(Windows)*: time spent servicing deferred procedure calls (DPCs);
    DPCs are interrupts that run at a lower priority than standard interrupts.

  When *percpu* is ``True`` return a list for each :term:`logical CPU` on the
  system. The list is ordered by CPU index. The order of the list is consistent
  across calls.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.cpu_times()
     scputimes(user=17411.7, system=3797.02, idle=51266.57, nice=77.99, iowait=732.58, irq=0.01, softirq=142.43, steal=0.0, guest=0.0, guest_nice=0.0)

  .. note::
    CPU times are always supposed to increase over time, or at least remain the
    same, and that's because time cannot go backwards. Surprisingly sometimes
    this might not be the case (at least on Windows and Linux), see
    `#1210 <https://github.com/giampaolo/psutil/issues/1210#issuecomment-363046156>`_.

  .. versionchanged:: 4.1.0
     Windows: added :field:`irq` and :field:`dpc` fields (:field:`irq` was
     called :field:`interrupt` before 8.0.0).

  .. versionchanged:: 8.0.0
     Windows: :field:`interrupt` field was renamed to :field:`irq`;
     :field:`interrupt` still works but raises :exc:`DeprecationWarning`.

  .. versionchanged:: 8.0.0
     field order was standardized: :field:`user`, :field:`system`,
     :field:`idle` are now always the first three fields. Previously on Linux,
     macOS, and BSD the first three were :field:`user`, :field:`nice`,
     :field:`system`. See :ref:`migration guide <migration-8.0>`.

.. function:: cpu_percent(interval=None, percpu=False)

  Return the current system-wide CPU utilization as a percentage.

  If *interval* is > ``0.0``, measures CPU times before and after the interval
  (blocking). If ``0.0`` or ``None``, returns the utilization since the last
  call or module import, returning immediately.
  That means the first time this is called it will return a meaningless ``0.0``
  value which you are supposed to ignore.
  In this case it is recommended for accuracy that this function be called with
  at least ``0.1`` seconds between calls.

  If *percpu* is ``True``, returns a list of floats representing each
  :term:`logical CPU`. The list is ordered by CPU index and consistent across
  calls.

  This function is thread-safe. It maintains an internal map of thread IDs
  (:func:`threading.get_ident`) so that independent results are returned when
  called from different threads at different intervals.

  .. code-block:: pycon

     >>> import psutil
     >>> # blocking
     >>> psutil.cpu_percent(interval=1)
     2.0
     >>> # non-blocking (percentage since last call)
     >>> psutil.cpu_percent(interval=None)
     2.9
     >>> # blocking, per-cpu
     >>> psutil.cpu_percent(interval=1, percpu=True)
     [5.6, 1.0]
     >>>

  .. seealso:: :ref:`faq_cpu_percent`

  .. versionchanged:: 5.9.6
     the function is now thread safe.

.. function:: cpu_times_percent(interval=None, percpu=False)

  Similar to :func:`cpu_percent`, but provides utilization percentages for each
  specific CPU time. *interval* and *percpu* arguments have the same meaning as
  in :func:`cpu_percent`. On Linux, :field:`guest` and :field:`guest_nice`
  percentages are not accounted in :field:`user` and :field:`user_nice`.

  .. seealso:: :ref:`faq_cpu_percent`

  .. versionchanged:: 4.1.0
     Windows: added :field:`irq` and :field:`dpc` fields (:field:`irq` was
     called :field:`interrupt` before 8.0.0).

  .. versionchanged:: 5.9.6
     function is now thread safe.

.. function:: cpu_count(logical=True)

  Return the number of :term:`logical CPUs <logical CPU>` in the system
  (same as :func:`os.cpu_count`), or ``None`` if undetermined.
  Unlike :func:`os.cpu_count`, this is not influenced by the
  :envvar:`PYTHON_CPU_COUNT` environment variable (Python 3.13+).

  If *logical* is ``False`` return the number of :term:`physical CPUs
  <physical CPU>` only, or ``None`` if undetermined (always ``None`` on
  OpenBSD and NetBSD).

  Example on a system with 2 cores + Hyper Threading:

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.cpu_count()
     4
     >>> psutil.cpu_count(logical=False)
     2

  Note that this may differ from the number of CPUs the current process can
  actually use (e.g. due to :term:`CPU affinity`, cgroups, or Windows
  processor groups). The number of usable CPUs can be obtained with:

  .. code-block:: pycon

     >>> len(psutil.Process().cpu_affinity())
     1

  .. seealso:: :ref:`faq_cpu_count`

.. function:: cpu_stats()

  Return various CPU statistics. All fields are
  :term:`cumulative counters <cumulative counter>` since boot.

  - :field:`ctx_switches`: number of :term:`context switches <context switch>`
    (voluntary + involuntary).
  - :field:`interrupts`:
    number of :term:`hardware interrupts <hardware interrupt>`.
  - :field:`soft_interrupts`:
    number of :term:`soft interrupts <soft interrupt>`; always set to ``0`` on
    Windows and SunOS.
  - :field:`syscalls`: number of system calls; always set to ``0`` on Linux.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.cpu_stats()
     scpustats(ctx_switches=20455687, interrupts=6598984, soft_interrupts=2134212, syscalls=0)

  .. versionadded:: 4.1.0

.. function:: cpu_freq(percpu=False)

  Return :field:`current`, :field:`min` and :field:`max` CPU frequencies
  expressed in MHz. On Linux, :field:`current` is the real-time frequency value
  (changing), on all other platforms this usually represents the nominal
  "fixed" value (never changing).

  If *percpu* is ``True``, and the system supports per-CPU frequency retrieval
  (Linux and FreeBSD), a list of frequencies is returned for each CPU; if not,
  a list with a single element is returned.

  If :field:`min` and :field:`max` cannot be determined they are set to ``0.0``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.cpu_freq()
     scpufreq(current=931.42925, min=800.0, max=3500.0)
     >>> psutil.cpu_freq(percpu=True)
     [scpufreq(current=2394.945, min=800.0, max=3500.0),
      scpufreq(current=2236.812, min=800.0, max=3500.0),
      scpufreq(current=1703.609, min=800.0, max=3500.0),
      scpufreq(current=1754.289, min=800.0, max=3500.0)]

  .. availability:: Linux, macOS, Windows, FreeBSD, OpenBSD.

  .. versionadded:: 5.1.0

  .. versionchanged:: 5.5.1
     added FreeBSD support.

  .. versionchanged:: 5.9.1
     added OpenBSD support.

.. function:: getloadavg()

  Return the average system load over the last 1, 5 and 15 minutes as a
  tuple. On UNIX, this relies on :func:`os.getloadavg`. On Windows, this is
  emulated via a background thread that updates every 5 seconds; the first
  call (and for the following 5 seconds) returns ``(0.0, 0.0, 0.0)``.
  The values only make sense relative to the number of installed
  :term:`logical CPUs <logical CPU>` (e.g. ``3.14`` on a 10-CPU system means
  31.4% load).

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.getloadavg()
     (3.14, 3.89, 4.67)
     >>> psutil.cpu_count()
     10
     >>> # percentage representation
     >>> [x / psutil.cpu_count() * 100 for x in psutil.getloadavg()]
     [31.4, 38.9, 46.7]

  .. versionadded:: 5.6.2

Memory
^^^^^^

.. function:: virtual_memory()

  Return statistics about system memory usage. All values are expressed in
  bytes.

  - :field:`total`: total physical memory (exclusive :term:`swap memory`).
  - :field:`available`: memory that can be given instantly to processes without the
    system going into :term:`swap <swap memory>`. On Linux it uses the ``MemAvailable``
    field from ``/proc/meminfo`` *(kernel 3.14+)*; on older kernels it falls back
    to an estimate. This is the recommended field for monitoring actual memory
    usage in a cross-platform fashion. See :term:`available memory`.
  - :field:`percent`: the percentage usage calculated as
    ``(total - available) / total * 100``.
  - :field:`used`: memory in use, calculated differently depending on the platform
    (see the table below). It is meant for informational purposes. Neither
    ``total - free`` nor ``total - available`` necessarily equals ``used``.
  - :field:`free`: memory not currently allocated to anything. This is
    typically much lower than :field:`available` because the OS keeps recently
    freed memory as reclaimable cache (see :field:`cached` and :field:`buffers`)
    rather than zeroing it immediately. Do not use this to check for
    memory pressure; use :field:`available` instead.
  - :field:`active` *(Linux, macOS, BSD)*: memory currently mapped by processes
    or recently accessed, held in RAM. It is unlikely to be reclaimed unless
    the system is under significant memory pressure.
  - :field:`inactive` *(Linux, macOS, BSD)*: memory not recently accessed. It
    still holds valid data (:term:`page cache`, old allocations) but is a
    candidate for reclamation or :term:`swapping <swap memory>`.
    On BSD systems it is counted in :field:`available`.
  - :field:`buffers` *(Linux, BSD)*: see :term:`buffers`.
    On OpenBSD :field:`buffers` and :field:`cached` are aliases.
  - :field:`cached` *(Linux, BSD, Windows)*: RAM used by the kernel to cache file
    contents (data read from or written to disk).
    On OpenBSD :field:`buffers` and :field:`cached` are aliases.
    See :term:`page cache`.
  - :field:`shared` *(Linux, BSD)*: :term:`shared memory` accessible by multiple
    processes simultaneously, such as in-memory ``tmpfs`` and POSIX shared
    memory objects (``shm_open``). On Linux this corresponds to ``Shmem`` in
    ``/proc/meminfo`` and is already counted within :field:`active` /
    :field:`inactive`.
  - :field:`slab` *(Linux)*: memory used by the kernel's internal object caches
    (e.g. inode and dentry caches). The reclaimable portion
    (``SReclaimable``) is already included in :field:`cached`.
  - :field:`wired` *(macOS, BSD, Windows)*: memory pinned in RAM by the kernel (e.g.
    kernel code and critical data structures). It can never be moved to disk.

  Below is a table showing implementation details. All info on Linux is
  retrieved from `/proc/meminfo`_. On macOS via ``host_statistics64()``. On
  Windows via `GetPerformanceInfo`_.

  .. list-table::
     :header-rows: 1
     :widths: 9 15 14 14 26

     * - Field
       - Linux
       - macOS
       - Windows
       - FreeBSD
     * - total
       - ``MemTotal``
       - ``sysctl() hw.memsize``
       - ``PhysicalTotal``
       - ``sysctl() hw.physmem``
     * - available
       - ``MemAvailable``
       - ``inactive + free``
       - ``PhysicalAvailable``
       - ``inactive + cached + free``
     * - used
       - ``total - available``
       - ``active + wired``
       - ``total - available``
       - ``active + wired + cached``
     * - free
       - ``MemFree``
       - ``free - speculative``
       - same as ``available``
       - ``sysctl() vm.stats.vm.v_free_count``
     * - active
       - ``Active``
       - ``active``
       -
       - ``sysctl() vm.stats.vm.v_active_count``
     * - inactive
       - ``Inactive``
       - ``inactive``
       -
       - ``sysctl() vm.stats.vm.v_inactive_count``
     * - buffers
       - ``Buffers``
       -
       -
       - ``sysctl() vfs.bufspace``
     * - cached
       - ``Cached + SReclaimable``
       -
       - ``SystemCache``
       - ``sysctl() vm.stats.vm.v_cache_count``
     * - shared
       - ``Shmem``
       -
       -
       - ``sysctl(CTL_VM/VM_METER) t_vmshr + t_rmshr``
     * - slab
       - ``Slab``
       -
       -
       -
     * - wired
       -
       - ``wired``
       - ``KernelNonpaged``
       - ``sysctl() vm.stats.vm.v_wire_count``

  Example on Linux:

  .. code-block:: pycon

     >>> import psutil
     >>> mem = psutil.virtual_memory()
     >>> mem
     svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120, free=2181107712, active=4748992512, inactive=2758115328, buffers=790724608, cached=3500347392, shared=787554304, slab=199348224)
     >>>
     >>> THRESHOLD = 500 * 1024 * 1024  # 500MB
     >>> if mem.available <= THRESHOLD:
     ...     print("warning")
     ...
     >>>

  .. note::
     - On Linux, :field:`total`, :field:`free`, :field:`used`, :field:`shared`,
       and :field:`available` match the output of the ``free`` command.
     - On macOS, :field:`free`, :field:`active`, :field:`inactive`,
       and :field:`wired` match ``vm_stat`` command.
     - On BSD, :field:`free`, :field:`active`, :field:`inactive`,
       :field:`cached`, and :field:`wired` match ``vmstat -s`` command.
     - On Windows, :field:`total`, :field:`used` ("In use"), and
       :field:`available` match the Task Manager (Performance > Memory tab).

  .. note::
    if you just want to know how much physical memory is left in a
    cross-platform manner, rely on :field:`available` and
    :field:`percent` fields.

  .. seealso::
    - `scripts/meminfo.py`_
    - :ref:`faq_virtual_memory_available`
    - :ref:`faq_used_plus_free`

  .. versionchanged:: 4.2.0
     Linux: added :field:`shared` field.

  .. versionchanged:: 5.4.4
     Linux: added :field:`slab` field.

  .. versionchanged:: 8.0.0
     Windows: added :field:`cached` and :field:`wired` fields.

.. function:: swap_memory()

  Return system :term:`swap memory` statistics:

  * :field:`total`: total swap space. On Windows this is derived as
    ``CommitLimit - PhysicalTotal``, representing virtual memory backed by
    the page file rather than the raw page-file size.
  * :field:`used`: swap space currently in use.
  * :field:`free`: swap space not in use (``total - used``).
  * :field:`percent`: swap usage as a percentage, calculated as
    ``used / total * 100``.
  * :field:`sin`: number of bytes the system has moved from disk
    (:term:`swap <swap memory>`) back into RAM. See :term:`swap-in`.
  * :field:`sout`: number of bytes the system has moved from RAM to disk
    (:term:`swap <swap memory>`). A continuously increasing
    :field:`sout` rate is a sign of memory pressure. See :term:`swap-out`.

  :field:`sin` and :field:`sout` are :term:`cumulative counters <cumulative counter>`
  since boot. Monitor their rate of change rather than the absolute value to
  detect active :term:`swapping <swap memory>`. On Windows both are always ``0``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.swap_memory()
     sswap(total=2097147904, used=886620160, free=1210527744, percent=42.3, sin=1050411008, sout=1906720768)

  .. seealso::
    - `scripts/meminfo.py`_
    - :ref:`Swap activity recipe <recipe_swap_activity>`

  .. versionchanged:: 5.2.3
     Linux: use /proc instead of ``sysinfo()`` syscall to support
     :data:`PROCFS_PATH` usage (e.g. useful for Docker containers ...).

Disks
^^^^^

.. function:: disk_partitions(all=False)

  Return mounted disk partitions as a list. This is similar to the ``df``
  command on UNIX. When *all* is ``False``, virtual/pseudo filesystems
  (tmpfs, sysfs, devtmpfs, cgroup, etc.) are excluded, keeping only physical
  devices (e.g., hard disks, CD-ROM drives, USB keys). The filtering logic
  varies by platform: on Linux, it checks ``/proc/filesystems`` for
  ``nodev``-flagged types (ZFS is always included); on macOS, it checks
  whether the device path exists; on SunOS and AIX, it excludes filesystems
  with zero total size. On BSD, *all* is ignored and all partitions are
  always returned.

  * :field:`device`: the device path (e.g. "/dev/hda1"). On Windows this is the
    drive letter (e.g. "C:\\").
  * :field:`mountpoint`: the mount point path (e.g. "/"). On Windows this is the
    drive letter (e.g. "C:\\").
  * :field:`fstype`: the partition filesystem (e.g. "ext3" on UNIX or "NTFS"
    on Windows).
  * :field:`opts`: a comma-separated string indicating different mount options for
    the drive/partition. Platform-dependent.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.disk_partitions()
     [sdiskpart(device='/dev/sda3', mountpoint='/', fstype='ext4', opts='rw,errors=remount-ro'),
      sdiskpart(device='/dev/sda7', mountpoint='/home', fstype='ext4', opts='rw')]

  .. seealso:: `scripts/disk_usage.py`_.

  .. versionchanged:: 5.7.4
     added :field:`maxfile` and :field:`maxpath` fields.

  .. versionchanged:: 6.0.0
     removed :field:`maxfile` and :field:`maxpath` fields.

.. function:: disk_usage(path)

  Return disk usage statistics for the partition containing *path*. Values are
  expressed in bytes and include :field:`total`, :field:`used` and
  :field:`free` space, plus the :field:`percentage` usage.
  On UNIX, *path* must point to a path within a **mounted** filesystem partition.
  This function was later incorporated in Python 3.3 as
  :func:`shutil.disk_usage` (see `BPO-12442`_).

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.disk_usage('/')
     sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)

  .. note::
    UNIX typically reserves 5% of disk space for root.
    :field:`total` and :field:`used` refer to overall space, while
    :field:`free` and :field:`percent` reflect unprivileged user usage.
    As a result, :field:`percent` may appear ~5% higher than expected.
    All values match the ``df`` command line utility.

  .. seealso:: `scripts/disk_usage.py`_.

  .. versionchanged:: 4.3.0
     :field:`percent` value takes root reserved space into account.

.. function:: disk_io_counters(perdisk=False, nowrap=True)

  Return system-wide disk I/O statistics:

  - :field:`read_count`: number of reads.
  - :field:`write_count`: number of writes.
  - :field:`read_bytes`: number of bytes read.
  - :field:`write_bytes`: number of bytes written.

  Platform-specific fields:

  - :field:`read_time`: (all except *NetBSD* and *OpenBSD*) time spent reading
    from disk (in milliseconds).
  - :field:`write_time`: (all except *NetBSD* and *OpenBSD*) time spent writing
    to disk (in milliseconds).
  - :field:`busy_time`: (*Linux*, *FreeBSD*) time spent doing actual I/Os (in
    milliseconds); see :term:`busy_time`.
  - :field:`read_merged_count` (*Linux*): number of merged reads
    (see `iostats doc`_).
  - :field:`write_merged_count` (*Linux*): number of merged writes
    (see `iostats doc`_).

  If *perdisk* is ``True``, return the same information for every physical disk
  as a dictionary with partition names as the keys.

  If *nowrap* is ``True`` (default), counters that overflow and wrap to zero
  are automatically adjusted so they never decrease (this can happen on very
  busy or long-lived systems). ``disk_io_counters.cache_clear()`` can be used
  to invalidate the *nowrap* cache.

  On diskless machines this function will return ``None`` or ``{}`` if
  *perdisk* is ``True``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.disk_io_counters()
     sdiskio(read_count=8141, write_count=2431, read_bytes=290203, write_bytes=537676, read_time=5868, write_time=94922)
     >>>
     >>> psutil.disk_io_counters(perdisk=True)
     {'sda1': sdiskio(read_count=920, write_count=1, read_bytes=2933248, write_bytes=512, read_time=6016, write_time=4),
      'sda2': sdiskio(read_count=18707, write_count=8830, read_bytes=6060, write_bytes=3443, read_time=24585, write_time=1572),
      'sdb1': sdiskio(read_count=161, write_count=0, read_bytes=786432, write_bytes=0, read_time=44, write_time=0)}

  .. note::
     On Windows, you may need to run ``diskperf -y`` command first, otherwise
     this function might not detect any disks.

  .. seealso::
     - `scripts/iotop.py`_
     - :ref:`Real-time disk I/O recipe <recipe_disk_io>`
     - :ref:`Real-time disk I/O percent recipe <recipe_disk_io_percent>`

  .. versionchanged:: 5.3.0
     numbers no longer wrap (restart from zero) across calls thanks to new
     *nowrap* argument.

  .. versionchanged:: 4.0.0
     added :field:`busy_time` (Linux, FreeBSD), :field:`read_merged_count` and
     :field:`write_merged_count` (Linux) fields.

  .. versionchanged:: 4.0.0
     NetBSD: removed :field:`read_time` and :field:`write_time` fields.

Network
^^^^^^^

.. function:: net_io_counters(pernic=False, nowrap=True)

  Return system-wide network I/O statistics:

  - :field:`bytes_sent`: number of bytes sent.
  - :field:`bytes_recv`: number of bytes received.
  - :field:`packets_sent`: number of packets sent.
  - :field:`packets_recv`: number of packets received.
  - :field:`errin`: total number of errors while receiving.
  - :field:`errout`: total number of errors while sending.
  - :field:`dropin`: total number of incoming packets dropped at the
    :term:`NIC` level. Unlike :field:`errin`, drops indicate the interface or
    kernel buffer was overwhelmed.
  - :field:`dropout`: total number of outgoing packets dropped (always 0 on macOS
    and BSD). A non-zero and growing count is a sign of network saturation.

  If *pernic* is ``True``, return the same information for every network
  interface as a dictionary, with interface names as the keys.

  If *nowrap* is ``True`` (default), counters that overflow and wrap to zero
  are automatically adjusted so they never decrease (this can happen on very
  busy or long-lived systems). ``net_io_counters.cache_clear()`` can be
  used to invalidate the *nowrap* cache.

  On machines with no :term:`NICs <NIC>` installed this function will return
  ``None`` or ``{}`` if *pernic* is ``True``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_io_counters()
     snetio(bytes_sent=14508483, bytes_recv=62749361, packets_sent=84311, packets_recv=94888, errin=0, errout=0, dropin=0, dropout=0)
     >>>
     >>> psutil.net_io_counters(pernic=True)
     {'lo': snetio(bytes_sent=547971, bytes_recv=547971, packets_sent=5075, packets_recv=5075, errin=0, errout=0, dropin=0, dropout=0),
      'wlan0': snetio(bytes_sent=13921765, bytes_recv=62162574, packets_sent=79097, packets_recv=89648, errin=0, errout=0, dropin=0, dropout=0)}

  .. seealso:: `scripts/nettop.py`_ and `scripts/ifconfig.py`_.

  .. versionchanged:: 5.3.0
     numbers no longer wrap (restart from zero) across calls thanks to new
     *nowrap* argument.

.. function:: net_connections(kind="inet")

  Return system-wide socket connections as a list. Each entry provides 7 fields:

  - :field:`fd`: the socket :term:`file descriptor`; set to ``-1`` on Windows
    and SunOS.
  - :field:`family`: the address family, either :data:`socket.AF_INET`,
    :data:`socket.AF_INET6` or :data:`socket.AF_UNIX`.
  - :field:`type`: the address type, either :data:`socket.SOCK_STREAM`,
    :data:`socket.SOCK_DGRAM` or :data:`socket.SOCK_SEQPACKET`.
  - :field:`laddr`: the local address as a ``(ip, port)`` named tuple, or a
    ``path`` for :data:`socket.AF_UNIX` sockets.
  - :field:`raddr`: the remote address. When the socket is not connected, this is either
    an empty tuple (``AF_INET*``) or an empty string (``""``) for ``AF_UNIX``
    sockets (see note below).
  - :field:`status`: a :data:`CONN_* <psutil.CONN_ESTABLISHED>` constant;
    always :data:`CONN_NONE` for UDP and UNIX sockets.
  - :field:`pid`: PID of the process which opened the socket. Set to ``None``
    if it can't be retrieved due to insufficient permissions (e.g. Linux).

  The *kind* parameter is a string which filters for connections matching the
  following criteria:

  .. table::

   +----------------+-----------------------------------------------------+
   | Kind value     | Connections using                                   |
   +================+=====================================================+
   | ``'inet'``     | IPv4 and IPv6                                       |
   +----------------+-----------------------------------------------------+
   | ``'inet4'``    | IPv4                                                |
   +----------------+-----------------------------------------------------+
   | ``'inet6'``    | IPv6                                                |
   +----------------+-----------------------------------------------------+
   | ``'tcp'``      | TCP                                                 |
   +----------------+-----------------------------------------------------+
   | ``'tcp4'``     | TCP over IPv4                                       |
   +----------------+-----------------------------------------------------+
   | ``'tcp6'``     | TCP over IPv6                                       |
   +----------------+-----------------------------------------------------+
   | ``'udp'``      | UDP                                                 |
   +----------------+-----------------------------------------------------+
   | ``'udp4'``     | UDP over IPv4                                       |
   +----------------+-----------------------------------------------------+
   | ``'udp6'``     | UDP over IPv6                                       |
   +----------------+-----------------------------------------------------+
   | ``'unix'``     | UNIX socket (both UDP and TCP protocols)            |
   +----------------+-----------------------------------------------------+
   | ``'all'``      | the sum of all the possible families and protocols  |
   +----------------+-----------------------------------------------------+

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_connections()
     [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>, pid=1254),
      pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=43761), raddr=addr(ip='72.14.234.100', port=80), status=<ConnectionStatus.CONN_CLOSING: 'CLOSING'>, pid=2987),
      pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=60759), raddr=addr(ip='72.14.234.104', port=80), status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>, pid=None),
      pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=51314), raddr=addr(ip='72.14.234.83', port=443), status=<ConnectionStatus.CONN_SYN_SENT: 'SYN_SENT'>, pid=None)
      ...]

  .. warning::
    on Linux, retrieving some connections requires root privileges. If psutil is
    not run as root, those connections are silently skipped instead of raising
    :exc:`PermissionError`. That means the returned list may be incomplete.

  .. note::
    - Linux, FreeBSD, OpenBSD: :field:`raddr` field for UNIX sockets is always set to
      ``""``; this is a limitation of the OS.
    - macOS and AIX: :exc:`AccessDenied` is always raised unless running
      as root; this is a limitation of the OS.
    - Solaris: UNIX sockets are not supported.

  .. seealso::

    - :meth:`Process.net_connections` to get per-process connections
    - `scripts/netstat.py`_

  .. versionadded:: 2.1.0

  .. versionchanged:: 5.3.0
     socket :field:`fd` is now set for real instead of being ``-1``.

  .. versionchanged:: 5.3.0
    :field:`laddr` and :field:`raddr` are named tuples.

  .. versionchanged:: 5.9.5
     OpenBSD: retrieve :field:`laddr` path for :data:`socket.AF_UNIX` sockets
     (before it was an empty string).

  .. versionchanged:: 8.0.0
     :field:`status` field is now a :class:`ConnectionStatus` enum member
     instead of a plain ``str``.
     See :ref:`migration guide <migration-8.0>`.

.. function:: net_if_addrs()

  Return a dict mapping each :term:`NIC` to its addresses. Interfaces may have
  multiple addresses per family. Each entry includes 5 fields (addresses may be
  ``None``):

  - :field:`family`: the address family, either :data:`socket.AF_INET` (IPv4),
    :data:`socket.AF_INET6` (IPv6), :data:`socket.AF_UNSPEC` (a virtual or
    unconfigured NIC), or :data:`AF_LINK` (a MAC address).
  - :field:`address`: the primary NIC address.
  - :field:`netmask`: the netmask address.
  - :field:`broadcast`: the broadcast address; always ``None`` on Windows.
  - :field:`ptp`: a "point to point" address (typically a VPN); always ``None`` on
    Windows.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_if_addrs()
     {'lo': [snicaddr(family=<AddressFamily.AF_INET: 2>, address='127.0.0.1', netmask='255.0.0.0', broadcast='127.0.0.1', ptp=None),
             snicaddr(family=<AddressFamily.AF_INET6: 10>, address='::1', netmask='ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', broadcast=None, ptp=None),
             snicaddr(family=<AddressFamily.AF_LINK: 17>, address='00:00:00:00:00:00', netmask=None, broadcast='00:00:00:00:00:00', ptp=None)],
      'wlan0': [snicaddr(family=<AddressFamily.AF_INET: 2>, address='192.168.1.3', netmask='255.255.255.0', broadcast='192.168.1.255', ptp=None),
                snicaddr(family=<AddressFamily.AF_INET6: 10>, address='fe80::c685:8ff:fe45:641%wlan0', netmask='ffff:ffff:ffff:ffff::', broadcast=None, ptp=None),
                snicaddr(family=<AddressFamily.AF_LINK: 17>, address='c4:85:08:45:06:41', netmask=None, broadcast='ff:ff:ff:ff:ff:ff', ptp=None)]}
     >>>

  .. seealso:: `scripts/nettop.py`_ and `scripts/ifconfig.py`_.

  .. versionadded:: 3.0.0

  .. versionchanged:: 3.2.0
     added :field:`ptp` field.

  .. versionchanged:: 4.4.0
     Windows: added support for :field:`netmask` field, which is no longer ``None``.

  .. versionchanged:: 7.0.0
     Windows: added support for :field:`broadcast` field, which is no longer ``None``.

.. function:: net_if_stats()

  Return a dictionary mapping each :term:`NIC` to its stats:

  - :field:`isup`: whether the NIC is up and running (bool).
  - :field:`duplex`: :data:`NIC_DUPLEX_FULL`, :data:`NIC_DUPLEX_HALF` or
    :data:`NIC_DUPLEX_UNKNOWN`.
  - :field:`speed`: NIC speed in megabits (Mbps); ``0`` if undetermined.
  - :field:`mtu`: maximum transmission unit in bytes.
  - :field:`flags`: a comma-separated string of interface flags (e.g.
    ``"up,broadcast,running,multicast"``); may be an empty string.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_if_stats()
     {'eth0': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_FULL: 2>, speed=100, mtu=1500, flags='up,broadcast,running,multicast'),
      'lo': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_UNKNOWN: 0>, speed=0, mtu=65536, flags='up,loopback,running')}

  .. seealso:: `scripts/nettop.py`_ and `scripts/ifconfig.py`_.

  .. versionadded:: 3.0.0

  .. versionchanged:: 5.7.3
     UNIX: :field:`isup` also reflects whether the :term:`NIC` is running.

  .. versionchanged:: 5.9.3
     added :field:`flags` field.

Sensors
^^^^^^^

.. function:: sensors_temperatures(fahrenheit=False)

  Return hardware temperatures. Each entry represents a sensor (CPU, disk,
  etc.). Values are in Celsius unless *fahrenheit* is ``True``. If unsupported,
  an empty dict is returned. Each entry includes:

  - :field:`label`: string label for the sensor, if available, else ``""``.
  - :field:`current`: current temperature reading (changing), or ``None`` if
    unavailable.
  - :field:`high`: sensor-specified high temperature threshold (fixed), or
    ``None`` if unavailable. Typically indicates when hardware may start
    throttling to reduce heat.
  - :field:`critical`: sensor-specified critical temperature threshold (fixed),
    or ``None`` if unavailable. Typically indicates when hardware considers
    itself at risk; behavior may include throttling, fan ramp-up, or shutdown.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.sensors_temperatures()
     {'acpitz': [shwtemp(label='', current=47.0, high=103.0, critical=103.0)],
      'asus': [shwtemp(label='', current=47.0, high=None, critical=None)],
      'coretemp': [shwtemp(label='Physical id 0', current=52.0, high=100.0, critical=100.0),
                   shwtemp(label='Core 0', current=45.0, high=100.0, critical=100.0),
                   shwtemp(label='Core 1', current=52.0, high=100.0, critical=100.0),
                   shwtemp(label='Core 2', current=45.0, high=100.0, critical=100.0),
                   shwtemp(label='Core 3', current=47.0, high=100.0, critical=100.0)]}

  .. seealso:: `scripts/temperatures.py`_ and `scripts/sensors.py`_.

  .. availability:: Linux, FreeBSD

  .. versionadded:: 5.1.0

  .. versionchanged:: 5.5.0
     added FreeBSD support.

.. function:: sensors_fans()

  Return hardware fan speeds in RPM (revolutions per minute).
  If unsupported, return an empty dict.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.sensors_fans()
     {'asus': [sfan(label='cpu_fan', current=3200)]}

  .. seealso:: `scripts/fans.py`_ and `scripts/sensors.py`_.

  .. availability:: Linux

  .. versionadded:: 5.2.0

.. function:: sensors_battery()

  Return battery status information. If no battery is installed or metrics
  can't be determined ``None`` is returned.

  - :field:`percent`: battery power left as a percentage.
  - :field:`secsleft`: a rough approximation of how many seconds are left before the
    battery runs out of power.
    If the AC power cable is connected this is set to :data:`POWER_TIME_UNLIMITED`.
    If it can't be determined it is set to :data:`POWER_TIME_UNKNOWN`.
  - :field:`power_plugged`: ``True`` if the AC power cable is connected, ``False``
    if not, or ``None`` if it can't be determined.

  .. code-block:: pycon

     >>> import psutil
     >>>
     >>> def secs2hours(secs):
     ...     mm, ss = divmod(secs, 60)
     ...     hh, mm = divmod(mm, 60)
     ...     return "%d:%02d:%02d" % (hh, mm, ss)
     ...
     >>> battery = psutil.sensors_battery()
     >>> battery
     sbattery(percent=93, secsleft=16628, power_plugged=False)
     >>> print("charge = %s%%, time left = %s" % (battery.percent, secs2hours(battery.secsleft)))
     charge = 93%, time left = 4:37:08

  .. seealso:: `scripts/battery.py`_ and `scripts/sensors.py`_.

  .. availability:: Linux, Windows, macOS, FreeBSD

  .. versionadded:: 5.1.0

  .. versionchanged:: 5.4.2
     added macOS support.

-------------------------------------------------------------------------------

Other system info
^^^^^^^^^^^^^^^^^

.. function:: boot_time()

  Return the system boot time expressed in seconds since the epoch (seconds
  since January 1, 1970, at midnight UTC). The return value is based on the
  system clock, which means it can be affected by changes such as manual
  adjustments or time synchronization (e.g. NTP).

  .. code-block:: pycon

     >>> import psutil, datetime
     >>> psutil.boot_time()
     1389563460.0
     >>> datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
     '2014-01-12 22:51:00'

.. function:: users()

  Return users currently connected on the system as a list. Each entry includes:

  - :field:`name`: the name of the user.
  - :field:`terminal`: the tty or pseudo-tty associated with the user, if any,
    else ``None``.
  - :field:`host`: the host name associated with the entry, if any (for
    example, the remote host in an SSH session), else ``None``.
  - :field:`started`: the creation time as a floating point number expressed in
    seconds since the epoch.
  - :field:`pid`: the PID of the login process (like sshd for remote logins,
    tmux, etc.). On Windows and OpenBSD this is always ``None``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.users()
     [suser(name='giampaolo', terminal='pts/2', host='localhost', started=1340737536.0, pid=1352),
      suser(name='giampaolo', terminal='pts/3', host='localhost', started=1340737792.0, pid=1788)]

  .. versionchanged:: 5.3.0
     added :field:`pid` field.

-------------------------------------------------------------------------------

Processes
---------

Functions
^^^^^^^^^

.. function:: pids()

  Return a sorted list of currently running PIDs.
  To iterate over all processes and avoid race conditions :func:`process_iter`
  is preferred, see :ref:`perf-process-iter`.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.pids()
     [1, 2, 3, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, ..., 32498]


  .. versionchanged:: 5.6.0
     PIDs are returned in sorted order.

.. function:: process_iter(attrs=None, ad_value=None)

  Return an iterator yielding a :class:`Process` instance for all running
  processes.
  This should be preferred over :func:`psutil.pids` to iterate over
  processes, as retrieving info is safe from race conditions.

  Every :class:`Process` instance is only created once, and then cached for the
  next time :func:`psutil.process_iter` is called (if PID is still alive).
  Cache can optionally be cleared via ``process_iter.cache_clear()``.

  *attrs* and *ad_value* have the same meaning as in :meth:`Process.as_dict`.

  If *attrs* is specified, :meth:`Process.as_dict` is called internally, and the
  results are cached so that subsequent method calls (e.g. ``p.name()``,
  ``p.status()``) return the cached values instead of issuing new system calls.
  See :attr:`Process.attrs` for a list of valid *attrs* names.

  If a method raises :exc:`AccessDenied` during pre-fetch, it will return
  *ad_value* (default ``None``) instead of raising.

  Processes are returned sorted by PID.

  .. code-block:: pycon

     >>> import psutil
     >>> for proc in psutil.process_iter(['pid', 'name', 'username']):
     ...     print(proc.pid, proc.name(), proc.username())  # return cached values, never raise
     ...
     1 systemd root
     2 kthreadd root
     3 ksoftirqd/0 root
     ...

  All process *attrs* except slow ones:

  .. code-block:: pycon

    >>> for p in psutil.process_iter(psutil.Process.attrs - {'memory_footprint', 'memory_maps'}):
    ...     print(p)

  Clear internal cache:

  .. code-block:: pycon

     >>> psutil.process_iter.cache_clear()

  .. note::

    since :class:`Process` instances are reused across calls, a subsequent
    :func:`process_iter` call will overwrite or clear any previously
    pre-fetched values. Do not rely on cached values from a prior iteration.

  .. seealso:: :ref:`perf-process-iter`

  .. versionchanged:: 5.3.0
     added *attrs* and *ad_value* arguments.

  .. versionchanged:: 6.0.0

     - No longer checks whether each yielded process PID has been reused.
     - Added ``psutil.process_iter.cache_clear()`` API.

  .. versionchanged:: 8.0.0

     - When *attrs* is specified, the pre-fetched values are cached directly on
       the :class:`Process` instance, so that subsequent method calls (e.g.
       ``p.name()``, ``p.status()``) return the cached values instead of making
       new system calls. The :attr:`Process.info` dict is deprecated in favor of
       this new approach.
     - Passing an empty list (``attrs=[]``) to mean "all attributes" is
       deprecated; use :attr:`Process.attrs` instead.

.. function:: pid_exists(pid)

  Check whether the given PID exists in the current process list. This is
  faster than doing ``pid in psutil.pids()``, and should be preferred.

  .. seealso:: :ref:`faq_pid_exists_vs_isrunning`

.. function:: wait_procs(procs, timeout=None, callback=None)

  Bulk operation that waits for a list of :class:`Process` instances to
  terminate. Return a ``(gone, alive)`` tuple. The ``gone`` processes will have
  a new ``returncode`` attribute set by
  :meth:`Process.wait`.

  *callback* is called with a :class:`Process` instance whenever a process
  terminates.

  Returns as soon as all processes terminate or *timeout* (seconds) expires.
  Unlike :meth:`Process.wait`, it does not raise :exc:`TimeoutExpired` on timeout.

  Typical usage:

  - send SIGTERM to a list of processes
  - wait a short time
  - send SIGKILL to any still alive

  .. code-block:: python

    import psutil

    def on_terminate(proc):
        print(f"{proc} terminated with exit code {proc.returncode}")

    procs = psutil.Process().children()
    for p in procs:
        p.terminate()
    gone, alive = psutil.wait_procs(procs, timeout=3, callback=on_terminate)
    for p in alive:
        print(f"{p} is still alive, send SIGKILL")
        p.kill()

Exceptions
^^^^^^^^^^

.. exception:: Error()

  Base exception class. All other exceptions inherit from this one.

.. exception:: NoSuchProcess(pid, name=None, msg=None)

  Raised by :class:`Process` class or its methods when a process with the given
  *pid* is not found, no longer exists, or its PID has been reused. *name*
  attribute is set only if
  :meth:`Process.name` was called before the process disappeared.

  .. seealso:: :ref:`faq_no_such_process`


.. exception:: ZombieProcess(pid, name=None, ppid=None, msg=None)

  Subclass of :exc:`NoSuchProcess`. Raised by :class:`Process` methods when
  encountering a :term:`zombie process` on UNIX (Windows does not have
  zombies). *name* and *ppid* attributes are set if :meth:`Process.name` or
  :meth:`Process.ppid` were called before the process became a zombie.

  If you do not need to detect zombies, you can ignore this exception and
  just catch :exc:`NoSuchProcess`.

  .. seealso:: :ref:`faq_zombie_process`

  .. versionadded:: 3.0.0

.. exception:: AccessDenied(pid=None, name=None, msg=None)

  Raised by :class:`Process` methods when an action is denied due to
  insufficient privileges. *name* is set if :meth:`Process.name` was called
  before the exception was raised.

  .. seealso:: :ref:`faq_access_denied`

.. exception:: TimeoutExpired(seconds, pid=None, name=None, msg=None)

  Raised by :meth:`Process.wait` method if timeout expires and the process is
  still alive.
  *name* attribute is set if :meth:`Process.name` was previously called.

Process class
^^^^^^^^^^^^^

.. class:: Process(pid=None)

  Represents an OS process with the given *pid*. If *pid* is omitted, the
  current process *pid* (:func:`os.getpid`) is used. Raises
  :exc:`NoSuchProcess` if *pid* does not exist.

  On Linux, *pid* can also refer to a thread ID (the :field:`id` field returned
  by :meth:`threads`).

  When calling methods of this class, always be prepared to catch
  :exc:`NoSuchProcess` and :exc:`AccessDenied` exceptions.
  The builtin :func:`hash` can be used on instances to uniquely identify a
  process over time (the hash combines PID and creation time), so instances
  can also be used in a :class:`set`.

  .. note::

    This class is bound to a process via its **PID**. If the process terminates
    and the OS reuses its PID, you may accidentally interact with another
    process. To prevent this, use :meth:`is_running` first. Some methods
    (e.g., setters and signal-related methods) perform an additional check
    using PID + creation time, and will raise :exc:`NoSuchProcess` if the PID
    has been reused. See :ref:`faq_pid_reuse` for details.

  .. note::

    To fetch multiple attributes efficiently, use the :meth:`oneshot` context
    manager or the :meth:`as_dict` utility method.

  .. attribute:: pid

    The process PID as a read-only property.

  .. attribute:: attrs

    A :class:`frozenset` of strings representing the valid attribute names accepted
    by :meth:`as_dict` and :func:`process_iter`. It defaults to all read-only
    :class:`Process` method names, minus the utility methods such as
    :meth:`as_dict`, :meth:`children`, etc.

    .. code-block:: pycon

       >>> import psutil
       >>> psutil.Process.attrs
       frozenset({'cmdline', 'cpu_num', 'cpu_percent', ...})
       >>> # all attrs
       >>> psutil.process_iter(attrs=psutil.Process.attrs)
       >>> # all attrs except 'net_connections'
       >>> psutil.process_iter(attrs=psutil.Process.attrs - {"net_connections"})

    .. versionadded:: 8.0.0

  .. attribute:: info

    A dict containing pre-fetched process info, set by
    :func:`process_iter` when called with ``attrs`` argument.
    Accessing this attribute is deprecated and raises :exc:`DeprecationWarning`.
    Use method calls instead (e.g. ``p.name()`` instead of ``p.info['name']``)
    or :func:`process_iter` + :meth:`Process.as_dict` if you need a dict
    structure.

    .. seealso:: :ref:`migration guide <migration-8.0>`.

    .. deprecated:: 8.0.0

  .. method:: oneshot()

    Context manager that speeds up retrieval of multiple process
    attributes. Internally, many attributes (e.g.
    :meth:`name`, :meth:`ppid`, :meth:`uids`, :meth:`create_time`, ...)
    share the same underlying system call; within this context, those
    calls are executed once and results are cached, avoiding redundant
    syscalls.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> with p.oneshot():
       ...     p.name()  # actual syscall
       ...     p.cpu_times()  # from cache
       ...     p.create_time()  # from cache
       ...     p.ppid()  # from cache
       ...     p.status()  # from cache
       ...
       >>>

    The table below lists methods that benefit from the speedup, grouped
    by platform. Methods separated by an empty row share the same
    underlying system call. The *speedup* row estimates the gain when all
    listed methods are called together (best case), as measured by
    `bench_oneshot.py <https://github.com/giampaolo/psutil/blob/master/scripts/internal/bench_oneshot.py>`_
    script.

    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | Linux                        | Windows                       | macOS                        | BSD                          | SunOS                    | AIX                      |
    +==============================+===============================+==============================+==============================+==========================+==========================+
    | :meth:`cpu_num`              | :meth:`~Process.cpu_percent`  | :meth:`~Process.cpu_percent` | :meth:`cpu_num`              | :meth:`name`             | :meth:`name`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`~Process.cpu_percent` | :meth:`cpu_times`             | :meth:`cpu_times`            | :meth:`~Process.cpu_percent` | :meth:`cmdline`          | :meth:`cmdline`          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`cpu_times`            | :meth:`io_counters`           | :meth:`memory_info`          | :meth:`cpu_times`            | :meth:`create_time`      | :meth:`create_time`      |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`create_time`          | :meth:`memory_info`           | :meth:`memory_percent`       | :meth:`create_time`          |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`name`                 | :meth:`memory_info_ex`        | :meth:`num_ctx_switches`     | :meth:`gids`                 | :meth:`memory_info`      | :meth:`memory_info`      |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`page_faults`          | :meth:`num_ctx_switches`      | :meth:`num_threads`          | :meth:`io_counters`          | :meth:`memory_percent`   | :meth:`memory_percent`   |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`ppid`                 | :meth:`num_handles`           |                              | :meth:`name`                 | :meth:`num_threads`      | :meth:`num_threads`      |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`status`               | :meth:`num_threads`           | :meth:`create_time`          | :meth:`memory_info`          | :meth:`ppid`             | :meth:`ppid`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`terminal`             |                               | :meth:`gids`                 | :meth:`memory_percent`       | :meth:`status`           | :meth:`status`           |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    |                              | :meth:`exe`                   | :meth:`name`                 | :meth:`num_ctx_switches`     | :meth:`terminal`         | :meth:`terminal`         |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`gids`                 | :meth:`name`                  | :meth:`ppid`                 | :meth:`ppid`                 |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`memory_info_ex`       |                               | :meth:`status`               | :meth:`status`               | :meth:`gids`             | :meth:`gids`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`num_ctx_switches`     |                               | :meth:`terminal`             | :meth:`terminal`             | :meth:`uids`             | :meth:`uids`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`num_threads`          |                               | :meth:`terminal`             | :meth:`terminal`             | :meth:`uids`             | :meth:`uids`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`uids`                 |                               | :meth:`uids`                 | :meth:`uids`                 | :meth:`username`         | :meth:`username`         |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`username`             |                               | :meth:`username`             | :meth:`username`             |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    |                              |                               |                              |                              |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`memory_footprint`     |                               |                              |                              |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`memory_maps`          |                               |                              |                              |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | *speedup: +1.8x*             | *speedup: +1.8x / +6.5x*      | *speedup: +1.9x*             | *speedup: +2.0x*             | *speedup: +1.3x*         | *speedup: +1.3x*         |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+

    .. seealso::
      - :ref:`perf-oneshot`
      - :ref:`perf-oneshot-bench`

    .. versionadded:: 5.0.0

  .. method:: name()

    The process name.  On Windows the return value is cached after first
    call. Not on POSIX because the process name may change.

    .. seealso:: how to :ref:`find a process by name <recipe_find_process_by_name>`.

  .. method:: exe()

    The process executable as an absolute path. On some systems, if exe cannot
    be determined for some internal reason (e.g. system process or path no
    longer exists), this is an empty string. The return value is cached after
    first call.

    .. code-block:: pycon

       >>> import psutil
       >>> psutil.Process().exe()
       '/usr/bin/python3'

  .. method:: cmdline()

    The command line used to start this process, as a list of strings.
    The return value is not cached because the cmdline of a process may change.

    .. code-block:: pycon

       >>> import psutil
       >>> psutil.Process().cmdline()
       ['python3', 'manage.py', 'runserver']

  .. method:: environ()

    The environment variables of the process as a dict.  Note: this might not
    reflect changes made after the process started.

    .. code-block:: pycon

       >>> import psutil
       >>> psutil.Process().environ()
       {'LC_NUMERIC': 'it_IT.UTF-8', 'QT_QPA_PLATFORMTHEME': 'appmenu-qt5', 'IM_CONFIG_PHASE': '1', 'XDG_GREETER_DATA_DIR': '/var/lib/lightdm-data/giampaolo', 'XDG_CURRENT_DESKTOP': 'Unity', 'UPSTART_EVENTS': 'started starting', 'GNOME_KEYRING_PID': '', 'XDG_VTNR': '7', 'QT_IM_MODULE': 'ibus', 'LOGNAME': 'giampaolo', 'USER': 'giampaolo', 'PATH': '/home/giampaolo/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/usr/games:/usr/local/games:/snap/bin:/home/giampaolo/svn/sysconf/bin', 'LC_PAPER': 'it_IT.UTF-8', 'GNOME_KEYRING_CONTROL': '', 'GTK_IM_MODULE': 'ibus', 'DISPLAY': ':0', 'LANG': 'en_US.UTF-8', 'LESS_TERMCAP_se': '\x1b[0m', 'TERM': 'xterm-256color', 'SHELL': '/bin/bash', 'XDG_SESSION_PATH': '/org/freedesktop/DisplayManager/Session0', 'XAUTHORITY': '/home/giampaolo/.Xauthority', 'LANGUAGE': 'en_US', 'COMPIZ_CONFIG_PROFILE': 'ubuntu', 'LC_MONETARY': 'it_IT.UTF-8', 'QT_LINUX_ACCESSIBILITY_ALWAYS_ON': '1', 'LESS_TERMCAP_me': '\x1b[0m', 'LESS_TERMCAP_md': '\x1b[01;38;5;74m', 'LESS_TERMCAP_mb': '\x1b[01;31m', 'HISTSIZE': '100000', 'UPSTART_INSTANCE': '', 'CLUTTER_IM_MODULE': 'xim', 'WINDOWID': '58786407', 'EDITOR': 'vim', 'SESSIONTYPE': 'gnome-session', 'XMODIFIERS': '@im=ibus', 'GPG_AGENT_INFO': '/home/giampaolo/.gnupg/S.gpg-agent:0:1', 'HOME': '/home/giampaolo', 'HISTFILESIZE': '100000', 'QT4_IM_MODULE': 'xim', 'GTK2_MODULES': 'overlay-scrollbar', 'XDG_SESSION_DESKTOP': 'ubuntu', 'SHLVL': '1', 'XDG_RUNTIME_DIR': '/run/user/1000', 'INSTANCE': 'Unity', 'LC_ADDRESS': 'it_IT.UTF-8', 'SSH_AUTH_SOCK': '/run/user/1000/keyring/ssh', 'VTE_VERSION': '4205', 'GDMSESSION': 'ubuntu', 'MANDATORY_PATH': '/usr/share/gconf/ubuntu.mandatory.path', 'VISUAL': 'vim', 'DESKTOP_SESSION': 'ubuntu', 'QT_ACCESSIBILITY': '1', 'XDG_SEAT_PATH': '/org/freedesktop/DisplayManager/Seat0', 'LESSCLOSE': '/usr/bin/lesspipe %s %s', 'LESSOPEN': '| /usr/bin/lesspipe %s', 'XDG_SESSION_ID': 'c2', 'DBUS_SESSION_BUS_ADDRESS': 'unix:abstract=/tmp/dbus-9GAJpvnt8r', '_': '/usr/bin/python', 'DEFAULTS_PATH': '/usr/share/gconf/ubuntu.default.path', 'LC_IDENTIFICATION': 'it_IT.UTF-8', 'LESS_TERMCAP_ue': '\x1b[0m', 'UPSTART_SESSION': 'unix:abstract=/com/ubuntu/upstart-session/1000/1294', 'XDG_CONFIG_DIRS': '/etc/xdg/xdg-ubuntu:/usr/share/upstart/xdg:/etc/xdg', 'GTK_MODULES': 'gail:atk-bridge:unity-gtk-module', 'XDG_SESSION_TYPE': 'x11', 'PYTHONSTARTUP': '/home/giampaolo/.pythonstart', 'LC_NAME': 'it_IT.UTF-8', 'OLDPWD': '/home/giampaolo/svn/curio_giampaolo/tests', 'GDM_LANG': 'en_US', 'LC_TELEPHONE': 'it_IT.UTF-8', 'HISTCONTROL': 'ignoredups:erasedups', 'LC_MEASUREMENT': 'it_IT.UTF-8', 'PWD': '/home/giampaolo/svn/curio_giampaolo', 'JOB': 'gnome-session', 'LESS_TERMCAP_us': '\x1b[04;38;5;146m', 'UPSTART_JOB': 'unity-settings-daemon', 'LC_TIME': 'it_IT.UTF-8', 'LESS_TERMCAP_so': '\x1b[38;5;246m', 'PAGER': 'less', 'XDG_DATA_DIRS': '/usr/share/ubuntu:/usr/share/gnome:/usr/local/share/:/usr/share/:/var/lib/snapd/desktop', 'XDG_SEAT': 'seat0'}

    .. note::
      on macOS Big Sur this function returns something meaningful only for the
      current process or in
      `other specific circumstances <https://github.com/apple/darwin-xnu/blob/2ff845c2e033bd0ff64b5b6aa6063a1f8f65aa32/bsd/kern/kern_sysctl.c#L1315-L1321>`_.

    .. versionadded:: 4.0.0

    .. versionchanged:: 5.3.0
       added SunOS support.

    .. versionchanged:: 5.6.3
       added AIX support.

    .. versionchanged:: 5.7.3
       added BSD support.

  .. method:: create_time()

    The process creation time as a floating point number expressed in seconds
    since the epoch (seconds since January 1, 1970, at midnight UTC). The
    return value, which is cached after first call, is based on the system
    clock, which means it is affected by changes such as manual adjustments
    or time synchronization (e.g. NTP).

    .. code-block:: pycon

       >>> import psutil, datetime
       >>> p = psutil.Process()
       >>> p.create_time()
       1307289803.47
       >>> datetime.datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S")
       '2011-03-05 18:03:52'

    .. method:: as_dict(attrs=None, ad_value=None)

      Utility method returning multiple process information as a dictionary.

      If *attrs* is specified, it must be a collection of strings reflecting
      available :class:`Process` class's attribute names. If not passed all
      :attr:`Process.attrs` names are assumed.

      *ad_value* is the value which gets assigned to a dict key in case
      :exc:`AccessDenied` or :exc:`ZombieProcess` exception is raised when
      retrieving that particular process information (default ``None``).

      The ``'net_connections'`` attribute is retrieved by calling
      :meth:`Process.net_connections` with ``kind="inet"``.

      Internally, :meth:`as_dict` uses :meth:`oneshot` context manager so
      there's no need you use it also.
    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.as_dict(attrs=['pid', 'name', 'username'])
       {'username': 'giampaolo', 'pid': 12366, 'name': 'python'}
       >>> # all attrs except slow ones
       >>> p.as_dict(attrs=p.attrs - {'memory_footprint', 'memory_maps'})
       {'username': 'giampaolo', 'pid': 12366, 'name': 'python', ...}
       >>>

    .. versionchanged:: 3.0.0
       *ad_value* is used also when incurring into :exc:`ZombieProcess`
       exception, not only :exc:`AccessDenied`.

    .. versionchanged:: 4.5.0
       :meth:`as_dict` is considerably faster thanks to :meth:`oneshot`
       context manager.

  .. method:: ppid()

    The process parent PID. On Windows the return value is cached after the
    first call. On POSIX it is not cached because it may change if the process
    becomes a :term:`zombie <zombie process>`. See also :meth:`parent` and
    :meth:`parents` methods.

  .. method:: parent()

    Utility method which returns the parent process as a :class:`Process`
    object, preemptively checking whether PID has been reused. If no parent
    PID is known return ``None``.
    See also :meth:`ppid` and :meth:`parents` methods.

  .. method:: parents()

    Utility method which returns the parents of this process as a list of
    :class:`Process` instances. If no parents are known return an empty list.
    See also :meth:`ppid` and :meth:`parent` methods.

    .. versionadded:: 5.6.0

  .. method:: status()

    The current process status as a :class:`ProcessStatus` enum member.
    The returned value is one of the :data:`STATUS_* <psutil.STATUS_RUNNING>`
    constants.
    A common use case is detecting :term:`zombie processes <zombie process>`
    (``p.status() == psutil.STATUS_ZOMBIE``).

    .. versionchanged:: 8.0.0
       return value is now a :class:`ProcessStatus` enum member instead of a
       plain ``str``.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: cwd()

    The process current working directory as an absolute path. If it cannot be
    determined (e.g. a system process or directory no longer exists) it returns
    an empty string.

    .. versionchanged:: 5.6.4
       added support for NetBSD.

  .. method:: username()

    The name of the user that owns the process. On UNIX this is calculated by
    using the :field:`real` process UID from :meth:`uids`.

  .. method:: uids()

    The :field:`real`, :field:`effective` and :field:`saved` user ID of this
    process as a named tuple. This is the same as :func:`os.getresuid`, but can
    be used for any process PID.

    .. availability:: UNIX

  .. method:: gids()

    The :field:`real`, :field:`effective` and :field:`saved` group ID of this
    process as a named tuple. This is the same as :func:`os.getresgid`, but can
    be used for any process PID.

    .. availability:: UNIX

  .. method:: terminal()

    The terminal associated with this process, if any, else ``None``. This is
    similar to ``tty`` command but can be used for any process PID.

    .. availability:: UNIX

  .. method:: nice(value=None)

    Get or set process :term:`niceness <nice>` (priority).
    On UNIX this is a number which goes from ``-20`` to ``20``.
    The higher the nice value, the lower the priority of the process.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.nice(10)  # set lower priority
       >>> p.nice()  # get
       10
       >>>

    On Windows *value* is one of the :ref:`*_PRIORITY_CLASS <const-proc-prio>`
    constants:

    .. code-block:: pycon

       >>> p.nice(psutil.HIGH_PRIORITY_CLASS)  # set higher priority
       >>> p.nice()  # get
       <ProcessPriority.HIGH_PRIORITY_CLASS: 32768>

    This method was later incorporated in Python 3.3 as
    :func:`os.getpriority` and :func:`os.setpriority` (see `BPO-10784`_).

    .. versionchanged:: 8.0.0
       on Windows, the return value is now a :class:`ProcessPriority` enum
       member. See :ref:`migration guide <migration-8.0>`.

  .. method:: ionice(ioclass=None, value=None)

    Get or set process :term:`I/O niceness <ionice>` (priority). Called with no
    arguments (get), returns a ``(ioclass, value)`` named tuple on Linux or an
    *ioclass* integer on Windows. Called with *ioclass* (one of the
    :ref:`IOPRIO_* <const-proc-ioprio>` constants), sets the I/O priority. On
    Linux, an additional *value* ranging from ``0`` to ``7`` can be specified
    to further adjust the priority level specified by *ioclass*.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> if psutil.LINUX:
       ...     p.ionice(psutil.IOPRIO_CLASS_RT, value=7)  # highest
       ... else:
       ...     p.ionice(psutil.IOPRIO_HIGH)
       ...
       >>> p.ionice()  # get
       pionice(ioclass=<ProcessIOPriority.IOPRIO_CLASS_RT: 1>, value=7)

    .. availability:: Linux, Windows

    .. versionchanged:: 5.6.2
       Windows: accept new :data:`IOPRIO_* <psutil.IOPRIO_VERYLOW>` constants.

    .. versionchanged:: 8.0.0
       *ioclass* is now a :class:`ProcessIOPriority` enum member.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: rlimit(resource, limits=None)

    Get or set process :term:`resource limits <resource limit>`.
    *resource* must be one of the :ref:`RLIMIT_* <const-proc-rlimit>` constants.
    *limits* is an optional ``(soft, hard)`` tuple. If provided, the method sets
    the limits; if omitted, it returns the current ``(soft, hard)`` tuple.
    This is the same as stdlib :func:`resource.getrlimit` and
    :func:`resource.setrlimit`, but can be used for any process PID.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.rlimit(psutil.RLIMIT_NOFILE, (128, 128))   # max 128 file descriptors
       >>> p.rlimit(psutil.RLIMIT_FSIZE, (1024, 1024))  # max file size 1024 bytes
       >>> p.rlimit(psutil.RLIMIT_FSIZE)                # get current limits of ...
       (1024, 1024)

    .. seealso:: `scripts/procinfo.py`_.

    .. availability:: Linux, FreeBSD

    .. versionchanged:: 5.7.3
       added FreeBSD support.

  .. method:: io_counters()

    Return process I/O statistics.
    All fields are :term:`cumulative counters <cumulative counter>` since
    process creation.

    - :field:`read_count`: number of read syscalls (e.g., ``read()``, ``pread()``).
    - :field:`write_count`: number of write syscalls (e.g., ``write()``, ``pwrite()``).
    - :field:`read_bytes`: bytes read (``-1`` on BSD).
    - :field:`write_bytes`: bytes written (``-1`` on BSD).

    Linux specific:

    - :field:`read_chars` *(Linux)*: bytes read via ``read()`` and
      ``pread()`` syscalls. Unlike :field:`read_bytes`, this includes tty
      I/O and counts bytes regardless of whether actual disk I/O occurred
      (e.g. reads served from :term:`page cache` are included).
    - :field:`write_chars` *(Linux)*: bytes written via ``write()`` and
      ``pwrite()`` syscalls. Same caveats as :field:`read_chars`.

    Windows specific:

    - :field:`other_count` *(Windows)*: the number of I/O operations performed
      other than read and write operations.
    - :field:`other_bytes` *(Windows)*: the number of bytes transferred during
      operations other than read and write operations.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.io_counters()
       pio(read_count=454556, write_count=3456, read_bytes=110592, write_bytes=0, read_chars=769931, write_chars=203)

    .. availability:: Linux, Windows, BSD, AIX

    .. versionchanged:: 5.2.0
       Linux: added :field:`read_chars` and :field:`write_chars` fields.

    .. versionchanged:: 5.2.0
       Windows: added :field:`other_count` and :field:`other_bytes` fields.

  .. method:: num_ctx_switches()

    The number of :term:`context switches <context switch>` performed by this
    process as a ``(voluntary, involuntary)`` named tuple
    (:term:`cumulative counter`).

    .. note::
      (Windows, macOS) :field:`involuntary` value is always set to 0, while
      :field:`voluntary` value reflects the total number of context switches
      (voluntary + involuntary). This is a limitation of the OS.

    .. versionchanged:: 5.4.1
       added AIX support.

  .. method:: num_fds()

    The number of :term:`file descriptors <file descriptor>` currently opened
    by this process (non cumulative).

    .. availability:: UNIX

  .. method:: num_handles()

    The number of :term:`handles <handle>` currently used by this process (non
    cumulative).

    .. availability:: Windows

  .. method:: num_threads()

    The number of threads currently used by this process (non cumulative).

  .. method:: threads()

    Return a list of threads spawned by this process. On OpenBSD, root privileges
    are required. Each entry includes:

    - :field:`id`: native thread ID assigned by the kernel. If :attr:`pid` refers
      to the current process, this matches :attr:`threading.Thread.native_id`,
      and can be used to reference individual Python threads in your app.
    - :field:`user_time`: time spent in user mode.
    - :field:`system_time`: time spent in kernel mode.

  .. method:: cpu_times()

    Return accumulated process CPU times as
    :term:`cumulative counters <cumulative counter>` (seconds)
    (see `explanation <http://stackoverflow.com/questions/556405/>`_).
    Same as :func:`os.times`, but works for any process PID.

    - :field:`user`: time spent in user mode.
    - :field:`system`: time spent in kernel mode.
    - :field:`children_user`: user time of all child processes (always ``0`` on
      Windows and macOS).
    - :field:`children_system`: system time of all child processes (always
      ``0`` on Windows and macOS).
    - :field:`iowait`: (Linux) time spent waiting for blocking I/O to complete.
      (:term:`iowait`). Excluded from :field:`user` and :field:`system` times
      count (because the CPU is idle).

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.cpu_times()
       pcputimes(user=0.03, system=0.67, children_user=0.0, children_system=0.0, iowait=0.08)
       >>> sum(p.cpu_times()[:2])  # cumulative, excluding children and iowait
       0.70

    .. versionchanged:: 4.1.0
       added :field:`children_user` and :field:`children_system` fields.

    .. versionchanged:: 5.6.4
       Linux: added :field:`iowait` field.

  .. method:: cpu_percent(interval=None)

    Return process CPU utilization as a percentage. Values can exceed ``100.0``
    if the process runs multiple threads on different CPUs.

    If *interval* is > ``0.0``, measures CPU times before and after the interval
    (blocking). If ``0.0`` or ``None``, returns the utilization since the last
    call or module import, returning immediately.
    That means the first time this is called it will return a meaningless ``0.0``
    value which you are supposed to ignore.
    In this case it is recommended for accuracy that this method be called with
    at least ``0.1`` seconds between calls.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> # blocking
       >>> p.cpu_percent(interval=1)
       2.0
       >>> # non-blocking (percentage since last call)
       >>> p.cpu_percent(interval=None)
       2.9

    .. note::
      the returned value is *not* split evenly between all available CPUs
      (differently from :func:`psutil.cpu_percent`). To emulate Windows
      ``taskmgr.exe`` behavior: ``p.cpu_percent() / psutil.cpu_count()``.

    .. seealso::
      - :ref:`faq_cpu_percent`
      - :ref:`faq_cpu_percent_gt_100`

  .. method:: cpu_affinity(cpus=None)

    Get or set process :term:`CPU affinity` (the set of CPUs the process is
    allowed to run on).
    If no argument is passed, return the current affinity as a list of
    integers. If passed, *cpus* must be a list of CPU integers. An empty
    list sets affinity to all eligible CPUs.

    .. code-block:: pycon

       >>> import psutil
       >>> psutil.cpu_count()
       4
       >>> p = psutil.Process()
       >>> # get
       >>> p.cpu_affinity()
       [0, 1, 2, 3]
       >>> # set; from now on, process will run on CPU #0 and #1 only
       >>> p.cpu_affinity([0, 1])
       >>> p.cpu_affinity()
       [0, 1]
       >>> # reset affinity against all eligible CPUs
       >>> p.cpu_affinity([])

    .. availability:: Linux, Windows, FreeBSD

    .. versionchanged:: 2.2.0
       added support for FreeBSD.

    .. versionchanged:: 5.1.0
       an empty list can be passed to set affinity against all eligible CPUs.

  .. method:: cpu_num()

    Return what CPU this process is currently running on.
    The returned number should be ``<=`` :func:`psutil.cpu_count`.
    On FreeBSD certain kernel process may return ``-1``.
    It may be used in conjunction with ``psutil.cpu_percent(percpu=True)`` to
    observe the system workload distributed across multiple CPUs.

    .. seealso:: `scripts/cpu_distribution.py`_.

    .. availability:: Linux, FreeBSD, SunOS

    .. versionadded:: 5.1.0

  .. method:: memory_info()

    Return memory information about the process. Fields vary by platform
    (all values in bytes). The portable fields available on all platforms
    are :field:`rss` and :field:`vms`.

    +---------+---------+----------+---------+-----+-----------------+
    | Linux   | macOS   | BSD      | Solaris | AIX | Windows         |
    +=========+=========+==========+=========+=====+=================+
    | rss     | rss     | rss      | rss     | rss | rss             |
    +---------+---------+----------+---------+-----+-----------------+
    | vms     | vms     | vms      | vms     | vms | vms             |
    +---------+---------+----------+---------+-----+-----------------+
    | shared  |         | text     |         |     |                 |
    +---------+---------+----------+---------+-----+-----------------+
    | text    |         | data     |         |     |                 |
    +---------+---------+----------+---------+-----+-----------------+
    | data    |         | stack    |         |     |                 |
    +---------+---------+----------+---------+-----+-----------------+
    |         |         | peak_rss |         |     | peak_rss        |
    +---------+---------+----------+---------+-----+-----------------+
    |         |         |          |         |     | peak_vms        |
    +---------+---------+----------+---------+-----+-----------------+

    - :field:`rss`: aka :term:`RSS`. On UNIX matches the ``top`` RES column. On
      Windows maps to ``WorkingSetSize``.

    - :field:`vms`: aka :term:`VMS`. On UNIX matches the ``top`` VIRT column. On
      Windows maps to ``PrivateUsage`` (private committed pages only), which
      differs from the UNIX definition; use :field:`virtual` from
      :meth:`memory_info_ex` for the true virtual address space size.

    - :field:`shared` *(Linux)*: :term:`shared memory` that *could* be shared
      with other processes (shared libraries, :term:`memory-mapped files <mapped memory>`).
      Counted even if no other process is currently mapping it. Matches
      ``top``'s SHR column.

    - :field:`text` *(Linux, BSD)*: aka TRS (Text Resident Set). Resident memory
      devoted to executable code. This memory is read-only and typically
      shared across all processes running the same binary. Matches ``top``'s
      CODE column.

    - :field:`data` *(Linux, BSD)*: aka DRS (Data Resident Set). On Linux this
      covers the data **and** stack segments combined (from
      ``/proc/<pid>/statm``). On BSD it covers the data segment only (see
      :field:`stack`). Matches ``top``'s DATA column.

    - :field:`stack` *(BSD)*: size of the process stack segment. Reported
      separately from :field:`data` (unlike Linux where both are combined).

    - :field:`peak_rss` *(BSD, Windows)*: see :term:`peak_rss`. On BSD may be
      ``0`` for kernel PIDs. On Windows maps to ``PeakWorkingSetSize``.

    - :field:`peak_vms` *(Windows)*: see :term:`peak_vms`. Maps to
      ``PeakPagefileUsage``.

    For the full definitions of Windows fields see
    `PROCESS_MEMORY_COUNTERS_EX`_.

    Example on Linux:

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.memory_info()
       pmem(rss=15491072, vms=84025344, shared=5206016, text=2555904, data=9891840)


    .. seealso::
      - :ref:`faq_memory_rss_vs_vms`
      - :ref:`faq_memory_footprint`

    .. versionchanged:: 4.0.0
       multiple fields are returned, not only :field:`rss` and :field:`vms`.

    .. versionchanged:: 8.0.0 (see :ref:`migration guide <migration-8.0>`)

       - *Linux*: :field:`lib` and :field:`dirty` removed (always 0 since Linux
         2.6). Deprecated aliases returning 0 and emitting :exc:`DeprecationWarning`
         are kept.
       - *macOS*: removed :field:`pfaults` and :field:`pageins` fields with no
         backward-compatible aliases. Use :meth:`page_faults` instead.
       - *Windows*: eliminated old aliases:
         :field:`wset` → :field:`rss`,
         :field:`peak_wset` → :field:`peak_rss`,
         :field:`pagefile` and :field:`private` → :field:`vms`,
         :field:`peak_pagefile` → :field:`peak_vms`,
         :field:`num_page_faults` → :meth:`page_faults` method.
         At the same time :field:`paged_pool`, :field:`nonpaged_pool`,
         :field:`peak_paged_pool`, :field:`peak_nonpaged_pool` were moved to
         :meth:`memory_info_ex`.
         All these old names still work but raise :exc:`DeprecationWarning`.
       - *BSD*: added :field:`peak_rss` field.

  .. method:: memory_info_ex()

    Extends :meth:`memory_info` with additional platform-specific memory
    metrics (all values in bytes). On platforms where extra fields are not
    implemented this returns the same result as :meth:`memory_info`.

    +-------------+----------------+--------------------+
    | Linux       | macOS          | Windows            |
    +=============+================+====================+
    | peak_rss    | peak_rss       | virtual            |
    +-------------+----------------+--------------------+
    | peak_vms    |                | peak_virtual       |
    +-------------+----------------+--------------------+
    | rss_anon    | rss_anon       | paged_pool         |
    +-------------+----------------+--------------------+
    | rss_file    | rss_file       | nonpaged_pool      |
    +-------------+----------------+--------------------+
    | rss_shmem   | wired          | peak_paged_pool    |
    +-------------+----------------+--------------------+
    | swap        | compressed     | peak_nonpaged_pool |
    +-------------+----------------+--------------------+
    | hugetlb     | phys_footprint |                    |
    +-------------+----------------+--------------------+

    - :field:`peak_rss` *(Linux, macOS)*: see :term:`peak_rss`.
    - :field:`peak_vms` *(Linux)*: see :term:`peak_vms`.
    - :field:`rss_anon` *(Linux, macOS)*: resident :term:`anonymous memory`
      (:term:`heap`, stack, private mappings) not backed by any file. Set to 0
      on Linux < 4.5.
    - :field:`rss_file` *(Linux, macOS)*: resident file-backed memory mapped
      from files (:term:`shared libraries <shared memory>`,
      :term:`memory-mapped files <mapped memory>`). Set to 0 on Linux < 4.5.
    - :field:`rss_shmem` *(Linux)*: resident :term:`shared memory` (``tmpfs``,
      ``shm_open``). ``rss_anon + rss_file + rss_shmem`` equals :field:`rss`. Set to
      0 on Linux < 4.5.
    - :field:`wired` *(macOS)*: memory pinned in RAM by the kernel on behalf of this
      process; cannot be compressed or paged out.
    - :field:`swap` *(Linux)*: process memory currently in
      :term:`swap <swap memory>`. Equivalent to ``memory_footprint().swap`` but
      cheaper, as it reads from ``/proc/<pid>/status`` instead of
      ``/proc/<pid>/smaps``.
    - :field:`compressed` *(macOS)*: memory held in the in-RAM memory compressor;
      not counted in :field:`rss`. A large value signals memory pressure but has
      not yet triggered :term:`swapping <swap memory>`.
    - :field:`hugetlb` *(Linux)*: resident memory backed by huge pages. Set to
      0 on Linux < 4.4.
    - :field:`phys_footprint` *(macOS)*: total physical memory impact including
      compressed memory. What Xcode and ``footprint(1)`` report; prefer this
      over :field:`rss` macOS memory monitoring.
    - :field:`virtual` *(Windows)*: true virtual address space size, including
      reserved-but-uncommitted regions (unlike :field:`vms` in
      :meth:`memory_info`).
    - :field:`peak_virtual` *(Windows)*: peak virtual address space size.
    - :field:`paged_pool` *(Windows)*: kernel memory used for objects created by
      this process (open file handles, registry keys, etc.) that the OS may
      swap to disk under memory pressure.
    - :field:`nonpaged_pool` *(Windows)*: kernel memory used for objects that
      must stay in RAM at all times (I/O request packets, device driver
      buffers, etc.). A large or growing value may indicate a driver memory
      leak.
    - :field:`peak_paged_pool` *(Windows)*: peak paged-pool usage.
    - :field:`peak_nonpaged_pool` *(Windows)*: peak non-paged-pool usage.

    For the full definitions of Windows fields see
    `PROCESS_MEMORY_COUNTERS_EX`_.

    .. versionadded:: 8.0.0

  .. method:: memory_footprint()

    Return :field:`uss`, :field:`pss` and :field:`swap` memory metrics. These
    give a more accurate picture of actual memory consumption than
    :meth:`memory_info` (see this `blog post
    <https://gmpy.dev/blog/2016/real-process-memory-and-environ-in-python>`_).
    It walks the full process address space, so it is slower than
    :meth:`memory_info` and may require elevated privileges.

    - :field:`uss` *(Linux, macOS, Windows)*: aka :term:`USS`; the
      :term:`private memory` of the process, which would be freed if the
      process were terminated right now.

    - :field:`pss` *(Linux)*: aka :term:`PSS`; shared memory divided evenly among
      the processes sharing it. I.e. if a process has 10 MBs all to itself, and
      10 MBs shared with another process, its PSS will be 15 MBs.

    - :field:`swap` *(Linux)*: process memory currently in :term:`swap <swap memory>`,
      counted per-mapping.

    Example on Linux:

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.memory_footprint()
       pfootprint(uss=6545408, pss=6872064, swap=0)

    .. seealso::
      - `scripts/procsmem.py`_.
      - :ref:`faq_memory_footprint`

    .. availability:: Linux, macOS, Windows

    .. versionadded:: 8.0.0

  .. method:: memory_full_info()

    This deprecated method returns the same information as :meth:`memory_info`
    plus :meth:`memory_footprint` in a single named tuple.

    .. versionadded:: 4.0.0

    .. deprecated:: 8.0.0
       use :meth:`memory_footprint` instead.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: memory_percent(memtype="rss")

    Return process memory usage as a percentage of total physical memory. Same
    as:

    .. code-block:: python

       Process().memory_info().rss / virtual_memory().total * 100

    *memtype* selects which memory field to use and can be any attribute
    from :meth:`memory_info`, :meth:`memory_info_ex`, or :meth:`memory_footprint`
    (default is ``"rss"``).

    .. versionchanged:: 4.0.0
       added *memtype* parameter.

  .. method:: memory_maps(grouped=True)

    Return the process's :term:`memory-mapped <mapped memory>` file regions as
    a list. Fields vary by platform (all values in bytes).

    If *grouped* is ``True``, regions with the same *path* are merged and their
    numeric fields summed. If *grouped* is ``False``, each region is listed
    individually; the tuple also includes *addr* (address range) and *perms*
    (permission string, e.g., ``"r-xp"``).

    +---------------+---------+--------------+-----------+
    | Linux         | Windows | FreeBSD      | Solaris   |
    +===============+=========+==============+===========+
    | rss           | rss     | rss          | rss       |
    +---------------+---------+--------------+-----------+
    | size          |         | private      | anonymous |
    +---------------+---------+--------------+-----------+
    | pss           |         | ref_count    | locked    |
    +---------------+---------+--------------+-----------+
    | shared_clean  |         | shadow_count |           |
    +---------------+---------+--------------+-----------+
    | shared_dirty  |         |              |           |
    +---------------+---------+--------------+-----------+
    | private_clean |         |              |           |
    +---------------+---------+--------------+-----------+
    | private_dirty |         |              |           |
    +---------------+---------+--------------+-----------+
    | referenced    |         |              |           |
    +---------------+---------+--------------+-----------+
    | anonymous     |         |              |           |
    +---------------+---------+--------------+-----------+
    | swap          |         |              |           |
    +---------------+---------+--------------+-----------+

    Linux fields (from ``/proc/<pid>/smaps``):

    - :field:`rss`: :term:`RSS` for this mapping.
    - :field:`size`: total virtual size; may far exceed :field:`rss` if parts
      have never been accessed.
    - :field:`pss`: :term:`PSS` for this mapping, that is :field:`rss` split
      proportionally among all processes sharing it.
    - :field:`shared_clean`: :term:`shared memory` not written to since loaded
      (clean); can be discarded and reloaded from disk for free.
    - :field:`shared_dirty`: :term:`shared memory` that has been written to (dirty).
    - :field:`private_clean`: :term:`private memory` not written to (clean).
    - :field:`private_dirty`: :term:`private memory` that has been written to
      (dirty); must be saved to swap before it can be freed. The key
      indicator of real memory cost.
    - :field:`referenced`: bytes recently accessed.
    - :field:`anonymous`: :term:`anonymous memory` in this mapping (:term:`heap`,
      stack).
    - :field:`swap`: bytes from this mapping currently in
      :term:`swap <swap memory>`.

    FreeBSD fields:

    - :field:`private`: :term:`private memory` in this mapping.
    - :field:`ref_count`: reference count on the underlying memory object.
    - :field:`shadow_count`: depth of the copy-on-write chain.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.memory_maps()
       [pmmap_grouped(path='/lib/x8664-linux-gnu/libutil-2.15.so', rss=32768, size=2125824, pss=32768, shared_clean=0, shared_dirty=0, private_clean=20480, private_dirty=12288, referenced=32768, anonymous=12288, swap=0),
        pmmap_grouped(path='/lib/x8664-linux-gnu/libc-2.15.so', rss=3821568, size=3842048, pss=3821568, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=3821568, referenced=3575808, anonymous=3821568, swap=0),
        ...]

    .. seealso:: `scripts/pmap.py`_.

    .. availability:: Linux, Windows, FreeBSD, SunOS

    .. versionchanged:: 5.6.0
       removed macOS support because inherently broken (see issue :gh:`1291`)

  .. method:: children(recursive=False)

    Return the children of this process as a list of :class:`Process`
    instances. If *recursive* is ``True``, return all descendants.
    Pseudo-code example (assuming A is this process):

    .. code-block:: none

      A ─┐
         │
         ├─ B (child) ─┐
         │             └─ X (grandchild) ─┐
         │                                └─ Y (great-grandchild)
         ├─ C (child)
         └─ D (child)

    .. code-block:: pycon

       >>> p.children()
       B, C, D
       >>> p.children(recursive=True)
       B, X, Y, C, D

    Note: if a process in the tree disappears (e.g., X), its descendants
    (Y) won’t be returned since the reference to the parent is lost.
    This concept is well illustrated by this
    `unit test <https://github.com/giampaolo/psutil/blob/65a52341b55faaab41f68ebc4ed31f18f0929754/psutil/tests/test_process.py#L1064-L1075>`_.

    .. seealso:: how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

  .. method:: page_faults()

    Return the number of :term:`page faults <page fault>` for this process
    as a ``(minor, major)`` named tuple. Both are
    :term:`cumulative counters <cumulative counter>` since process creation.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.page_faults()
       ppagefaults(minor=5905, major=3)

    .. versionadded:: 8.0.0

  .. method:: open_files()

    Return regular files opened by process as a list. Each entry includes:

    - :field:`path`: the absolute file name.
    - :field:`fd`: the :term:`file descriptor` number; on Windows this is always
      ``-1``.

    Linux only:

    - :field:`position` (*Linux*): the file position (offset).
    - :field:`mode` (*Linux*): a string indicating how the file was opened,
      similarly to :func:`open` builtin *mode* argument.
      Possible values are ``'r'``, ``'w'``, ``'a'``, ``'r+'`` and ``'a+'``.
      There's no distinction between files opened in binary or text mode
      (``"b"`` or ``"t"``).
    - :field:`flags` (*Linux*): the flags which were passed to the underlying
      :func:`os.open` C call when the file was opened (e.g. :data:`os.O_RDONLY`,
      :data:`os.O_TRUNC`, etc).

    .. code-block:: pycon

       >>> import psutil
       >>> f = open('file.ext', 'w')
       >>> p = psutil.Process()
       >>> p.open_files()
       [popenfile(path='/home/giampaolo/svn/psutil/file.ext', fd=3, position=0, mode='w', flags=32769)]

    .. warning::
      - Windows: this is not guaranteed to enumerate all file handles (see
        :ref:`faq_open_files_windows`)
      - BSD: can return empty-string paths due to a kernel bug (see
        `issue 595 <https://github.com/giampaolo/psutil/pull/595>`_)

    .. versionchanged:: 3.1.0
       no longer hangs on Windows.

    .. versionchanged:: 4.1.0
       Linux: added :field:`position`, :field:`mode` and :field:`flags` fields.

  .. method:: net_connections(kind="inet")

    Same as :func:`psutil.net_connections` but for this process only (the
    returned named tuples have no :field:`pid` field). The *kind* parameter and
    the same limitations apply (root may be needed on some platforms).

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process(1694)
       >>> p.name()
       'firefox'
       >>> p.net_connections()
       [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>),
        pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=43761), raddr=addr(ip='72.14.234.100', port=80), status=<ConnectionStatus.CONN_CLOSING: 'CLOSING'>),
        pconn(fd=119, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=60759), raddr=addr(ip='72.14.234.104', port=80), status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>),
        pconn(fd=123, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=51314), raddr=addr(ip='72.14.234.83', port=443), status=<ConnectionStatus.CONN_SYN_SENT: 'SYN_SENT'>)]

  .. method:: connections()

    Same as :meth:`net_connections` (deprecated).

    .. deprecated:: 6.0.0
       use :meth:`net_connections` instead.

  .. method:: is_running()

    Return whether the current process is running.
    Differently from ``psutil.pid_exists(p.pid)``, this is reliable also in
    case the process is gone and its PID reused by another process.

    If PID has been reused, this method will also remove the process from
    :func:`process_iter` internal cache.

    This will return ``True`` also if the process is a :term:`zombie process`
    (``p.status() == psutil.STATUS_ZOMBIE``).

    .. seealso::
      - :ref:`faq_pid_reuse`
      - :ref:`faq_pid_exists_vs_isrunning`

    .. versionchanged:: 6.0.0
       automatically remove process from :func:`process_iter` internal cache
       if PID has been reused by another process.

  .. method:: send_signal(sig)

    Send signal *sig* to process (see :mod:`signal` module constants),
    preemptively checking whether PID has been reused. On UNIX this is the same
    as ``os.kill(pid, sig)``. On Windows only ``SIGTERM``, ``CTRL_C_EVENT`` and
    ``CTRL_BREAK_EVENT`` signals are supported, and ``SIGTERM`` is treated as
    an alias for :meth:`kill`.

    .. seealso:: how to :ref:`kill a process tree <recipe_kill_proc_tree>`

    .. versionchanged:: 3.2.0
       Windows: add support for CTRL_C_EVENT and CTRL_BREAK_EVENT signals.

  .. method:: suspend()

    Suspend process execution with ``SIGSTOP`` signal, preemptively
    checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGSTOP)``.
    On Windows this is done by suspending all process threads.

  .. method:: resume()

    Resume process execution with ``SIGCONT`` signal, preemptively
    checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGCONT)``.
    On Windows this is done by resuming all process threads.

  .. method:: terminate()

    Terminate the process with ``SIGTERM`` signal, preemptively checking
    whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGTERM)``.
    On Windows this is an alias for :meth:`kill`.

    .. seealso:: how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

  .. method:: kill()

    Kill the current process by using ``SIGKILL`` signal, preemptively
    checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGKILL)``.
    On Windows this is done by using `TerminateProcess`_.

    .. seealso:: how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

  .. method:: wait(timeout=None)

    Wait for a process PID to terminate. The details about the return value
    differ on UNIX and Windows.

    *On UNIX*: if the process terminated normally, the return value is an
    integer >= 0 indicating the exit code. If the process was terminated by a
    signal, returns the negated value of the signal which caused the
    termination (e.g. ``-SIGTERM``). If PID is not a child of :func:`os.getpid`
    (current process), it just waits until the process disappears and return
    ``None``. If PID does not exist return ``None`` immediately.

    *On Windows*: always return the exit code via `GetExitCodeProcess`_.

    *timeout* is expressed in seconds. If specified, and the process is still
    alive, raise :exc:`TimeoutExpired`.
    ``timeout=0`` can be used in non-blocking apps: it will either return
    immediately or raise :exc:`TimeoutExpired`.

    The return value is cached.
    To wait for multiple processes use :func:`psutil.wait_procs`.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process(9891)
       >>> p.terminate()
       >>> p.wait()
       <NegSignal.SIGTERM: -15>

    .. note::

      when *timeout* is not ``None`` and the platform supports it, an
      efficient event-driven mechanism is used to wait for process termination:

      - Linux >= 5.3 with Python >= 3.9 uses :func:`os.pidfd_open` + :func:`select.poll`
      - macOS and other BSD variants use :func:`select.kqueue` + ``KQ_FILTER_PROC``
        + ``KQ_NOTE_EXIT``
      - Windows uses `WaitForSingleObject`_

      If none of these mechanisms are available, the function falls back to a
      busy loop (non-blocking call and short sleeps).

      Functionality also ported to the :mod:`subprocess` module in Python 3.15,
      see `GH-144047`_.

    .. versionchanged:: 5.7.2
       if *timeout* is not ``None``, use efficient event-driven implementation
       on Linux >= 5.3 and macOS / BSD.

    .. versionchanged:: 5.7.1
       return value is cached (instead of returning ``None``).

    .. versionchanged:: 5.7.1
       POSIX: if the signal is negative, return it as a human readable
       :mod:`enum`.

    .. versionchanged:: 7.2.2
       on Linux >= 5.3 + Python >= 3.9 and macOS/BSD, use :func:`os.pidfd_open` and
       :func:`select.kqueue` respectively, instead of less efficient busy-loop
       polling.

-------------------------------------------------------------------------------

Popen class
^^^^^^^^^^^

.. class:: Popen(*args, **kwargs)

  Same as :class:`subprocess.Popen`, but in addition it provides all
  :class:`psutil.Process` methods in a single class.
  For the following methods, which are common to both classes, psutil
  implementation takes precedence:
  :meth:`send_signal() <psutil.Process.send_signal()>`,
  :meth:`terminate() <psutil.Process.terminate()>`,
  :meth:`kill() <psutil.Process.kill()>`.
  This is done to avoid killing another process if its PID has been reused,
  fixing `BPO-6973`_.

  .. code-block:: pycon

     >>> import psutil
     >>> from subprocess import PIPE
     >>>
     >>> p = psutil.Popen(["/usr/bin/python3", "-c", "print('hello')"], stdout=PIPE)
     >>> p.name()
     'python3'
     >>> p.username()
     'giampaolo'
     >>> p.communicate()
     ('hello\n', None)
     >>> p.wait(timeout=2)
     0
     >>>

  .. versionchanged:: 4.4.0
     added context manager support.

-------------------------------------------------------------------------------

C heap introspection
--------------------

The following functions provide direct access to the platform's native
:term:`heap` allocator (such as glibc's ``malloc`` on Linux or ``jemalloc``
on BSD). They are low-level interfaces intended for detecting memory leaks in C
extensions, which are usually not revealed via standard :term:`RSS` / :term:`VMS`
metrics.
These functions do not reflect Python object memory; they operate solely on
allocations made in C via ``malloc()``, ``free()``, and related calls.

The general idea behind these functions is straightforward: capture the state
of the :term:`heap` before and after repeatedly invoking a function
implemented in a
C extension, and compare the results. If ``heap_used`` or ``mmap_used`` grows
steadily across iterations, the C code is likely retaining memory it should be
releasing. This provides an allocator-level way to spot native leaks that
Python's memory tracking misses.

.. tip::

  Check out `psleak`_ project to see a practical example of how these APIs can be
  used to detect memory leaks in C extensions.

.. function:: heap_info()

  Return low-level heap statistics from the system's C allocator. On Linux,
  this exposes ``uordblks`` and ``hblkhd`` fields from glibc `mallinfo2`_.

  - ``heap_used``: total number of bytes currently allocated via ``malloc()``
    (small allocations).
  - ``mmap_used``: total number of bytes currently allocated via ``mmap()`` or
    via large ``malloc()`` allocations. Always set to 0 on macOS.
  - ``heap_count``: (Windows only) number of private heaps created via
    ``HeapCreate()``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.heap_info()
     pheap(heap_used=5177792, mmap_used=819200)

  These fields reflect how unreleased C allocations affect the heap:

  +---------------+------------------------------------------------------------------------------------+-----------------+
  | Platform      | Allocation type                                                                    | Affected field  |
  +===============+====================================================================================+=================+
  | UNIX / glibc  | small ``malloc()`` ≤128KB without ``free()``                                       | ``heap_used``   |
  +---------------+------------------------------------------------------------------------------------+-----------------+
  | UNIX / glibc  | large ``malloc()`` >128KB without ``free()`` , or ``mmap()`` without ``munmap()``  | ``mmap_used``   |
  +---------------+------------------------------------------------------------------------------------+-----------------+
  | Windows       | ``HeapAlloc()`` without ``HeapFree()``                                             | ``heap_used``   |
  +---------------+------------------------------------------------------------------------------------+-----------------+
  | Windows       | ``VirtualAlloc()`` without ``VirtualFree()``                                       | ``mmap_used``   |
  +---------------+------------------------------------------------------------------------------------+-----------------+
  | Windows       | ``HeapCreate()`` without ``HeapDestroy()``                                         | ``heap_count``  |
  +---------------+------------------------------------------------------------------------------------+-----------------+

  .. availability:: Linux with glibc, Windows, macOS, FreeBSD, NetBSD

  .. versionadded:: 7.2.0

.. function:: heap_trim()

  Request that the underlying allocator free any unused memory it's holding in
  the :term:`heap` (typically small ``malloc()`` allocations).

  In practice, modern allocators rarely comply, so this is not a
  general-purpose memory-reduction tool and won't meaningfully shrink :term:`RSS`
  in real programs. Its primary value is in **leak detection tools**.

  Calling ``heap_trim()`` before taking measurements helps reduce allocator
  noise, giving you a cleaner baseline so that changes in ``heap_used`` come
  from the code you're testing, not from internal allocator caching or
  fragmentation. Its effectiveness depends on allocator behavior and
  fragmentation patterns.

  .. availability:: Linux with glibc, Windows, macOS, FreeBSD, NetBSD

  .. versionadded:: 7.2.0

-------------------------------------------------------------------------------

Windows services
----------------

.. function:: win_service_iter()

  Return an iterator yielding :class:`WindowsService` instances for all
  installed Windows services.

  .. versionadded:: 4.2.0

  .. availability:: Windows

.. function:: win_service_get(name)

  Get a Windows service by name, returning a :class:`WindowsService` instance.
  Raise :exc:`NoSuchProcess` if no service with such name exists.

  .. versionadded:: 4.2.0

  .. availability:: Windows

.. class:: WindowsService

  Represents a Windows service with the given *name*. This class is returned
  by :func:`win_service_iter` and :func:`win_service_get` functions, and it's
  not supposed to be instantiated directly.

  .. method:: name()

    The service name. This string is how a service is referenced, and can be
    passed to :func:`win_service_get` to get a new :class:`WindowsService`
    instance.

  .. method:: display_name()

    The service display name. The value is cached when this class is
    instantiated.

  .. method:: binpath()

    The fully qualified path to the service binary/exe file as a string,
    including command line arguments.

  .. method:: username()

    The name of the user that owns this service.

  .. method:: start_type()

    A string which can either be either ``'automatic'``, ``'manual'`` or
    ``'disabled'``.

  .. method:: pid()

    The process PID, if any, else ``None``. This can be passed to
    :class:`Process` class to control the service's process.

  .. method:: status()

    Service status as a string, which can be either ``'running'``,
    ``'paused'``, ``'start_pending'``, ``'pause_pending'``,
    ``'continue_pending'``, ``'stop_pending'`` or ``'stopped'``.

  .. method:: description()

    Service long description.

  .. method:: as_dict()

    Utility method retrieving all the information above as a dictionary.

  .. code-block:: pycon

     >>> import psutil
     >>> list(psutil.win_service_iter())
     [<WindowsService(name='AeLookupSvc', display_name='Application Experience') at 38850096>,
      <WindowsService(name='ALG', display_name='Application Layer Gateway Service') at 38850128>,
      <WindowsService(name='APNMCP', display_name='Ask Update Service') at 38850160>,
      <WindowsService(name='AppIDSvc', display_name='Application Identity') at 38850192>,
      ...]
     >>> s = psutil.win_service_get('alg')
     >>> s.as_dict()
     {'binpath': 'C:\\Windows\\System32\\alg.exe',
      'description': 'Provides support for 3rd party protocol plug-ins for Internet Connection Sharing',
      'display_name': 'Application Layer Gateway Service',
      'name': 'alg',
      'pid': None,
      'start_type': 'manual',
      'status': 'stopped',
      'username': 'NT AUTHORITY\\LocalService'}

  .. availability:: Windows

  .. versionadded:: 4.2.0

-------------------------------------------------------------------------------

Constants
---------

The following enum classes group related constants, and are useful for type
annotations and introspection. The individual constants (e.g.
:data:`STATUS_RUNNING`) are also accessible directly from the psutil
namespace as aliases for the enum members, and should be preferred over
accessing them via the enum class (e.g. prefer ``psutil.STATUS_RUNNING`` over
``psutil.ProcessStatus.STATUS_RUNNING``).

.. class:: ProcessStatus

  :class:`enum.StrEnum` collection of :data:`STATUS_* <psutil.STATUS_RUNNING>`
  constants. Returned by :meth:`Process.status`.

  .. versionadded:: 8.0.0

.. class:: ProcessPriority

  :class:`enum.IntEnum` collection of
  :data:`*_PRIORITY_CLASS <psutil.ABOVE_NORMAL_PRIORITY_CLASS>` constants for
  :meth:`Process.nice` on Windows.

  .. availability:: Windows

  .. versionadded:: 8.0.0

.. class:: ProcessIOPriority

  :class:`enum.IntEnum` collection of I/O priority constants for
  :meth:`Process.ionice`.

  :data:`IOPRIO_CLASS_* <psutil.IOPRIO_CLASS_NONE>` on Linux,
  :data:`IOPRIO_* <psutil.IOPRIO_VERYLOW>` on Windows.

  .. availability:: Linux, Windows

  .. versionadded:: 8.0.0

.. class:: ProcessRlimit

  :class:`enum.IntEnum` collection of :data:`RLIMIT_* <psutil.RLIMIT_NOFILE>`
  constants for :meth:`Process.rlimit`.

  .. availability:: Linux, FreeBSD

  .. versionadded:: 8.0.0

.. class:: ConnectionStatus

  :class:`enum.StrEnum` collection of :data:`CONN_* <psutil.CONN_ESTABLISHED>`
  constants. Returned in the :field:`status` field of
  :func:`psutil.net_connections` and :meth:`Process.net_connections`.

  .. versionadded:: 8.0.0

.. class:: NicDuplex

  :class:`enum.IntEnum` collection of :data:`NIC_DUPLEX_* <psutil.NIC_DUPLEX_FULL>`
  constants. Returned in the *duplex* field of :func:`psutil.net_if_stats`.

  .. versionadded:: 3.0.0

.. class:: BatteryTime

  :class:`enum.IntEnum` collection of :data:`POWER_TIME_* <psutil.POWER_TIME_UNKNOWN>`
  constants. May appear in the *secsleft* field of :func:`psutil.sensors_battery`.

  .. versionadded:: 5.1.0

.. _const-oses:

Operating system constants
^^^^^^^^^^^^^^^^^^^^^^^^^^

``bool`` constants which define what platform you're on.
``True`` if on the platform, ``False`` otherwise.

.. data:: POSIX
.. data:: LINUX
.. data:: WINDOWS
.. data:: MACOS
.. data:: FREEBSD
.. data:: NETBSD
.. data:: OPENBSD
.. data:: BSD
.. data:: SUNOS
.. data:: AIX
.. data:: OSX

  Alias for :data:`MACOS`.

  .. deprecated:: 5.4.7
     use :data:`MACOS` instead.

.. _const-pstatus:

Process status constants
^^^^^^^^^^^^^^^^^^^^^^^^

Represent the current status of a process. Returned by :meth:`Process.status`.

.. versionchanged:: 8.0.0
   constants are now :class:`ProcessStatus` enum members (were plain strings).
   See :ref:`migration guide <migration-8.0>`.

.. data:: STATUS_RUNNING

   The process is running or ready to run (e.g. ``while True: pass``).

.. data:: STATUS_SLEEPING

   The process is dormant (e.g. during ``time.sleep()``) but can be woken up,
   e.g. via a signal.

.. data:: STATUS_DISK_SLEEP

   The process is waiting for disk I/O to complete. The kernel usually ignores
   signals in this state to prevent data corruption. E.g. ``os.read(fd, 1024)``
   on a slow / blocked device can produce this state.

.. data:: STATUS_STOPPED

   The process is stopped (e.g., by ``SIGSTOP`` or ``SIGTSTP``, which is sent
   on Ctrl+Z) and will not run until resumed (e.g., via ``SIGCONT``).

.. data:: STATUS_TRACING_STOP

   The process is temporarily halted because it is being inspected by a
   debugger (e.g. via ``strace -p <pid>``).

.. data:: STATUS_ZOMBIE

   The process has finished execution and released its resources, but it
   remains in the process table until the parent reaps it via ``wait()``.
   See also :ref:`faq_zombie_process`.

.. data:: STATUS_DEAD

   The process is about to disappear (final state before it is gone).

.. data:: STATUS_WAKE_KILL

   (Linux only) A variant of :data:`STATUS_DISK_SLEEP` where the process can be
   awakened by ``SIGKILL``. Used for tasks which might otherwise remain blocked
   indefinitely, e.g. unresponsive network filesystems such as NFS, as in
   ``open("/mnt/nfs_hung/file").read()``.

.. data:: STATUS_WAKING

   (Linux only) A transient state right before the process becomes runnable
   (:data:`STATUS_RUNNING`).

.. data:: STATUS_PARKED

   (Linux only) A dormant state for kernel threads tied to a specific CPU.
   These threads are "parked" when a CPU core is taken offline and will
   remain inactive until the core is re-enabled.

   .. versionadded:: 5.4.7

.. data:: STATUS_IDLE

   (Linux, macOS, FreeBSD) A sleep for kernel threads waiting for work.

   .. versionadded:: 3.4.1

.. data:: STATUS_LOCKED

   (FreeBSD only) The process is blocked specifically waiting for a
   kernel-level synchronization primitive (e.g. a mutex).

   .. versionadded:: 3.4.1

.. data:: STATUS_WAITING

   (FreeBSD only) The process is waiting in a kernel sleep queue for a
   specific system event to occur.

   .. versionadded:: 3.4.1

.. data:: STATUS_SUSPENDED

   (NetBSD only) The process has been explicitly paused, similar to
   the stopped state but managed by the NetBSD scheduler.

   .. versionadded:: 3.4.1

.. _const-proc-prio:

Process priority constants
^^^^^^^^^^^^^^^^^^^^^^^^^^

Represent the priority of a process on Windows (see `SetPriorityClass`_ doc).
They can be used in conjunction with :meth:`Process.nice` to get or
set process priority.

.. availability:: Windows

.. versionchanged:: 8.0.0
   constants are now :class:`ProcessPriority` enum members (were plain
   integers).
   See :ref:`migration guide <migration-8.0>`.

.. _const-prio:

.. data:: REALTIME_PRIORITY_CLASS
.. data:: HIGH_PRIORITY_CLASS
.. data:: ABOVE_NORMAL_PRIORITY_CLASS
.. data:: NORMAL_PRIORITY_CLASS
.. data:: IDLE_PRIORITY_CLASS
.. data:: BELOW_NORMAL_PRIORITY_CLASS

-------------------------------------------------------------------------------

.. _const-proc-ioprio:

Process I/O priority constants
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Represent the I/O priority class of a process (Linux and Windows only).
They can be used in conjunction with :meth:`Process.ionice` (*ioclass* argument).

Linux (see `ioprio_get()`_ manual):

  .. data:: IOPRIO_CLASS_RT

     Highest priority.

  .. data:: IOPRIO_CLASS_BE

     Normal priority.

  .. data:: IOPRIO_CLASS_IDLE

     Lowest priority.

  .. data:: IOPRIO_CLASS_NONE

     No priority set (default; treated as :data:`IOPRIO_CLASS_BE`).

Windows:

  .. data:: IOPRIO_VERYLOW
  .. data:: IOPRIO_LOW
  .. data:: IOPRIO_NORMAL
  .. data:: IOPRIO_HIGH

.. versionadded:: 5.6.2

.. versionchanged:: 8.0.0
   constants are now :class:`ProcessIOPriority` enum members.
   See :ref:`migration guide <migration-8.0>`.

.. _const-proc-rlimit:

Process resource constants
^^^^^^^^^^^^^^^^^^^^^^^^^^

Constants for getting or setting process resource limits, to be used in in
conjunction with :meth:`Process.rlimit`. The meaning of each constant is
explained in :func:`resource.getrlimit` documentation.

.. availability:: Linux, FreeBSD

.. versionchanged:: 8.0.0
   these constants are now :class:`ProcessRlimit` enum members (were plain
   integers). See :ref:`migration guide <migration-8.0>`.

Linux / FreeBSD:

  .. data:: RLIM_INFINITY
  .. data:: RLIMIT_AS
  .. data:: RLIMIT_CORE
  .. data:: RLIMIT_CPU
  .. data:: RLIMIT_DATA
  .. data:: RLIMIT_FSIZE
  .. data:: RLIMIT_MEMLOCK
  .. data:: RLIMIT_NOFILE
  .. data:: RLIMIT_NPROC
  .. data:: RLIMIT_RSS
  .. data:: RLIMIT_STACK

Linux specific:

  .. data:: RLIMIT_LOCKS
  .. data:: RLIMIT_MSGQUEUE
  .. data:: RLIMIT_NICE
  .. data:: RLIMIT_RTPRIO
  .. data:: RLIMIT_RTTIME
  .. data:: RLIMIT_SIGPENDING

FreeBSD specific:

  .. data:: RLIMIT_SWAP

    .. versionadded:: 5.7.3


  .. data:: RLIMIT_SBSIZE

    .. versionadded:: 5.7.3

  .. data:: RLIMIT_NPTS

    .. versionadded:: 5.7.3

.. _const-conn:

Connections constants
^^^^^^^^^^^^^^^^^^^^^

:class:`enum.StrEnum` constants representing the status of a TCP connection.
Returned by :meth:`Process.net_connections` and :func:`psutil.net_connections`
(:field:`status` field).

.. versionchanged:: 8.0.0
   constants are now :class:`ConnectionStatus` enum members (were plain strings).
   See :ref:`migration guide <migration-8.0>`.

.. data:: CONN_ESTABLISHED
.. data:: CONN_SYN_SENT
.. data:: CONN_SYN_RECV
.. data:: CONN_FIN_WAIT1
.. data:: CONN_FIN_WAIT2
.. data:: CONN_TIME_WAIT
.. data:: CONN_CLOSE
.. data:: CONN_CLOSE_WAIT
.. data:: CONN_LAST_ACK
.. data:: CONN_LISTEN
.. data:: CONN_CLOSING
.. data:: CONN_NONE
.. data:: CONN_DELETE_TCB (Windows)
.. data:: CONN_IDLE (Solaris)
.. data:: CONN_BOUND (Solaris)

Hardware constants
^^^^^^^^^^^^^^^^^^

.. _const-aflink:

.. data:: AF_LINK

  Identifies a MAC address associated with a network interface. Returned by
  :func:`psutil.net_if_addrs` (:field:`family` field).

  .. versionadded:: 3.0.0

.. _const-duplex:

.. data:: NIC_DUPLEX_FULL
.. data:: NIC_DUPLEX_HALF
.. data:: NIC_DUPLEX_UNKNOWN

  Identifies whether a :term:`NIC` operates in full, half, or unknown duplex
  mode.
  FULL allows simultaneous send/receive, HALF allows only one at a time.
  Returned by :func:`psutil.net_if_stats` (:field:`duplex` field).

  .. versionadded:: 3.0.0

.. _const-power:

.. data:: POWER_TIME_UNKNOWN
.. data:: POWER_TIME_UNLIMITED

  Whether the remaining time of a battery cannot be determined or is unlimited.
  May be assigned to :func:`psutil.sensors_battery`'s :field:`secsleft` field.

  .. versionadded:: 5.1.0

Other constants
^^^^^^^^^^^^^^^

.. _const-procfs_path:

.. data:: PROCFS_PATH

  The path of the ``/proc`` filesystem on Linux, Solaris and AIX (defaults to
  ``'/proc'``).
  You may want to re-set this constant right after importing psutil in case
  ``/proc`` is mounted elsewhere, or if you want to retrieve
  information about Linux containers such as Docker, Heroku or LXC (see
  `here <https://fabiokung.com/2014/03/13/memory-inside-linux-containers/>`_
  for more info).

  It must be noted that this trick works only for APIs which rely on ``/proc``
  filesystem (e.g. memory-related APIs and many (but not all)
  :class:`Process` class methods).

  .. availability:: Linux, SunOS, AIX

  .. versionadded:: 3.2.3

  .. versionchanged:: 3.4.2
     also available on Solaris.

  .. versionchanged:: 5.4.0
     also available on AIX.

.. _const-version-info:

.. data:: version_info

  A tuple to check psutil installed version.

  .. code-block:: pycon

     >>> import psutil
     >>> if psutil.version_info >= (4, 5):
     ...    pass

Environment variables
---------------------

.. envvar:: PSUTIL_DEBUG

  If set, psutil will print debug messages to stderr. This is useful for
  troubleshooting internal errors or understanding the library's behavior at
  a lower level. The variable is checked at import time, and affects both the
  Python layer and the underlying C extension modules. It can also be toggled
  programmatically at runtime via ``psutil._set_debug(True)``.

  .. code-block:: bash

     $ PSUTIL_DEBUG=1 python3 script.py

  .. versionadded:: 5.4.2

.. _`ioprio_get()`: https://linux.die.net/man/2/ioprio_get
.. _`iostats doc`: https://www.kernel.org/doc/Documentation/iostats.txt
.. _`mallinfo2`: https://man7.org/linux/man-pages/man3/mallinfo.3.html
.. _`psleak`: https://github.com/giampaolo/psleak
.. _`/proc/meminfo`: https://man7.org/linux/man-pages/man5/proc_meminfo.5.html

.. === Windows API

.. _`GetExitCodeProcess`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess
.. _`GetPerformanceInfo`: https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getperformanceinfo
.. _`PROCESS_MEMORY_COUNTERS_EX`: https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex
.. _`SetPriorityClass`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setpriorityclass
.. _`TerminateProcess`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess
.. _`WaitForSingleObject`: https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
