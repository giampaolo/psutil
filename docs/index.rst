.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola <grodola@gmail.com>
.. title:: Home

.. ============================================================================
.. Hero
.. ============================================================================

.. raw:: html

   <script>document.body.classList.add('home-page');</script>

   <div class="hero">
     <h1 class="hero-title"><img src="_static/images/logo-psutil.svg" class="hero-logo" alt="psutil logo"><span>psutil</span></h1>
     <div class="hero-subtitle">Process and System Utilities for Python</div>
   </div>

.. container:: home-intro

   Psutil is a cross-platform library for retrieving information about running
   processes and system utilization in Python. It is useful mainly for system
   monitoring, profiling, limiting process resources, and managing running
   processes. Psutil implements many functionalities offered by UNIX command
   line tool such as *ps, top, free, iotop, netstat, ifconfig, lsof* and
   others.

.. ============================================================================
.. Install one-liner
.. ============================================================================

.. raw:: html

   <div class="home-install" role="group" aria-label="Install command">
     <span class="home-install-prompt" aria-hidden="true">$</span>
     <code class="home-install-cmd">pip install psutil</code>
     <button type="button" class="home-install-copy" aria-label="Copy install command">
       <svg class="home-install-icon-copy" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.6" aria-hidden="true">
         <rect x="4" y="4" width="9" height="9" rx="1.2"></rect>
         <path d="M3 11V3a1 1 0 0 1 1-1h8"></path>
       </svg>
       <svg class="home-install-icon-check" viewBox="0 0 16 16" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
         <path d="M3 8.5l3.5 3.5L13 5"></path>
       </svg>
     </button>
     <span class="home-install-toast" aria-hidden="true">Copied</span>
   </div>

.. ============================================================================
.. Platform pills
.. ============================================================================

.. raw:: html

   <div class="home-platforms">
     <a class="home-platforms-label" href="platform.html">Runs on</a>
     <div class="home-platforms-pills">
       <a class="home-platform-pill" href="platform.html">Linux</a>
       <a class="home-platform-pill" href="platform.html">Windows</a>
       <a class="home-platform-pill" href="platform.html">macOS</a>
       <a class="home-platform-pill" href="platform.html">FreeBSD</a>
       <a class="home-platform-pill" href="platform.html">OpenBSD</a>
       <a class="home-platform-pill" href="platform.html">NetBSD</a>
       <a class="home-platform-pill" href="platform.html">Solaris</a>
       <a class="home-platform-pill" href="platform.html">AIX</a>
     </div>
   </div>

.. ============================================================================
.. Feature cards
.. ============================================================================

.. raw:: html

   <div class="home-section-label">Explore the API</div>
   <div class="home-feature-cards">
     <a class="home-feature-card" href="api.html#cpu">
       <img class="home-icon-svg" src="_static/images/icon-cpu.svg" alt="">
       <div class="home-feature-title">CPU</div>
     </a>
     <a class="home-feature-card" href="api.html#memory">
       <img class="home-icon-svg" src="_static/images/icon-memory.svg" alt="">
       <div class="home-feature-title">Memory</div>
     </a>
     <a class="home-feature-card" href="api.html#disks">
       <img class="home-icon-svg" src="_static/images/icon-disks.svg" alt="">
       <div class="home-feature-title">Disks</div>
     </a>
     <a class="home-feature-card" href="api.html#network">
       <img class="home-icon-svg" src="_static/images/icon-network.svg" alt="">
       <div class="home-feature-title">Network</div>
     </a>
     <a class="home-feature-card" href="api.html#sensors">
       <img class="home-icon-svg" src="_static/images/icon-sensors.svg" alt="">
       <div class="home-feature-title">Sensors</div>
     </a>
     <a class="home-feature-card" href="api.html#processes">
       <img class="home-icon-svg" src="_static/images/icon-processes.svg" alt="">
       <div class="home-feature-title">Processes</div>
     </a>
   </div>

.. ============================================================================
.. Quickstart code preview (tabs by category)
.. ============================================================================

.. raw:: html

   <div class="home-section-label">Try it</div>

.. container:: home-quickstart

   .. tab-set::

      .. tab-item:: CPU

         .. code-block:: pycon

            >>> import psutil
            >>> psutil.cpu_times()
            scputimes(user=3961.46, nice=169.72, system=2150.65, idle=16900.54, iowait=629.59, ...)
            >>> psutil.cpu_percent(interval=1)
            4.0
            >>> psutil.cpu_count(logical=False)
            2
            >>> psutil.cpu_freq()
            scpufreq(current=931.42, min=800.0, max=3500.0)

         .. container:: home-tab-more

            :ref:`See more → <api-overview-cpu>`

      .. tab-item:: Memory

         .. code-block:: pycon

            >>> import psutil
            >>> psutil.virtual_memory()
            svmem(total=10367352832, available=6472179712, percent=37.6, used=8186245120, free=2181107712, ...)
            >>> psutil.swap_memory()
            sswap(total=2097147904, used=296128512, free=1801019392, percent=14.1, sin=304193536, sout=677842944)

         .. container:: home-tab-more

            :ref:`See more → <api-overview-memory>`

      .. tab-item:: Disks

         .. code-block:: pycon

            >>> import psutil
            >>> psutil.disk_partitions()
            [sdiskpart(device='/dev/sda1', mountpoint='/',     fstype='ext4', opts='rw,nosuid'),
             sdiskpart(device='/dev/sda2', mountpoint='/home', fstype='ext4', opts='rw')]
            >>> psutil.disk_usage('/')
            sdiskusage(total=21378641920, used=4809781248, free=15482871808, percent=22.5)
            >>> psutil.disk_io_counters()
            sdiskio(read_count=719566, write_count=1082197, read_bytes=18626220, write_bytes=24081764, ...)

         .. container:: home-tab-more

            :ref:`See more → <api-overview-disks>`

      .. tab-item:: Network

         .. code-block:: pycon

            >>> import psutil
            >>> psutil.net_io_counters(pernic=True)
            {'eth0': netio(bytes_sent=485291293, bytes_recv=6004858642, ...),
             'lo':   netio(bytes_sent=2838627,   bytes_recv=2838627,   ...)}
            >>> psutil.net_connections(kind='tcp')
            [sconn(family=2, type=1, laddr=addr('10.0.0.1', 48776), raddr=addr('93.186.135.91', 80), status='ESTABLISHED', pid=1254), ...]
            >>> psutil.net_if_addrs()['wlan0']
            [snicaddr(family=2,  address='192.168.1.3', netmask='255.255.255.0', ...), ...]
            >>> psutil.net_if_stats()['wlan0']
            snicstats(isup=True, duplex=2, speed=100, mtu=1500, flags='up,broadcast,running')

         .. container:: home-tab-more

            :ref:`See more → <api-overview-network>`

      .. tab-item:: Sensors

         .. code-block:: pycon

            >>> import psutil
            >>> psutil.sensors_temperatures()
            {'coretemp': [shwtemp(label='Physical id 0', current=52.0, high=100.0, critical=100.0),
                          shwtemp(label='Core 0',        current=45.0, high=100.0, critical=100.0)],
             'acpitz':   [shwtemp(label='',              current=47.0, high=103.0, critical=103.0)]}
            >>> psutil.sensors_fans()
            {'asus': [sfan(label='cpu_fan', current=3200)]}
            >>> psutil.sensors_battery()
            sbattery(percent=93, secsleft=16628, power_plugged=False)

         .. container:: home-tab-more

            :ref:`See more → <api-overview-sensors>`

      .. tab-item:: Processes

         .. code-block:: pycon

            >>> import psutil
            >>> p = psutil.Process(7055)
            >>> p.name(), p.exe(), p.cmdline()
            ('python3', '/usr/bin/python3', ['/usr/bin/python3', 'main.py'])
            >>> p.status()
            <ProcessStatus.STATUS_RUNNING: 'running'>
            >>> p.cpu_percent(interval=1.0)
            12.1
            >>> p.memory_info()
            pmem(rss=3164160, vms=4410163, shared=897433, text=302694, data=2422374)
            >>> p.parent(), p.children(recursive=True)
            (psutil.Process(pid=4699, name='bash'), [psutil.Process(pid=29835, name='python3'), ...])

         .. container:: home-tab-more

            :ref:`See more → <api-overview-processes>`

.. ============================================================================
.. Adoption stats. Numbers kept in sync with adoption.rst and README.rst
.. by scripts/internal/refresh_adoption_stats.py.
.. ============================================================================

.. raw:: html

   <div class="home-section-label">Stats</div>
   <div class="home-stats">
     <a class="home-stat" href="https://clickpy.clickhouse.com/dashboard/psutil">
       <span class="home-stat-num">370+ million</span>
       <span class="home-stat-label">downloads per month</span>
     </a>
     <a class="home-stat" href="https://github.com/giampaolo/psutil/network/dependents">
       <span class="home-stat-num">780,000+</span>
       <span class="home-stat-label">GitHub repositories</span>
     </a>
     <a class="home-stat" href="timeline.html">
       <span class="home-stat-num">17 years</span>
       <span class="home-stat-label">in active development</span>
     </a>
   </div>

.. ============================================================================
.. Sponsors
.. ============================================================================

.. raw:: html

   <div id="sponsors">
     <div class="home-section-label">Sponsors</div>

.. raw:: html
   :file: _sponsors.html

.. raw:: html

   </div>

.. ============================================================================
.. TOC: hidden via CSS, needed by Sphinx for sidebar nav
.. ============================================================================

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   Install <install>
   API overview <api-overview>
   API Reference <api>
   FAQ <faq>
   Performance <performance>
   Recipes <recipes>

.. toctree::
   :maxdepth: 2
   :caption: Reference

   Shell equivalents <shell-equivalents>
   Stdlib equivalents <stdlib-equivalents>
   Glossary <glossary>
   Platform support <platform>
   Migration <migration>

.. toctree::
   :maxdepth: 2
   :caption: About

   Who uses psutil <adoption>
   Alternatives <alternatives>
   Funding <funding>
   Credits <credits>

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: Project

   Blog <blog>
   Changelog <changelog>
   Timeline <timeline>
   Development guide <devguide>
   General Index <genindex>
