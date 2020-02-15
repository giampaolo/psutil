|  |downloads| |stars| |forks| |contributors| |coverage| |quality|
|  |version| |py-versions| |packages| |license|
|  |travis| |appveyor| |cirrus| |doc| |twitter| |tidelift|

.. |downloads| image:: https://img.shields.io/pypi/dm/psutil.svg
    :target: https://pepy.tech/project/psutil
    :alt: Downloads

.. |stars| image:: https://img.shields.io/github/stars/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/stargazers
    :alt: Github stars

.. |forks| image:: https://img.shields.io/github/forks/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/network/members
    :alt: Github forks

.. |contributors| image:: https://img.shields.io/github/contributors/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/graphs/contributors
    :alt: Contributors

.. |quality| image:: https://img.shields.io/codacy/grade/ce63e7f7f69d44b5b59682196e6fbfca.svg
    :target: https://www.codacy.com/app/g-rodola/psutil?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=giampaolo/psutil&amp;utm_campaign=Badge_Grade
    :alt: Code quality

.. |travis| image:: https://img.shields.io/travis/giampaolo/psutil/master.svg?maxAge=3600&label=Linux,%20OSX,%20PyPy
    :target: https://travis-ci.org/giampaolo/psutil
    :alt: Linux tests (Travis)

.. |appveyor| image:: https://img.shields.io/appveyor/ci/giampaolo/psutil/master.svg?maxAge=3600&label=Windows
    :target: https://ci.appveyor.com/project/giampaolo/psutil
    :alt: Windows tests (Appveyor)

.. |cirrus| image:: https://img.shields.io/cirrus/github/giampaolo/psutil?label=FreeBSD
    :target: https://cirrus-ci.com/github/giampaolo/psutil-cirrus-ci
    :alt: FreeBSD tests (Cirrus-Ci)

.. |coverage| image:: https://img.shields.io/coveralls/github/giampaolo/psutil.svg?label=test%20coverage
    :target: https://coveralls.io/github/giampaolo/psutil?branch=master
    :alt: Test coverage (coverall.io)

.. |doc| image:: https://readthedocs.org/projects/psutil/badge/?version=latest
    :target: http://psutil.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. |version| image:: https://img.shields.io/pypi/v/psutil.svg?label=pypi
    :target: https://pypi.org/project/psutil
    :alt: Latest version

.. |py-versions| image:: https://img.shields.io/pypi/pyversions/psutil.svg
    :target: https://pypi.org/project/psutil
    :alt: Supported Python versions

.. |packages| image:: https://repology.org/badge/tiny-repos/python:psutil.svg
    :target: https://repology.org/metapackage/python:psutil/versions
    :alt: Binary packages

.. |license| image:: https://img.shields.io/pypi/l/psutil.svg
    :target: https://github.com/giampaolo/psutil/blob/master/LICENSE
    :alt: License

.. |twitter| image:: https://img.shields.io/twitter/follow/grodola.svg?label=follow&style=flat&logo=twitter&logoColor=4FADFF
    :target: https://twitter.com/grodola
    :alt: Twitter Follow

.. |tidelift| image:: https://tidelift.com/badges/github/giampaolo/psutil?style=flat
    :target: https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme
    :alt: Tidelift

-----

Quick links
===========

- `Home page <https://github.com/giampaolo/psutil>`_
- `Install <https://github.com/giampaolo/psutil/blob/master/INSTALL.rst>`_
- `Documentation <http://psutil.readthedocs.io>`_
- `Download <https://pypi.org/project/psutil/#files>`_
- `Forum <http://groups.google.com/group/psutil/topics>`_
- `StackOverflow <https://stackoverflow.com/questions/tagged/psutil>`_
- `Blog <http://grodola.blogspot.com/search/label/psutil>`_
- `Development guide <https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst>`_
- `What's new <https://github.com/giampaolo/psutil/blob/master/HISTORY.rst>`_

Summary
=======

psutil (process and system utilities) is a cross-platform library for
retrieving information on **running processes** and **system utilization**
(CPU, memory, disks, network, sensors) in Python.
It is useful mainly for **system monitoring**, **profiling and limiting process
resources** and **management of running processes**.
It implements many functionalities offered by classic UNIX command line tools
such as *ps, top, iotop, lsof, netstat, ifconfig, free* and others.
psutil currently supports the following platforms:

- **Linux**
- **Windows**
- **macOS**
- **FreeBSD, OpenBSD**, **NetBSD**
- **Sun Solaris**
- **AIX**

...both **32-bit** and **64-bit** architectures. Supported Python versions are **2.6**, **2.7** and **3.4+**. `PyPy3 <http://pypy.org/>`__ is also known to work.

psutil for enterprise
=====================

.. |tideliftlogo| image:: https://nedbatchelder.com/pix/Tidelift_Logos_RGB_Tidelift_Shorthand_On-White_small.png
   :width: 150
   :alt: Tidelift
   :target: https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme

.. list-table::
   :widths: 10 150

   * - |tideliftlogo|
     - The maintainer of psutil and thousands of other packages are working
       with Tidelift to deliver commercial support and maintenance for the open
       source dependencies you use to build your applications. Save time,
       reduce risk, and improve code health, while paying the maintainers of
       the exact dependencies you use.
       `Learn more <https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=enterprise&utm_term=repo>`__.

       By subscribing to Tidelift you will help me (`Giampaolo Rodola`_) support
       psutil future development. Alternatively consider making a small
       `donation`_.

Security
========

To report a security vulnerability, please use the `Tidelift security
contact`_.  Tidelift will coordinate the fix and disclosure.

Example applications
====================

+------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| .. image:: https://github.com/giampaolo/psutil/blob/master/docs/_static/procinfo-small.png     | .. image:: https://github.com/giampaolo/psutil/blob/master/docs/_static/top-small.png      |
|    :target: https://github.com/giampaolo/psutil/blob/master/docs/_static/procinfo.png          |     :target: https://github.com/giampaolo/psutil/blob/master/docs/_static/top.png          |
+------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+
| .. image:: https://github.com/giampaolo/psutil/blob/master/docs/_static/procsmem-small.png     | .. image:: https://github.com/giampaolo/psutil/blob/master/docs/_static/pmap-small.png     |
|     :target: https://github.com/giampaolo/psutil/blob/master/docs/_static/procsmem.png         |     :target: https://github.com/giampaolo/psutil/blob/master/docs/_static/pmap.png         |
+------------------------------------------------------------------------------------------------+--------------------------------------------------------------------------------------------+

Also see `scripts directory <https://github.com/giampaolo/psutil/tree/master/scripts>`__
and `doc recipes <http://psutil.readthedocs.io/#recipes/>`__.

Projects using psutil
=====================

psutil has roughly the following monthly downloads:

.. image:: https://img.shields.io/pypi/dm/psutil.svg
    :target: https://pepy.tech/project/psutil
    :alt: Downloads

There are over
`10.000 open source projects <https://libraries.io/pypi/psutil/dependent_repositories?page=1>`__
on github which depend from psutil.
Here's some I find particularly interesting:

- https://github.com/google/grr
- https://github.com/facebook/osquery/
- https://github.com/nicolargo/glances
- https://github.com/Jahaja/psdash
- https://github.com/ajenti/ajenti
- https://github.com/home-assistant/home-assistant/


Portings
========

- Go: https://github.com/shirou/gopsutil
- C: https://github.com/hamon-in/cpslib
- Rust: https://github.com/borntyping/rust-psutil
- Nim: https://github.com/johnscillieri/psutil-nim


Example usages
==============

This represents pretty much the whole psutil API.

CPU
---

.. code-block:: python

    >>> import psutil
    >>>
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
    >>>
    >>> psutil.cpu_freq()
    scpufreq(current=931.42925, min=800.0, max=3500.0)
    >>>
    >>> psutil.getloadavg()  # also on Windows (emulated)
    (3.14, 3.89, 4.67)

Memory
------

.. code-block:: python

    >>> psutil.virtual_memory()
    svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120, free=2181107712, active=4748992512, inactive=2758115328, buffers=790724608, cached=3500347392, shared=787554304)
    >>> psutil.swap_memory()
    sswap(total=2097147904, used=296128512, free=1801019392, percent=14.1, sin=304193536, sout=677842944)
    >>>

Disks
-----

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
-------

.. code-block:: python

    >>> psutil.net_io_counters(pernic=True)
    {'eth0': netio(bytes_sent=485291293, bytes_recv=6004858642, packets_sent=3251564, packets_recv=4787798, errin=0, errout=0, dropin=0, dropout=0),
     'lo': netio(bytes_sent=2838627, bytes_recv=2838627, packets_sent=30567, packets_recv=30567, errin=0, errout=0, dropin=0, dropout=0)}
    >>>
    >>> psutil.net_connections()
    [sconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status='ESTABLISHED', pid=1254),
     sconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=43761), raddr=addr(ip='72.14.234.100', port=80), status='CLOSING', pid=2987),
     ...]
    >>>
    >>> psutil.net_if_addrs()
    {'lo': [snicaddr(family=<AddressFamily.AF_INET: 2>, address='127.0.0.1', netmask='255.0.0.0', broadcast='127.0.0.1', ptp=None),
            snicaddr(family=<AddressFamily.AF_INET6: 10>, address='::1', netmask='ffff:ffff:ffff:ffff:ffff:ffff:ffff:ffff', broadcast=None, ptp=None),
            snicaddr(family=<AddressFamily.AF_LINK: 17>, address='00:00:00:00:00:00', netmask=None, broadcast='00:00:00:00:00:00', ptp=None)],
     'wlan0': [snicaddr(family=<AddressFamily.AF_INET: 2>, address='192.168.1.3', netmask='255.255.255.0', broadcast='192.168.1.255', ptp=None),
               snicaddr(family=<AddressFamily.AF_INET6: 10>, address='fe80::c685:8ff:fe45:641%wlan0', netmask='ffff:ffff:ffff:ffff::', broadcast=None, ptp=None),
               snicaddr(family=<AddressFamily.AF_LINK: 17>, address='c4:85:08:45:06:41', netmask=None, broadcast='ff:ff:ff:ff:ff:ff', ptp=None)]}
    >>>
    >>> psutil.net_if_stats()
    {'lo': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_UNKNOWN: 0>, speed=0, mtu=65536),
     'wlan0': snicstats(isup=True, duplex=<NicDuplex.NIC_DUPLEX_FULL: 2>, speed=100, mtu=1500)}
    >>>

Sensors
-------

.. code-block:: python

    >>> import psutil
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
-----------------

.. code-block:: python

    >>> import psutil
    >>> psutil.users()
    [suser(name='giampaolo', terminal='pts/2', host='localhost', started=1340737536.0, pid=1352),
     suser(name='giampaolo', terminal='pts/3', host='localhost', started=1340737792.0, pid=1788)]
    >>>
    >>> psutil.boot_time()
    1365519115.0
    >>>

Process management
------------------

.. code-block:: python

    >>> import psutil
    >>> psutil.pids()
    [1, 2, 3, 4, 5, 6, 7, 46, 48, 50, 51, 178, 182, 222, 223, 224, 268, 1215, 1216, 1220, 1221, 1243, 1244,
     1301, 1601, 2237, 2355, 2637, 2774, 3932, 4176, 4177, 4185, 4187, 4189, 4225, 4243, 4245, 4263, 4282,
     4306, 4311, 4312, 4313, 4314, 4337, 4339, 4357, 4358, 4363, 4383, 4395, 4408, 4433, 4443, 4445, 4446,
     5167, 5234, 5235, 5252, 5318, 5424, 5644, 6987, 7054, 7055, 7071]
    >>>
    >>> p = psutil.Process(7055)
    >>> p
    psutil.Process(pid=7055, name='python', started='09:04:44')
    >>> p.name()
    'python'
    >>> p.exe()
    '/usr/bin/python'
    >>> p.cwd()
    '/home/giampaolo'
    >>> p.cmdline()
    ['/usr/bin/python', 'main.py']
    >>>
    >>> p.pid
    7055
    >>> p.ppid()
    7054
    >>> p.children(recursive=True)
    [psutil.Process(pid=29835, name='python2.7', started='11:45:38'),
     psutil.Process(pid=29836, name='python2.7', started='11:43:39')]
    >>>
    >>> p.parent()
    psutil.Process(pid=4699, name='bash', started='09:06:44')
    >>> p.parents()
    [psutil.Process(pid=4699, name='bash', started='09:06:44'),
     psutil.Process(pid=4689, name='gnome-terminal-server', started='0:06:44'),
     psutil.Process(pid=1, name='systemd', started='05:56:55')]
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
    pcputimes(user=1.02, system=0.31, children_user=0.32, children_system=0.1, iowait=0.0)
    >>> p.cpu_percent(interval=1.0)
    12.1
    >>> p.cpu_affinity()
    [0, 1, 2, 3]
    >>> p.cpu_affinity([0, 1])  # set
    >>> p.cpu_num()
    1
    >>>
    >>> p.memory_info()
    pmem(rss=10915840, vms=67608576, shared=3313664, text=2310144, lib=0, data=7262208, dirty=0)
    >>> p.memory_full_info()  # "real" USS memory usage (Linux, macOS, Win only)
    pfullmem(rss=10199040, vms=52133888, shared=3887104, text=2867200, lib=0, data=5967872, dirty=0, uss=6545408, pss=6872064, swap=0)
    >>> p.memory_percent()
    0.7823
    >>> p.memory_maps()
    [pmmap_grouped(path='/lib/x8664-linux-gnu/libutil-2.15.so', rss=32768, size=2125824, pss=32768, shared_clean=0, shared_dirty=0, private_clean=20480, private_dirty=12288, referenced=32768, anonymous=12288, swap=0),
     pmmap_grouped(path='/lib/x8664-linux-gnu/libc-2.15.so', rss=3821568, size=3842048, pss=3821568, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=3821568, referenced=3575808, anonymous=3821568, swap=0),
     pmmap_grouped(path='[heap]',  rss=32768, size=139264, pss=32768, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=32768, referenced=32768, anonymous=32768, swap=0),
     pmmap_grouped(path='[stack]', rss=2465792, size=2494464, pss=2465792, shared_clean=0, shared_dirty=0, private_clean=0, private_dirty=2465792, referenced=2277376, anonymous=2465792, swap=0),
     ...]
    >>>
    >>> p.io_counters()
    pio(read_count=478001, write_count=59371, read_bytes=700416, write_bytes=69632, read_chars=456232, write_chars=517543)
    >>>
    >>> p.open_files()
    [popenfile(path='/home/giampaolo/monit.py', fd=3, position=0, mode='r', flags=32768),
     popenfile(path='/var/log/monit.log', fd=4, position=235542, mode='a', flags=33793)]
    >>>
    >>> p.connections()
    [pconn(fd=115, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status='ESTABLISHED'),
     pconn(fd=117, family=<AddressFamily.AF_INET: 2>, type=<SocketType.SOCK_STREAM: 1>, laddr=addr(ip='10.0.0.1', port=43761), raddr=addr(ip='72.14.234.100', port=80), status='CLOSING')]
    >>>
    >>> p.num_threads()
    4
    >>> p.num_fds()
    8
    >>> p.threads()
    [pthread(id=5234, user_time=22.5, system_time=9.2891),
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
    'XDG_CONFIG_DIRS': '/etc/xdg/xdg-ubuntu:/usr/share/upstart/xdg:/etc/xdg',
     ...}
    >>>
    >>> p.as_dict()
    {'status': 'running', 'num_ctx_switches': pctxsw(voluntary=63, involuntary=1), 'pid': 5457, ...}
    >>> p.is_running()
    True
    >>> p.suspend()
    >>> p.resume()
    >>>
    >>> p.terminate()
    >>> p.kill()
    >>> p.wait(timeout=3)
    0
    >>>
    >>> psutil.test()
    USER         PID %CPU %MEM     VSZ     RSS TTY        START    TIME  COMMAND
    root           1  0.0  0.0   24584    2240            Jun17   00:00  init
    root           2  0.0  0.0       0       0            Jun17   00:00  kthreadd
    ...
    giampaolo  31475  0.0  0.0   20760    3024 /dev/pts/0 Jun19   00:00  python2.4
    giampaolo  31721  0.0  2.2  773060  181896            00:04   10:30  chrome
    root       31763  0.0  0.0       0       0            00:05   00:00  kworker/0:1
    >>>

Further process APIs
--------------------

.. code-block:: python

    >>> import psutil
    >>> for proc in psutil.process_iter(['pid', 'name']):
    ...     print(proc.info)
    ...
    {'pid': 1, 'name': 'systemd'}
    {'pid': 2, 'name': 'kthreadd'}
    {'pid': 3, 'name': 'ksoftirqd/0'}
    ...
    >>>
    >>> psutil.pid_exists(3)
    True
    >>>
    >>> def on_terminate(proc):
    ...     print("process {} terminated".format(proc))
    ...
    >>> # waits for multiple processes to terminate
    >>> gone, alive = psutil.wait_procs(procs_list, timeout=3, callback=on_terminate)
    >>>

Popen wrapper:

.. code-block:: python

    >>> import psutil
    >>> from subprocess import PIPE
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

Windows services
----------------

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


.. _`Giampaolo Rodola`: http://grodola.blogspot.com/p/about.html
.. _`donation`: https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A9ZS7PKKRM3S8
.. _Tidelift security contact: https://tidelift.com/security
.. _Tidelift Subscription: https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme

