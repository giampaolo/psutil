.. <PYPI-EXCLUDE>

.. raw:: html

    <div align="center">
        <a href="https://github.com/giampaolo/psutil"><img src="https://github.com/giampaolo/psutil/raw/master/docs/_static/images/logo-psutil-readme.svg" alt="psutil" /></a>
        <p align="center">Process and System Utilities for Python</p>
        <a href="https://psutil.readthedocs.io"><b>Documentation</b></a>&nbsp;&nbsp;&nbsp;
        <a href="https://psutil.io/blog/"><b>Blog</b></a>&nbsp;&nbsp;&nbsp;
        <a href="https://psutil.io/adoption/"><b>Who uses psutil</b></a>&nbsp;&nbsp;&nbsp;
    </div>

    <br/>

    <div align="center">
      <a href="https://clickpy.clickhouse.com/dashboard/psutil">
        <img src="https://static.pepy.tech/badge/psutil/month" alt="Downloads">
      </a>

      <a href="https://repology.org/metapackage/python:psutil/versions">
        <img src="https://repology.org/badge/tiny-repos/python:psutil.svg" alt="Binary packages">
      </a>

      <a href="https://pypi.org/project/psutil">
        <img src="https://img.shields.io/pypi/v/psutil.svg?label=pypi&color=yellowgreen" alt="Latest version">
      </a>

      <a href="https://github.com/giampaolo/psutil/actions/workflows/build.yml">
        <img src="https://github.com/giampaolo/psutil/actions/workflows/build.yml/badge.svg" alt="Linux, macOS, Windows">
      </a>

      <a href="https://github.com/giampaolo/psutil/actions/workflows/bsd.yml">
        <img src="https://github.com/giampaolo/psutil/actions/workflows/bsd.yml/badge.svg" alt="FreeBSD, NetBSD, OpenBSD">
      </a>

      <a href="https://github.com/giampaolo/psutil/actions/workflows/docs.yml">
        <img src="https://github.com/giampaolo/psutil/actions/workflows/docs.yml/badge.svg" alt="Documentation">
      </a>
    </div>

.. </PYPI-EXCLUDE>

About
=====

psutil is a cross-platform library for retrieving information about running
**processes** and **system utilization** (CPU, memory, disks, network, sensors)
in Python. It is useful mainly for **system monitoring**, **profiling**,
**limiting process resources**, and **managing running processes**.

It implements many functionalities offered by UNIX command line tool such as
*ps, top, free, iotop, netstat, ifconfig, lsof* and others (see
`shell equivalents`_). psutil supports the following platforms:

- **Linux**
- **Windows**
- **macOS**
- **FreeBSD, OpenBSD**, **NetBSD**
- **Sun Solaris**
- **AIX**

Adoption
========

psutil is among the
`top 100 <https://clickpy.clickhouse.com/dashboard/psutil>`__ most-downloaded
packages on PyPI, with **370+ million** downloads per month and **780,000+**
`GitHub repositories <https://github.com/giampaolo/psutil/network/dependents>`__
using it.

See also `adoptions <https://psutil.io/adoption/>`__ and
`alternatives <https://psutil.io/alternatives/>`__.

Install
=======

.. code-block::

    pip install psutil

For platform-specific details see `installation <https://psutil.io/install/>`_.

Documentation
=============

psutil documentation is available at https://psutil.io.

.. <PYPI-EXCLUDE>

Sponsors
========

.. raw:: html

    <table border="0" cellpadding="10" cellspacing="0" class="sponsor-table">
      <tr>
        <td align="center" style="vertical-align: middle;">
          <a href="https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme">
            <img width="160" src="https://raw.githubusercontent.com/giampaolo/psutil/refs/heads/master/docs/_static/images/logo-tidelift.svg" class="sponsor-logo">
          </a>
        </td>
        <td align="center" style="vertical-align: middle;">
          <a href="https://sansec.io/">
            <img width="145" src="https://raw.githubusercontent.com/giampaolo/psutil/refs/heads/master/docs/_static/images/logo-sansec.svg" class="sponsor-logo">
          </a>
        </td>
        <td align="center" style="vertical-align: middle;">
          <a href="https://www.apivoid.com/">
            <img width="130" src="https://raw.githubusercontent.com/giampaolo/psutil/refs/heads/master/docs/_static/images/logo-apivoid.svg" class="sponsor-logo">
          </a>
        </td>
      </tr>
    </table>

    <div style="text-align: center;"><sup><a href="https://psutil.io/funding/">add your logo</a></sup></div>

.. </PYPI-EXCLUDE>

Example usages
==============

For the full API with more examples, see the
`API overview <https://psutil.io/api-overview/>`_ and
`API reference <https://psutil.io/api/>`_.

**CPU**

.. code-block:: python

    >>> import psutil
    >>> psutil.cpu_percent(interval=1, percpu=True)
    [4.0, 6.9, 3.7, 9.2]
    >>> psutil.cpu_count(logical=False)
    2
    >>> psutil.cpu_freq()
    scpufreq(current=931.42, min=800.0, max=3500.0)

**Memory**

.. code-block:: python

    >>> psutil.virtual_memory()
    svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120, free=2181107712, ...)
    >>> psutil.swap_memory()
    sswap(total=2097147904, used=296128512, free=1801019392, percent=14.1, sin=304193536, sout=677842944)

**Disks**

.. code-block:: python

    >>> psutil.disk_partitions()
    [sdiskpart(device='/dev/sda1', mountpoint='/', fstype='ext4', opts='rw,nosuid'),
     sdiskpart(device='/dev/sda2', mountpoint='/home', fstype='ext', opts='rw')]
    >>> psutil.disk_usage('/')
    sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)

**Network**

.. code-block:: python

    >>> psutil.net_io_counters(pernic=True)
    {'eth0': netio(bytes_sent=485291293, bytes_recv=6004858642, ...),
     'lo': netio(bytes_sent=2838627, bytes_recv=2838627, ...)}
    >>> psutil.net_connections(kind='tcp')
    [sconn(fd=115, family=2, type=1, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status='ESTABLISHED', pid=1254),
     ...]

**Sensors**

.. code-block:: python

    >>> psutil.sensors_temperatures()
    {'coretemp': [shwtemp(label='Physical id 0', current=52.0, high=100.0, critical=100.0),
                  shwtemp(label='Core 0', current=45.0, high=100.0, critical=100.0)]}
    >>> psutil.sensors_battery()
    sbattery(percent=93, secsleft=16628, power_plugged=False)

**Processes**

.. code-block:: python

    >>> p = psutil.Process(7055)
    >>> p.name()
    'python3'
    >>> p.exe()
    '/usr/bin/python3'
    >>> p.cpu_percent(interval=1.0)
    12.1
    >>> p.memory_info()
    pmem(rss=3164160, vms=4410163, shared=897433, text=302694, data=2422374)
    >>> p.net_connections(kind='tcp')
    [pconn(fd=115, family=2, type=1, laddr=addr(ip='10.0.0.1', port=48776), raddr=addr(ip='93.186.135.91', port=80), status='ESTABLISHED')]
    >>> p.open_files()
    [popenfile(path='/home/giampaolo/monit.py', fd=3, position=0, mode='r', flags=32768)]
    >>>
    >>> for p in psutil.process_iter(['pid', 'name']):
    ...     print(p.pid, p.name())
    ...
    1 systemd
    2 kthreadd
    3 ksoftirqd/0
    ...

.. _`shell equivalents`: https://psutil.io/shell-equivalents/

.. <PYPI-EXCLUDE>

License
=======

BSD-3
