.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola' <grodola@gmail.com>

.. warning::

   This documentation refers to new 2.X version of psutil.
   Instructions on how to port existing 1.2.1 code are
   `here <http://grodola.blogspot.com/2014/01/psutil-20-porting.html>`__.
   Old 1.2.1 documentation is still available
   `here <https://code.google.com/p/psutil/wiki/Documentation>`__.

psutil documentation
====================

Quick links
-----------

* `Home page <http://code.google.com/p/psutil>`__
* `Blog <http://grodola.blogspot.com/search/label/psutil>`__
* `Download <https://pypi.python.org/pypi?:action=display&name=psutil#downloads>`__
* `Forum <http://groups.google.com/group/psutil/topics>`__
* `What's new <https://psutil.googlecode.com/hg/HISTORY>`__

About
-----

From project's home page:

  psutil (python system and process utilities) is a cross-platform library for
  retrieving information on running
  **processes** and **system utilization** (CPU, memory, disks, network) in
  **Python**.
  It is useful mainly for **system monitoring**, **profiling** and **limiting
  process resources** and **management of running processes**.
  It implements many functionalities offered by command line tools
  such as: *ps, top, lsof, netstat, ifconfig, who, df, kill, free, nice,
  ionice, iostat, iotop, uptime, pidof, tty, taskset, pmap*.
  It currently supports **Linux, Windows, OSX, FreeBSD** and **Sun Solaris**,
  both **32-bit** and **64-bit** architectures, with Python versions from
  **2.4** to **3.4**.
  `Pypy <http://pypy.org/>`__ is also known to work.

The psutil documentation you're reading is distributed as a single HTML page.

System related functions
========================

CPU
---

.. function:: cpu_times(percpu=False)

  Return system CPU times as a namedtuple.
  Every attribute represents the seconds the CPU has spent in the given mode.
  The attributes availability varies depending on the platform:

  - **user**
  - **system**
  - **idle**
  - **nice** *(UNIX)*
  - **iowait** *(Linux)*
  - **irq** *(Linux, FreeBSD)*
  - **softirq** *(Linux)*
  - **steal** *(Linux 2.6.11+)*
  - **guest** *(Linux 2.6.24+)*
  - **guest_nice** *(Linux 3.2.0+)*

  When *percpu* is ``True`` return a list of nameduples for each logical CPU
  on the system.
  First element of the list refers to first CPU, second element to second CPU
  and so on.
  The order of the list is consistent across calls.
  Example output on Linux:

    >>> import psutil
    >>> psutil.cpu_times()
    scputimes(user=17411.7, nice=77.99, system=3797.02, idle=51266.57, iowait=732.58, irq=0.01, softirq=142.43, steal=0.0, guest=0.0, guest_nice=0.0)

.. function:: cpu_percent(interval=None, percpu=False)

  Return a float representing the current system-wide CPU utilization as a
  percentage. When *interval* is > ``0.0`` compares system CPU times elapsed
  before and after the interval (blocking).
  When *interval* is ``0.0`` or ``None`` compares system CPU times elapsed
  since last call or module import, returning immediately.
  That means the first time this is called it will return a meaningless ``0.0``
  value which you are supposed to ignore.
  In this case is recommended for accuracy that this function be called with at
  least ``0.1`` seconds between calls.
  When *percpu* is ``True`` returns a list of floats representing the
  utilization as a percentage for each CPU.
  First element of the list refers to first CPU, second element to second CPU
  and so on. The order of the list is consistent across calls.

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

  .. warning::

    the first time this function is called with *interval* = ``0.0`` or ``None``
    it will return a meaningless ``0.0`` value which you are supposed to
    ignore.

.. function:: cpu_times_percent(interval=None, percpu=False)

  Same as :func:`cpu_percent()` but provides utilization percentages for each
  specific CPU time as is returned by
  :func:`psutil.cpu_times(percpu=True)<cpu_times()>`.
  *interval* and
  *percpu* arguments have the same meaning as in :func:`cpu_percent()`.

  .. warning::

    the first time this function is called with *interval* = ``0.0`` or
    ``None`` it will return a meaningless ``0.0`` value which you are supposed
    to ignore.

.. function:: cpu_count(logical=True)

    Return the number of logical CPUs in the system (same as
    `os.cpu_count() <http://docs.python.org/3/library/os.html#os.cpu_count>`__
    in Python 3.4).
    If *logical* is ``False`` return the number of physical cores only (hyper
    thread CPUs are excluded). Return ``None`` if undetermined.

      >>> import psutil
      >>> psutil.cpu_count()
      4
      >>> psutil.cpu_count(logical=False)
      2
      >>>

Memory
------

.. function:: virtual_memory()

  Return statistics about system memory usage as a namedtuple including the
  following fields, expressed in bytes:

  - **total**: total physical memory available.
  - **available**: the actual amount of available memory that can be given
    instantly to processes that request more memory in bytes; this is
    calculated by summing different memory values depending on the platform
    (e.g. free + buffers + cached on Linux) and it is supposed to be used to
    monitor actual memory usage in a cross platform fashion.
  - **percent**: the percentage usage calculated as
    ``(total - available) / total * 100``.
  - **used**: memory used, calculated differently depending on the platform and
    designed for informational purposes only.
  - **free**: memory not being used at all (zeroed) that is readily available;
    note that this doesn't reflect the actual memory available (use 'available'
    instead).

  Platform-specific fields:

  - **active**: (UNIX): memory currently in use or very recently used, and so
    it is in RAM.
  - **inactive**: (UNIX): memory that is marked as not used.
  - **buffers**: (Linux, BSD): cache for things like file system metadata.
  - **cached**: (Linux, BSD): cache for various things.
  - **wired**: (BSD, OSX): memory that is marked to always stay in RAM. It is
    never moved to disk.
  - **shared**: (BSD): memory that may be simultaneously accessed by multiple
    processes.

  The sum of **used** and **available** does not necessarily equal **total**.
  On Windows **available** and **free** are the same.
  See `examples/meminfo.py <http://code.google.com/p/psutil/source/browse/examples/meminfo.py>`__
  script providing an example on how to convert bytes in a human readable form.

    >>> import psutil
    >>> mem = psutil.virtual_memory()
    >>> mem
    svmem(total=8374149120L, available=1247768576L, percent=85.1, used=8246628352L, free=127520768L, active=3208777728, inactive=1133408256, buffers=342413312L, cached=777834496)
    >>>
    >>> THRESHOLD = 100 * 1024 * 1024  # 100MB
    >>> if mem.available <= THRESHOLD:
    ...     print("warning")
    ...
    >>>


.. function:: swap_memory()

  Return system swap memory statistics as a namedtuple including the following
  fields:

  * **total**: total swap memory in bytes
  * **used**: used swap memory in bytes
  * **free**: free swap memory in bytes
  * **percent**: the percentage usage
  * **sin**: the number of bytes the system has swapped in from disk
    (cumulative)
  * **sout**: the number of bytes the system has swapped out from disk
    (cumulative)

  **sin** and **sout** on Windows are meaningless and are always set to ``0``.
  See `examples/meminfo.py <http://code.google.com/p/psutil/source/browse/examples/meminfo.py>`__
  script providing an example on how to convert bytes in a human readable form.

    >>> import psutil
    >>> psutil.swap_memory()
    sswap(total=2097147904L, used=886620160L, free=1210527744L, percent=42.3, sin=1050411008, sout=1906720768)

Disks
-----

.. function:: disk_partitions(all=False)

  Return all mounted disk partitions as a list of namedtuples including device,
  mount point and filesystem type, similarly to "df" command on UNIX. If *all*
  parameter is ``False`` return physical devices only (e.g. hard disks, cd-rom
  drives, USB keys) and ignore all others (e.g. memory partitions such as
  `/dev/shm <http://www.cyberciti.biz/tips/what-is-devshm-and-its-practical-usage.html>`__).
  Namedtuple's **fstype** field is a string which varies depending on the
  platform.
  On Linux it can be one of the values found in /proc/filesystems (e.g.
  ``'ext3'`` for an ext3 hard drive o ``'iso9660'`` for the CD-ROM drive).
  On Windows it is determined via
  `GetDriveType <http://msdn.microsoft.com/en-us/library/aa364939(v=vs.85).aspx>`__
  and can be either ``"removable"``, ``"fixed"``, ``"remote"``, ``"cdrom"``,
  ``"unmounted"`` or ``"ramdisk"``. On OSX and FreeBSD it is retrieved via
  `getfsstat(2) <http://www.manpagez.com/man/2/getfsstat/>`__. See
  `disk_usage.py <http://code.google.com/p/psutil/source/browse/examples/disk_usage.py>`__
  script providing an example usage.

    >>> import psutil
    >>> psutil.disk_partitions()
    [sdiskpart(device='/dev/sda3', mountpoint='/', fstype='ext4', opts='rw,errors=remount-ro'),
     sdiskpart(device='/dev/sda7', mountpoint='/home', fstype='ext4', opts='rw')]

.. function:: disk_usage(path)

  Return disk usage statistics about the given *path* as a namedtuple including
  **total**, **used** and **free** space expressed in bytes, plus the
  **percentage** usage.
  `OSError <http://docs.python.org/3/library/exceptions.html#OSError>`__ is
  raised if *path* does not exist. See
  `examples/disk_usage.py <http://code.google.com/p/psutil/source/browse/examples/disk_usage.py>`__
  script providing an example usage. Starting from
  `Python 3.3 <http://bugs.python.org/issue12442>`__  this is also
  available as
  `shutil.disk_usage() <http://docs.python.org/3/library/shutil.html#shutil.disk_usage>`__.
  See
  `disk_usage.py <http://code.google.com/p/psutil/source/browse/examples/disk_usage.py>`__
  script providing an example usage.

    >>> import psutil
    >>> psutil.disk_usage('/')
    sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)

.. function:: disk_io_counters(perdisk=False)

  Return system-wide disk I/O statistics as a namedtuple including the
  following fields:

  - **read_count**: number of reads
  - **write_count**: number of writes
  - **read_bytes**: number of bytes read
  - **write_bytes**: number of bytes written
  - **read_time**: time spent reading from disk (in milliseconds)
  - **write_time**: time spent writing to disk (in milliseconds)

  If *perdisk* is ``True`` return the same information for every physical disk
  installed on the system as a dictionary with partition names as the keys and
  the namedutuple described above as the values.
  See `examples/iotop.py <http://code.google.com/p/psutil/source/browse/examples/iotop.py>`__
  for an example application.

    >>> import psutil
    >>> psutil.disk_io_counters()
    sdiskio(read_count=8141, write_count=2431, read_bytes=290203, write_bytes=537676, read_time=5868, write_time=94922)
    >>>
    >>> psutil.disk_io_counters(perdisk=True)
    {'sda1': sdiskio(read_count=920, write_count=1, read_bytes=2933248, write_bytes=512, read_time=6016, write_time=4),
     'sda2': sdiskio(read_count=18707, write_count=8830, read_bytes=6060, write_bytes=3443, read_time=24585, write_time=1572),
     'sdb1': sdiskio(read_count=161, write_count=0, read_bytes=786432, write_bytes=0, read_time=44, write_time=0)}

Network
-------

.. function:: net_io_counters(pernic=False)

  Return system-wide network I/O statistics as a namedtuple including the
  following attributes:

  - **bytes_sent**: number of bytes sent
  - **bytes_recv**: number of bytes received
  - **packets_sent**: number of packets sent
  - **packets_recv**: number of packets received
  - **errin**: total number of errors while receiving
  - **errout**: total number of errors while sending
  - **dropin**: total number of incoming packets which were dropped
  - **dropout**: total number of outgoing packets which were dropped (always 0
    on OSX and BSD)

  If *pernic* is ``True`` return the same information for every network
  interface installed on the system as a dictionary with network interface
  names as the keys and the namedtuple described above as the values.
  See `examples/nettop.py <http://code.google.com/p/psutil/source/browse/examples/nettop.py>`__
  for an example application.

    >>> import psutil
    >>> psutil.net_io_counters()
    snetio(bytes_sent=14508483, bytes_recv=62749361, packets_sent=84311, packets_recv=94888, errin=0, errout=0, dropin=0, dropout=0)
    >>>
    >>> psutil.net_io_counters(pernic=True)
    {'lo': snetio(bytes_sent=547971, bytes_recv=547971, packets_sent=5075, packets_recv=5075, errin=0, errout=0, dropin=0, dropout=0),
    'wlan0': snetio(bytes_sent=13921765, bytes_recv=62162574, packets_sent=79097, packets_recv=89648, errin=0, errout=0, dropin=0, dropout=0)}

.. function:: net_connections(kind='inet')

  Return system-wide socket connections as a list of namedutples.
  Every namedtuple provides 7 attributes:

  - **fd**: the socket file descriptor, if retrievable, else ``-1``.
    If the connection refers to the current process this may be passed to
    `socket.fromfd() <http://docs.python.org/library/socket.html#socket.fromfd>`__
    to obtain a usable socket object.
  - **family**: the address family, either `AF_INET
    <http://docs.python.org//library/socket.html#socket.AF_INET>`__,
    `AF_INET6 <http://docs.python.org//library/socket.html#socket.AF_INET6>`__
    or `AF_UNIX <http://docs.python.org//library/socket.html#socket.AF_UNIX>`__.
  - **type**: the address type, either `SOCK_STREAM
    <http://docs.python.org//library/socket.html#socket.SOCK_STREAM>`__ or
    `SOCK_DGRAM
    <http://docs.python.org//library/socket.html#socket.SOCK_DGRAM>`__.
  - **laddr**: the local address as a ``(ip, port)`` tuple or a ``path``
    in case of AF_UNIX sockets.
  - **raddr**: the remote address as a ``(ip, port)`` tuple or an absolute
    ``path`` in case of UNIX sockets.
    When the remote endpoint is not connected you'll get an empty tuple
    (AF_INET*) or ``None`` (AF_UNIX).
    On Linux AF_UNIX sockets will always have this set to ``None``.
  - **status**: represents the status of a TCP connection. The return value
    is one of the :data:`psutil.CONN_* <psutil.CONN_ESTABLISHED>` constants
    (a string).
    For UDP and UNIX sockets this is always going to be
    :const:`psutil.CONN_NONE`.
  - **pid**: the PID of the process which opened the socket, if retrievable,
    else ``None``. On some platforms (e.g. Linux) the availability of this
    field changes depending on process privileges (root is needed).

  The *kind* parameter is a string which filters for connections that fit the
  following criteria:

  .. table::

   +----------------+-----------------------------------------------------+
   | **Kind value** | **Connections using**                               |
   +================+=====================================================+
   | "inet"         | IPv4 and IPv6                                       |
   +----------------+-----------------------------------------------------+
   | "inet4"        | IPv4                                                |
   +----------------+-----------------------------------------------------+
   | "inet6"        | IPv6                                                |
   +----------------+-----------------------------------------------------+
   | "tcp"          | TCP                                                 |
   +----------------+-----------------------------------------------------+
   | "tcp4"         | TCP over IPv4                                       |
   +----------------+-----------------------------------------------------+
   | "tcp6"         | TCP over IPv6                                       |
   +----------------+-----------------------------------------------------+
   | "udp"          | UDP                                                 |
   +----------------+-----------------------------------------------------+
   | "udp4"         | UDP over IPv4                                       |
   +----------------+-----------------------------------------------------+
   | "udp6"         | UDP over IPv6                                       |
   +----------------+-----------------------------------------------------+
   | "unix"         | UNIX socket (both UDP and TCP protocols)            |
   +----------------+-----------------------------------------------------+
   | "all"          | the sum of all the possible families and protocols  |
   +----------------+-----------------------------------------------------+

  To get per-process connections use :meth:`Process.connections`.
  Also, see
  `netstat.py sample script <https://code.google.com/p/psutil/source/browse/examples/netstat.py>`__.
  Example:

    >>> import psutil
    >>> psutil.net_connections()
    [pconn(fd=115, family=2, type=1, laddr=('10.0.0.1', 48776), raddr=('93.186.135.91', 80), status='ESTABLISHED', pid=1254),
     pconn(fd=117, family=2, type=1, laddr=('10.0.0.1', 43761), raddr=('72.14.234.100', 80), status='CLOSING', pid=2987),
     pconn(fd=-1, family=2, type=1, laddr=('10.0.0.1', 60759), raddr=('72.14.234.104', 80), status='ESTABLISHED', pid=None),
     pconn(fd=-1, family=2, type=1, laddr=('10.0.0.1', 51314), raddr=('72.14.234.83', 443), status='SYN_SENT', pid=None)
     ...]

  .. note:: (OSX) :class:`psutil.AccessDenied` is always raised unless running
     as root (lsof does the same).
  .. note:: (Solaris) UNIX sockets are not supported.

  *New in 2.1.0*


Other system info
-----------------

.. function:: users()

  Return users currently connected on the system as a list of namedtuples
  including the following fields:

  - **user**: the name of the user.
  - **terminal**: the tty or pseudo-tty associated with the user, if any,
    else ``None``.
  - **host**: the host name associated with the entry, if any.
  - **started**: the creation time as a floating point number expressed in
    seconds since the epoch.

  Example::

    >>> import psutil
    >>> psutil.users()
    [suser(name='giampaolo', terminal='pts/2', host='localhost', started=1340737536.0),
     suser(name='giampaolo', terminal='pts/3', host='localhost', started=1340737792.0)]

.. function:: boot_time()

  Return the system boot time expressed in seconds since the epoch.
  Example:

  .. code-block:: python

     >>> import psutil, datetime
     >>> psutil.boot_time()
     1389563460.0
     >>> datetime.datetime.fromtimestamp(psutil.boot_time()).strftime("%Y-%m-%d %H:%M:%S")
     '2014-01-12 22:51:00'

Processes
=========

Functions
---------

.. function:: pids()

  Return a list of current running PIDs. To iterate over all processes
  :func:`process_iter()` should be preferred.

.. function:: pid_exists(pid)

  Check whether the given PID exists in the current process list. This is
  faster than doing ``"pid in psutil.pids()"`` and should be preferred.

.. function:: process_iter()

  Return an iterator yielding a :class:`Process` class instance for all running
  processes on the local machine.
  Every instance is only created once and then cached into an internal table
  which is updated every time an element is yielded.
  Cached :class:`Process` instances are checked for identity so that you're
  safe in case a PID has been reused by another process, in which case the
  cached instance is updated.
  This is should be preferred over :func:`psutil.pids()` for iterating over
  processes.
  Sorting order in which processes are returned is
  based on their PID. Example usage::

    import psutil

    for proc in psutil.process_iter():
        try:
            pinfo = proc.as_dict(attrs=['pid', 'name'])
        except psutil.NoSuchProcess:
            pass
        else:
            print(pinfo)

.. function:: wait_procs(procs, timeout=None, callback=None)

  Convenience function which waits for a list of :class:`Process` instances to
  terminate. Return a ``(gone, alive)`` tuple indicating which processes are
  gone and which ones are still alive. The *gone* ones will have a new
  *returncode* attribute indicating process exit status (it may be ``None``).
  ``callback`` is a function which gets called every time a process terminates
  (a :class:`Process` instance is passed as callback argument). Function will
  return as soon as all processes terminate or when timeout occurs. Tipical use
  case is:

  - send SIGTERM to a list of processes
  - give them some time to terminate
  - send SIGKILL to those ones which are still alive

  Example::

    import psutil

    def on_terminate(proc):
        print("process {} terminated".format(proc))

    procs = [...]  # a list of Process instances
    for p in procs:
        p.terminate()
    gone, alive = wait_procs(procs, timeout=3, callback=on_terminate)
    for p in alive:
        p.kill()

Exceptions
----------

.. class:: Error()

  Base exception class. All other exceptions inherit from this one.

.. class:: NoSuchProcess(pid, name=None, msg=None)

   Raised by :class:`Process` class methods when no process with the given
   *pid* is found in the current process list or when a process no longer
   exists. "name" is the name the process had before disappearing
   and gets set only if :meth:`Process.name()` was previosly called.

.. class:: AccessDenied(pid=None, name=None, msg=None)

    Raised by :class:`Process` class methods when permission to perform an
    action is denied. "name" is the name of the process (may be ``None``).

.. class:: TimeoutExpired(seconds, pid=None, name=None, msg=None)

    Raised by :meth:`Process.wait` if timeout expires and process is still
    alive.

Process class
-------------

.. class:: Process(pid=None)

  Represents an OS process with the given *pid*. If *pid* is omitted current
  process *pid* (`os.getpid() <http://docs.python.org/library/os.html#os.getpid>`__)
  is used.
  Raise :class:`NoSuchProcess` if *pid* does not exist.
  When accessing methods of this class always be  prepared to catch
  :class:`NoSuchProcess` and :class:`AccessDenied` exceptions.
  `hash() <http://docs.python.org/2/library/functions.html#hash>`__ builtin can
  be used against instances of this class in order to identify a process
  univocally over time (the hash is determined by mixing process PID
  and creation time). As such it can also be used with
  `set()s <http://docs.python.org/2/library/stdtypes.html#types-set>`__.

  .. warning::

    the way this class is bound to a process is uniquely via its **PID**.
    That means that if the :class:`Process` instance is old enough and
    the PID has been reused by another process in the meantime you might end up
    interacting with another process.
    The only exceptions for which process identity is pre-emptively checked
    (via PID + creation time) and guaranteed are for
    :meth:`nice` (set),
    :meth:`ionice`  (set),
    :meth:`cpu_affinity` (set),
    :meth:`rlimit` (set),
    :meth:`children`,
    :meth:`parent`,
    :meth:`suspend`
    :meth:`resume`,
    :meth:`send_signal`,
    :meth:`terminate`, and
    :meth:`kill`
    methods.
    To prevent this problem for all other methods you can use
    :meth:`is_running()` before querying the process or use
    :func:`process_iter()` in case you're iterating over all processes.

  .. attribute:: pid

     The process PID.

  .. method:: ppid()

     The process parent pid.  On Windows the return value is cached after first
     call.

  .. method:: name()

     The process name. The return value is cached after first call.

  .. method:: exe()

     The process executable as an absolute path.
     On some systems this may also be an empty string.
     The return value is cached after first call.

  .. method:: cmdline()

     The command line this process has been called with.

  .. method:: create_time()

     The process creation time as a floating point number expressed in seconds
     since the epoch, in
     `UTC <http://en.wikipedia.org/wiki/Coordinated_universal_time>`__.
     The return value is cached after first call.

        >>> import psutil, datetime
        >>> p = psutil.Process()
        >>> p.create_time()
        1307289803.47
        >>> datetime.datetime.fromtimestamp(p.create_time()).strftime("%Y-%m-%d %H:%M:%S")
        '2011-03-05 18:03:52'

  .. method:: as_dict(attrs=[], ad_value=None)

     Utility method returning process information as a hashable dictionary.
     If *attrs* is specified it must be a list of strings reflecting available
     :class:`Process` class's attribute names (e.g. ``['cpu_times', 'name']``)
     else all public (read only) attributes are assumed. *ad_value* is the
     value which gets assigned to a dict key in case :class:`AccessDenied`
     exception is raised when retrieving that particular process information.

        >>> import psutil
        >>> p = psutil.Process()
        >>> p.as_dict(attrs=['pid', 'name', 'username'])
        {'username': 'giampaolo', 'pid': 12366, 'name': 'python'}

  .. method:: parent()

     Utility method which returns the parent process as a :class:`Process`
     object pre-emptively checking whether PID has been reused. If no parent
     PID is known return ``None``.

  .. method:: status()

     The current process status as a string. The returned string is one of the
     :data:`psutil.STATUS_*<psutil.STATUS_RUNNING>` constants.

  .. method:: cwd()

     The process current working directory as an absolute path.

  .. method:: username()

     The name of the user that owns the process. On UNIX this is calculated by
     using real process uid.

  .. method:: uids()

     The **real**, **effective** and **saved** user ids of this process as a
     nameduple. This is the same as
     `os.getresuid() <http://docs.python.org//library/os.html#os.getresuid>`__
     but can be used for every process PID.

     Availability: UNIX

  .. method:: gids()

     The **real**, **effective** and **saved** group ids of this process as a
     nameduple. This is the same as
     `os.getresgid() <http://docs.python.org//library/os.html#os.getresgid>`__
     but can be used for every process PID.

     Availability: UNIX

  .. method:: terminal()

     The terminal associated with this process, if any, else ``None``. This is
     similar to "tty" command but can be used for every process PID.

     Availability: UNIX

  .. method:: nice(value=None)

     Get or set process
     `niceness <blogs.techrepublic.com.com/opensource/?p=140>`__ (priority).
     On UNIX this is a number which usually goes from ``-20`` to ``20``.
     The higher the nice value, the lower the priority of the process.

        >>> import psutil
        >>> p = psutil.Process()
        >>> p.nice(10)  # set
        >>> p.nice()  # get
        10
        >>>

     On Windows this is available as well by using
     `GetPriorityClass <http://msdn.microsoft.com/en-us/library/ms683211(v=vs.85).aspx>`__
     and `SetPriorityClass <http://msdn.microsoft.com/en-us/library/ms686219(v=vs.85).aspx>`__
     and *value* is one of the
     :data:`psutil.*_PRIORITY_CLASS <psutil.ABOVE_NORMAL_PRIORITY_CLASS>`
     constants.
     Example which increases process priority on Windows:

        >>> p.nice(psutil.HIGH_PRIORITY_CLASS)

     Starting from `Python 3.3 <http://bugs.python.org/issue10784>`__ this
     same functionality is available as
     `os.getpriority() <http://docs.python.org/3/library/os.html#os.getpriority>`__
     and
     `os.setpriority() <http://docs.python.org/3/library/os.html#os.setpriority>`__.

  .. method:: ionice(ioclass=None, value=None)

     Get or set
     `process I/O niceness <http://friedcpu.wordpress.com/2007/07/17/why-arent-you-using-ionice-yet/>`__ (priority).
     On Linux *ioclass* is one of the
     :data:`psutil.IOPRIO_CLASS_*<psutil.IOPRIO_CLASS_NONE>` constants.
     *value* is a number which goes from  ``0`` to ``7``. The higher the value,
     the lower the I/O priority of the process. On Windows only *ioclass* is
     used and it can be set to ``2`` (normal), ``1`` (low) or ``0`` (very low).
     The example below sets IDLE priority class for the current process,
     meaning it will only get I/O time when no other process needs the disk:

      >>> import psutil
      >>> p = psutil.Process()
      >>> p.ionice(psutil.IOPRIO_CLASS_IDLE)  # set
      >>> p.ionice()  # get
      pionice(ioclass=3, value=0)
      >>>

     On Windows only *ioclass* is used and it can be set to ``2`` (normal),
     ``1`` (low) or ``0`` (very low).

     Availability: Linux and Windows > Vista

  .. method:: rlimit(resource, limits=None)

     Get or set process resource limits (see
     `man prlimit <http://linux.die.net/man/2/prlimit>`__). *resource* is one of
     the :data:`psutil.RLIMIT_* <psutil.RLIMIT_INFINITY>` constants.
     *limits* is a ``(soft, hard)`` tuple.
     This is the same as `resource.getrlimit() <http://docs.python.org/library/resource.html#resource.getrlimit>`__
     and `resource.setrlimit() <http://docs.python.org/library/resource.html#resource.setrlimit>`__
     but can be used for every process PID and only on Linux.
     Example:

      >>> import psutil
      >>> p = psutil.Process()
      >>> # process may open no more than 128 file descriptors
      >>> p.rlimit(psutil.RLIMIT_NOFILE, (128, 128))
      >>> # process may create files no bigger than 1024 bytes
      >>> p.rlimit(psutil.RLIMIT_FSIZE, (1024, 1024))
      >>> # get
      >>> p.rlimit(psutil.RLIMIT_FSIZE)
      (1024, 1024)
      >>>

     Availability: Linux

  .. method:: io_counters()

     Return process I/O statistics as a namedtuple including the number of read
     and write operations performed by the process and the amount of bytes read
     and written. For Linux refer to
     `/proc filesysem documentation <https://www.kernel.org/doc/Documentation/filesystems/proc.txt>`__.
     On BSD there's apparently no way to retrieve bytes counters, hence ``-1``
     is returned for **read_bytes** and **write_bytes** fields. OSX is not
     supported.

      >>> import psutil
      >>> p = psutil.Process()
      >>> p.io_counters()
      pio(read_count=454556, write_count=3456, read_bytes=110592, write_bytes=0)

     Availability: all platforms except OSX

  .. method:: num_ctx_switches()

     The number voluntary and involuntary context switches performed by
     this process.

  .. method:: num_fds()

     The number of file descriptors used by this process.

     Availability: UNIX

  .. method:: num_handles()

     The number of handles used by this process.

     Availability: Windows

  .. method:: num_threads()

     The number of threads currently used by this process.

  .. method:: threads()

     Return threads opened by process as a list of namedtuples including thread
     id and thread CPU times (user/system).

  .. method:: cpu_times()

     Return a tuple whose values are process CPU **user** and **system**
     times which means the amount of time expressed in seconds that a process
     has spent in
     `user / system mode <http://stackoverflow.com/questions/556405/what-do-real-user-and-sys-mean-in-the-output-of-time1>`__.
     This is similar to
     `os.times() <http://docs.python.org//library/os.html#os.times>`__
     but can be used for every process PID.

  .. method:: cpu_percent(interval=None)

     Return a float representing the process CPU utilization as a percentage.
     When *interval* is > ``0.0`` compares process times to system CPU times
     elapsed before and after the interval (blocking). When interval is ``0.0``
     or ``None`` compares process times to system CPU times elapsed since last
     call, returning immediately. That means the first time this is called it
     will return a meaningless ``0.0`` value which you are supposed to ignore.
     In this case is recommended for accuracy that this function be called a
     second time with at least ``0.1`` seconds between calls. Example:

      >>> import psutil
      >>> p = psutil.Process()
      >>>
      >>> # blocking
      >>> p.cpu_percent(interval=1)
      2.0
      >>> # non-blocking (percentage since last call)
      >>> p.cpu_percent(interval=None)
      2.9
      >>>

     .. note::
        a percentage > 100 is legitimate as it can result from a process with
        multiple threads running on different CPU cores.

     .. warning::
        the first time this method is called with interval = ``0.0`` or
        ``None`` it will return a meaningless ``0.0`` value which you are
        supposed to ignore.

  .. method:: cpu_affinity(cpus=None)

     Get or set process current
     `CPU affinity <http://www.linuxjournal.com/article/6799?page=0,0>`__.
     CPU affinity consists in telling the OS to run a certain process on a
     limited set of CPUs only. The number of eligible CPUs can be obtained with
     ``list(range(psutil.cpu_count()))``.

      >>> import psutil
      >>> psutil.cpu_count()
      4
      >>> p = psutil.Process()
      >>> p.cpu_affinity()  # get
      [0, 1, 2, 3]
      >>> p.cpu_affinity([0])  # set; from now on, process will run on CPU #0 only
      >>>

     Availability: Linux, Windows

  .. method:: memory_info()

     Return a tuple representing RSS (Resident Set Size) and VMS (Virtual
     Memory Size) in bytes. On UNIX *rss* and *vms* are the same values shown
     by ps. On Windows *rss* and *vms* refer to "Mem Usage" and "VM Size"
     columns of taskmgr.exe. For more detailed memory stats use
     :meth:`memory_info_ex`.

  .. method:: memory_info_ex()

     Return a namedtuple with variable fields depending on the platform
     representing extended memory information about the process.
     All numbers are expressed in bytes.

     +--------+---------+-------+-------+--------------------+
     | Linux  | OSX     | BSD   | SunOS | Windows            |
     +========+=========+=======+=======+====================+
     | rss    | rss     | rss   | rss   | num_page_faults    |
     +--------+---------+-------+-------+--------------------+
     | vms    | vms     | vms   | vms   | peak_wset          |
     +--------+---------+-------+-------+--------------------+
     | shared | pfaults | text  |       | wset               |
     +--------+---------+-------+-------+--------------------+
     | text   | pageins | data  |       | peak_paged_pool    |
     +--------+---------+-------+-------+--------------------+
     | lib    |         | stack |       | paged_pool         |
     +--------+---------+-------+-------+--------------------+
     | data   |         |       |       | peak_nonpaged_pool |
     +--------+---------+-------+-------+--------------------+
     | dirty  |         |       |       | nonpaged_pool      |
     +--------+---------+-------+-------+--------------------+
     |        |         |       |       | pagefile           |
     +--------+---------+-------+-------+--------------------+
     |        |         |       |       | peak_pagefile      |
     +--------+---------+-------+-------+--------------------+
     |        |         |       |       | private            |
     +--------+---------+-------+-------+--------------------+

     Windows metrics are extracted from
     `PROCESS_MEMORY_COUNTERS_EX <http://msdn.microsoft.com/en-us/library/windows/desktop/ms684874(v=vs.85).aspx>`__ structure.
     Example on Linux:

     >>> import psutil
     >>> p = psutil.Process()
     >>> p.memory_info_ex()
     pextmem(rss=15491072, vms=84025344, shared=5206016, text=2555904, lib=0, data=9891840, dirty=0)

  .. method:: memory_percent()

     Compare physical system memory to process resident memory (RSS) and
     calculate process memory utilization as a percentage.

  .. method:: memory_maps(grouped=True)

     Return process's mapped memory regions as a list of nameduples whose
     fields are variable depending on the platform. As such, portable
     applications should rely on namedtuple's `path` and `rss` fields only.
     This method is useful to obtain a detailed representation of process
     memory usage as explained
     `here <http://bmaurer.blogspot.it/2006/03/memory-usage-with-smaps.html>`__.
     If *grouped* is ``True`` the mapped regions with the same *path* are
     grouped together and the different memory fields are summed.  If *grouped*
     is ``False`` every mapped region is shown as a single entity and the
     namedtuple will also include the mapped region's address space (*addr*)
     and permission set (*perms*).
     See `examples/pmap.py <http://code.google.com/p/psutil/source/browse/examples/pmap.py>`__
     for an example application.

      >>> import psutil
      >>> p = psutil.Process()
      >>> p.memory_maps()
      [pmmap_grouped(path='/lib/x8664-linux-gnu/libutil-2.15.so', rss=16384, anonymous=8192, swap=0),
       pmmap_grouped(path='/lib/x8664-linux-gnu/libc-2.15.so', rss=6384, anonymous=15, swap=0),
       pmmap_grouped(path='/lib/x8664-linux-gnu/libcrypto.so.0.1', rss=34124, anonymous=1245, swap=0),
       pmmap_grouped(path='[heap]', rss=54653, anonymous=8192, swap=0),
       pmmap_grouped(path='[stack]', rss=1542, anonymous=166, swap=0),
       ...]
      >>>

  .. method:: children(recursive=False)

     Return the children of this process as a list of :Class:`Process` objects,
     pre-emptively checking whether PID has been reused. If recursive is `True`
     return all the parent descendants.
     Example assuming *A == this process*:
     ::

          A ─┐
             │
             ├─ B (child) ─┐
             │             └─ X (grandchild) ─┐
             │                                └─ Y (great grandchild)
             ├─ C (child)
             └─ D (child)

          >>> p.children()
          B, C, D
          >>> p.children(recursive=True)
          B, X, Y, C, D

     Note that in the example above if process X disappears process Y won't be
     returned either as the reference to process A is lost.

  .. method:: open_files()

     Return regular files opened by process as a list of namedtuples including
     the absolute file name and the file descriptor number (on Windows this is
     always ``-1``). Example:

      >>> import psutil
      >>> f = open('file.ext', 'w')
      >>> p = psutil.Process()
      >>> p.open_files()
      [popenfile(path='/home/giampaolo/svn/psutil/file.ext', fd=3)]

  .. method:: connections(kind="inet")

    Return socket connections opened by process as a list of namedutples.
    To get system-wide connections use :func:`psutil.net_connections()`.
    Every namedtuple provides 6 attributes:

    - **fd**: the socket file descriptor. This can be passed to
      `socket.fromfd() <http://docs.python.org/library/socket.html#socket.fromfd>`__
      to obtain a usable socket object.
      This is only available on UNIX; on Windows ``-1`` is always returned.
    - **family**: the address family, either `AF_INET
      <http://docs.python.org//library/socket.html#socket.AF_INET>`__,
      `AF_INET6 <http://docs.python.org//library/socket.html#socket.AF_INET6>`__
      or `AF_UNIX <http://docs.python.org//library/socket.html#socket.AF_UNIX>`__.
    - **type**: the address type, either `SOCK_STREAM
      <http://docs.python.org//library/socket.html#socket.SOCK_STREAM>`__ or
      `SOCK_DGRAM
      <http://docs.python.org//library/socket.html#socket.SOCK_DGRAM>`__.
    - **laddr**: the local address as a ``(ip, port)`` tuple or a ``path``
      in case of AF_UNIX sockets.
    - **raddr**: the remote address as a ``(ip, port)`` tuple or an absolute
      ``path`` in case of UNIX sockets.
      When the remote endpoint is not connected you'll get an empty tuple
      (AF_INET) or ``None`` (AF_UNIX).
      On Linux AF_UNIX sockets will always have this set to ``None``.
    - **status**: represents the status of a TCP connection. The return value
      is one of the :data:`psutil.CONN_* <psutil.CONN_ESTABLISHED>` constants.
      For UDP and UNIX sockets this is always going to be
      :const:`psutil.CONN_NONE`.

    The *kind* parameter is a string which filters for connections that fit the
    following criteria:

    .. table::

     +----------------+-----------------------------------------------------+
     | **Kind value** | **Connections using**                               |
     +================+=====================================================+
     | "inet"         | IPv4 and IPv6                                       |
     +----------------+-----------------------------------------------------+
     | "inet4"        | IPv4                                                |
     +----------------+-----------------------------------------------------+
     | "inet6"        | IPv6                                                |
     +----------------+-----------------------------------------------------+
     | "tcp"          | TCP                                                 |
     +----------------+-----------------------------------------------------+
     | "tcp4"         | TCP over IPv4                                       |
     +----------------+-----------------------------------------------------+
     | "tcp6"         | TCP over IPv6                                       |
     +----------------+-----------------------------------------------------+
     | "udp"          | UDP                                                 |
     +----------------+-----------------------------------------------------+
     | "udp4"         | UDP over IPv4                                       |
     +----------------+-----------------------------------------------------+
     | "udp6"         | UDP over IPv6                                       |
     +----------------+-----------------------------------------------------+
     | "unix"         | UNIX socket (both UDP and TCP protocols)            |
     +----------------+-----------------------------------------------------+
     | "all"          | the sum of all the possible families and protocols  |
     +----------------+-----------------------------------------------------+

    Example:

      >>> import psutil
      >>> p = psutil.Process(1694)
      >>> p.name()
      'firefox'
      >>> p.connections()
      [pconn(fd=115, family=2, type=1, laddr=('10.0.0.1', 48776), raddr=('93.186.135.91', 80), status='ESTABLISHED'),
       pconn(fd=117, family=2, type=1, laddr=('10.0.0.1', 43761), raddr=('72.14.234.100', 80), status='CLOSING'),
       pconn(fd=119, family=2, type=1, laddr=('10.0.0.1', 60759), raddr=('72.14.234.104', 80), status='ESTABLISHED'),
       pconn(fd=123, family=2, type=1, laddr=('10.0.0.1', 51314), raddr=('72.14.234.83', 443), status='SYN_SENT')]

  .. method:: is_running()

     Return whether the current process is running in the current process list.
     This is reliable also in case the process is gone and its PID reused by
     another process, therefore it must be preferred over doing
     ``psutil.pid_exists(p.pid)``.

     .. note::
      this will return ``True`` also if the process is a zombie
      (``p.status() == psutil.STATUS_ZOMBIE``).

  .. method:: send_signal(signal)

     Send a signal to process (see
     `signal module <http://docs.python.org//library/signal.html>`__
     constants) pre-emptively checking whether PID has been reused.
     This is the same as ``os.kill(pid, sig)``.
     On Windows only **SIGTERM** is valid and is treated as an alias for
     :meth:`kill()`.

  .. method:: suspend()

     Suspend process execution with **SIGSTOP** signal pre-emptively checking
     whether PID has been reused.
     On UNIX this is the same as ``os.kill(pid, signal.SIGSTOP)``.
     On Windows this is done by suspending all process threads execution.

  .. method:: resume()

     Resume process execution with **SIGCONT** signal pre-emptively checking
     whether PID has been reused.
     On UNIX this is the same as ``os.kill(pid, signal.SIGCONT)``.
     On Windows this is done by resuming all process threads execution.

  .. method:: terminate()

     Terminate the process with **SIGTERM** signal pre-emptively checking
     whether PID has been reused.
     On UNIX this is the same as ``os.kill(pid, signal.SIGTERM)``.
     On Windows this is an alias for :meth:`kill`.

  .. method:: kill()

     Kill the current process by using **SIGKILL** signal pre-emptively
     checking whether PID has been reused.
     On UNIX this is the same as ``os.kill(pid, signal.SIGKILL)``.
     On Windows this is done by using
     `TerminateProcess <http://msdn.microsoft.com/en-us/library/windows/desktop/ms686714(v=vs.85).aspx>`__.

  .. method:: wait(timeout=None)

     Wait for process termination and if the process is a children of the
     current one also return the exit code, else ``None``. On Windows there's
     no such limitation (exit code is always returned). If the process is
     already terminated immediately return ``None`` instead of raising
     :class:`NoSuchProcess`. If *timeout* is specified and process is still
     alive raise :class:`TimeoutExpired` exception. It can also be used in a
     non-blocking fashion by specifying ``timeout=0`` in which case it will
     either return immediately or raise :class:`TimeoutExpired`.
     To wait for multiple processes use :func:`psutil.wait_procs()`.


Popen class
-----------

.. class:: Popen(*args, **kwargs)

  A more convenient interface to stdlib
  `subprocess.Popen <http://docs.python.org/library/subprocess.html#subprocess.Popen>`__.
  It starts a sub process and deals with it exactly as when using
  `subprocess.Popen <http://docs.python.org/library/subprocess.html#subprocess.Popen>`__
  but in addition it also provides all the methods of
  :class:`psutil.Process` class in a single interface.
  For method names common to both classes such as
  :meth:`send_signal() <psutil.Process.send_signal()>`,
  :meth:`terminate() <psutil.Process.terminate()>` and
  :meth:`kill() <psutil.Process.kill()>`
  :class:`psutil.Process` implementation takes precedence.
  For a complete documentation refer to
  `subprocess module documentation <http://docs.python.org/library/subprocess.html>`__.

  .. note::

     Unlike `subprocess.Popen <http://docs.python.org/library/subprocess.html#subprocess.Popen>`__
     this class pre-emptively checks wheter PID has been reused on
     :meth:`send_signal() <psutil.Process.send_signal()>`,
     :meth:`terminate() <psutil.Process.terminate()>` and
     :meth:`kill() <psutil.Process.kill()>`
     so that you don't accidentally terminate another process, fixing
     http://bugs.python.org/issue6973.

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

Constants
=========

.. _const-pstatus:
.. data:: STATUS_RUNNING
          STATUS_SLEEPING
          STATUS_DISK_SLEEP
          STATUS_STOPPED
          STATUS_TRACING_STOP
          STATUS_ZOMBIE
          STATUS_DEAD
          STATUS_WAKE_KILL
          STATUS_WAKING
          STATUS_IDLE
          STATUS_LOCKED
          STATUS_WAITING

  A set of strings representing the status of a process.
  Returned by :meth:`psutil.Process.status()`.

.. _const-conn:
.. data:: CONN_ESTABLISHED
          CONN_SYN_SENT
          CONN_SYN_RECV
          CONN_FIN_WAIT1
          CONN_FIN_WAIT2
          CONN_TIME_WAIT
          CONN_CLOSE
          CONN_CLOSE_WAIT
          CONN_LAST_ACK
          CONN_LISTEN
          CONN_CLOSING
          CONN_NONE
          CONN_DELETE_TCB (Windows)
          CONN_IDLE (Solaris)
          CONN_BOUND (Solaris)

  A set of strings representing the status of a TCP connection.
  Returned by :meth:`psutil.Process.connections()` (`status` field).

.. _const-prio:
.. data:: ABOVE_NORMAL_PRIORITY_CLASS
          BELOW_NORMAL_PRIORITY_CLASS
          HIGH_PRIORITY_CLASS
          IDLE_PRIORITY_CLASS
          NORMAL_PRIORITY_CLASS
          REALTIME_PRIORITY_CLASS

  A set of integers representing the priority of a process on Windows (see
  `MSDN documentation <http://msdn.microsoft.com/en-us/library/ms686219(v=vs.85).aspx>`__).
  They can be used in conjunction with
  :meth:`psutil.Process.nice()` to get or set process priority.

  Availability: Windows

.. _const-ioprio:
.. data:: IOPRIO_CLASS_NONE
          IOPRIO_CLASS_RT
          IOPRIO_CLASS_BE
          IOPRIO_CLASS_IDLE

  A set of integers representing the I/O priority of a process on Linux. They
  can be used in conjunction with :meth:`psutil.Process.ionice()` to get or set
  process I/O priority.
  *IOPRIO_CLASS_NONE* and *IOPRIO_CLASS_BE* (best effort) is the default for
  any process that hasn't set a specific I/O priority.
  *IOPRIO_CLASS_RT* (real time) means the process is given first access to the
  disk, regardless of what else is going on in the system.
  *IOPRIO_CLASS_IDLE* means the process will get I/O time when no-one else
  needs the disk.
  For further information refer to manuals of
  `ionice <http://linux.die.net/man/1/ionice>`__
  command line utility or
  `ioprio_get <http://linux.die.net/man/2/ioprio_get>`__
  system call.

  Availability: Linux

.. _const-rlimit:
.. data:: RLIMIT_INFINITY
          RLIMIT_AS
          RLIMIT_CORE
          RLIMIT_CPU
          RLIMIT_DATA
          RLIMIT_FSIZE
          RLIMIT_LOCKS
          RLIMIT_MEMLOCK
          RLIMIT_MSGQUEUE
          RLIMIT_NICE
          RLIMIT_NOFILE
          RLIMIT_NPROC
          RLIMIT_RSS
          RLIMIT_RTPRIO
          RLIMIT_RTTIME
          RLIMIT_RTPRIO
          RLIMIT_SIGPENDING
          RLIMIT_STACK

  Constants used for getting and setting process resource limits to be used in
  conjunction with :meth:`psutil.Process.rlimit()`. See
  `man prlimit <http://linux.die.net/man/2/prlimit>`__ for futher information.

  Availability: Linux
