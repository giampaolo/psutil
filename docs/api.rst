.. currentmodule:: psutil
.. include:: _links.rst
.. _availability:

API reference
=============

.. note::
   psutil 8.0 introduces breaking API changes. See the
   :ref:`migration guide <migration-8.0>` if upgrading from 7.x.

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

  - **user**: time spent by normal processes executing in user mode; on Linux
    this also includes **guest** time

  - **system**: time spent by processes executing in kernel mode

  - **idle**: time spent doing nothing

  Platform-specific fields:

  - **nice** *(Linux, macOS, BSD)*: time spent by :term:`niced <nice>`
    (lower-priority) processes executing in user mode; on Linux this also
    includes **guest_nice** time.

  - **iowait** *(Linux, SunOS, AIX)*: time spent waiting for I/O to complete
    (:term:`iowait`). This is *not* accounted in **idle** time counter.

  - **irq** *(Linux, Windows, BSD)*: time spent for servicing
    :term:`hardware interrupts <hardware interrupt>`

  - **softirq** *(Linux)*: time spent for servicing
    :term:`soft interrupts <soft interrupt>`

  - **steal** *(Linux)*: CPU time the virtual machine wanted to run but was
    used by other virtual machines or the host. A sustained non-zero steal rate
    indicates CPU contention.

  - **guest** *(Linux)*: time the host CPU spent running a guest operating
    system (virtual machine). Already included in **user** time.

  - **guest_nice** *(Linux)*: like **guest**, but for virtual CPUs running at a
    lower :term:`nice` priority. Already included in **nice** time.

  - **dpc** *(Windows)*: time spent servicing deferred procedure calls (DPCs);
    DPCs are interrupts that run at a lower priority than standard interrupts.

  When *percpu* is ``True`` return a list of named tuples for each logical CPU
  on the system.
  The list is ordered by CPU index.
  The order of the list is consistent across calls.
  Example output on Linux:

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.cpu_times()
     scputimes(user=17411.7, system=3797.02, idle=51266.57, nice=77.99, iowait=732.58, irq=0.01, softirq=142.43, steal=0.0, guest=0.0, guest_nice=0.0)

  .. note::
    CPU times are always supposed to increase over time, or at least remain the
    same, and that's because time cannot go backwards. Surprisingly sometimes
    this might not be the case (at least on Windows and Linux), see `#1210
    <https://github.com/giampaolo/psutil/issues/1210#issuecomment-363046156>`_.

  .. versionchanged:: 4.1.0
     added *irq* and *dpc* fields on Windows (*irq* was called *interrupt*
     before 8.0.0).

  .. versionchanged:: 8.0.0
     *interrupt* field on Windows was renamed to *irq*; *interrupt* still
     works but raises :exc:`DeprecationWarning`.

  .. versionchanged:: 8.0.0
     ``cpu_times()`` field order was standardized: ``user``, ``system``,
     ``idle`` are now always the first three fields. Previously on Linux,
     macOS, and BSD the first three were ``user``, ``nice``, ``system``.
     See :ref:`migration guide <migration-8.0>`.

.. function:: cpu_percent(interval=None, percpu=False)

  Return a float representing the current system-wide CPU utilization as a
  percentage. When *interval* is > ``0.0`` compares system CPU times elapsed
  before and after the interval (blocking).
  When *interval* is ``0.0`` or ``None`` compares system CPU times elapsed
  since last call or module import, returning immediately.
  That means the first time this is called it will return a meaningless ``0.0``
  value which you are supposed to ignore.
  In this case it is recommended for accuracy that this function be called with
  at least ``0.1`` seconds between calls.
  When *percpu* is ``True`` returns a list of floats representing the
  utilization as a percentage for each CPU.
  The list is ordered by CPU index. The order of the list is consistent across
  calls.
  Internally this function maintains a global map (a dict) where each key is
  the ID of the calling thread (:func:`threading.get_ident`). This means it can be
  called from different threads, at different intervals, and still return
  meaningful and independent results.

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
     [2.0, 1.0]
     >>>

  .. note::
    the first time this function is called with *interval* = ``0.0`` or ``None``
    it will return a meaningless ``0.0`` value which you are supposed to
    ignore. See also :ref:`faq_cpu_percent` FAQ.

  .. versionchanged:: 5.9.6
     the function is now thread safe.

.. function:: cpu_times_percent(interval=None, percpu=False)

  Same as :func:`cpu_percent` but provides utilization percentages for each
  specific CPU time as is returned by
  :func:`psutil.cpu_times(percpu=True)<cpu_times()>`.
  *interval* and
  *percpu* arguments have the same meaning as in :func:`cpu_percent`.
  On Linux "guest" and "guest_nice" percentages are not accounted in "user"
  and "user_nice" percentages.

  .. note::
    the first time this function is called with *interval* = ``0.0`` or
    ``None`` it will return a meaningless ``0.0`` value which you are supposed
    to ignore. See also :ref:`faq_cpu_percent` FAQ.

  .. versionchanged:: 4.1.0
     two new *irq* and *dpc* fields are returned on Windows (*irq* was
     called *interrupt* before 8.0.0).

  .. versionchanged:: 5.9.6
     function is now thread safe.

.. function:: cpu_count(logical=True)

  Return the number of :term:`logical CPUs <logical CPU>` in the system
  (similar to :func:`os.cpu_count`) or ``None`` if undetermined.
  Unlike :func:`os.cpu_count`, this is not influenced by the ``PYTHON_CPU_COUNT``
  environment variable introduced in Python 3.13.
  "logical CPUs" means the number of physical cores multiplied by the number
  of threads that can run on each core (this is known as Hyper Threading).
  This is what cloud providers often refer to as vCPUs.
  If *logical* is ``False`` return the number of physical cores only, or
  ``None`` if undetermined.
  On OpenBSD and NetBSD ``psutil.cpu_count(logical=False)`` always return
  ``None``.
  Example on a system having 2 cores + Hyper Threading:

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.cpu_count()
     4
     >>> psutil.cpu_count(logical=False)
     2

  Note that ``psutil.cpu_count()`` may not necessarily be equivalent to the
  actual number of CPUs the current process can use.
  That can vary in case process CPU affinity has been changed, Linux cgroups
  are being used or (in case of Windows) on systems using processor groups or
  having more than 64 CPUs.
  The number of usable CPUs can be obtained with:

  .. code-block:: pycon

     >>> len(psutil.Process().cpu_affinity())
     1

.. function:: cpu_stats()

  Return various CPU statistics as a named tuple. All fields are
  :term:`cumulative counters <cumulative counter>` since boot.

  - **ctx_switches**: number of :term:`context switches <context switch>`
    (voluntary + involuntary).
  - **interrupts**:
    number of :term:`hardware interrupts <hardware interrupt>`.
  - **soft_interrupts**:
    number of :term:`soft interrupts <soft interrupt>`. Always set to ``0`` on
    Windows and SunOS.
  - **syscalls**: number of system calls. Always set to ``0`` on Linux.

  Example (Linux):

  .. code-block:: python

     >>> import psutil
     >>> psutil.cpu_stats()
     scpustats(ctx_switches=20455687, interrupts=6598984, soft_interrupts=2134212, syscalls=0)

  .. versionadded:: 4.1.0


.. function:: cpu_freq(percpu=False)

    Return CPU frequency as a named tuple including *current*, *min* and *max*
    frequencies expressed in Mhz. On Linux *current* frequency reports the
    real-time value, on all other platforms this usually represents the
    nominal "fixed" value (never changing). If *percpu* is ``True`` and the
    system supports per-cpu frequency retrieval (Linux and FreeBSD), a list of
    frequencies is returned for each CPU, if not, a list with a single element
    is returned. If *min* and *max* cannot be determined they are set to
    ``0.0``.

    Example (Linux):

    .. code-block:: python

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

    Return the average system load over the last 1, 5 and 15 minutes as a tuple.
    The "load" represents the processes which are in a runnable state, either
    using the CPU or waiting to use the CPU (e.g. waiting for disk I/O).
    On UNIX systems this relies on :func:`os.getloadavg`. On Windows this is emulated
    by using a Windows API that spawns a thread which keeps running in
    background and updates results every 5 seconds, mimicking the UNIX behavior.
    Thus, on Windows, the first time this is called and for the next 5 seconds
    it will return a meaningless ``(0.0, 0.0, 0.0)`` tuple.
    The numbers returned only make sense when compared to the number of CPU cores
    installed on the system. So, for instance, a value of `3.14` on a system
    with 10 logical CPUs means that the system load was 31.4% percent over the
    last N minutes.

    .. code-block:: python

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

  Return statistics about system memory usage as a named tuple including the
  following fields, expressed in bytes.

  - **total**: total physical memory (exclusive swap).
  - **available**: memory that can be given instantly to processes without the
    system going into swap. On Linux it uses the ``MemAvailable`` field from
    ``/proc/meminfo`` *(kernel 3.14+)*; on older kernels it falls back to an
    estimate. This is the recommended field for monitoring actual memory usage
    in a cross-platform fashion. See :term:`available memory`.
  - **percent**: the percentage usage calculated as
    ``(total - available) / total * 100``.
  - **used**: memory in use, calculated differently depending on the platform
    (see the table below). It is meant for informational purposes. Neither
    ``total - free`` nor ``total - available`` necessarily equals ``used``.
  - **free**: memory not currently allocated to anything. This is
    typically much lower than **available** because the OS keeps recently
    freed memory as reclaimable cache (see **cached** and **buffers**)
    rather than zeroing it immediately. Do not use this to check for
    memory pressure; use **available** instead.
  - **active** *(Linux, macOS, BSD)*: memory currently mapped by processes
    or recently accessed, held in RAM. It is unlikely to be reclaimed unless
    the system is under significant memory pressure.
  - **inactive** *(Linux, macOS, BSD)*: memory not recently accessed. It
    still holds valid data (:term:`page cache`, old allocations) but is a
    candidate for reclamation or swapping. On BSD systems it is counted in
    **available**.
  - **buffers** *(Linux, BSD)*: memory used by the kernel to cache disk
    metadata (e.g. filesystem structures). Reclaimable by the OS when needed.
  - **cached** *(Linux, BSD, Windows)*: RAM used by the kernel to cache file
    contents (data read from or written to disk). Reclaimable by the OS when
    needed. See :term:`page cache`.
  - **shared** *(Linux, BSD)*: memory accessible by multiple processes
    simultaneously, such as in-memory ``tmpfs`` and POSIX shared memory objects
    (``shm_open``). On Linux this corresponds to ``Shmem`` in ``/proc/meminfo``
    and is already counted within **active** / **inactive**.
  - **slab** *(Linux)*: memory used by the kernel's internal object caches
    (e.g. inode and dentry caches). The reclaimable portion
    (``SReclaimable``) is already included in **cached**.
  - **wired** *(macOS, BSD, Windows)*: memory pinned in RAM by the kernel (e.g.
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

  .. note:: if you just want to know how much physical memory is left in a
    cross-platform manner, simply rely on **available** and **percent**
    fields.

  .. note::
     - On Linux, **total**, **free**, **used**, **shared**, and **available**
       match the output of the ``free`` command.
     - On macOS, **free**, **active**, **inactive**, and **wired** match
       ``vm_stat`` output.
     - On Windows, **total**, **used** ("In use"), and **available** match
       the Task Manager (Performance > Memory tab).

  .. note::  see also `scripts/meminfo.py`_.

  .. versionchanged:: 4.2.0
     added *shared* metric on Linux.

  .. versionchanged:: 5.4.4
     added *slab* metric on Linux.

  .. versionchanged:: 8.0.0
     added *cached* and *wired* metric on Windows.

.. function:: swap_memory()

  Return system swap memory statistics as a named tuple including the following
  fields:

  * **total**: total swap space. On Windows this is derived as
    ``CommitLimit - PhysicalTotal``, representing virtual memory backed by
    the page file rather than the raw page-file size.
  * **used**: swap space currently in use.
  * **free**: swap space not in use (``total - used``).
  * **percent**: swap usage as a percentage, calculated as
    ``used / total * 100``.
  * **sin**: number of bytes the system has paged *in* from disk (pages moved
    from swap space back into RAM) since boot. See :term:`swap-in`.
  * **sout**: number of bytes the system has paged *out* to disk (pages moved
    from RAM into swap space) since boot. A continuously increasing **sout**
    is a sign of memory pressure. See :term:`swap-out`.

  **sin** and **sout** are :term:`cumulative counters <cumulative counter>` since boot; monitor
  their rate of change rather than the absolute value to detect active
  swapping. See :term:`swap-in` and :term:`swap-out`.
  On Windows both are always ``0``.
  See `scripts/meminfo.py`_ script providing an example on how to convert bytes in a
  human readable form.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.swap_memory()
     sswap(total=2097147904L, used=886620160L, free=1210527744L, percent=42.3, sin=1050411008, sout=1906720768)

  .. versionchanged:: 5.2.3
     on Linux this function relies on /proc fs instead of sysinfo() syscall so
     that it can be used in conjunction with
     :const:`psutil.PROCFS_PATH` in order to retrieve memory info about
     Linux containers such as Docker and Heroku.

Disks
^^^^^

.. function:: disk_partitions(all=False)

  Return all mounted disk partitions as a list of named tuples including device,
  mount point and filesystem type, similarly to "df" command on UNIX. If *all*
  parameter is ``False`` it tries to distinguish and return physical devices
  only (e.g. hard disks, cd-rom drives, USB keys) and ignore all others
  (e.g. pseudo, memory, duplicate, inaccessible filesystems).
  Note that this may not be fully reliable on all systems (e.g. on BSD this
  parameter is ignored).
  See `scripts/disk_usage.py`_ script providing an example usage.
  Returns a list of named tuples with the following fields:

  * **device**: the device path (e.g. "/dev/hda1"). On Windows this is the
    drive letter (e.g. "C:\\").
  * **mountpoint**: the mount point path (e.g. "/"). On Windows this is the
    drive letter (e.g. "C:\\").
  * **fstype**: the partition filesystem (e.g. "ext3" on UNIX or "NTFS"
    on Windows).
  * **opts**: a comma-separated string indicating different mount options for
    the drive/partition. Platform-dependent.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.disk_partitions()
     [sdiskpart(device='/dev/sda3', mountpoint='/', fstype='ext4', opts='rw,errors=remount-ro'),
      sdiskpart(device='/dev/sda7', mountpoint='/home', fstype='ext4', opts='rw')]

  .. versionchanged:: 5.7.4
     added *maxfile* and *maxpath* fields.

  .. versionchanged:: 6.0.0
     removed *maxfile* and *maxpath* fields.

.. function:: disk_usage(path)

  Return disk usage statistics about the partition which contains the given
  *path* as a named tuple including **total**, **used** and **free** space
  expressed in bytes, plus the **percentage** usage.
  See `scripts/disk_usage.py`_ script providing an example usage.

  This function was later incorporated in Python 3.3 as
  :func:`shutil.disk_usage` (`BPO-12442`_).

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.disk_usage('/')
     sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)

  .. note::
    Note On UNIX, path must point to a path within a **mounted** filesystem partition.

  .. note::
    UNIX usually reserves 5% of the total disk space for the root user.
    *total* and *used* fields on UNIX refer to the overall total and used
    space, whereas *free* represents the space available for the **user** and
    *percent* represents the **user** utilization (see
    `source code <https://github.com/giampaolo/psutil/blob/3dea30d583b8c1275057edb1b3b720813b4d0f60/psutil/_psposix.py#L123>`_).
    That is why *percent* value may look 5% bigger than what you would expect
    it to be.
    Also note that both 4 values match "df" cmdline utility.

  .. versionchanged:: 4.3.0
     *percent* value takes root reserved space into account.

.. function:: disk_io_counters(perdisk=False, nowrap=True)

  Return system-wide disk I/O statistics as a named tuple including the
  following fields:

  - **read_count**: number of reads
  - **write_count**: number of writes
  - **read_bytes**: number of bytes read
  - **write_bytes**: number of bytes written

  Platform-specific fields:

  - **read_time**: (all except *NetBSD* and *OpenBSD*) time spent reading from
    disk (in milliseconds)
  - **write_time**: (all except *NetBSD* and *OpenBSD*) time spent writing to disk
    (in milliseconds)
  - **busy_time**: (*Linux*, *FreeBSD*) time spent doing actual I/Os (in
    milliseconds). See :term:`busy_time`.
  - **read_merged_count** (*Linux*): number of merged reads (see `iostats doc`_)
  - **write_merged_count** (*Linux*): number of merged writes (see `iostats doc`_)

  If *perdisk* is ``True`` return the same information for every physical disk
  installed on the system as a dictionary with partition names as the keys and
  the named tuple described above as the values.
  See `scripts/iotop.py`_ for an example application.
  On some systems such as Linux, on a very busy or long-lived system, the
  numbers returned by the kernel may overflow and wrap (restart from zero).
  If *nowrap* is ``True`` psutil will detect and adjust those numbers across
  function calls and add "old value" to "new value" so that the returned
  numbers will always be increasing or remain the same, but never decrease.
  ``disk_io_counters.cache_clear()`` can be used to invalidate the *nowrap*
  cache.
  On Windows it may be necessary to issue ``diskperf -y`` command from cmd.exe
  first in order to enable IO counters.
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
    on Windows ``"diskperf -y"`` command may need to be executed first
    otherwise this function won't find any disk.

  .. versionchanged:: 5.3.0
     numbers no longer wrap (restart from zero) across calls thanks to new
    *nowrap* argument.

  .. versionchanged:: 4.0.0
     added *busy_time* (Linux, FreeBSD), *read_merged_count* and
    *write_merged_count* (Linux) fields.

  .. versionchanged:: 4.0.0
     NetBSD no longer has *read_time* and *write_time* fields.

Network
^^^^^^^

.. function:: net_io_counters(pernic=False, nowrap=True)

  Return system-wide network I/O statistics as a named tuple including the
  following attributes:

  - **bytes_sent**: number of bytes sent
  - **bytes_recv**: number of bytes received
  - **packets_sent**: number of packets sent
  - **packets_recv**: number of packets received
  - **errin**: total number of errors while receiving
  - **errout**: total number of errors while sending
  - **dropin**: total number of incoming packets which were dropped
  - **dropout**: total number of outgoing packets which were dropped (always 0
    on macOS and BSD). See :term:`dropin / dropout`.

  If *pernic* is ``True`` return the same information for every network
  interface installed on the system as a dictionary with network interface
  names as the keys and the named tuple described above as the values.
  On some systems such as Linux, on a very busy or long-lived system, the
  numbers returned by the kernel may overflow and wrap (restart from zero).
  If *nowrap* is ``True`` psutil will detect and adjust those numbers across
  function calls and add "old value" to "new value" so that the returned
  numbers will always be increasing or remain the same, but never decrease.
  ``net_io_counters.cache_clear()`` can be used to invalidate the *nowrap*
  cache.
  On machines with no network interfaces this function will return ``None`` or
  ``{}`` if *pernic* is ``True``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_io_counters()
     snetio(bytes_sent=14508483, bytes_recv=62749361, packets_sent=84311, packets_recv=94888, errin=0, errout=0, dropin=0, dropout=0)
     >>>
     >>> psutil.net_io_counters(pernic=True)
     {'lo': snetio(bytes_sent=547971, bytes_recv=547971, packets_sent=5075, packets_recv=5075, errin=0, errout=0, dropin=0, dropout=0),
     'wlan0': snetio(bytes_sent=13921765, bytes_recv=62162574, packets_sent=79097, packets_recv=89648, errin=0, errout=0, dropin=0, dropout=0)}

  Also see `scripts/nettop.py`_ and `scripts/ifconfig.py`_ for an example application.

  .. versionchanged:: 5.3.0
     numbers no longer wrap (restart from zero) across calls thanks to new
     *nowrap* argument.

.. function:: net_connections(kind='inet')

  Return system-wide socket connections as a list of named tuples.
  Every named tuple provides 7 attributes:

  - **fd**: the socket file descriptor. If the connection refers to the current
    process this may be passed to :func:`socket.fromfd`
    to obtain a usable socket object.
    On Windows and SunOS this is always set to ``-1``.
  - **family**: the address family, either :data:`socket.AF_INET`, :data:`socket.AF_INET6` or :data:`socket.AF_UNIX`.
  - **type**: the address type, either :data:`socket.SOCK_STREAM`, :data:`socket.SOCK_DGRAM` or
    :data:`socket.SOCK_SEQPACKET`.
  - **laddr**: the local address as a ``(ip, port)`` named tuple or a ``path``
    in case of AF_UNIX sockets. For UNIX sockets see notes below.
  - **raddr**: the remote address as a ``(ip, port)`` named tuple or an
    absolute ``path`` in case of UNIX sockets.
    When the remote endpoint is not connected you'll get an empty tuple
    (AF_INET*) or ``""`` (AF_UNIX). For UNIX sockets see notes below.
  - **status**: represents the status of a TCP connection. The return value
    is one of the `psutil.CONN_* <#connections-constants>`_ constants
    (a string).
    For UDP and UNIX sockets this is always going to be
    :const:`psutil.CONN_NONE`.
  - **pid**: the PID of the process which opened the socket, if retrievable,
    else ``None``. On some platforms (e.g. Linux) the availability of this
    field changes depending on process privileges (root is needed).

  The *kind* parameter is a string which filters for connections matching the
  following criteria:

  .. table::

   +----------------+-----------------------------------------------------+
   | Kind value     | Connections using                                   |
   +================+=====================================================+
   | ``"inet"``     | IPv4 and IPv6                                       |
   +----------------+-----------------------------------------------------+
   | ``"inet4"``    | IPv4                                                |
   +----------------+-----------------------------------------------------+
   | ``"inet6"``    | IPv6                                                |
   +----------------+-----------------------------------------------------+
   | ``"tcp"``      | TCP                                                 |
   +----------------+-----------------------------------------------------+
   | ``"tcp4"``     | TCP over IPv4                                       |
   +----------------+-----------------------------------------------------+
   | ``"tcp6"``     | TCP over IPv6                                       |
   +----------------+-----------------------------------------------------+
   | ``"udp"``      | UDP                                                 |
   +----------------+-----------------------------------------------------+
   | ``"udp4"``     | UDP over IPv4                                       |
   +----------------+-----------------------------------------------------+
   | ``"udp6"``     | UDP over IPv6                                       |
   +----------------+-----------------------------------------------------+
   | ``"unix"``     | UNIX socket (both UDP and TCP protocols)            |
   +----------------+-----------------------------------------------------+
   | ``"all"``      | the sum of all the possible families and protocols  |
   +----------------+-----------------------------------------------------+

  On macOS and AIX this function requires root privileges.
  To get per-process connections use :meth:`Process.net_connections`.
  Also, see `scripts/netstat.py`_ example script.
  Example:

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_connections()
     [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>, pid=1254),
      pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=43761), raddr=addr(ip='72.14.234.100', port=80), status=<ConnectionStatus.CONN_CLOSING: 'CLOSING'>, pid=2987),
      pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=60759), raddr=addr(ip='72.14.234.104', port=80), status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>, pid=None),
      pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=51314), raddr=addr(ip='72.14.234.83', port=443), status=<ConnectionStatus.CONN_SYN_SENT: 'SYN_SENT'>, pid=None)
      ...]

  .. warning::
    On Linux, retrieving some connections requires root privileges. If psutil is
    not run as root, those connections are silently skipped instead of raising
    :exc:`PermissionError`. That means the returned list may be incomplete.

  .. note::
    (macOS and AIX) :exc:`psutil.AccessDenied` is always raised unless running
    as root. This is a limitation of the OS and ``lsof`` does the same.

  .. note::
    (Solaris) UNIX sockets are not supported.

  .. note::
     (Linux, FreeBSD, OpenBSD) *raddr* field for UNIX sockets is always set to
     ``""`` (empty string). This is a limitation of the OS.

  .. versionadded:: 2.1.0

  .. versionchanged:: 5.3.0
     socket "fd" is now set for real instead of being ``-1``.

  .. versionchanged:: 5.3.0
    *laddr* and *raddr* are named tuples.

  .. versionchanged:: 5.9.5
     OpenBSD: retrieve *laddr* path for AF_UNIX sockets (before it was an empty
     string).

  .. versionchanged:: 8.0.0
     *status* field is now a :class:`psutil.ConnectionStatus` enum member
     instead of a plain ``str``.
     See :ref:`migration guide <migration-8.0>`.

.. function:: net_if_addrs()

  Return the addresses associated to each :term:`NIC` (network interface card)
  installed on the system as a dictionary whose keys are the NIC names and
  value is a list of named tuples for each address assigned to the NIC.
  Each named tuple includes 5 fields:

  - **family**: the address family, either :data:`socket.AF_INET`,
    :data:`socket.AF_INET6`, :const:`psutil.AF_LINK` in case of MAC address,
    :data:`socket.AF_UNSPEC` in case of virtual or unconfigured interfaces.
  - **address**: the primary NIC address (may be ``None`` in case of virtual
    or unconfigured interfaces).
  - **netmask**: the netmask address (may be ``None``).
  - **broadcast**: the broadcast address (may be ``None``).
  - **ptp**: stands for "point to point"; it's the destination address on a
    point to point interface (typically a VPN). *broadcast* and *ptp* are
    mutually exclusive. May be ``None``.

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

  See also `scripts/nettop.py`_ and `scripts/ifconfig.py`_ for an example application.

  .. note::
    if you're interested in others families (e.g. AF_BLUETOOTH) you can use
    the more powerful `netifaces <https://pypi.org/project/netifaces/>`_
    extension.

  .. note::
    you can have more than one address of the same family associated with each
    interface (that's why dict values are lists).

  .. note::
    *broadcast* and *ptp* are not supported on Windows and are always ``None``.

  .. versionadded:: 3.0.0

  .. versionchanged:: 3.2.0
     *ptp* field was added.

  .. versionchanged:: 4.4.0
     added support for *netmask* field on Windows which is no longer ``None``.

  .. versionchanged:: 7.0.0
     added support for *broadcast* field on Windows which is no longer ``None``.

.. function:: net_if_stats()

  Return information about each :term:`NIC` (network interface card) installed on the
  system as a dictionary whose keys are the NIC names and value is a named tuple
  with the following fields:

  - **isup**: a bool indicating whether the NIC is up and running (meaning
    ethernet cable or Wi-Fi is connected).
  - **duplex**: the duplex communication type;
    it can be either :const:`NIC_DUPLEX_FULL`, :const:`NIC_DUPLEX_HALF` or
    :const:`NIC_DUPLEX_UNKNOWN`.
  - **speed**: the NIC speed expressed in megabits (Mbps), if it can't be
    determined (e.g. 'localhost') it will be set to ``0``.
  - **mtu**: NIC's maximum transmission unit expressed in bytes.
  - **flags**: a string of comma-separated flags on the interface (may be an empty string).
    Possible flags are: ``up``, ``broadcast``, ``debug``, ``loopback``,
    ``pointopoint``, ``notrailers``, ``running``, ``noarp``, ``promisc``,
    ``allmulti``, ``master``, ``slave``, ``multicast``, ``portsel``,
    ``dynamic``, ``oactive``, ``simplex``, ``link0``, ``link1``, ``link2``,
    and ``d2`` (some flags are only available on certain platforms).

  Also see `scripts/nettop.py`_ and `scripts/ifconfig.py`_ for an example application.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.net_if_stats()
     {'eth0': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_FULL: 2>, speed=100, mtu=1500, flags='up,broadcast,running,multicast'),
      'lo': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_UNKNOWN: 0>, speed=0, mtu=65536, flags='up,loopback,running')}

  .. availability:: UNIX

  .. versionadded:: 3.0.0

  .. versionchanged:: 5.7.3
     `isup` on UNIX also checks whether the NIC is running.

  .. versionchanged:: 5.9.3
     *flags* field was added on POSIX.

Sensors
^^^^^^^

.. function:: sensors_temperatures(fahrenheit=False)

  Return hardware temperatures. Each entry is a named tuple representing a
  certain hardware temperature sensor (it may be a CPU, an hard disk or
  something else, depending on the OS and its configuration).
  All temperatures are expressed in celsius unless *fahrenheit* is set to
  ``True``.
  If sensors are not supported by the OS an empty dict is returned.
  Each named tuple includes 4 fields:

  - **label**: a string label for the sensor, if available, else ``""``.
  - **current**: current temperature, or ``None`` if not available.
  - **high**: temperature at which the system will throttle, or ``None``
    if not available.
  - **critical**: temperature at which the system will shut down, or
    ``None`` if not available.

  See also `scripts/temperatures.py`_ and `scripts/sensors.py`_ for an example application.

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

  .. availability:: Linux, FreeBSD

  .. versionadded:: 5.1.0

  .. versionchanged:: 5.5.0
     added FreeBSD support.

.. function:: sensors_fans()

  Return hardware fans speed. Each entry is a named tuple representing a
  certain hardware sensor fan.
  Fan speed is expressed in RPM (revolutions per minute).
  If sensors are not supported by the OS an empty dict is returned.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.sensors_fans()
     {'asus': [sfan(label='cpu_fan', current=3200)]}

  See also `scripts/fans.py`_  and `scripts/sensors.py`_ for an example application.

  .. availability:: Linux

  .. versionadded:: 5.2.0

.. function:: sensors_battery()

  Return battery status information as a named tuple including the following
  values. If no battery is installed or metrics can't be determined ``None``
  is returned.

  - **percent**: battery power left as a percentage.
  - **secsleft**: a rough approximation of how many seconds are left before the
    battery runs out of power.
    If the AC power cable is connected this is set to
    :data:`psutil.POWER_TIME_UNLIMITED <psutil.POWER_TIME_UNLIMITED>`.
    If it can't be determined it is set to
    :data:`psutil.POWER_TIME_UNKNOWN <psutil.POWER_TIME_UNKNOWN>`.
  - **power_plugged**: ``True`` if the AC power cable is connected, ``False``
    if not or ``None`` if it can't be determined.

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

  See also `scripts/battery.py`_  and `scripts/sensors.py`_ for an example application.

  .. availability:: Linux, Windows, macOS, FreeBSD

  .. versionadded:: 5.1.0

  .. versionchanged:: 5.4.2
     added macOS support.

----

Other system info
^^^^^^^^^^^^^^^^^

.. function:: boot_time()

  Return the system boot time expressed in seconds since the epoch (seconds
  since January 1, 1970, at midnight UTC). The returned value is based on the
  system clock, which means it may be affected by changes such as manual
  adjustments or time synchronization (e.g. NTP).

  .. code-block:: python

     >>> import psutil, datetime
     >>> psutil.boot_time()
     1389563460.0
     >>> datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
     '2014-01-12 22:51:00'

  .. note::
    on Windows this function may return a time which is off by 1 second if it's
    used across different processes (see issue :gh:`1007`).

.. function:: users()

  Return users currently connected on the system as a list of named tuples
  including the following fields:

  - **name**: the name of the user.
  - **terminal**: the tty or pseudo-tty associated with the user, if any,
    else ``None``.
  - **host**: the host name associated with the entry, if any, else ``None``.
  - **started**: the creation time as a floating point number expressed in
    seconds since the epoch.
  - **pid**: the PID of the login process (like sshd, tmux, gdm-session-worker,
    ...). On Windows and OpenBSD this is always set to ``None``.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.users()
     [suser(name='giampaolo', terminal='pts/2', host='localhost', started=1340737536.0, pid=1352),
      suser(name='giampaolo', terminal='pts/3', host='localhost', started=1340737792.0, pid=1788)]

  .. versionchanged:: 5.3.0
     added "pid" field.

----

Processes
---------

Functions
^^^^^^^^^

.. function:: pids()

  Return a sorted list of current running PIDs.
  To iterate over all processes and avoid race conditions :func:`process_iter`
  should be preferred.

  .. code-block:: pycon

     >>> import psutil
     >>> psutil.pids()
     [1, 2, 3, 5, 7, 8, 9, 10, 11, 12, 13, 14, 15, 17, 18, 19, ..., 32498]


  .. versionchanged:: 5.6.0
     PIDs are returned in sorted order.

.. function:: process_iter(attrs=None, ad_value=None)

  Return an iterator yielding a :class:`Process` class instance for all running
  processes on the local machine.
  This should be preferred over :func:`psutil.pids` to iterate over
  processes, as retrieving info is safe from race conditions.

  Every :class:`Process` instance is only created once, and then cached for the
  next time :func:`psutil.process_iter` is called (if PID is still alive).
  Cache can optionally be cleared via ``process_iter.cache_clear()``.

  *attrs* and *ad_value* have the same meaning as in :meth:`Process.as_dict`.
  If *attrs* is specified, the requested attributes are pre-fetched and
  cached so that subsequent method calls (e.g. :meth:`Process.name`,
  :meth:`Process.status`) return the cached values instead of issuing new
  system calls. If a method raises :exc:`AccessDenied` during pre-fetch,
  it will return *ad_value* (default ``None``) instead of raising.
  If *attrs* is an empty list it will retrieve all process info (slow).

  Sorting order in which processes are returned is based on their PID.

  .. note::

    Since :class:`Process` instances are reused across calls, a subsequent
    :func:`process_iter` call will overwrite or clear any previously
    pre-fetched values. Do not rely on cached values from a prior iteration.

  .. code-block:: pycon

     >>> import psutil
     >>> for proc in psutil.process_iter(['pid', 'name', 'username']):
     ...     print(proc.pid, proc.name(), proc.username())
     ...
     1 systemd root
     2 kthreadd root
     3 ksoftirqd/0 root
     ...

  A dict comprehension to create a ``{pid: name, ...}`` data structure:

  .. code-block:: pycon

     >>> import psutil
     >>> procs = {p.pid: p.name() for p in psutil.process_iter(['name'])}
     >>> procs
     {1: 'systemd',
      2: 'kthreadd',
      3: 'ksoftirqd/0',
      ...}

  Clear internal cache:

  .. code-block:: pycon

     >>> psutil.process_iter.cache_clear()

  .. versionchanged:: 5.3.0
     added "attrs" and "ad_value" parameters.

  .. versionchanged:: 6.0.0
     no longer checks whether each yielded process PID has been reused.

  .. versionchanged:: 6.0.0
     added ``psutil.process_iter.cache_clear()`` API.

  .. versionchanged:: 8.0.0
     when *attrs* is specified, the pre-fetched values are cached
     directly on the :class:`Process` instance so that subsequent
     method calls (e.g. ``p.name()``, ``p.status()``) return the
     cached values instead of making new system calls. The ``p.info``
     dict is deprecated in favor of this new approach.

.. function:: pid_exists(pid)

  Check whether the given PID exists in the current process list. This is
  faster than doing ``pid in psutil.pids()`` and should be preferred.

.. function:: wait_procs(procs, timeout=None, callback=None)

  Convenience function which waits for a list of :class:`Process` instances to
  terminate. Return a ``(gone, alive)`` tuple indicating which processes are
  gone and which ones are still alive. The *gone* ones will have a new
  *returncode* attribute indicating process exit status as returned by
  :meth:`Process.wait`.
  ``callback`` is a function which gets called when one of the processes being
  waited on is terminated and a :class:`Process` instance is passed as callback
  argument (the instance will also have a *returncode* attribute set).
  This function will return as soon as all processes terminate or when
  *timeout* (seconds) occurs.
  Differently from :meth:`Process.wait` it will not raise
  :exc:`TimeoutExpired` if timeout occurs.
  A typical use case may be:

  - send SIGTERM to a list of processes
  - give them some time to terminate
  - send SIGKILL to those ones which are still alive

  Example which terminates and waits all the children of this process::

    import psutil

    def on_terminate(proc):
        print("process {} terminated with exit code {}".format(proc, proc.returncode))

    procs = psutil.Process().children()
    for p in procs:
        p.terminate()
    gone, alive = psutil.wait_procs(procs, timeout=3, callback=on_terminate)
    for p in alive:
        p.kill()

Exceptions
^^^^^^^^^^

.. exception:: Error()

  Base exception class. All other exceptions inherit from this one.

.. exception:: NoSuchProcess(pid, name=None, msg=None)

  Raised by :class:`Process` class methods when no process with the given
  *pid* is found in the current process list, or when a process no longer
  exists. *name* is the name the process had before disappearing
  and gets set only if :meth:`Process.name` was previously called.

  See also :ref:`faq_no_such_process` FAQ.

.. exception:: ZombieProcess(pid, name=None, ppid=None, msg=None)

  This may be raised by :class:`Process` class methods when querying a
  :term:`zombie process` on UNIX (Windows doesn't have zombie processes).
  *name* and *ppid* attributes are available if :meth:`Process.name` or
  :meth:`Process.ppid` methods were called before the process turned into a
  zombie.

  See also :ref:`faq_zombie_process` FAQ.

  .. note::

    this is a subclass of :exc:`NoSuchProcess` so if you're not interested
    in retrieving zombies (e.g. when using :func:`process_iter`) you can
    ignore this exception and just catch :exc:`NoSuchProcess`.

  .. versionadded:: 3.0.0

.. exception:: AccessDenied(pid=None, name=None, msg=None)

  Raised by :class:`Process` class methods when permission to perform an
  action is denied due to insufficient privileges.
  *name* attribute is available if :meth:`Process.name` was previously called.

  See also :ref:`faq_access_denied` FAQ.

.. exception:: TimeoutExpired(seconds, pid=None, name=None, msg=None)

  Raised by :meth:`Process.wait` method if timeout expires and the process is
  still alive.
  *name* attribute is available if :meth:`Process.name` was previously called.

Process class
^^^^^^^^^^^^^

.. class:: Process(pid=None)

  Represents an OS process with the given *pid*.
  If *pid* is omitted current process *pid* (:func:`os.getpid`) is used.
  Raise :exc:`NoSuchProcess` if *pid* does not exist.
  On Linux *pid* can also refer to a thread ID (the *id* field returned by
  :meth:`threads` method).
  When calling methods of this class, always be prepared to catch
  :exc:`NoSuchProcess` and :exc:`AccessDenied` exceptions.
  :func:`hash` builtin can be used against instances of this class in order to
  identify a process univocally over time (the hash is determined by mixing
  process PID + creation time). As such it can also be used with :class:`set`.

  .. note::

    In order to efficiently fetch more than one information about the process
    at the same time, make sure to use either :meth:`oneshot` context manager
    or :meth:`as_dict` utility method.

  .. note::

    the way this class is bound to a process is via its **PID**.
    That means that if the process terminates and the OS reuses its PID you may
    inadvertently end up interacting with another process. To prevent this
    problem you can use :meth:`is_running` first.
    Some methods (e.g. setters and signal-related methods) perform an
    additional check based on PID + creation time and will raise
    :exc:`NoSuchProcess` if the PID has been reused. See :ref:`faq_pid_reuse`
    FAQ for details.

  .. method:: oneshot()

    Utility context manager which considerably speeds up the retrieval of
    multiple process information at the same time.
    Internally different process info (e.g. :meth:`name`, :meth:`ppid`,
    :meth:`uids`, :meth:`create_time`, ...) may be fetched by using the same
    routine, but only one value is returned and the others are discarded.
    When using this context manager the internal routine is executed once (in
    the example below on :meth:`name`) the value of interest is returned and
    the others are cached.
    The subsequent calls sharing the same internal routine will return the
    cached value.
    The cache is cleared when exiting the context manager block.
    The advice is to use this every time you retrieve more than one information
    about the process. If you're lucky, you'll get a hell of a speedup.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> with p.oneshot():
       ...     p.name()  # execute internal routine once collecting multiple info
       ...     p.cpu_times()  # return cached value
       ...     p.cpu_percent()  # return cached value
       ...     p.create_time()  # return cached value
       ...     p.ppid()  # return cached value
       ...     p.status()  # return cached value
       ...
       >>>

    Here's a list of methods which can take advantage of the speedup depending
    on what platform you're on.
    In the table below horizontal empty rows indicate what process methods can
    be efficiently grouped together internally.
    The last column (speedup) shows an approximation of the speedup you can get
    if you call all the methods together (best case scenario).

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
    | :meth:`ppid`                 | :meth:`num_ctx_switches`      | :meth:`num_threads`          | :meth:`io_counters`          | :meth:`memory_percent`   | :meth:`memory_percent`   |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`status`               | :meth:`num_handles`           |                              | :meth:`name`                 | :meth:`num_threads`      | :meth:`num_threads`      |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`terminal`             | :meth:`num_threads`           | :meth:`create_time`          | :meth:`memory_info`          | :meth:`ppid`             | :meth:`ppid`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    |                              |                               | :meth:`gids`                 | :meth:`memory_percent`       | :meth:`status`           | :meth:`status`           |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`gids`                 | :meth:`exe`                   | :meth:`name`                 | :meth:`num_ctx_switches`     | :meth:`terminal`         | :meth:`terminal`         |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`memory_info_ex`       | :meth:`name`                  | :meth:`ppid`                 | :meth:`ppid`                 |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`num_ctx_switches`     |                               | :meth:`status`               | :meth:`status`               | :meth:`gids`             | :meth:`gids`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`num_threads`          |                               | :meth:`terminal`             | :meth:`terminal`             | :meth:`uids`             | :meth:`uids`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`uids`                 |                               | :meth:`terminal`             | :meth:`terminal`             | :meth:`uids`             | :meth:`uids`             |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`username`             |                               | :meth:`uids`                 | :meth:`uids`                 | :meth:`username`         | :meth:`username`         |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    |                              |                               | :meth:`username`             | :meth:`username`             |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`memory_footprint`     |                               |                              |                              |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | :meth:`memory_maps`          |                               |                              |                              |                          |                          |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+
    | *speedup: +2.6x*             | *speedup: +1.8x / +6.5x*      | *speedup: +1.9x*             | *speedup: +2.0x*             | *speedup: +1.3x*         | *speedup: +1.3x*         |
    +------------------------------+-------------------------------+------------------------------+------------------------------+--------------------------+--------------------------+

    .. versionadded:: 5.0.0

  .. attribute:: pid

     The process PID. This is the only (read-only) attribute of the class.

  .. method:: ppid()

    The process parent PID. On Windows the return value is cached after the
    first call. On POSIX it is not cached because the ppid may change if the
    process becomes a :term:`zombie process`.
    See also :meth:`parent` and :meth:`parents` methods.

  .. method:: name()

    The process name.  On Windows the return value is cached after first
    call. Not on POSIX because the process name may change.
    See also how to `find a process by name <#find-process-by-name>`_.

  .. method:: exe()

    The process executable as an absolute path. On some systems, if exe cannot
    be determined for some internal reason (e.g. system process or path no
    longer exists), this may be an empty string. The return value is cached
    after first call.

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
       ['python', 'manage.py', 'runserver']

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
    clock, which means it may be affected by changes such as manual adjustments
    or time synchronization (e.g. NTP).

    .. code-block:: pycon

       >>> import psutil, datetime
       >>> p = psutil.Process()
       >>> p.create_time()
       1307289803.47
       >>> datetime.datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S")
       '2011-03-05 18:03:52'

  .. method:: as_dict(attrs=None, ad_value=None)

    Utility method retrieving multiple process information as a dictionary.
    If *attrs* is specified it must be a list of strings reflecting available
    :class:`Process` class's attribute names. Here's a list of possible string
    values:
    ``'cmdline'``, ``'net_connections'``, ``'cpu_affinity'``, ``'cpu_num'``, ``'cpu_percent'``, ``'cpu_times'``, ``'create_time'``, ``'cwd'``, ``'environ'``, ``'exe'``, ``'gids'``, ``'io_counters'``, ``'ionice'``, ``'memory_footprint'``, ``'memory_full_info'``, ``'memory_info'``, ``'memory_info_ex'``, ``'memory_maps'``, ``'memory_percent'``, ``'name'``, ``'nice'``, ``'num_ctx_switches'``, ``'num_fds'``, ``'num_handles'``, ``'num_threads'``, ``'open_files'``, ``'pid'``, ``'ppid'``, ``'status'``, ``'terminal'``, ``'threads'``, ``'uids'``, ``'username'```.
    If *attrs* argument is not passed all public read only attributes are
    assumed.
    *ad_value* is the value which gets assigned to a dict key in case
    :exc:`AccessDenied` or :exc:`ZombieProcess` exception is raised when
    retrieving that particular process information.
    Internally, :meth:`as_dict` uses :meth:`oneshot` context manager so
    there's no need you use it also.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.as_dict(attrs=['pid', 'name', 'username'])
       {'username': 'giampaolo', 'pid': 12366, 'name': 'python'}
       >>>
       >>> # get a list of valid attrs names
       >>> list(psutil.Process().as_dict().keys())
       ['cmdline', 'connections', 'cpu_affinity', 'cpu_num', 'cpu_percent', 'cpu_times', 'create_time', 'cwd', 'environ', 'exe', 'gids', 'io_counters', 'ionice', 'memory_footprint', 'memory_full_info', 'memory_info', 'memory_info_ex', 'memory_maps', 'memory_percent', 'name', 'net_connections', 'nice', 'num_ctx_switches', 'num_fds', 'num_threads', 'open_files', 'pid', 'ppid', 'status', 'terminal', 'threads', 'uids', 'username']

    .. versionchanged:: 3.0.0
       *ad_value* is used also when incurring into :exc:`ZombieProcess`
       exception, not only :exc:`AccessDenied`.

    .. versionchanged:: 4.5.0
       :meth:`as_dict` is considerably faster thanks to :meth:`oneshot`
       context manager.

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

    The current process status as a :class:`psutil.ProcessStatus` enum member.
    The returned value is one of the
    `psutil.STATUS_* <#process-status-constants>`_ constants.
    A common use case is detecting :term:`zombie processes <zombie process>`
    (``p.status() == psutil.STATUS_ZOMBIE``).

    .. versionchanged:: 8.0.0
       return value is now a :class:`psutil.ProcessStatus` enum member instead
       of a plain ``str``.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: cwd()

    The process current working directory as an absolute path. If cwd cannot be
    determined for some internal reason (e.g. system process or directory no
    longer exists) it may return an empty string.

    .. versionchanged:: 5.6.4
       added support for NetBSD.

  .. method:: username()

    The name of the user that owns the process. On UNIX this is calculated by
    using real process uid.

  .. method:: uids()

    The real, effective and saved user ids of this process as a named tuple.
    This is the same as :func:`os.getresuid` but can be used for any process PID.

    .. availability:: UNIX

  .. method:: gids()

    The real, effective and saved group ids of this process as a named tuple.
    This is the same as :func:`os.getresgid` but can be used for any process PID.

    .. availability:: UNIX

  .. method:: terminal()

    The terminal associated with this process, if any, else ``None``. This is
    similar to "tty" command but can be used for any process PID.

    .. availability:: UNIX

  .. method:: nice(value=None)

    Get or set process niceness (priority).
    On UNIX this is a number which usually goes from ``-20`` to ``20``.
    The higher the nice value, the lower the priority of the process.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.nice(10)  # set
       >>> p.nice()  # get
       10
       >>>

    This method was later incorporated in Python 3.3 as
    :func:`os.getpriority` and :func:`os.setpriority` (see `BPO-10784`_).

    On Windows this is implemented via `GetPriorityClass`_ and
    `SetPriorityClass`_ Windows APIs and *value* is one of the
    :data:`psutil.*_PRIORITY_CLASS <psutil.ABOVE_NORMAL_PRIORITY_CLASS>`
    constants reflecting the MSDN documentation.
    The return value on Windows is a :class:`psutil.ProcessPriority` enum member.
    Example which increases process priority on Windows:

    .. code-block:: pycon

       >>> p.nice(psutil.HIGH_PRIORITY_CLASS)

    .. versionchanged:: 8.0.0
       on Windows, return value is now a :class:`psutil.ProcessPriority` enum
       member.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: ionice(ioclass=None, value=None)

    Get or set process I/O niceness (priority).
    If no argument is provided it acts as a get, returning a ``(ioclass, value)``
    tuple on Linux and a *ioclass* integer on Windows.
    If *ioclass* is provided it acts as a set. In this case an additional
    *value* can be specified on Linux only in order to increase or decrease the
    I/O priority even further.
    Here's the possible platform-dependent *ioclass* values.

    Linux (see `ioprio_get`_ manual):

    * :const:`IOPRIO_CLASS_RT`: (high) the process gets first access to the disk
      every time. Use it with care as it can starve the entire
      system. Additional priority *level* can be specified and ranges from
      ``0`` (highest) to ``7`` (lowest).
    * :const:`IOPRIO_CLASS_BE`: (normal) the default for any process that hasn't set
      a specific I/O priority. Additional priority *level* ranges from
      ``0`` (highest) to ``7`` (lowest).
    * :const:`IOPRIO_CLASS_IDLE`: (low) get I/O time when no-one else needs the disk.
      No additional *value* is accepted.
    * :const:`IOPRIO_CLASS_NONE`: returned when no priority was previously set.

    Windows:

    * :const:`IOPRIO_HIGH`: highest priority.
    * :const:`IOPRIO_NORMAL`: default priority.
    * :const:`IOPRIO_LOW`: low priority.
    * :const:`IOPRIO_VERYLOW`: lowest priority.

    Here's an example on how to set the highest I/O priority depending on what
    platform you're on:

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> if psutil.LINUX:
       ...     p.ionice(psutil.IOPRIO_CLASS_RT, value=7)
       ... else:
       ...     p.ionice(psutil.IOPRIO_HIGH)
       ...
       >>> p.ionice()  # get
       pionice(ioclass=<ProcessIOPriority.IOPRIO_CLASS_RT: 1>, value=7)

    .. availability:: Linux, Windows

    .. versionchanged:: 5.6.2
       Windows accepts new :data:`IOPRIO_* <psutil.IOPRIO_VERYLOW>` constants.

    .. versionchanged:: 8.0.0
       *ioclass* is now a :class:`psutil.ProcessIOPriority` enum member.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: rlimit(resource, limits=None)

    Get or set process :term:`resource limits <resource limit>` (see `man prlimit`_).
    *resource* is one of the :data:`psutil.RLIMIT_* <psutil.RLIM_INFINITY>`
    constants.
    *limits* is a ``(soft, hard)`` tuple.
    This is the same as :func:`resource.getrlimit` and :func:`resource.setrlimit`
    but can be used for any process PID, not only :func:`os.getpid`.
    For get, return value is a ``(soft, hard)`` tuple. Each value may be either
    an integer or :data:`psutil.RLIMIT_* <psutil.RLIM_INFINITY>`.
    Also see `scripts/procinfo.py`_ script.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.rlimit(psutil.RLIMIT_NOFILE, (128, 128))   # process can open max 128 file descriptors
       >>> p.rlimit(psutil.RLIMIT_FSIZE, (1024, 1024))  # can create files no bigger than 1024 bytes
       >>> p.rlimit(psutil.RLIMIT_FSIZE)                # get
       (1024, 1024)
       >>>

    .. availability:: Linux, FreeBSD

    .. versionchanged:: 5.7.3
       added FreeBSD support.

  .. method:: io_counters()

    Return process I/O statistics as a named tuple.
    For Linux you can refer to
    `/proc filesystem documentation <https://stackoverflow.com/questions/3633286/>`_.

    All fields are :term:`cumulative counters <cumulative counter>` since process creation.

    - **read_count**: the number of read operations performed.
      This is supposed to count the number of read-related syscalls such as
      ``read()`` and ``pread()`` on UNIX.
    - **write_count**: the number of write operations performed.
      This is supposed to count the number of write-related syscalls such as
      ``write()`` and ``pwrite()`` on UNIX.
    - **read_bytes**: the number of bytes read. Always ``-1`` on BSD.
    - **write_bytes**: the number of bytes written. Always ``-1`` on BSD.

    Linux specific:

    - **read_chars** *(Linux)*: the amount of bytes which this process passed
      to ``read()`` and ``pread()`` syscalls. Differently from *read_bytes*
      it doesn't care whether or not actual physical disk I/O occurred.
    - **write_chars** *(Linux)*: the amount of bytes which this process passed
      to ``write()`` and ``pwrite()`` syscalls. Differently from *write_bytes*
      it doesn't care whether or not actual physical disk I/O occurred.

    Windows specific:

    - **other_count** *(Windows)*: the number of I/O operations performed
      other than read and write operations.
    - **other_bytes** *(Windows)*: the number of bytes transferred during
      operations other than read and write operations.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.io_counters()
       pio(read_count=454556, write_count=3456, read_bytes=110592, write_bytes=0, read_chars=769931, write_chars=203)


    .. availability:: Linux, BSD, Windows, AIX

    .. versionchanged:: 5.2.0
       added *read_chars* + *write_chars* on Linux and *other_count* +
       *other_bytes* on Windows.

  .. method:: num_ctx_switches()

    The number of :term:`context switches <context switch>` performed by this process
    (:term:`cumulative counter`).

    .. note::
      (Windows, macOS) *involuntary* value is always set to 0, while
      *voluntary* value reflect the total number of context switches (voluntary
      + involuntary). This is a limitation of the OS.

    .. versionchanged:: 5.4.1
       added AIX support.

  .. method:: num_fds()

    The number of :term:`file descriptors <file descriptor>` currently opened by this process
    (non cumulative).

    .. availability:: UNIX

  .. method:: num_handles()

    The number of :term:`handles <handle>` currently used by this process (non cumulative).

    .. availability:: Windows

  .. method:: num_threads()

    The number of threads currently used by this process (non cumulative).

  .. method:: threads()

    Return threads opened by process as a list of named tuples. On OpenBSD this
    method requires root privileges.

    - **id**: the native thread ID assigned by the kernel. If :attr:`pid` refers
      to the current process, this matches the
      `native_id <https://docs.python.org/3/library/threading.html#threading.Thread.native_id>`_
      attribute of the :class:`threading.Thread` class, and can be used to reference
      individual Python threads running within your own Python app.
    - **user_time**: time spent in user mode.
    - **system_time**: time spent in kernel mode.

  .. method:: cpu_times()

    Return a named tuple of :term:`cumulative counters <cumulative counter>` (seconds)
    representing the accumulated process CPU times
    (see `explanation <http://stackoverflow.com/questions/556405/>`_).
    This is similar to :func:`os.times` but can be used for any process PID.

    - **user**: time spent in user mode.
    - **system**: time spent in kernel mode.
    - **children_user**: user time of all child processes (always ``0`` on
      Windows and macOS).
    - **children_system**: system time of all child processes (always ``0`` on
      Windows and macOS).
    - **iowait**: (Linux) time spent waiting for blocking I/O to complete (:term:`iowait`).
      This value is excluded from `user` and `system` times count (because the
      CPU is not doing any work).

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.cpu_times()
       pcputimes(user=0.03, system=0.67, children_user=0.0, children_system=0.0, iowait=0.08)
       >>> sum(p.cpu_times()[:2])  # cumulative, excluding children and iowait
       0.70


    .. versionchanged:: 4.1.0
       return two extra fields: *children_user* and *children_system*.

    .. versionchanged:: 5.6.4
       added *iowait* on Linux.

  .. method:: cpu_percent(interval=None)

    Return a float representing the process CPU utilization as a percentage
    which can also be ``> 100.0`` in case of a process running multiple threads
    on different CPUs.
    When *interval* is > ``0.0`` compares process times to system CPU times
    elapsed before and after the interval (blocking). When interval is ``0.0``
    or ``None`` compares process times to system CPU times elapsed since last
    call, returning immediately. That means the first time this is called it
    will return a meaningless ``0.0`` value which you are supposed to ignore.
    For accuracy, it is recommended to call this function a second time with
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
      the first time this method is called with interval = ``0.0`` or
      ``None`` it will return a meaningless ``0.0`` value which you are
      supposed to ignore. See also :ref:`faq_cpu_percent` FAQ.

    .. note::
      the returned value can be > 100.0 in case of a process running multiple
      threads on different CPU cores.

    .. note::
      the returned value is explicitly *not* split evenly between all available
      CPUs (differently from :func:`psutil.cpu_percent`).
      This means that a busy loop process running on a system with 2 logical
      CPUs will be reported as having 100% CPU utilization instead of 50%.
      This was done in order to be consistent with ``top`` UNIX utility,
      and also to make it easier to identify processes hogging CPU resources
      independently from the number of CPUs.
      It must be noted that ``taskmgr.exe`` on Windows does not behave like
      this (it would report 50% usage instead).
      To emulate Windows ``taskmgr.exe`` behavior you can do:
      ``p.cpu_percent() / psutil.cpu_count()``.

  .. method:: cpu_affinity(cpus=None)

    Get or set process current
    `CPU affinity <http://www.linuxjournal.com/article/6799?page=0,0>`_.
    CPU affinity consists in telling the OS to run a process on a limited set
    of CPUs only (on Linux cmdline, ``taskset`` command is typically used).
    If no argument is passed it returns the current CPU affinity as a list
    of integers.
    If passed it must be a list of integers specifying the new CPUs affinity.
    If an empty list is passed all eligible CPUs are assumed (and set).
    On some systems such as Linux this may not necessarily mean all available
    logical CPUs as in ``list(range(psutil.cpu_count()))``).

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
    observe the system workload distributed across multiple CPUs as shown by
    `scripts/cpu_distribution.py`_ example script.

    .. availability:: Linux, FreeBSD, SunOS

    .. versionadded:: 5.1.0

  .. method:: memory_info()

    Return a named tuple with variable fields depending on the platform
    representing memory information about the process.
    The "portable" fields available on all platforms are `rss` and `vms`.
    All numbers are expressed in bytes.

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

    - **rss**: aka :term:`RSS`. The portion of physical memory
      currently held by this process (code, data, stack, and mapped files that
      are resident). Pages swapped out to disk are not counted. On UNIX it
      matches the ``top`` RES column. On Windows it maps to ``WorkingSetSize``.
      See also :ref:`faq_memory_rss_vs_vms` FAQ.

    - **vms**: aka :term:`VMS`. The total address space reserved by
      the process, including pages not yet touched, pages in swap, and
      memory-mapped files not yet accessed. Typically much larger than
      **rss**. On UNIX it matches the ``top`` VIRT column. On Windows this
      maps to ``PrivateUsage`` (private committed pages only), which differs
      from the UNIX definition; use ``virtual`` from :meth:`memory_info_ex`
      for the true virtual address space size.

    - **shared** *(Linux)*: memory backed by a file or device (shared
      libraries, mmap'd files, POSIX shared memory) that *could* be shared
      with other processes. A page is counted here even if no other process
      is currently mapping it. Matches ``top``'s SHR column.

    - **text** *(Linux, BSD)*: aka TRS (Text Resident Set). Resident memory
      devoted to executable code. These pages are read-only and typically
      shared across all processes running the same binary. Matches ``top``'s
      CODE column.

    - **data** *(Linux, BSD)*: aka DRS (Data Resident Set). On Linux this
      covers the data **and** stack segments combined (from
      ``/proc/<pid>/statm``). On BSD it covers the data segment only (see
      **stack**). Matches ``top``'s DATA column.

    - **stack** *(BSD)*: size of the process stack segment. Reported
      separately from **data** (unlike Linux where both are combined).

    - **peak_rss** *(BSD, Windows)*: the highest :term:`RSS` value (high water mark)
      the process has ever reached. See :term:`peak_rss`. On BSD this may be
      ``0`` for kernel PIDs.
      On Windows it maps to ``PeakWorkingSetSize``.

    - **peak_vms** *(Windows)*: peak private committed (page-file-backed)
      virtual memory. Maps to ``PeakPagefileUsage``.

    For the full definitions of Windows fields see
    `PROCESS_MEMORY_COUNTERS_EX`_.

    Example on Linux:

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.memory_info()
       pmem(rss=15491072, vms=84025344, shared=5206016, text=2555904, data=9891840)

    .. versionchanged:: 4.0.0
       multiple fields are returned, not only *rss* and *vms*.

    .. versionchanged:: 8.0.0
       Linux: *lib* and *dirty* removed (always 0 since Linux 2.6). Deprecated
       aliases returning 0 and emitting `DeprecationWarning` are kept.
       See :ref:`migration guide <migration-8.0>`.

    .. versionchanged:: 8.0.0
       macOS: *pfaults* and *pageins* removed with **no backward-compatible
       aliases**. Use :meth:`page_faults` instead.
       See :ref:`migration guide <migration-8.0>`.

    .. versionchanged:: 8.0.0
       Windows: eliminated old aliases: *wset* → *rss*, *peak_wset* →
       *peak_rss*, *pagefile* / *private* → *vms*, *peak_pagefile* →
       *peak_vms*, *num_page_faults* → :meth:`page_faults` method. At the same
       time *paged_pool*, *nonpaged_pool*, *peak_paged_pool*,
       *peak_nonpaged_pool* were moved to :meth:`memory_info_ex`. All these old
       names still work but raise `DeprecationWarning`.
       See :ref:`migration guide <migration-8.0>`.

    .. versionchanged:: 8.0.0
       BSD: added *peak_rss*.

  .. method:: memory_info_ex()

    Return a named tuple extending :meth:`memory_info` with additional
    platform-specific memory metrics. On platforms where extra fields are not
    implemented this returns the same result as :meth:`memory_info`. All
    numbers are expressed in bytes.

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

    - **peak_rss** *(Linux, macOS)*: the highest :term:`RSS` value (high water
      mark) the process has reached since it started. See :term:`peak_rss`.
    - **peak_vms** *(Linux)*: the highest VMS value the process has reached
      since it started.
    - **rss_anon** *(Linux, macOS)*: resident :term:`anonymous memory` pages
      (heap, stack, private mappings) not backed by any file. Set to 0
      on Linux < 4.5.
    - **rss_file** *(Linux, macOS)*: resident file-backed memory; pages mapped
      from files (shared libraries, mmap'd files). Set to 0 on Linux < 4.5.
    - **rss_shmem** *(Linux)*: resident shared memory pages (``tmpfs``,
      ``shm_open``). ``rss_anon + rss_file + rss_shmem`` equals **rss**. Set to
      0 on Linux < 4.5.
    - **wired** *(macOS)*: memory pinned in RAM by the kernel on behalf of this
      process; cannot be compressed or paged out.
    - **swap** *(Linux)*: process memory currently in swap. Equivalent to
      ``memory_footprint().swap`` but cheaper, as it reads from
      ``/proc/<pid>/status`` instead of ``/proc/<pid>/smaps``.
    - **compressed** *(macOS)*: pages held in the in-RAM memory compressor; not
      counted in **rss**. A large value signals memory pressure but has not yet
      triggered swapping.
    - **hugetlb** *(Linux)*: resident memory backed by huge pages. Set to 0 on
      Linux < 4.4.
    - **phys_footprint** *(macOS)*: total physical memory impact including
      compressed pages. What Xcode and ``footprint(1)`` report; prefer this
      over **rss** macOS memory monitoring.
    - **virtual** *(Windows)*: true virtual address space size, including
      reserved-but-uncommitted regions (unlike **vms** in
      :meth:`memory_info`).
    - **peak_virtual** *(Windows)*: peak virtual address space size.
    - **paged_pool** *(Windows)*: kernel memory used for objects created by
      this process (open file handles, registry keys, etc.) that the OS may
      swap to disk under memory pressure.
    - **nonpaged_pool** *(Windows)*: kernel memory used for objects that must
      stay in RAM at all times (I/O request packets, device driver buffers,
      etc.). A large or growing value may indicate a driver memory leak.
    - **peak_paged_pool** *(Windows)*: peak paged-pool usage.
    - **peak_nonpaged_pool** *(Windows)*: peak non-paged-pool usage.

    For the full definitions of Windows fields see
    `PROCESS_MEMORY_COUNTERS_EX`_.

    .. versionadded:: 8.0.0

  .. method:: memory_footprint()

    Return a named tuple with USS, PSS and swap memory metrics. These give
    a more accurate picture of actual memory consumption than
    :meth:`memory_info`, as explained in this
    `blog post <https://gmpy.dev/blog/2016/real-process-memory-and-environ-in-python>`_.
    It works by walking the full process address space, so it is
    considerably slower than :meth:`memory_info` and may require elevated
    privileges.

    - **uss** *(Linux, macOS, Windows)*: aka :term:`USS`. This is the
      memory which is unique to a process and which would be freed if the
      process were terminated right now. The most representative metric for
      actual memory usage.

    - **pss** *(Linux)*: aka :term:`PSS`, is the amount of memory
      shared with other processes, accounted in a way that the amount is
      divided evenly between the processes that share it. I.e. if a process has
      10 MBs all to itself, and 10 MBs shared with another process, its PSS
      will be 15 MBs.

    - **swap** *(Linux)*: process memory currently in swap, counted per-mapping
      (slower, but may be more accurate than ``memory_info_ex().swap``).

    Example on Linux:

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.memory_footprint()
       pfootprint(uss=6545408, pss=6872064, swap=0)

    See also `scripts/procsmem.py`_ for an example application.

    .. versionadded:: 8.0.0

    .. availability:: Linux, macOS, Windows

  .. method:: memory_full_info()

    This deprecated method returns the same information as :meth:`memory_info`
    plus :meth:`memory_footprint` in a single named tuple.

    .. versionadded:: 4.0.0

    .. deprecated:: 8.0.0
       use :meth:`memory_footprint` instead.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: memory_percent(memtype="rss")

    Return process memory usage as a percentage of total physical memory
    (``process.memory_info().rss / virtual_memory().total * 100``).
    *memtype* can be any field name from :meth:`memory_info`,
    :meth:`memory_info_ex`, or :meth:`memory_footprint` and controls which
    memory value is used in the calculation (defaults to ``"rss"``).

    .. versionchanged:: 4.0.0
       added `memtype` parameter.

  .. method:: memory_maps(grouped=True)

    Return process's memory-mapped file regions as a list of named tuples whose
    fields vary by platform (all values in bytes). If *grouped* is ``True``
    regions with the same *path* are merged and their numeric fields summed.
    If *grouped* is ``False`` each region is listed individually and the
    tuple also includes *addr* (address range) and *perms* (permission
    string e.g. ``"r-xp"``).
    See `scripts/pmap.py`_ for an example application.

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

    - **rss**: resident pages in this mapping.
    - **size**: total virtual size; may far exceed **rss** for sparse or
      reserved-but-unaccessed mappings.
    - **pss**: proportional RSS. **rss** divided by the number of processes
      sharing this mapping. Useful for fair per-process accounting.
    - **shared_clean**: shared pages not modified (e.g. shared library code);
      can be dropped from RAM without writing to swap.
    - **shared_dirty**: shared pages that have been written to.
    - **private_clean**: private unmodified pages; can be dropped without
      writing to swap.
    - **private_dirty**: private modified pages; must be written to swap
      before they can be reclaimed. The key indicator of a mapping's real
      memory cost.
    - **referenced**: pages recently accessed.
    - **anonymous**: :term:`anonymous memory` pages not backed by a file (heap, stack allocations).
    - **swap**: pages from this mapping currently in swap.

    FreeBSD fields:

    - **private**: pages in this mapping private to this process.
    - **ref_count**: reference count on the VM object backing this mapping.
    - **shadow_count**: depth of the copy-on-write shadow object chain.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.memory_maps()
       [pmmap_grouped(path='/lib/x8664-linux-gnu/libutil-2.15.so', rss=32768, size=2125824, pss=32768, shared_clean=0, shared_dirty=0, private_clean=20480, private_dirty=12288, referenced=32768, anonymous=12288, swap=0),
        pmmap_grouped(path='/lib/x8664-linux-gnu/libc-2.15.so', rss=3821568, size=3842048, pss=3821568, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=3821568, referenced=3575808, anonymous=3821568, swap=0),
        ...]

    .. availability:: Linux, Windows, FreeBSD, SunOS

    .. versionchanged:: 5.6.0
       removed macOS support because inherently broken (see issue `#1291
       <https://github.com/giampaolo/psutil/issues/1291>`_)

  .. method:: children(recursive=False)

    Return the children of this process as a list of :class:`Process`
    instances.
    If recursive is ``True`` return all the parent descendants.
    Pseudo code example assuming *A == this process*:

    ::

      A ─┐
         │
         ├─ B (child) ─┐
         │             └─ X (grandchild) ─┐
         │                                └─ Y (great grandchild)
         ├─ C (child)
         └─ D (child)

      .. code-block:: pycon

         >>> p.children()
         B, C, D
         >>> p.children(recursive=True)
         B, X, Y, C, D

    Note that in the example above if process X disappears process Y won't be
    returned either as the reference to process A is lost.
    This concept is well illustrated by this
    `unit test <https://github.com/giampaolo/psutil/blob/65a52341b55faaab41f68ebc4ed31f18f0929754/psutil/tests/test_process.py#L1064-L1075>`_.
    See also how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

  .. method:: page_faults()

    Return the number of :term:`page faults <page fault>` for this process as a
    ``(minor, major)`` named tuple.

    - **minor** (a.k.a. *soft* faults): occur when a memory page is not
      currently mapped into the process address space, but is already present
      in physical RAM (e.g. a shared library loaded by another process). The
      kernel resolves these without disk I/O.
    - **major** (a.k.a. *hard* faults): occur when the page must be fetched
      from disk. These are expensive because they stall the process until I/O
      completes.

    Both counters are :term:`cumulative counters <cumulative counter>` since process creation.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process()
       >>> p.page_faults()
       ppagefaults(minor=5905, major=3)

    .. versionadded:: 8.0.0

  .. method:: open_files()

    Return regular files opened by process as a list of named tuples including
    the following fields:

    - **path**: the absolute file name.
    - **fd**: the file descriptor number; on Windows this is always ``-1``.

    Linux only:

    - **position** (*Linux*): the file (offset) position.
    - **mode** (*Linux*): a string indicating how the file was opened, similarly
      to :func:`open` builtin ``mode`` argument.
      Possible values are ``'r'``, ``'w'``, ``'a'``, ``'r+'`` and ``'a+'``.
      There's no distinction between files opened in binary or text mode
      (``"b"`` or ``"t"``).
    - **flags** (*Linux*): the flags which were passed to the underlying
      :func:`os.open` C call when the file was opened (e.g. :data:`os.O_RDONLY`,
      :data:`os.O_TRUNC`, etc).

    .. code-block:: pycon

       >>> import psutil
       >>> f = open('file.ext', 'w')
       >>> p = psutil.Process()
       >>> p.open_files()
       [popenfile(path='/home/giampaolo/svn/psutil/file.ext', fd=3, position=0, mode='w', flags=32769)]


    .. warning::
      on Windows this method is not reliable due to some limitations of the
      underlying Windows API which may hang when retrieving certain file
      handles.
      In order to work around that psutil spawns a thread to determine the file
      handle name and kills it if it's not responding after 100ms.
      That implies that this method on Windows is not guaranteed to enumerate
      all regular file handles (see
      `issue 597 <https://github.com/giampaolo/psutil/pull/597>`_).
      Tools like ProcessHacker have the same limitation.

    .. warning::
      on BSD this method can return files with a null path ("") due to a
      kernel bug, hence it's not reliable
      (see `issue 595 <https://github.com/giampaolo/psutil/pull/595>`_).

    .. versionchanged:: 3.1.0
       no longer hangs on Windows.

    .. versionchanged:: 4.1.0
       new *position*, *mode* and *flags* fields on Linux.

  .. method:: net_connections(kind="inet")

    Return socket connections opened by process as a list of named tuples.
    To get system-wide connections use :func:`psutil.net_connections`.
    Every named tuple provides 6 attributes:

    - **fd**: the socket file descriptor. If the connection refers to the
      current process this may be passed to :func:`socket.fromfd` to obtain a usable
      socket object.
      On Windows, FreeBSD and SunOS this is always set to ``-1``.
    - **family**: the address family, either :data:`socket.AF_INET`, :data:`socket.AF_INET6` or
      :data:`socket.AF_UNIX`.
    - **type**: the address type, either :data:`socket.SOCK_STREAM`, :data:`socket.SOCK_DGRAM` or
      :data:`socket.SOCK_SEQPACKET`.
    - **laddr**: the local address as a ``(ip, port)`` named tuple or a ``path``
      in case of AF_UNIX sockets. For UNIX sockets see notes below.
    - **raddr**: the remote address as a ``(ip, port)`` named tuple or an
      absolute ``path`` in case of UNIX sockets.
      When the remote endpoint is not connected you'll get an empty tuple
      (AF_INET*) or ``""`` (AF_UNIX). For UNIX sockets see notes below.
    - **status**: represents the status of a TCP connection. The return value
      is one of the :data:`psutil.CONN_* <psutil.CONN_ESTABLISHED>` constants.
      For UDP and UNIX sockets this is always going to be
      :const:`psutil.CONN_NONE`.

    The *kind* parameter is a string which filters for connections that fit the
    following criteria:

    +----------------+-----------------------------------------------------+
    | Kind value     | Connections using                                   |
    +================+=====================================================+
    | ``"inet"``     | IPv4 and IPv6                                       |
    +----------------+-----------------------------------------------------+
    | ``"inet4"``    | IPv4                                                |
    +----------------+-----------------------------------------------------+
    | ``"inet6"``    | IPv6                                                |
    +----------------+-----------------------------------------------------+
    | ``"tcp"``      | TCP                                                 |
    +----------------+-----------------------------------------------------+
    | ``"tcp4"``     | TCP over IPv4                                       |
    +----------------+-----------------------------------------------------+
    | ``"tcp6"``     | TCP over IPv6                                       |
    +----------------+-----------------------------------------------------+
    | ``"udp"``      | UDP                                                 |
    +----------------+-----------------------------------------------------+
    | ``"udp4"``     | UDP over IPv4                                       |
    +----------------+-----------------------------------------------------+
    | ``"udp6"``     | UDP over IPv6                                       |
    +----------------+-----------------------------------------------------+
    | ``"unix"``     | UNIX socket (both UDP and TCP protocols)            |
    +----------------+-----------------------------------------------------+
    | ``"all"``      | the sum of all the possible families and protocols  |
    +----------------+-----------------------------------------------------+

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

    .. warning::
      On Linux, retrieving connections for certain processes requires root
      privileges. If psutil is not run as root, those connections are silently
      skipped instead of raising :exc:`psutil.AccessDenied`. That means
      the returned list may be incomplete.

    .. note::
      (Solaris) UNIX sockets are not supported.

    .. note::
       (Linux, FreeBSD) *raddr* field for UNIX sockets is always set to "".
       This is a limitation of the OS.

    .. note::
       (OpenBSD) *laddr* and *raddr* fields for UNIX sockets are always set to
       "". This is a limitation of the OS.

    .. note::
      (AIX) :exc:`psutil.AccessDenied` is always raised unless running
      as root (lsof does the same).

    .. versionchanged:: 5.3.0
       *laddr* and *raddr* are named tuples.

    .. versionchanged:: 6.0.0
       method renamed from `connections` to `net_connections`.

    .. versionchanged:: 8.0.0
       *status* field is now a :class:`psutil.ConnectionStatus` enum member
       instead of a plain ``str``.
       See :ref:`migration guide <migration-8.0>`.

  .. method:: connections()

    Same as :meth:`net_connections` (deprecated).

    .. deprecated:: 6.0.0
       use :meth:`net_connections` instead.

  .. method:: is_running()

    Return whether the current process is running in the current process list.
    Differently from ``psutil.pid_exists(p.pid)``, this is reliable also in
    case the process is gone and its PID reused by another process (:ref:`PID reuse <faq_pid_reuse>`).

    If PID has been reused, this method will also remove the process from
    :func:`process_iter` internal cache.

    .. note::
      this will return ``True`` also if the process is a :term:`zombie process`
      (``p.status() == psutil.STATUS_ZOMBIE``).

    .. versionchanged:: 6.0.0
       automatically remove process from :func:`process_iter` internal cache
       if PID has been reused by another process.

  .. method:: send_signal(signal)

    Send a signal to process (see :mod:`signal` module constants)
    preemptively checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, sig)``.
    On Windows only *SIGTERM*, *CTRL_C_EVENT* and *CTRL_BREAK_EVENT* signals
    are supported and *SIGTERM* is treated as an alias for :meth:`kill`.
    See also how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

    .. versionchanged:: 3.2.0
       support for CTRL_C_EVENT and CTRL_BREAK_EVENT signals on Windows was
       added.

  .. method:: suspend()

    Suspend process execution with *SIGSTOP* signal preemptively
    checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGSTOP)``.
    On Windows this is done by suspending all process threads execution.

  .. method:: resume()

    Resume process execution with *SIGCONT* signal preemptively
    checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGCONT)``.
    On Windows this is done by resuming all process threads execution.

  .. method:: terminate()

    Terminate the process with *SIGTERM* signal preemptively checking
    whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGTERM)``.
    On Windows this is an alias for :meth:`kill`.
    See also how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

  .. method:: kill()

    Kill the current process by using *SIGKILL* signal preemptively
    checking whether PID has been reused.
    On UNIX this is the same as ``os.kill(pid, signal.SIGKILL)``.
    On Windows this is done by using `TerminateProcess`_.
    See also how to :ref:`kill a process tree <recipe_kill_proc_tree>`.

  .. method:: wait(timeout=None)

    Wait for a process PID to terminate. The details about the return value
    differ on UNIX and Windows.

    *On UNIX*: if the process terminated normally, the return value is a
    positive integer >= 0 indicating the exit code.
    If the process was terminated by a signal return the negated value of the
    signal which caused the termination (e.g. ``-SIGTERM``).
    If PID is not a child of :func:`os.getpid` (current process) just wait until
    the process disappears and return ``None``.
    If PID does not exist return ``None`` immediately.

    *On Windows*: always return the exit code, which is a positive integer as
    returned by `GetExitCodeProcess`_.

    *timeout* is expressed in seconds. If specified and the process is still
    alive raise :exc:`TimeoutExpired` exception.
    ``timeout=0`` can be used in non-blocking apps: it will either return
    immediately or raise :exc:`TimeoutExpired`.

    The return value is cached.
    To wait for multiple processes use :func:`psutil.wait_procs`.

    .. code-block:: pycon

       >>> import psutil
       >>> p = psutil.Process(9891)
       >>> p.terminate()
       >>> p.wait()
       <Negsignal.SIGTERM: -15>

    .. note::

      When ``timeout`` is not ``None`` and the platform supports it, an
      efficient event-driven mechanism is used to wait for process termination:

      - Linux >= 5.3 with Python >= 3.9 uses :func:`os.pidfd_open` + :func:`select.poll`
      - macOS and other BSD variants use :func:`select.kqueue` + ``KQ_FILTER_PROC``
        + ``KQ_NOTE_EXIT``
      - Windows uses `WaitForSingleObject`_

      If none of these mechanisms are available, the function falls back to a
      busy loop (non-blocking call and short sleeps).

    .. versionchanged:: 5.7.2
       if *timeout* is not ``None``, use efficient event-driven implementation
       on Linux >= 5.3 and macOS / BSD.

    .. versionchanged:: 5.7.1
       return value is cached (instead of returning ``None``).

    .. versionchanged:: 5.7.1
       on POSIX, in case of negative signal, return it as a human readable
       :mod:`enum`.

    .. versionchanged:: 7.2.2
       on Linux >= 5.3 + Python >= 3.9 and macOS/BSD, use :func:`os.pidfd_open` and
       :func:`select.kqueue` respectively, instead of less efficient busy-loop
       polling. Later added to CPython 3.15 in `GH-144047`_.

----

Popen class
^^^^^^^^^^^

.. class:: Popen(*args, **kwargs)

  Same as :class:`subprocess.Popen` but in addition it provides all
  :class:`psutil.Process` methods in a single class.
  For the following methods which are common to both classes, psutil
  implementation takes precedence:
  :meth:`send_signal() <psutil.Process.send_signal()>`,
  :meth:`terminate() <psutil.Process.terminate()>`,
  :meth:`kill() <psutil.Process.kill()>`.
  This is done in order to avoid killing another process in case its PID has
  been reused, fixing `BPO-6973`_.

  .. code-block:: pycon

     >>> import psutil
     >>> from subprocess import PIPE
     >>>
     >>> p = psutil.Popen(["/usr/bin/python", "-c", "print('hello')"], stdout=PIPE)
     >>> p.name()
     'python'
     >>> p.username()
     'giampaolo'
     >>> p.communicate()
     ('hello\n', None)
     >>> p.wait(timeout=2)
     0
     >>>


  .. versionchanged:: 4.4.0
     added context manager support.

----

C heap introspection
--------------------

The following functions provide direct access to the platform's native C heap
allocator (such as glibc's ``malloc`` on Linux or ``jemalloc`` on BSD). They
are low-level interfaces intended for detecting memory leaks in C extensions,
which are usually not revealed via standard RSS/VMS metrics. These functions do
not reflect Python object memory; they operate solely on allocations made in C
via ``malloc()``, ``free()``, and related calls.

The general idea behind these functions is straightforward: capture the state
of the C heap before and after repeatedly invoking a function implemented in a
C extension, and compare the results. If ``heap_used`` or ``mmap_used`` grows
steadily across iterations, the C code is likely retaining memory it should be
releasing. This provides an allocator-level way to spot native leaks that
Python's memory tracking misses.

.. tip::

  Check out `psleak`_ project to see a practical example of how these APIs can be
  used to detect memory leaks in C extensions.

.. function:: heap_info()

  Return low-level heap statistics from the system's C allocator. On Linux,
  this exposes ``uordblks`` and ``hblkhd`` fields from glibc's `mallinfo2`_.
  Returns a named tuple containing:

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
  the heap (typically small ``malloc()`` allocations).

  In practice, modern allocators rarely comply, so this is not a
  general-purpose memory-reduction tool and won't meaningfully shrink RSS in
  real programs. Its primary value is in **leak detection tools**.

  Calling ``heap_trim()`` before taking measurements helps reduce allocator
  noise, giving you a cleaner baseline so that changes in ``heap_used`` come
  from the code you're testing, not from internal allocator caching or
  fragmentation. Its effectiveness depends on allocator behavior and
  fragmentation patterns.

  .. availability:: Linux with glibc, Windows, macOS, FreeBSD, NetBSD

  .. versionadded:: 7.2.0

----

Windows services
----------------

.. function:: win_service_iter()

  Return an iterator yielding a :class:`WindowsService` class instance for all
  Windows services installed.

  .. versionadded:: 4.2.0

  .. availability:: Windows

.. function:: win_service_get(name)

  Get a Windows service by name, returning a :class:`WindowsService` instance.
  Raise :exc:`psutil.NoSuchProcess` if no service with such name exists.

  .. versionadded:: 4.2.0

  .. availability:: Windows

.. class:: WindowsService

  Represents a Windows service with the given *name*. This class is returned
  by :func:`win_service_iter` and :func:`win_service_get` functions and it is
  not supposed to be instantiated directly.

  .. method:: name()

    The service name. This string is how a service is referenced and can be
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

    A string which can either be `"automatic"`, `"manual"` or `"disabled"`.

  .. method:: pid()

    The process PID, if any, else `None`. This can be passed to
    :class:`Process` class to control the service's process.

  .. method:: status()

    Service status as a string, which may be either `"running"`, `"paused"`,
    `"start_pending"`, `"pause_pending"`, `"continue_pending"`,
    `"stop_pending"` or `"stopped"`.

  .. method:: description()

    Service long description.

  .. method:: as_dict()

    Utility method retrieving all the information above as a dictionary.

  Example code:

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

----

Constants
---------

The following enum classes group related constants and are useful for type
annotations and introspection. The individual constants (e.g.
:data:`psutil.STATUS_RUNNING`) are also accessible directly from the psutil
namespace as aliases for the enum members and should be preferred over
accessing them via the enum class (e.g. prefer ``psutil.STATUS_RUNNING`` over
``psutil.ProcessStatus.STATUS_RUNNING``).

.. class:: psutil.ProcessStatus

  :class:`enum.StrEnum` collection of :data:`STATUS_* <psutil.STATUS_RUNNING>`
  constants. Returned by :meth:`Process.status`.

  .. versionadded:: 8.0.0

.. class:: psutil.ProcessPriority

  :class:`enum.IntEnum` collection of
  :data:`*_PRIORITY_CLASS <psutil.ABOVE_NORMAL_PRIORITY_CLASS>` constants for
  :meth:`Process.nice` on Windows.

  .. availability:: Windows

  .. versionadded:: 8.0.0

.. class:: psutil.ProcessIOPriority

  :class:`enum.IntEnum` collection of I/O priority constants for
  :meth:`Process.ionice`.

  :data:`IOPRIO_CLASS_* <psutil.IOPRIO_CLASS_NONE>` on Linux,
  :data:`IOPRIO_* <psutil.IOPRIO_VERYLOW>` on Windows.

  .. availability:: Linux, Windows

  .. versionadded:: 8.0.0

.. class:: psutil.ProcessRlimit

  :class:`enum.IntEnum` collection of :data:`RLIMIT_* <psutil.RLIMIT_NOFILE>`
  constants for :meth:`Process.rlimit`.

  .. availability:: Linux, FreeBSD

  .. versionadded:: 8.0.0

.. class:: psutil.ConnectionStatus

  :class:`enum.StrEnum` collection of :data:`CONN_* <psutil.CONN_ESTABLISHED>`
  constants. Returned in the *status* field of
  :func:`psutil.net_connections` and :meth:`Process.net_connections`.

  .. versionadded:: 8.0.0

.. class:: psutil.NicDuplex

  :class:`enum.IntEnum` collection of :data:`NIC_DUPLEX_* <psutil.NIC_DUPLEX_FULL>`
  constants. Returned in the *duplex* field of :func:`psutil.net_if_stats`.

  .. versionadded:: 3.0.0

.. class:: psutil.BatteryTime

  :class:`enum.IntEnum` collection of :data:`POWER_TIME_* <psutil.POWER_TIME_UNKNOWN>`
  constants. May appear in the *secsleft* field of :func:`psutil.sensors_battery`.

  .. versionadded:: 5.1.0

Operating system constants
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _const-oses:

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

  ``bool`` constants which define what platform you're on. E.g. if on Windows,
  :const:`WINDOWS` constant will be ``True``, all others will be ``False``.

  .. versionadded:: 4.0.0

  .. versionchanged:: 5.4.0
     added AIX.

.. data:: OSX

  Alias for :const:`MACOS`.

  .. deprecated:: 5.4.7
     use :const:`MACOS` instead.

Process status constants
^^^^^^^^^^^^^^^^^^^^^^^^

.. _const-pstatus:

.. data:: STATUS_RUNNING
.. data:: STATUS_SLEEPING
.. data:: STATUS_DISK_SLEEP
.. data:: STATUS_STOPPED
.. data:: STATUS_TRACING_STOP
.. data:: STATUS_ZOMBIE
.. data:: STATUS_DEAD
.. data:: STATUS_WAKE_KILL
.. data:: STATUS_WAKING
.. data:: STATUS_PARKED (Linux)
.. data:: STATUS_IDLE (Linux, macOS, FreeBSD)
.. data:: STATUS_LOCKED (FreeBSD)
.. data:: STATUS_WAITING (FreeBSD)
.. data:: STATUS_SUSPENDED (NetBSD)

  Represent a process status. Returned by :meth:`Process.status`.
  These constants are members of the :class:`psutil.ProcessStatus` enum.

  .. versionadded:: 3.4.1 ``STATUS_SUSPENDED`` (NetBSD)

  .. versionadded:: 5.4.7 ``STATUS_PARKED`` (Linux)

  .. versionchanged:: 8.0.0
     constants are now :class:`psutil.ProcessStatus` enum members (were plain
     strings).
     See :ref:`migration guide <migration-8.0>`.

Process priority constants
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _const-prio:

.. data:: REALTIME_PRIORITY_CLASS
.. data:: HIGH_PRIORITY_CLASS
.. data:: ABOVE_NORMAL_PRIORITY_CLASS
.. data:: NORMAL_PRIORITY_CLASS
.. data:: IDLE_PRIORITY_CLASS
.. data:: BELOW_NORMAL_PRIORITY_CLASS

  Represent the priority of a process on Windows (see `SetPriorityClass`_).
  They can be used in conjunction with :meth:`Process.nice` to get or
  set process priority.
  These constants are members of the :class:`psutil.ProcessPriority` enum.

  .. availability:: Windows

  .. versionchanged:: 8.0.0
     constants are now :class:`psutil.ProcessPriority` enum members (were plain
     integers).
     See :ref:`migration guide <migration-8.0>`.

.. _const-ioprio-linux:

.. data:: IOPRIO_CLASS_NONE
.. data:: IOPRIO_CLASS_RT
.. data:: IOPRIO_CLASS_BE
.. data:: IOPRIO_CLASS_IDLE

  A set of integers representing the I/O priority of a process on Linux. They
  can be used in conjunction with :meth:`Process.ionice` to get or set
  process I/O priority.
  These constants are members of the :class:`psutil.ProcessIOPriority`
  enum.
  :const:`IOPRIO_CLASS_NONE` and :const:`IOPRIO_CLASS_BE` (best effort) is the
  default for any process that hasn't set a specific I/O priority.
  :const:`IOPRIO_CLASS_RT` (real time) means the process is given first access
  to the disk, regardless of what else is going on in the system.
  :const:`IOPRIO_CLASS_IDLE` means the process will get I/O time when no-one else
  needs the disk.
  For further information refer to manuals of
  `ionice <http://linux.die.net/man/1/ionice>`_ command line utility or
  `ioprio_get`_ system call.

  .. availability:: Linux

  .. versionchanged:: 8.0.0
     constants are now :class:`psutil.ProcessIOPriority` enum members
     (previously ``IOPriority`` enum).
     See :ref:`migration guide <migration-8.0>`.

.. _const-ioprio-windows:

.. data:: IOPRIO_VERYLOW
.. data:: IOPRIO_LOW
.. data:: IOPRIO_NORMAL
.. data:: IOPRIO_HIGH

  A set of integers representing the I/O priority of a process on Windows.
  They can be used in conjunction with :meth:`Process.ionice` to get
  or set process I/O priority.
  These constants are members of the :class:`psutil.ProcessIOPriority`
  enum.

  .. availability:: Windows

  .. versionadded:: 5.6.2

  .. versionchanged:: 8.0.0
     constants are now :class:`psutil.ProcessIOPriority` enum members
     (previously ``IOPriority`` enum).
     See :ref:`migration guide <migration-8.0>`.

Process resource constants
^^^^^^^^^^^^^^^^^^^^^^^^^^

.. _const-rlimit:

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
  .. data:: RLIMIT_SBSIZE
  .. data:: RLIMIT_NPTS

Constants used for getting and setting process resource limits to be used in
conjunction with :meth:`Process.rlimit`. See :func:`resource.getrlimit`
for further information.
These constants are members of the :class:`psutil.ProcessRlimit` enum.

.. availability:: Linux, FreeBSD

.. versionchanged:: 5.7.3
   added FreeBSD support, added ``RLIMIT_SWAP``, ``RLIMIT_SBSIZE``,
   ``RLIMIT_NPTS``.

.. versionchanged:: 8.0.0
   constants are now :class:`psutil.ProcessRlimit` enum members (were plain
   integers).
   See :ref:`migration guide <migration-8.0>`.

Connections constants
^^^^^^^^^^^^^^^^^^^^^

.. _const-conn:

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

  A set of strings representing the status of a TCP connection.
  Returned by :meth:`Process.net_connections` and
  :func:`psutil.net_connections` (`status` field).
  These constants are members of the :class:`psutil.ConnectionStatus` enum.

  .. versionchanged:: 8.0.0
     constants are now :class:`psutil.ConnectionStatus` enum members (were
     plain strings).
     See :ref:`migration guide <migration-8.0>`.

Hardware constants
^^^^^^^^^^^^^^^^^^

.. _const-aflink:

.. data:: AF_LINK

  Constant which identifies a MAC address associated with a network interface.
  To be used in conjunction with :func:`psutil.net_if_addrs`.

  .. versionadded:: 3.0.0

.. _const-duplex:

.. data:: NIC_DUPLEX_FULL
.. data:: NIC_DUPLEX_HALF
.. data:: NIC_DUPLEX_UNKNOWN

  Constants which identifies whether a :term:`NIC` (network interface card) has
  full or half mode speed. NIC_DUPLEX_FULL means the NIC is able to send and
  receive data (files) simultaneously, NIC_DUPLEX_HALF means the NIC can either
  send or receive data at a time.
  To be used in conjunction with :func:`psutil.net_if_stats`.

  .. versionadded:: 3.0.0

.. _const-power:

.. data:: POWER_TIME_UNKNOWN
.. data:: POWER_TIME_UNLIMITED

  Whether the remaining time of the battery cannot be determined or is
  unlimited.
  May be assigned to :func:`psutil.sensors_battery`'s *secsleft* field.

  .. versionadded:: 5.1.0

Other constants
^^^^^^^^^^^^^^^

.. _const-procfs_path:

.. data:: PROCFS_PATH

  The path of the /proc filesystem on Linux, Solaris and AIX (defaults to
  ``"/proc"``).
  You may want to re-set this constant right after importing psutil in case
  your /proc filesystem is mounted elsewhere or if you want to retrieve
  information about Linux containers such as Docker, Heroku or LXC (see
  `here <https://fabiokung.com/2014/03/13/memory-inside-linux-containers/>`_
  for more info).
  It must be noted that this trick works only for APIs which rely on /proc
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

  A tuple to check psutil installed version. Example:

  .. code-block:: pycon

     >>> import psutil
     >>> if psutil.version_info >= (4, 5):
     ...    pass

.. _`ioprio_get`: https://linux.die.net/man/2/ioprio_get
.. _`iostats doc`: https://www.kernel.org/doc/Documentation/iostats.txt
.. _`mallinfo2`: https://man7.org/linux/man-pages/man3/mallinfo.3.html
.. _`man prlimit`: https://linux.die.net/man/2/prlimit
.. _`psleak`: https://github.com/giampaolo/psleak
.. _`/proc/meminfo`: https://man7.org/linux/man-pages/man5/proc_meminfo.5.html

.. === scripts

.. _`scripts/battery.py`: https://github.com/giampaolo/psutil/blob/master/scripts/battery.py
.. _`scripts/cpu_distribution.py`: https://github.com/giampaolo/psutil/blob/master/scripts/cpu_distribution.py
.. _`scripts/disk_usage.py`: https://github.com/giampaolo/psutil/blob/master/scripts/disk_usage.py
.. _`scripts/fans.py`: https://github.com/giampaolo/psutil/blob/master/scripts/fans.py
.. _`scripts/ifconfig.py`: https://github.com/giampaolo/psutil/blob/master/scripts/ifconfig.py
.. _`scripts/iotop.py`: https://github.com/giampaolo/psutil/blob/master/scripts/iotop.py
.. _`scripts/meminfo.py`: https://github.com/giampaolo/psutil/blob/master/scripts/meminfo.py
.. _`scripts/netstat.py`: https://github.com/giampaolo/psutil/blob/master/scripts/netstat.py
.. _`scripts/nettop.py`: https://github.com/giampaolo/psutil/blob/master/scripts/nettop.py
.. _`scripts/pmap.py`: https://github.com/giampaolo/psutil/blob/master/scripts/pmap.py
.. _`scripts/procinfo.py`: https://github.com/giampaolo/psutil/blob/master/scripts/procinfo.py
.. _`scripts/procsmem.py`: https://github.com/giampaolo/psutil/blob/master/scripts/procsmem.py
.. _`scripts/sensors.py`: https://github.com/giampaolo/psutil/blob/master/scripts/sensors.py
.. _`scripts/temperatures.py`: https://github.com/giampaolo/psutil/blob/master/scripts/temperatures.py

.. === Windows API

.. _`GetExitCodeProcess`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getexitcodeprocess
.. _`GetPerformanceInfo`: https://learn.microsoft.com/en-us/windows/win32/api/psapi/nf-psapi-getperformanceinfo
.. _`GetPriorityClass`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-getpriorityclass
.. _`PROCESS_MEMORY_COUNTERS_EX`: https://learn.microsoft.com/en-us/windows/win32/api/psapi/ns-psapi-process_memory_counters_ex
.. _`SetPriorityClass`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-setpriorityclass
.. _`TerminateProcess`: https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-terminateprocess
.. _`WaitForSingleObject`: https://learn.microsoft.com/en-us/windows/win32/api/synchapi/nf-synchapi-waitforsingleobject
