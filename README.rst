.. image:: https://img.shields.io/pypi/dm/psutil.svg
    :target: https://pypi.python.org/pypi/psutil#downloads
    :alt: Downloads this month

.. image:: https://api.travis-ci.org/giampaolo/psutil.png?branch=master
    :target: https://travis-ci.org/giampaolo/psutil
    :alt: Linux tests (Travis)

.. image:: https://ci.appveyor.com/api/projects/status/qdwvw7v1t915ywr5/branch/master?svg=true
    :target: https://ci.appveyor.com/project/giampaolo/psutil
    :alt: Windows tests (Appveyor)

.. image:: https://coveralls.io/repos/giampaolo/psutil/badge.svg?branch=master&service=github
    :target: https://coveralls.io/github/giampaolo/psutil?branch=master
    :alt: Test coverage (coverall.io)

.. image:: https://img.shields.io/pypi/v/psutil.svg
    :target: https://pypi.python.org/pypi/psutil/
    :alt: Latest version

.. image:: https://img.shields.io/github/stars/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/
    :alt: Github stars

.. image:: https://img.shields.io/pypi/l/psutil.svg
    :target: https://pypi.python.org/pypi/psutil/
    :alt: License

===========
Quick links
===========

- `Home page <https://github.com/giampaolo/psutil>`_
- `Install <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`_
- `Documentation <http://pythonhosted.org/psutil/>`_
- `Download <https://pypi.python.org/pypi?:action=display&name=psutil#downloads>`_
- `Forum <http://groups.google.com/group/psutil/topics>`_
- `Blog <http://grodola.blogspot.com/search/label/psutil>`_
- `Development guide <https://github.com/giampaolo/psutil/blob/master/DEVGUIDE.rst>`_
- `What's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst>`_

=======
Summary
=======

psutil (process and system utilities) is a cross-platform library for
retrieving information on **running processes** and **system utilization**
(CPU, memory, disks, network) in Python. It is useful mainly for **system
monitoring**, **profiling and limiting process resources** and **management of
running processes**. It implements many functionalities offered by command line
tools such as: ps, top, lsof, netstat, ifconfig, who, df, kill, free, nice,
ionice, iostat, iotop, uptime, pidof, tty, taskset, pmap. It currently supports
**Linux, Windows, OSX, Sun Solaris, FreeBSD, OpenBSD** and **NetBSD**,
both **32-bit** and **64-bit** architectures, with Python versions from **2.6
to 3.5** (users of Python 2.4 and 2.5 may use
`2.1.3 <https://pypi.python.org/pypi?name=psutil&version=2.1.3&:action=files>`__ version).
`PyPy <http://pypy.org/>`__ is also known to work.

====================
Example applications
====================

.. image:: http://psutil.googlecode.com/svn/wiki/images/top-thumb.png
    :target: http://psutil.googlecode.com/svn/wiki/images/top.png
    :alt: top

.. image:: http://psutil.googlecode.com/svn/wiki/images/nettop-thumb.png
    :target: http://psutil.googlecode.com/svn/wiki/images/nettop.png
    :alt: nettop

.. image:: http://psutil.googlecode.com/svn/wiki/images/iotop-thumb.png
    :target: http://psutil.googlecode.com/svn/wiki/images/iotop.png
    :alt: iotop

See also:

 * https://github.com/nicolargo/glances
 * https://github.com/google/grr
 * https://github.com/Jahaja/psdash

==============
Example usages
==============

CPU
===

.. code-block:: python

    >>> import psutil
    >>> psutil.cpu_times()
    scputimes(user=3961.46, nice=169.729, system=2150.659, idle=16900.540, iowait=629.59, irq=0.0, softirq=19.42, steal=0.0, guest=0, nice=0.0)
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

Memory
======

.. code-block:: python

    >>> psutil.virtual_memory()
    svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120, free=2181107712, active=4748992512, inactive=2758115328, buffers=790724608, cached=3500347392, shared=787554304)
    >>> psutil.swap_memory()
    sswap(total=2097147904, used=296128512, free=1801019392, percent=14.1, sin=304193536, sout=677842944)
    >>>

Disks
=====

.. code-block:: python

    >>> psutil.disk_partitions()
    [sdiskpart(device='/dev/sda1', mountpoint='/', fstype='ext4', opts='rw,nosuid'),
     sdiskpart(device='/dev/sda2', mountpoint='/home', fstype='ext, opts='rw')]
    >>>
    >>> psutil.disk_usage('/')
    sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)
    >>>
    >>> psutil.disk_io_counters(perdisk=False)
    sdiskio(read_count=719566, write_count=1082197, read_bytes=18626220032, write_bytes=24081764352, read_time=5023392, write_time=63199568, read_merged_count=619166, write_merged_count=812396, busy_time=4523412)
    >>>

Network
=======

.. code-block:: python

    >>> psutil.net_io_counters(pernic=True)
    {'eth0': netio(bytes_sent=485291293, bytes_recv=6004858642, packets_sent=3251564, packets_recv=4787798, errin=0, errout=0, dropin=0, dropout=0),
     'lo': netio(bytes_sent=2838627, bytes_recv=2838627, packets_sent=30567, packets_recv=30567, errin=0, errout=0, dropin=0, dropout=0)}
    >>>
    >>> psutil.net_connections()
    [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 48776), raddr=('93.186.135.91', 80), status='ESTABLISHED', pid=1254),
     pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 43761), raddr=('72.14.234.100', 80), status='CLOSING', pid=2987),
     pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 60759), raddr=('72.14.234.104', 80), status='ESTABLISHED', pid=None),
     pconn(fd=-1, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 51314), raddr=('72.14.234.83', 443), status='SYN_SENT', pid=None)
     ...]
    >>>
    >>> psutil.net_if_addrs()
    {'lo': [snic(family=<AddressFamily.AF_INET: 2>, address='127.0.0.1', netmask='255.0.0.0', broadcast='127.0.0.1', ptp=None),
            snic(family=<AddressFamily.AF_INET6: 10>, address='::1', netmask='ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', broadcast=None, ptp=None),
            snic(family=<AddressFamily.AF_LINK: 17>, address='00:00:00:00:00:00', netmask=None, broadcast='00:00:00:00:00:00', ptp=None)],
     'wlan0': [snic(family=<AddressFamily.AF_INET: 2>, address='192.168.1.3', netmask='255.255.255.0', broadcast='192.168.1.255', ptp=None),
               snic(family=<AddressFamily.AF_INET6: 10>, address='fe80::c685:8ff:fe45:641%wlan0', netmask='ffff:ffff:ffff:ffff::', broadcast=None, ptp=None),
               snic(family=<AddressFamily.AF_LINK: 17>, address='c4:85:08:45:06:41', netmask=None, broadcast='ff:ff:ff:ff:ff:ff', ptp=None)]}
    >>>
    >>> psutil.net_if_stats()
    {'eth0': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_FULL: 2>, speed=100, mtu=1500),
     'lo': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_UNKNOWN: 0>, speed=0, mtu=65536)}

Other system info
=================

.. code-block:: python

    >>> psutil.users()
    [user(name='giampaolo', terminal='pts/2', host='localhost', started=1340737536.0),
     user(name='giampaolo', terminal='pts/3', host='localhost', started=1340737792.0)]
    >>>
    >>> psutil.boot_time()
    1365519115.0
    >>>

Process management
==================

.. code-block:: python

    >>> import psutil
    >>> psutil.pids()
    [1, 2, 3, 4, 5, 6, 7, 46, 48, 50, 51, 178, 182, 222, 223, 224,
     268, 1215, 1216, 1220, 1221, 1243, 1244, 1301, 1601, 2237, 2355,
     2637, 2774, 3932, 4176, 4177, 4185, 4187, 4189, 4225, 4243, 4245,
     4263, 4282, 4306, 4311, 4312, 4313, 4314, 4337, 4339, 4357, 4358,
     4363, 4383, 4395, 4408, 4433, 4443, 4445, 4446, 5167, 5234, 5235,
     5252, 5318, 5424, 5644, 6987, 7054, 7055, 7071]
    >>>
    >>> p = psutil.Process(7055)
    >>> p.name()
    'python'
    >>> p.exe()
    '/usr/bin/python'
    >>> p.cwd()
    '/home/giampaolo'
    >>> p.cmdline()
    ['/usr/bin/python', 'main.py']
    >>>
    >>> p.status()
    'running'
    >>> p.username()
    'giampaolo'
    >>> p.create_time()
    1267551141.5019531
    >>> p.terminal()
    '/dev/pts/0'
    >>>
    >>> p.uids()
    puids(real=1000, effective=1000, saved=1000)
    >>> p.gids()
    pgids(real=1000, effective=1000, saved=1000)
    >>>
    >>> p.cpu_times()
    pcputimes(user=1.02, system=0.31, children_user=0.32, children_system=0.1)
    >>> p.cpu_percent(interval=1.0)
    12.1
    >>> p.cpu_affinity()
    [0, 1, 2, 3]
    >>> p.cpu_affinity([0])  # set
    >>>
    >>> p.memory_percent()
    0.63423
    >>>
    >>> p.memory_info()
    pmem(rss=10915840, vms=67608576, shared=3313664, text=2310144, lib=0, data=7262208, dirty=0)
    >>>
    >>> p.memory_full_info()  # "real" USS memory usage (Linux, OSX, Win only)
    pfullmem(rss=10199040, vms=52133888, shared=3887104, text=2867200, lib=0, data=5967872, dirty=0, uss=6545408, pss=6872064, swap=0)
    >>>
    >>> p.memory_maps()
    [pmmap_grouped(path='/lib/x8664-linux-gnu/libutil-2.15.so', rss=32768, size=2125824, pss=32768, shared_clean=0, shared_dirty=0, private_clean=20480, private_dirty=12288, referenced=32768, anonymous=12288, swap=0),
     pmmap_grouped(path='/lib/x8664-linux-gnu/libc-2.15.so', rss=3821568, size=3842048, pss=3821568, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=3821568, referenced=3575808, anonymous=3821568, swap=0),
     pmmap_grouped(path='/lib/x8664-linux-gnu/libcrypto.so.0.1', rss=34124, rss=32768, size=2134016, pss=15360, shared_clean=24576, shared_dirty=0, private_clean=0, private_dirty=8192, referenced=24576, anonymous=8192, swap=0),
     pmmap_grouped(path='[heap]',  rss=32768, size=139264, pss=32768, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=32768, referenced=32768, anonymous=32768, swap=0),
     pmmap_grouped(path='[stack]', rss=2465792, size=2494464, pss=2465792, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=2465792, referenced=2277376, anonymous=2465792, swap=0),
     ...]
    >>>
    >>> p.io_counters()
    pio(read_count=478001, write_count=59371, read_bytes=700416, write_bytes=69632)
    >>>
    >>> p.open_files()
    [popenfile(path='/home/giampaolo/svn/psutil/setup.py', fd=3, position=0, mode='r', flags=32768),
     popenfile(path='/var/log/monitd', fd=4, position=235542, mode='a', flags=33793)]
    >>>
    >>> p.connections()
    [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 48776), raddr=('93.186.135.91', 80), status='ESTABLISHED'),
     pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 43761), raddr=('72.14.234.100', 80), status='CLOSING'),
     pconn(fd=119, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 60759), raddr=('72.14.234.104', 80), status='ESTABLISHED'),
     pconn(fd=123, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=('10.0.0.1', 51314), raddr=('72.14.234.83', 443), status='SYN_SENT')]
    >>>
    >>> p.num_threads()
    4
    >>> p.num_fds()
    8
    >>> p.threads()
    [pthread(id=5234, user_time=22.5, system_time=9.2891),
     pthread(id=5235, user_time=0.0, system_time=0.0),
     pthread(id=5236, user_time=0.0, system_time=0.0),
     pthread(id=5237, user_time=0.0707, system_time=1.1)]
    >>>
    >>> p.num_ctx_switches()
    pctxsw(voluntary=78, involuntary=19)
    >>>
    >>> p.nice()
    0
    >>> p.nice(10)  # set
    >>>
    >>> p.ionice(psutil.IOPRIO_CLASS_IDLE)  # IO priority (Win and Linux only)
    >>> p.ionice()
    pionice(ioclass=<IOPriority.IOPRIO_CLASS_IDLE: 3>, value=0)
    >>>
    >>> p.rlimit(psutil.RLIMIT_NOFILE, (5, 5))  # set resource limits (Linux only)
    >>> p.rlimit(psutil.RLIMIT_NOFILE)
    (5, 5)
    >>>
    >>> p.environ()
    {'LC_PAPER': 'it_IT.UTF-8', 'SHELL': '/bin/bash', 'GREP_OPTIONS': '--color=auto',
    'XDG_CONFIG_DIRS': '/etc/xdg/xdg-ubuntu:/usr/share/upstart/xdg:/etc/xdg', 'COLORTERM': 'gnome-terminal',
     ...}
    >>>
    >>> p.suspend()
    >>> p.resume()
    >>>
    >>> p.terminate()
    >>> p.wait(timeout=3)
    0
    >>>
    >>> psutil.test()
    USER         PID %CPU %MEM     VSZ     RSS TTY        START    TIME  COMMAND
    root           1  0.0  0.0   24584    2240            Jun17   00:00  init
    root           2  0.0  0.0       0       0            Jun17   00:00  kthreadd
    root           3  0.0  0.0       0       0            Jun17   00:05  ksoftirqd/0
    ...
    giampaolo  31475  0.0  0.0   20760    3024 /dev/pts/0 Jun19   00:00  python2.4
    giampaolo  31721  0.0  2.2  773060  181896            00:04   10:30  chrome
    root       31763  0.0  0.0       0       0            00:05   00:00  kworker/0:1
    >>>

Further process APIs
====================

.. code-block:: python

    >>> for p in psutil.process_iter():
    ...     print(p)
    ...
    psutil.Process(pid=1, name='init')
    psutil.Process(pid=2, name='kthreadd')
    psutil.Process(pid=3, name='ksoftirqd/0')
    ...
    >>>
    >>> def on_terminate(proc):
    ...     print("process {} terminated".format(proc))
    ...
    >>> # waits for multiple processes to terminate
    >>> gone, alive = psutil.wait_procs(procs_list, timeout=3, callback=on_terminate)
    >>>

Windows services
================

.. code-block:: python

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

======
Donate
======

A lot of time and effort went into making psutil as it is right now.
If you feel psutil is useful to you or your business and want to support its future development please consider donating me (`Giampaolo Rodola' <http://grodola.blogspot.com/p/about.html>`_) some money.
I only ask for a small donation, but of course I appreciate any amount.

.. image:: http://www.paypal.com/en_US/i/btn/x-click-but04.gif
    :target: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A9ZS7PKKRM3S8
    :alt: Donate via PayPal

Don't want to donate money? Then maybe you could `write me a recommendation on Linkedin <http://www.linkedin.com/in/grodola>`_.

============
Mailing list
============

http://groups.google.com/group/psutil/

========
Timeline
========

- 2016-03-12: `psutil-4.1.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-4.1.0.tar.gz>`_
- 2016-02-17: `psutil-4.0.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-4.0.0.tar.gz>`_
- 2016-01-20: `psutil-3.4.2.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.4.2.tar.gz>`_
- 2016-01-15: `psutil-3.4.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.4.1.tar.gz>`_
- 2015-11-25: `psutil-3.3.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.3.0.tar.gz>`_
- 2015-10-04: `psutil-3.2.2.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.2.2.tar.gz>`_
- 2015-09-03: `psutil-3.2.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.2.1.tar.gz>`_
- 2015-09-02: `psutil-3.2.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.2.0.tar.gz>`_
- 2015-07-15: `psutil-3.1.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.1.1.tar.gz>`_
- 2015-07-15: `psutil-3.1.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.1.0.tar.gz>`_
- 2015-06-18: `psutil-3.0.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.0.1.tar.gz>`_
- 2015-06-13: `psutil-3.0.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-3.0.0.tar.gz>`_
- 2015-02-02: `psutil-2.2.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.2.1.tar.gz>`_
- 2015-01-06: `psutil-2.2.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.2.0.tar.gz>`_
- 2014-09-26: `psutil-2.1.3.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.1.3.tar.gz>`_
- 2014-09-21: `psutil-2.1.2.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.1.2.tar.gz>`_
- 2014-04-30: `psutil-2.1.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.1.1.tar.gz>`_
- 2014-04-08: `psutil-2.1.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.1.0.tar.gz>`_
- 2014-03-10: `psutil-2.0.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-2.0.0.tar.gz>`_
- 2013-11-25: `psutil-1.2.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.2.1.tar.gz>`_
- 2013-11-20: `psutil-1.2.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.2.0.tar.gz>`_
- 2013-11-07: `psutil-1.1.3.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.1.3.tar.gz>`_
- 2013-10-22: `psutil-1.1.2.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.1.2.tar.gz>`_
- 2013-10-08: `psutil-1.1.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.1.1.tar.gz>`_
- 2013-09-28: `psutil-1.1.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.1.0.tar.gz>`_
- 2013-07-12: `psutil-1.0.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.0.1.tar.gz>`_
- 2013-07-10: `psutil-1.0.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-1.0.0.tar.gz>`_
- 2013-05-03: `psutil-0.7.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.7.1.tar.gz>`_
- 2013-04-12: `psutil-0.7.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.7.0.tar.gz>`_
- 2012-08-16: `psutil-0.6.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.6.1.tar.gz>`_
- 2012-08-13: `psutil-0.6.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.6.0.tar.gz>`_
- 2012-06-29: `psutil-0.5.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.5.1.tar.gz>`_
- 2012-06-27: `psutil-0.5.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.5.0.tar.gz>`_
- 2011-12-14: `psutil-0.4.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.4.1.tar.gz>`_
- 2011-10-29: `psutil-0.4.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.4.0.tar.gz>`_
- 2011-07-08: `psutil-0.3.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.3.0.tar.gz>`_
- 2011-03-20: `psutil-0.2.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.2.1.tar.gz>`_
- 2010-11-13: `psutil-0.2.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.2.0.tar.gz>`_
- 2010-03-02: `psutil-0.1.3.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.1.3.tar.gz>`_
- 2009-05-06: `psutil-0.1.2.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.1.2.tar.gz>`_
- 2009-03-06: `psutil-0.1.1.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.1.1.tar.gz>`_
- 2009-01-27: `psutil-0.1.0.tar.gz <https://pypi.python.org/packages/source/p/psutil/psutil-0.1.0.tar.gz>`_
