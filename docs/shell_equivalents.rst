.. currentmodule:: psutil

Shell equivalents
=================

This page maps psutil's Python API to the equivalent native terminal commands
on each platform. This is useful for understanding what psutil replaces and for
cross-checking results.

System-wide functions
---------------------

CPU
~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - BSD
     - Windows
   * - :func:`cpu_count(logical=True) <cpu_count>`
     - ``nproc``, ``lscpu``
     - ``sysctl hw.logicalcpu``
     - ``sysctl hw.ncpu``
     - WMIC
   * - :func:`cpu_count(logical=False) <cpu_count>`
     - ``lscpu``
     - ``sysctl hw.physicalcpu``
     - —
     - WMIC
   * - :func:`cpu_times(percpu=False) <cpu_times>`
     - ``/proc/stat``
     - —
     - —
     - —
   * - :func:`cpu_times(percpu=True) <cpu_times>`
     - ``mpstat -P ALL``
     - —
     - —
     - —
   * - :func:`cpu_percent`
     - ``top``
     - ``top``
     - ``top``
     - Task Manager
   * - :func:`cpu_freq`
     - ``cpufreq-info``
     - ``sysctl hw.cpufrequency``
     - ``sysctl dev.cpu.0.freq``
     - WMIC
   * - :func:`cpu_stats`
     - ``vmstat``
     - —
     - ``sysctl vm.stats.sys``
     - —
   * - :func:`getloadavg`
     - ``uptime``, ``cat /proc/loadavg``
     - ``uptime``
     - ``uptime``
     - —

Memory
~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - BSD
     - Windows
   * - :func:`virtual_memory`
     - ``free``, ``vmstat``
     - ``vm_stat``
     - ``sysctl vm.stats``
     - WMI
   * - :func:`swap_memory`
     - ``free``
     - ``vm_stat``
     - ``swapinfo``
     - WMI

Disks
~~~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - BSD
     - Windows
   * - :func:`disk_usage`
     - ``df``
     - ``df``
     - ``df``
     - ``dir``
   * - :func:`disk_partitions`
     - ``findmnt``, ``mount``
     - ``mount``
     - ``mount``
     - ``wmic logicaldisk``
   * - :func:`disk_io_counters`
     - ``iostat``
     - ``iostat``
     - ``iostat``
     - —

Network
~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - BSD
     - Windows
   * - :func:`net_connections`
     - ``netstat -antp``, ``ss``, ``lsof -nP -i -U``
     - ``netstat``
     - ``netstat``
     - ``netstat``
   * - :func:`net_if_addrs`
     - ``ifconfig``, ``ip addr``
     - ``ifconfig``
     - ``ifconfig``
     - ``ipconfig``
   * - :func:`net_io_counters`
     - ``ifconfig``, ``ip -s link``
     - ``netstat -i``
     - ``netstat -i``
     - ``ipconfig``
   * - :func:`net_if_stats`
     - ``ifconfig``, ``ip -br link``, ``ip link``
     - ``ifconfig``
     - ``ifconfig``
     - ``ipconfig``

Sensors
~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - BSD
     - Windows
   * - :func:`sensors_temperatures`
     - ``sensors``
     - —
     - ``sysctl dev.cpu.*.temperature``
     - —
   * - :func:`sensors_fans`
     - ``sensors``
     - —
     - —
     - —
   * - :func:`sensors_battery`
     - ``acpi -b``
     - ``pmset -g batt``
     - ``acpiconf -i 0``
     - —

Other
~~~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - BSD
     - Windows
   * - :func:`boot_time`
     - ``uptime``, ``who -b``
     - ``sysctl kern.boottime``
     - ``sysctl kern.boottime``
     - ``systeminfo``
   * - :func:`users`
     - ``who -a``, ``w``
     - same
     - same
     - ``query user``
   * - :func:`pids`
     - ``ps -eo pid``
     - same
     - same
     - ``tasklist``

Process methods
---------------

Identity
~~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.name`
     - ``ps -o comm -p PID``
     - same
     - ``procstat -b PID``
     - ``tasklist``
   * - :meth:`Process.exe`
     - ``readlink /proc/PID/exe``
     - ``lsof -p PID``
     - ``procstat -b PID``
     - —
   * - :meth:`Process.cmdline`
     - ``ps -o args -p PID``
     - same
     - ``procstat -c PID``
     - ``wmic process get commandline``
   * - :meth:`Process.status`
     - ``ps -o stat -p PID``
     - same
     - same
     - —
   * - :meth:`Process.ppid`
     - ``ps -o ppid -p PID``
     - same
     - same
     - —
   * - :meth:`Process.create_time`
     - ``ps -o lstart -p PID``
     - same
     - same
     - —
   * - :meth:`Process.uids`
     - ``ps -o uid,ruid,suid -p PID``
     - same
     - ``procstat -s PID``
     - —
   * - :meth:`Process.gids`
     - ``ps -o gid,rgid,sgid -p PID``
     - same
     - ``procstat -s PID``
     - —
   * - :meth:`Process.username`
     - ``ps -o user -p PID``
     - same
     - same
     - —
   * - :meth:`Process.environ`
     - ``xargs -0 -a /proc/PID/environ``
     - —
     - ``procstat -e PID``
     - —
   * - :meth:`Process.cwd`
     - ``ls -la /proc/PID/cwd``
     - ``lsof -p PID -a -d cwd``
     - —
     - —
   * - :meth:`Process.nice`
     - ``ps -o nice -p PID``
     - same
     - same
     - —

CPU
~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.cpu_percent`
     - ``ps -o %cpu -p PID``
     - same
     - same
     - —
   * - :meth:`Process.cpu_times`
     - ``ps -o cputime -p PID``
     - same
     - ``procstat -r PID``
     - —
   * - :meth:`Process.cpu_num`
     - ``ps -o psr -p PID``
     - —
     - —
     - —

Memory
~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.memory_info`
     - ``ps -o rss,vsz -p PID``
     - same
     - same
     - —
   * - :meth:`Process.memory_percent`
     - ``ps -o %mem -p PID``
     - same
     - same
     - —
   * - :meth:`Process.memory_maps`
     - ``pmap PID``
     - ``vmmap PID``
     - ``procstat -v PID``
     - —

Threads
~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.num_threads`
     - ``ps -o nlwp -p PID``
     - same
     - same
     - —
   * - :meth:`Process.num_ctx_switches`
     - ``/proc/PID/status``
     - —
     - ``procstat -r PID``
     - —
   * - :meth:`Process.threads`
     - ``ps -T -p PID``
     - —
     - —
     - —

Files and connections
~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.net_connections`
     - ``ss -p``, ``lsof -p PID -i``
     - ``lsof -p PID -i``
     - —
     - —
   * - :meth:`Process.open_files`
     - ``lsof -p PID``
     - ``lsof -p PID``
     - ``procstat -f PID``
     - —
   * - :meth:`Process.num_fds`
     - ``ls /proc/PID/fd | wc -l``
     - —
     - —
     - —
   * - :meth:`Process.io_counters`
     - ``cat /proc/PID/io``
     - —
     - —
     - —
