.. <PYPI-EXCLUDE>

.. raw:: html

    <div align="center">
        <a href="https://github.com/giampaolo/psutil"><img src="https://github.com/giampaolo/psutil/raw/doc-reorg/docs/_static/images/logo-psutil-readme.svg" alt="psutil" /></a>
        <p align="center">Process and System Utilities for Python</p>
        <a href="https://psutil.readthedocs.io/"><b>Documentation</b></a>&nbsp;&nbsp;&nbsp;
        <a href="https://gmpy.dev/tags/psutil"><b>Blog</b></a>&nbsp;&nbsp;&nbsp;
        <a href="https://psutil.readthedocs.io/latest/adoption.html"><b>Who uses psutil</b></a>&nbsp;&nbsp;&nbsp;
    </div>

    <br/>

    <div align="center">
      <a href="https://clickpy.clickhouse.com/dashboard/psutil">
        <img src="https://img.shields.io/pypi/dm/psutil?label=downloads" alt="Downloads">
      </a>

      <a href="https://repology.org/metapackage/python:psutil/versions">
        <img src="https://repology.org/badge/tiny-repos/python:psutil.svg" alt="Binary packages">
      </a>

      <a href="https://pypi.org/project/psutil">
        <img src="https://img.shields.io/pypi/v/psutil.svg?label=pypi&color=yellowgreen" alt="Latest version">
      </a>

      <a href="https://github.com/giampaolo/psutil/actions?query=workflow%3Abuild">
        <img src="https://img.shields.io/github/actions/workflow/status/giampaolo/psutil/.github/workflows/build.yml.svg?label=Linux%2C%20macOS%2C%20Win" alt="Linux, macOS, Windows">
      </a>

      <a href="https://github.com/giampaolo/psutil/actions?query=workflow%3Absd-tests">
        <img src="https://img.shields.io/github/actions/workflow/status/giampaolo/psutil/.github/workflows/bsd.yml.svg?label=BSD" alt="FreeBSD, NetBSD, OpenBSD">
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

Install
=======

.. code-block::

    pip install psutil

For platform-specific details see
`installation <https://psutil.readthedocs.io/latest/install.html>`_.


Documentation
=============

psutil documentation is available at https://psutil.readthedocs.io/.

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

    <div style="text-align: center;"><sup><a href="https://psutil.readthedocs.io/latest/funding.html">add your logo</a></sup></div>

.. </PYPI-EXCLUDE>

Projects using psutil
=====================

psutil is one of the `top 100`_ most-downloaded packages on PyPI, with 300+
million downloads per month, `760,000+ GitHub repositories
<https://github.com/giampaolo/psutil/network/dependents>`_ using it, and
14,000+ packages depending on it. Some notable projects using psutil:

- `TensorFlow <https://github.com/tensorflow/tensorflow>`_,
  `PyTorch <https://github.com/pytorch/pytorch>`_,
- `Home Assistant <https://github.com/home-assistant/core>`_,
  `Ansible <https://github.com/ansible/ansible>`_,
  `Apache Airflow <https://github.com/apache/airflow>`_,
  `Sentry <https://github.com/getsentry/sentry>`_
- `Celery <https://github.com/celery/celery>`_,
  `Dask <https://github.com/dask/dask>`_
- `Glances <https://github.com/nicolargo/glances>`_,
  `bpytop <https://github.com/aristocratos/bpytop>`_,
  `Ajenti <https://github.com/ajenti/ajenti>`_,
  `GRR <https://github.com/google/grr>`_

`Full list <https://psutil.readthedocs.io/latest/adoption.html>`_

Example usages
==============

For the full API with more examples, see the
`API overview <https://psutil.readthedocs.io/latest/api-overview.html>`_ and
`API reference <https://psutil.readthedocs.io/latest/api.html>`_.

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

.. _`shell equivalents`: https://psutil.readthedocs.io/latest/shell-equivalents.html
.. _`top 100`: https://clickpy.clickhouse.com/dashboard/psutil

.. <PYPI-EXCLUDE>

Supporters
==========

People who donated money over the years:

.. raw:: html

    <div>
      <a href="https://github.com/codingjoe"><img height="35" width="35" title="Johannes Maron" src="https://avatars.githubusercontent.com/u/1772890?v=4" /></a>
      <a href="https://github.com/eallrich"><img height="35" width="35" title="Evan Allrich" src="https://avatars.githubusercontent.com/u/17393?v=4" /></a>
      <a href="https://github.com/ofek"><img height="35" width="35" title="Ofek Lev" src="https://avatars.githubusercontent.com/u/9677399?v=4" /></a>
      <a href="https://github.com/roboflow"><img height="35" width="35" title="roboflow.com" src="https://avatars.githubusercontent.com/u/53104118?s=200&v=4" /></a>
      <a href="https://github.com/sansecio"><img height="35" width="35" title="sansec.io" src="https://avatars.githubusercontent.com/u/60706188?s=200&v=4" /></a>
      <a href="https://github.com/Trash-Nothing"><img height="35" width="35" title="trashnothing.com" src="https://avatars.githubusercontent.com/u/230028908?s=200&v=4" /></a>

      <a href="https://github.com/abramov-v"><img height="35" width="35" title="Valeriy Abramov" src="https://avatars.githubusercontent.com/u/76448042?v=4" /></a>
      <a href="https://github.com/alexdlaird"><img height="35" width="35" title="Alex Laird" src="https://avatars.githubusercontent.com/u/1660326?v=4" /></a>
      <a href="https://github.com/aristocratos"><img height="35" width="35" title="aristocratos" src="https://avatars3.githubusercontent.com/u/59659483?s=96&amp;v=4" /></a>
      <a href="https://github.com/ArtyomVancyan"><img height="35" width="35" title="Artyom Vancyan" src="https://avatars.githubusercontent.com/u/44609997?v=4" /></a>
      <a href="https://github.com/c0m4r"><img height="35" width="35" title="c0m4r" src="https://avatars.githubusercontent.com/u/6292788?v=4" /></a>
      <a href="https://github.com/coskundeniz"><img height="35" width="35" title="Coşkun Deniz" src="https://avatars.githubusercontent.com/u/4516210?v=4" /></a>
      <a href="https://github.com/cybersecgeek"><img height="35" width="35" title="cybersecgeek" src="https://avatars.githubusercontent.com/u/12847926?v=4" /></a>
      <a href="https://github.com/dbwiddis"><img height="35" width="35" title="Daniel Widdis" src="https://avatars1.githubusercontent.com/u/9291703?s=88&amp;v=4" /></a>
      <a href="https://github.com/getsentry"><img height="35" width="35" title="getsentry" src="https://avatars.githubusercontent.com/u/1396951?s=200&v=4" /></a>
      <a href="https://github.com/great-work-told-is"><img height="35" width="35" title="great-work-told-is" src="https://avatars.githubusercontent.com/u/113922084?v=4" /></a>
      <a href="https://github.com/guilt"><img height="35" width="35" title="Karthik Kumar Viswanathan" src="https://avatars.githubusercontent.com/u/195178?v=4" /></a>
      <a href="https://github.com/inarikami"><img height="35" width="35" title="inarikami" src="https://avatars.githubusercontent.com/u/22864465?v=4" /></a>
      <a href="https://github.com/indeedeng"><img height="35" width="35" title="indeedeng" src="https://avatars.githubusercontent.com/u/2905043?s=200&v=4" /></a>
      <a href="https://github.com/JeremyGrosser"><img height="35" width="35" title="JeremyGrosser" src="https://avatars.githubusercontent.com/u/2151?v=4" /></a>
      <a href="https://github.com/maxesisn"><img height="35" width="35" title="Maximilian Wu" src="https://avatars.githubusercontent.com/u/20412597?v=4" /></a>
      <a href="https://github.com/Mehver"><img height="35" width="35" title="Mehver" src="https://avatars.githubusercontent.com/u/75297777?v=4" /></a>
      <a href="https://github.com/mirbyte"><img height="35" width="35" title="mirko" src="https://avatars.githubusercontent.com/u/83219244?v=4" /></a>
      <a href="https://github.com/PySimpleGUI"><img height="35" width="35" title="PySimpleGUI" src="https://avatars.githubusercontent.com/u/46163555?v=4" /></a>
      <a href="https://github.com/robusta-dev"><img height="35" width="35" title="Robusta" src="https://avatars.githubusercontent.com/u/82757710?s=200&v=4" /></a>
      <a href="https://github.com/sasozivanovic"><img height="35" width="35" title="Sašo Živanović" src="https://avatars.githubusercontent.com/u/3317028?v=4" /></a>
      <a href="https://github.com/scoutapm-sponsorships"><img height="35" width="35" title="scoutapm-sponsorships" src="https://avatars.githubusercontent.com/u/71095532?v=4" /></a>
      <a href="https://github.com/u93"><img height="35" width="35" title="Eugenio E Breijo" src="https://avatars.githubusercontent.com/u/16807302?v=4" /></a>
      <a href="https://opencollective.com/alexey-vazhnov"><img height="35" width="35" title="Alexey Vazhnov" src="https://images.opencollective.com/alexey-vazhnov/daed334/avatar/40.png" /></a>
      <a href="https://opencollective.com/chenyoo-hao"><img height="35" width="35" title="Chenyoo Hao" src="https://images.opencollective.com/chenyoo-hao/avatar/40.png" /></a>
    </div>

    <sup><a href="https://github.com/sponsors/giampaolo">add your avatar</a></sup>

.. </PYPI-EXCLUDE>

License
=======

BSD-3
