
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
     - FreeBSD
     - Windows
   * - :func:`cpu_percent`
     - ``top``
     - same
     - same
     -
   * - :func:`cpu_count(logical=True) <cpu_count>`
     - ``nproc``
     - ``sysctl hw.logicalcpu``
     - ``sysctl hw.ncpu``
     - ``$env:NUMBER_OF_PROCESSORS``
   * - :func:`cpu_count(logical=False) <cpu_count>`
     - ``lscpu | grep '^Core(s)'``
     - ``sysctl hw.physicalcpu``
     -
     - ``(Get-CimInstance Win32_Processor).NumberOfCores``
   * - :func:`cpu_times(percpu=False) <cpu_times>`
     - ``cat /proc/stat | grep '^cpu\s'``
     -
     - ``systat -vmstat``
     -
   * - :func:`cpu_times(percpu=True) <cpu_times>`
     - ``cat /proc/stat | grep '^cpu'``
     -
     - ``systat -vmstat``
     -
   * - :func:`cpu_times_percent(percpu=False) <cpu_times_percent>`
     - ``mpstat``
     -
     -
     -
   * - :func:`cpu_times_percent(percpu=True) <cpu_times_percent>`
     - ``mpstat -P ALL``
     -
     -
     -
   * - :func:`cpu_freq`
     - ``cpufreq-info``, ``lscpu | grep "MHz"``
     - ``sysctl hw.cpufrequency``
     - ``sysctl dev.cpu.0.freq``
     - ``systeminfo``
   * - :func:`cpu_stats`
     -
     -
     - ``sysctl vm.stats.sys``
     -
   * - :func:`getloadavg`
     - ``uptime``
     - same
     - same
     -

Memory
~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil function
     - Linux
     - macOS
     - FreeBSD
     - Windows
   * - :func:`virtual_memory`
     - ``free``, ``vmstat``, ``cat /proc/meminfo``
     - ``vm_stat``
     - ``sysctl vm.stats``
     - ``systeminfo``
   * - :func:`swap_memory`
     - ``free``, ``vmstat``, ``swapon``
     - ``sysctl vm.swapusage``
     - ``swapinfo``
     -
   * - :func:`heap_info`
     -
     -
     -
     -
   * - :func:`heap_trim`
     -
     -
     -
     -

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
     - same
     - same
     - ``Get-PSDrive``
   * - :func:`disk_partitions`
     - ``findmnt``, ``mount``
     - ``mount``
     - ``mount``
     - ``Get-CimInstance Win32_LogicalDisk``
   * - :func:`disk_io_counters`
     - ``iostat -dx``
     - ``iostat``
     - ``iostat -x``
     - ``Get-Counter '\PhysicalDisk(*)\*'``

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
     - ``netstat -anp``, ``ss``, ``lsof -nP -i -U``
     - ``netstat -anp``
     - ``netstat -an``
     - ``netstat -an``
   * - :func:`net_if_addrs`
     - ``ifconfig``, ``ip addr``
     - ``ifconfig``
     - ``ifconfig``
     - ``ipconfig``, ``systeminfo``
   * - :func:`net_io_counters`
     - ``netstat -i``, ``ifconfig``, ``ip -s link``
     - ``netstat -i``
     - ``netstat -i``
     - ``netstat -e``
   * - :func:`net_if_stats`
     - ``ifconfig``, ``ip -br link``, ``ip link``
     - ``ifconfig``
     - ``ifconfig``
     - ``netsh interface show interface``

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
     -
     - ``sysctl dev.cpu.*.temperature``
     -
   * - :func:`sensors_fans`
     - ``sensors``
     -
     - ``sysctl dev.cpu.*.fan``
     -
   * - :func:`sensors_battery`
     - ``acpi -b``
     - ``pmset -g batt``
     - ``apm -b``
     - ``Get-CimInstance Win32_Battery``

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
     -
   * - :func:`pids`
     - ``ps -eo pid``
     - same
     - same
     - ``tasklist``
   * - :func:`pid_exists`
     - ``kill -0 PID``
     - same
     - same
     - ``tasklist /FI "PID eq PID"``

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
     - ``(Get-Process -Id PID).Path``
   * - :meth:`Process.cmdline`
     - ``ps -o args -p PID``
     - same
     - ``procstat -c PID``
     - ``(Get-CimInstance Win32_Process -Filter "ProcessId=PID").CommandLine``
   * - :meth:`Process.status`
     - ``ps -o stat -p PID``
     - same
     - same
     -
   * - :meth:`Process.create_time`
     - ``ps -o lstart -p PID``
     - same
     - same
     - ``(Get-Process -Id PID).StartTime``
   * - :meth:`Process.is_running`
     - ``kill -0 PID``
     - same
     - same
     - ``tasklist /FI "PID eq PID"``
   * - :meth:`Process.environ`
     - ``xargs -0 -a /proc/PID/environ``
     -
     - ``procstat -e PID``
     -
   * - :meth:`Process.cwd`
     - ``pwdx PID``
     - ``lsof -p PID -a -d cwd``
     -
     -

Process tree
~~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.ppid`
     - ``ps -o ppid= -p PID``
     - same
     - same
     - ``(Get-CimInstance Win32_Process -Filter "ProcessId=PID").ParentProcessId``
   * - :meth:`Process.parent`
     - ``ps -p $(ps -o ppid= -p PID)``
     - same
     - same
     - ``(Get-CimInstance Win32_Process -Filter "ProcessId=PID").ParentProcessId``
   * - :meth:`Process.parents`
     - ``pstree -s PID``
     - same
     - same
     -
   * - :meth:`Process.children(recursive=False) <Process.children>`
     - ``pgrep -P PID``
     - same
     - same
     - ``(Get-CimInstance Win32_Process -Filter "ParentProcessId=PID").ProcessId``
   * - :meth:`Process.children(recursive=True) <Process.children>`
     - ``pstree -p PID``
     - same
     - same
     -

Credentials
~~~~~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.uids`
     - ``ps -o uid,ruid,suid -p PID``
     - same
     - ``procstat -s PID``
     -
   * - :meth:`Process.gids`
     - ``ps -o gid,rgid,sgid -p PID``
     - same
     - ``procstat -s PID``
     -
   * - :meth:`Process.username`
     - ``ps -o user -p PID``
     - same
     - same
     - ``tasklist /V /FI "PID eq PID"``
   * - :meth:`Process.terminal`
     - ``ps -o tty -p PID``
     - same
     - same
     -

CPU / scheduling
~~~~~~~~~~~~~~~~

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
     -
   * - :meth:`Process.cpu_times`
     - ``ps -o cputime -p PID``
     - same
     - ``procstat -r PID``
     -
   * - :meth:`Process.cpu_num`
     - ``ps -o psr -p PID``
     -
     -
     -
   * - :meth:`Process.num_ctx_switches`
     - ``pidstat -w -p PID``
     -
     - ``procstat -r PID``
     -
   * - :meth:`Process.cpu_affinity() <Process.cpu_affinity>`
     - ``taskset -p PID``
     -
     - ``cpuset -g -p PID``
     -
   * - :meth:`Process.cpu_affinity(CPUS) <Process.cpu_affinity>`
     - ``taskset -p MASK PID``
     -
     - ``cpuset -s -p PID -l CPUS``
     -
   * - :meth:`Process.ionice() <Process.ionice>`
     - ``ionice -p PID``
     -
     -
     -
   * - :meth:`Process.ionice(CLASS) <Process.ionice>`
     - ``ionice -c CLASS -p PID``
     -
     -
     -
   * - :meth:`Process.nice() <Process.nice>`
     - ``ps -o nice -p PID``
     - same
     - same
     -
   * - :meth:`Process.nice(VALUE) <Process.nice>`
     - ``renice -n VALUE -p PID``
     - same
     - same
     -
   * - :meth:`Process.rlimit(RES) <Process.rlimit>`
     - ``prlimit --pid PID``
     -
     - ``procstat rlimit PID``
     -
   * - :meth:`Process.rlimit(RES, LIMITS) <Process.rlimit>`
     - ``prlimit --pid PID --RES=SOFT:HARD``
     -
     -
     -

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
     - ``tasklist /FI "PID eq PID"``
   * - :meth:`Process.memory_info_ex`
     - ``cat /proc/PID/status``
     -
     -
     -
   * - :meth:`Process.memory_percent`
     - ``ps -o %mem -p PID``
     - same
     - same
     - ``tasklist /FI "PID eq PID"``
   * - :meth:`Process.memory_maps`
     - ``pmap PID``
     - ``vmmap PID``
     - ``procstat -v PID``
     -
   * - :meth:`Process.memory_footprint`
     - ``smem``, ``smemstat``
     -
     -
     -
   * - :meth:`Process.page_faults`
     - ``ps -o maj_flt,min_flt -p PID``
     - ``ps -o faults -p PID``
     - ``procstat -r PID``
     -

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
     - ``(Get-Process -Id PID).Threads.Count``
   * - :meth:`Process.threads`
     - ``ps -T -p PID``
     -
     -
     -

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
     -
     - ``netstat -ano | findstr PID``
   * - :meth:`Process.open_files`
     - ``lsof -p PID``
     - same
     - ``procstat -f PID``
     - ``handle.exe -p PID``
   * - :meth:`Process.io_counters`
     - ``cat /proc/PID/io``
     -
     -
     - ``(Get-Process -Id PID) | select *IO*``
   * - :meth:`Process.num_fds`
     - ``ls /proc/PID/fd | wc -l``
     -
     -
     -
   * - :meth:`Process.num_handles`
     -
     -
     -
     - ``(Get-Process -Id PID).HandleCount``

Signals
~~~~~~~

.. list-table::
   :header-rows: 1

   * - psutil method
     - Linux
     - macOS
     - BSD
     - Windows
   * - :meth:`Process.send_signal`
     - ``kill -SIG PID``
     - same
     - same
     -
   * - :meth:`Process.suspend`
     - ``kill -STOP PID``
     - same
     - same
     -
   * - :meth:`Process.resume`
     - ``kill -CONT PID``
     - same
     - same
     -
   * - :meth:`Process.terminate`
     - ``kill -TERM PID``
     - same
     - same
     - ``taskkill /PID PID``
   * - :meth:`Process.kill`
     - ``kill -KILL PID``
     - same
     - same
     - ``taskkill /F /PID PID``
   * - :meth:`Process.wait`
     - ``tail --pid=PID -f /dev/null``
     - ``lsof -p PID +r 1``
     - ``pwait PID``
     - ``(Get-Process -Id PID).WaitForExit()``
