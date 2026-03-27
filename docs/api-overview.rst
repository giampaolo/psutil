API overview
============

Overview of the entire psutil API (on Linux). This serves as a quick reference
to all available functions. For detailed documentation of each function see the
full :doc:`API reference <api>`.

System related functions
------------------------

CPU
^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.cpu_times()
    scputimes(user=3961.46,
              nice=169.729,
              system=2150.659,
              idle=16900.540,
              iowait=629.59,
              irq=0.0,
              softirq=19.42,
              steal=0.0,
              guest=0,
              guest_nice=0.0)
    >>>
    >>> for x in range(3):
    ...     psutil.cpu_percent(interval=1)
    ...
    4.0
    5.9
    3.8
    >>>
    >>> for x in range(3):
    ...     psutil.cpu_percent(interval=1, percpu=True)
    ...
    [4.0, 6.9, 3.7, 9.2]
    [7.0, 8.5, 2.4, 2.1]
    [1.2, 9.0, 9.9, 7.2]
    >>>
    >>> for x in range(3):
    ...     psutil.cpu_times_percent(interval=1, percpu=False)
    ...
    scputimes(user=1.5, nice=0.0, system=0.5, idle=96.5, iowait=1.5, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0)
    scputimes(user=1.0, nice=0.0, system=0.0, idle=99.0, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0)
    scputimes(user=2.0, nice=0.0, system=0.0, idle=98.0, iowait=0.0, irq=0.0, softirq=0.0, steal=0.0, guest=0.0, guest_nice=0.0)
    >>>
    >>> psutil.cpu_count()
    4
    >>> psutil.cpu_count(logical=False)
    2
    >>>
    >>> psutil.cpu_stats()
    scpustats(ctx_switches=20455687, interrupts=6598984, soft_interrupts=2134212, syscalls=0)
    >>>
    >>> psutil.cpu_freq()
    scpufreq(current=931.42925, min=800.0, max=3500.0)
    >>>
    >>> psutil.getloadavg()  # also on Windows (emulated)
    (3.14, 3.89, 4.67)
    >>>

Memory
^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.virtual_memory()
    svmem(total=10367352832,
          available=6472179712,
          percent=37.6,
          used=8186245120,
          free=2181107712,
          active=4748992512,
          inactive=2758115328,
          buffers=790724608,
          cached=3500347392,
          shared=787554304)
    >>>
    >>> psutil.swap_memory()
    sswap(total=2097147904,
          used=296128512,
          free=1801019392,
          percent=14.1,
          sin=304193536,
          sout=677842944)
    >>>

Disks
^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.disk_partitions()
    [sdiskpart(device='/dev/sda1', mountpoint='/', fstype='ext4', opts='rw,nosuid'),
     sdiskpart(device='/dev/sda2', mountpoint='/home', fstype='ext', opts='rw')]
    >>>
    >>> psutil.disk_usage('/')
    sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)
    >>>
    >>> psutil.disk_io_counters(perdisk=False)
    sdiskio(read_count=719566,
            write_count=1082197,
            read_bytes=18626220032,
            write_bytes=24081764352,
            read_time=5023392,
            write_time=63199568,
            read_merged_count=619166,
            write_merged_count=812396,
            busy_time=4523412)
    >>>

Network
^^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.net_io_counters(pernic=True)
    {'eth0': netio(bytes_sent=485291293,
                   bytes_recv=6004858642,
                   packets_sent=3251564,
                   packets_recv=4787798,
                   errin=0,
                   errout=0,
                   dropin=0,
                   dropout=0),
     'lo': netio(bytes_sent=2838627,
                 bytes_recv=2838627,
                 packets_sent=30567,
                 packets_recv=30567,
                 errin=0,
                 errout=0,
                 dropin=0,
                 dropout=0)}
    >>>
    >>> psutil.net_connections(kind='tcp')
    [sconn(fd=115,
           family=<AddressFamily.AF_INET: 2>,
           type=<SocketType.SOCK_STREAM: 1>,
           laddr=addr(ip='10.0.0.1', port=48776),
           raddr=addr(ip='93.186.135.91', port=80),
           status='ESTABLISHED',
           pid=1254),
     sconn(fd=117,
           family=<AddressFamily.AF_INET: 2>,
           type=<SocketType.SOCK_STREAM: 1>,
           laddr=addr(ip='10.0.0.1', port=43761),
           raddr=addr(ip='72.14.234.100', port=80),
           status='CLOSING',
           pid=2987),
     ...]
    >>>
    >>> psutil.net_if_addrs()
    {'lo': [snicaddr(family=<AddressFamily.AF_INET: 2>,
                     address='127.0.0.1',
                     netmask='255.0.0.0',
                     broadcast='127.0.0.1',
                     ptp=None),
            snicaddr(family=<AddressFamily.AF_INET6: 10>,
                     address='::1',
                     netmask='ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff',
                     broadcast=None,
                     ptp=None),
            snicaddr(family=<AddressFamily.AF_LINK: 17>,
                     address='00:00:00:00:00:00',
                     netmask=None,
                     broadcast='00:00:00:00:00:00',
                     ptp=None)],
     'wlan0': [snicaddr(family=<AddressFamily.AF_INET: 2>,
                        address='192.168.1.3',
                        netmask='255.255.255.0',
                        broadcast='192.168.1.255',
                        ptp=None),
               snicaddr(family=<AddressFamily.AF_INET6: 10>,
                        address='fe80::c685:8ff:fe45:641%wlan0',
                        netmask='ffff:ffff:ffff:ffff::',
                        broadcast=None,
                        ptp=None),
               snicaddr(family=<AddressFamily.AF_LINK: 17>,
                        address='c4:85:08:45:06:41',
                        netmask=None,
                        broadcast='ff:ff:ff:ff:ff:ff',
                        ptp=None)]}
    >>>
    >>> psutil.net_if_stats()
    {'lo': snicstats(isup=True,
                     duplex=<NicDuplex.NIC_DUPLEX_UNKNOWN: 0>,
                     speed=0,
                     mtu=65536,
                     flags='up,loopback,running'),
     'wlan0': snicstats(isup=True,
                        duplex=<NicDuplex.NIC_DUPLEX_FULL: 2>,
                        speed=100,
                        mtu=1500,
                        flags='up,broadcast,running,multicast')}
    >>>

Sensors
^^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.sensors_temperatures()
    {'acpitz': [shwtemp(label='', current=47.0, high=103.0, critical=103.0)],
     'asus': [shwtemp(label='', current=47.0, high=None, critical=None)],
     'coretemp': [shwtemp(label='Physical id 0', current=52.0, high=100.0, critical=100.0),
                  shwtemp(label='Core 0', current=45.0, high=100.0, critical=100.0)]}
    >>>
    >>> psutil.sensors_fans()
    {'asus': [sfan(label='cpu_fan', current=3200)]}
    >>>
    >>> psutil.sensors_battery()
    sbattery(percent=93, secsleft=16628, power_plugged=False)
    >>>

Other system info
^^^^^^^^^^^^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.users()
    [suser(name='giampaolo', terminal='pts/2', host='localhost', started=1340737536.0, pid=1352),
     suser(name='giampaolo', terminal='pts/3', host='localhost', started=1340737792.0, pid=1788)]
    >>>
    >>> psutil.boot_time()
    1365519115.0
    >>>

Processes
---------

Oneshot
^^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> p = psutil.Process(7055)
    >>> with p.oneshot():
    ...     p.name()
    ...     p.cpu_times()
    ...     p.memory_info()
    ...
    'python3'
    pcputimes(user=1.02, system=0.31, children_user=0.32, children_system=0.1, iowait=0.0)
    pmem(rss=3164160, vms=4410163, shared=897433, text=302694, data=2422374)
    >>>

Identity
^^^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> p = psutil.Process(7055)
    >>> p
    psutil.Process(pid=7055, name='python3', status=<ProcessStatus.STATUS_RUNNING: 'running'>, started='09:04:44')
    >>> p.pid
    7055
    >>>
    >>> p.name()
    'python3'
    >>>
    >>> p.exe()
    '/usr/bin/python3'
    >>>
    >>> p.cwd()
    '/home/giampaolo'
    >>>
    >>> p.cmdline()
    ['/usr/bin/python3', 'main.py']
    >>>
    >>> p.status()
    <ProcessStatus.STATUS_RUNNING: 'running'>
    >>>
    >>> p.create_time()
    1267551141.5019531
    >>>
    >>> p.terminal()
    '/dev/pts/0'
    >>>
    >>> p.environ()
    {'GREP_OPTIONS': '--color=auto',
     'LC_PAPER': 'it_IT.UTF-8',
     'SHELL': '/bin/bash',
     'XDG_CONFIG_DIRS': '/etc/xdg/xdg-ubuntu:/usr/share/upstart/xdg:/etc/xdg',
     ...}
    >>>
    >>> p.is_running()
    True
    >>>
    >>> p.as_dict()
    {'num_ctx_switches': pctxsw(voluntary=63, involuntary=1),
     'pid': 5457,
     'status': <ProcessStatus.STATUS_RUNNING: 'running'>,
     ...}
    >>>

Process tree
^^^^^^^^^^^^

.. code-block:: pycon

    >>> p.ppid()
    7054
    >>> p.parent()
    psutil.Process(pid=4699, name='bash', status=<ProcessStatus.STATUS_SLEEPING: 'sleeping'>, started='09:06:44')
    >>>
    >>> p.parents()
    [psutil.Process(pid=4699, name='bash', started='09:06:44'),
     psutil.Process(pid=4689, name='gnome-terminal-server', status=<ProcessStatus.STATUS_SLEEPING: 'sleeping'>, started='0:06:44'),
     psutil.Process(pid=1, name='systemd', status=<ProcessStatus.STATUS_SLEEPING: 'sleeping'>, started='05:56:55')]
    >>>
    >>> p.children(recursive=True)
    [psutil.Process(pid=29835, name='python3', status=<ProcessStatus.STATUS_SLEEPING: 'sleeping'>, started='11:45:38'),
     psutil.Process(pid=29836, name='python3', status=<ProcessStatus.STATUS_WAKING: 'waking'>, started='11:43:39')]
    >>>

Credentials
^^^^^^^^^^^^

.. code-block:: pycon

    >>> p.username()
    'giampaolo'
    >>> p.uids()
    puids(real=1000, effective=1000, saved=1000)
    >>> p.gids()
    pgids(real=1000, effective=1000, saved=1000)
    >>>

CPU / scheduling
^^^^^^^^^^^^^^^^

.. code-block:: pycon

    >>> p.cpu_times()
    pcputimes(user=1.02, system=0.31, children_user=0.32, children_system=0.1, iowait=0.0)
    >>>
    >>> p.cpu_percent(interval=1.0)
    12.1
    >>>
    >>> p.cpu_affinity()
    [0, 1, 2, 3]
    >>> p.cpu_affinity([0, 1])  # set
    >>>
    >>> p.cpu_num()
    1
    >>>
    >>> p.num_ctx_switches()
    pctxsw(voluntary=78, involuntary=19)
    >>>
    >>> p.nice()
    0
    >>> p.nice(10)  # set
    >>>
    >>> p.ionice(psutil.IOPRIO_CLASS_IDLE)  # set IO priority
    >>> p.ionice()
    pionice(ioclass=<ProcessIOPriority.IOPRIO_CLASS_IDLE: 3>, value=0)
    >>>
    >>> p.rlimit(psutil.RLIMIT_NOFILE, (5, 5))  # set resource limits
    >>> p.rlimit(psutil.RLIMIT_NOFILE)
    (5, 5)
    >>>

Memory
^^^^^^

.. code-block:: pycon

    >>> p.memory_info()
    pmem(rss=3164160, vms=4410163, shared=897433, text=302694, data=2422374)
    >>>
    >>> p.memory_info_ex()
    pmem_ex(rss=3164160,
            vms=4410163,
            shared=897433,
            text=302694,
            data=2422374,
            peak_rss=4172190,
            peak_vms=6399001,
            rss_anon=2266726,
            rss_file=897433,
            rss_shmem=0,
            swap=0,
            hugetlb=0)
    >>>
    >>> p.memory_footprint()  # "real" USS memory usage
    pfootprint(uss=2355200, pss=2483712, swap=0)
    >>>
    >>> p.memory_percent()
    0.7823
    >>>
    >>> p.memory_maps()
     pmmap_grouped(path='/lib/x8664-linux-gnu/libc-2.15.so',
                   rss=3821568,
                   size=3842048,
                   pss=3821568,
                   shared_clean=0,
                   shared_dirty=0,
                   private_clean=0,
                   private_dirty=3821568,
                   referenced=3575808,
                   anonymous=3821568,
                   swap=0),
     pmmap_grouped(path='[heap]',
                   rss=32768,
                   size=139264,
                   pss=32768,
                   shared_clean=0,
                   shared_dirty=0,
                   private_clean=0,
                   private_dirty=32768,
                   referenced=32768,
                   anonymous=32768,
                   swap=0),
     ...]
    >>>
    >>> p.page_faults()
    ppagefaults(minor=5905, major=3)
    >>>

Threads
^^^^^^^

.. code-block:: pycon

    >>> p.threads()
    [pthread(id=5234, user_time=22.5, system_time=9.2891),
     pthread(id=5237, user_time=0.0707, system_time=1.1)]
    >>> p.num_threads()
    4
    >>>

Files and connections
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: pycon

    >>> p.io_counters()
    pio(read_count=478001,
        write_count=59371,
        read_bytes=700416,
        write_bytes=69632,
        read_chars=456232,
        write_chars=517543)
    >>>
    >>> p.open_files()
    [popenfile(path='/home/giampaolo/monit.py', fd=3, position=0, mode='r', flags=32768),
     popenfile(path='/var/log/monit.log', fd=4, position=235542, mode='a', flags=33793)]
    >>>
    >>> p.net_connections(kind='tcp')
    [pconn(fd=115,
           family=<AddressFamily.AF_INET: 2>,
           type=<SocketType.SOCK_STREAM: 1>,
           laddr=addr(ip='10.0.0.1', port=48776),
           raddr=addr(ip='93.186.135.91', port=80),
           status=<ConnectionStatus.CONN_ESTABLISHED: 'ESTABLISHED'>),
     pconn(fd=117,
           family=<AddressFamily.AF_INET: 2>,
           type=<SocketType.SOCK_STREAM: 1>,
           laddr=addr(ip='10.0.0.1', port=43761),
           raddr=addr(ip='72.14.234.100', port=80),
           status=<ConnectionStatus.CONN_CLOSING: 'CLOSING'>)]
    >>>
    >>> p.num_fds()
    8
    >>>

Signals
^^^^^^^

.. code-block:: pycon

    >>> p.send_signal(signal.SIGTERM)
    >>> p.suspend()
    >>> p.resume()
    >>> p.terminate()
    >>> p.kill()
    >>> p.wait(timeout=3)
    <Exitcode.EX_OK: 0>
    >>>

Other process functions
^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.pids()
    [1, 2, 3, 4, 5, 6, 7, 46, 48, 50, 51, 178, 182, ...]
    >>>
    >>> psutil.pid_exists(3)
    True
    >>>
    >>> for p in psutil.process_iter(['pid', 'name']):
    ...     print(p.pid, p.name())
    ...
    1 systemd
    2 kthreadd
    3 ksoftirqd/0
    ...
    >>>
    >>> def on_terminate(proc):
    ...     print("process {} terminated".format(proc))
    ...
    >>> # waits for multiple processes to terminate
    >>> gone, alive = psutil.wait_procs(procs_list, timeout=3, callback=on_terminate)
    >>>

C heap introspection
--------------------

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> psutil.heap_info()
    pheap(heap_used=5177792, mmap_used=819200)
    >>>
    >>> psutil.heap_trim()
    >>>

See also `psleak <https://github.com/giampaolo/psleak>`_.

Windows services
----------------

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> list(psutil.win_service_iter())
    [<WindowsService(name='AeLookupSvc', display_name='Application Experience') at 38850096>,
     <WindowsService(name='ALG', display_name='Application Layer Gateway Service') at 38850128>,
     <WindowsService(name='APNMCP', display_name='Ask Update Service') at 38850160>,
     <WindowsService(name='AppIDSvc', display_name='Application Identity') at 38850192>,
     ...]
    >>>
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
    >>>
