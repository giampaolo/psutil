*Bug tracker at https://github.com/giampaolo/psutil/issues*

5.7.4 (development version)
===========================

XXXX-XX-XX

**Enhancements**

- 1863_: `disk_partitions()` exposes 2 extra fields: `maxfile` and `maxpath`,
  which are the maximum file name and path name length.
- 1872_: [Windows] added support for PyPy 2.7.
- 1879_: provide pre-compiled wheels for Linux and macOS (yey!).
- 1880_: get rid of Travis and Cirrus CI services (they are no longer free).
  CI testing is now done by GitHub Actions on Linux, macOS and FreeBSD (yes). AppVeyor is still being used for Windows CI.

**Bug fixes**

- 1866_: [Windows] process exe(), cmdline(), environ() may raise "invalid
  access to memory location" on Python 3.9.
- 1874_: [Solaris] wrong swap output given when encrypted column is present

5.7.3
=====

2020-10-23

**Enhancements**

- 809_: [FreeBSD] add support for `Process.rlimit()`.
- 893_: [BSD] add support for `Process.environ()` (patch by Armin Gruner)
- 1830_: [UNIX] `net_if_stats()`'s `isup` also checks whether the NIC is
  running (meaning Wi-Fi or ethernet cable is connected).  (patch by Chris Burger)
- 1837_: [Linux] improved battery detection and charge "secsleft" calculation
  (patch by aristocratos)

**Bug fixes**

- 1620_: [Linux] physical cpu_count() result is incorrect on systems with more
  than one CPU socket.  (patch by Vincent A. Arcila)
- 1738_: [macOS] Process.exe() may raise FileNotFoundError if process is still
  alive but the exe file which launched it got deleted.
- 1791_: [macOS] fix missing include for getpagesize().
- 1823_: [Windows] Process.open_files() may cause a segfault due to a NULL
  pointer.
- 1838_: [Linux] sensors_battery(): if `percent` can be determined but not
  the remaining values, still return a result instead of None.
  (patch by aristocratos)

5.7.2
=====

2020-07-15

**Bug fixes**

- wheels for 2.7 were inadvertently deleted.

5.7.1
=====

2020-07-15

**Enhancements**

- 1729_: parallel tests on UNIX (make test-parallel). They're twice as fast!
- 1741_: "make build/install" is now run in parallel and it's about 15% faster
  on UNIX.
- 1747_: `Process.wait()` on POSIX returns an enum, showing the negative signal
  which was used to terminate the process::
    >>> import psutil
    >>> p = psutil.Process(9891)
    >>> p.terminate()
    >>> p.wait()
    <Negsignal.SIGTERM: -15>
- 1747_: `Process.wait()` return value is cached so that the exit code can be
  retrieved on then next call.
- 1747_: Process provides more info about the process on str() and repr()
  (status and exit code)::
    >>> proc
    psutil.Process(pid=12739, name='python3', status='terminated',
                   exitcode=<Negsigs.SIGTERM: -15>, started='15:08:20')
- 1757_: memory leak tests are now stable.
- 1768_: [Windows] added support for Windows Nano Server. (contributed by
  Julien Lebot)

**Bug fixes**

- 1726_: [Linux] cpu_freq() parsing should use spaces instead of tabs on ia64.
  (patch by Michał Górny)
- 1760_: [Linux] Process.rlimit() does not handle long long type properly.
- 1766_: [macOS] NoSuchProcess may be raised instead of ZombieProcess.
- 1781_: fix signature of callback function for getloadavg().  (patch by
  Ammar Askar)

5.7.0
=====

2020-02-18

**Enhancements**

- 1637_: [SunOS] add partial support for old SunOS 5.10 Update 0 to 3.
- 1648_: [Linux] sensors_temperatures() looks into an additional /sys/device/
  directory for additional data.  (patch by Javad Karabi)
- 1652_: [Windows] dropped support for Windows XP and Windows Server 2003.
  Minimum supported Windows version now is Windows Vista.
- 1671_: [FreeBSD] add CI testing/service for FreeBSD (Cirrus CI).
- 1677_: [Windows] process exe() will succeed for all process PIDs (instead of
  raising AccessDenied).
- 1679_: [Windows] net_connections() and Process.connections() are 10% faster.
- 1682_: [PyPy] added CI / test integration for PyPy via Travis.
- 1686_: [Windows] added support for PyPy on Windows.
- 1693_: [Windows] boot_time(), Process.create_time() and users()'s login time
  now have 1 micro second precision (before the precision was of 1 second).

**Bug fixes**

- 1538_: [NetBSD] process cwd() may return ENOENT instead of NoSuchProcess.
- 1627_: [Linux] Process.memory_maps() can raise KeyError.
- 1642_: [SunOS] querying basic info for PID 0 results in FileNotFoundError.
- 1646_: [FreeBSD] many Process methods may cause a segfault on FreeBSD 12.0
  due to a backward incompatible change in a C type introduced in 12.0.
- 1656_: [Windows] Process.memory_full_info() raises AccessDenied even for the
  current user and os.getpid().
- 1660_: [Windows] Process.open_files() complete rewrite + check of errors.
- 1662_: [Windows] process exe() may raise WinError 0.
- 1665_: [Linux] disk_io_counters() does not take into account extra fields
  added to recent kernels.  (patch by Mike Hommey)
- 1672_: use the right C type when dealing with PIDs (int or long). Thus far
  (long) was almost always assumed, which is wrong on most platforms.
- 1673_: [OpenBSD] Process connections(), num_fds() and threads() returned
  improper exception if process is gone.
- 1674_: [SunOS] disk_partitions() may raise OSError.
- 1684_: [Linux] disk_io_counters() may raise ValueError on systems not
  having /proc/diskstats.
- 1695_: [Linux] could not compile on kernels <= 2.6.13 due to
  PSUTIL_HAVE_IOPRIO not being defined.  (patch by Anselm Kruis)

5.6.7
=====

2019-11-26

**Bug fixes**

- 1630_: [Windows] can't compile source distribution due to C syntax error.

5.6.6
=====

2019-11-25

**Bug fixes**

- 1179_: [Linux] Process cmdline() now takes into account misbehaving processes
  renaming the command line and using inappropriate chars to separate args.
- 1616_: use of Py_DECREF instead of Py_CLEAR will result in double free and
  segfault
  (`CVE-2019-18874 <https://cve.mitre.org/cgi-bin/cvename.cgi?name=CVE-2019-18874>`__).
  (patch by Riccardo Schirone)
- 1619_: [OpenBSD] compilation fails due to C syntax error.  (patch by Nathan
  Houghton)

5.6.5
=====

2019-11-06

**Bug fixes**

- 1615_: remove pyproject.toml as it was causing installation issues.

5.6.4
=====

2019-11-04

**Enhancements**

- 1527_: [Linux] added Process.cpu_times().iowait counter, which is the time
  spent waiting for blocking I/O to complete.
- 1565_: add PEP 517/8 build backend and requirements specification for better
  pip integration.  (patch by Bernát Gábor)

**Bug fixes**

- 875_: [Windows] Process' cmdline(), environ() or cwd() may occasionally fail
  with ERROR_PARTIAL_COPY which now gets translated to AccessDenied.
- 1126_: [Linux] cpu_affinity() segfaults on CentOS 5 / manylinux.
  cpu_affinity() support for CentOS 5 was removed.
- 1528_: [AIX] compilation error on AIX 7.2 due to 32 vs 64 bit differences.
  (patch by Arnon Yaari)
- 1535_: 'type' and 'family' fields returned by net_connections() are not
  always turned into enums.
- 1536_: [NetBSD] process cmdline() erroneously raise ZombieProcess error if
  cmdline has non encodable chars.
- 1546_: usage percent may be rounded to 0 on Python 2.
- 1552_: [Windows] getloadavg() math for calculating 5 and 15 mins values is
  incorrect.
- 1568_: [Linux] use CC compiler env var if defined.
- 1570_: [Windows] `NtWow64*` syscalls fail to raise the proper error code
- 1585_: [OSX] calling close() (in C) on possible negative integers.  (patch
  by Athos Ribeiro)
- 1606_: [SunOS] compilation fails on SunOS 5.10.  (patch by vser1)

5.6.3
=====

2019-06-11

**Enhancements**

- 1494_: [AIX] added support for Process.environ().  (patch by Arnon Yaari)

**Bug fixes**

- 1276_: [AIX] can't get whole cmdline().  (patch by Arnon Yaari)
- 1501_: [Windows] Process cmdline() and exe() raise unhandled "WinError 1168
  element not found" exceptions for "Registry" and "Memory Compression" psuedo
  processes on Windows 10.
- 1526_: [NetBSD] process cmdline() could raise MemoryError.  (patch by
  Kamil Rytarowski)

5.6.2
=====

2019-04-26

**Enhancements**

- 604_: [Windows, Windows] add new psutil.getloadavg(), returning system load
  average calculation, including on Windows (emulated).  (patch by Ammar Askar)
- 1404_: [Linux] cpu_count(logical=False) uses a second method (read from
  `/sys/devices/system/cpu/cpu[0-9]/topology/core_id`) in order to determine
  the number of physical CPUs in case /proc/cpuinfo does not provide this info.
- 1458_: provide coloured test output. Also show failures on KeyboardInterrupt.
- 1464_: various docfixes (always point to python3 doc, fix links, etc.).
- 1476_: [Windows] it is now possible to set process high I/O priority
  (ionice()).Also, I/O priority values are now exposed as 4 new constants:
  IOPRIO_VERYLOW, IOPRIO_LOW, IOPRIO_NORMAL, IOPRIO_HIGH.
- 1478_: add make command to re-run tests failed on last run.

**Bug fixes**

- 1223_: [Windows] boot_time() may return value on Windows XP.
- 1456_: [Linux] cpu_freq() returns None instead of 0.0 when min/max not
  available (patch by Alex Manuskin)
- 1462_: [Linux] (tests) make tests invariant to LANG setting (patch by
  Benjamin Drung)
- 1463_: cpu_distribution.py script was broken.
- 1470_: [Linux] disk_partitions(): fix corner case when /etc/mtab doesn't
  exist.  (patch by Cedric Lamoriniere)
- 1471_: [SunOS] Process name() and cmdline() can return SystemError.  (patch
  by Daniel Beer)
- 1472_: [Linux] cpu_freq() does not return all CPUs on Rasbperry-pi 3.
- 1474_: fix formatting of psutil.tests() which mimicks 'ps aux' output.
- 1475_: [Windows] OSError.winerror attribute wasn't properly checked resuling
  in WindowsError being raised instead of AccessDenied.
- 1477_: [Windows] wrong or absent error handling for private NTSTATUS Windows
  APIs. Different process methods were affected by this.
- 1480_: [Windows] psutil.cpu_count(logical=False) could cause a crash due to
  fixed read violation.  (patch by Samer Masterson)
- 1486_: [AIX, SunOS] AttributeError when interacting with Process methods
  involved into oneshot() context.
- 1491_: [SunOS] net_if_addrs(): free() ifap struct on error.  (patch by
  Agnewee)
- 1493_: [Linux] cpu_freq(): handle the case where
  /sys/devices/system/cpu/cpufreq/ exists but is empty.

5.6.1
=====

2019-03-11

**Bug fixes**

- 1329_: [AIX] psutil doesn't compile on AIX 6.1.  (patch by Arnon Yaari)
- 1448_: [Windows] crash on import due to rtlIpv6AddressToStringA not available
  on Wine.
- 1451_: [Windows] Process.memory_full_info() segfaults. NtQueryVirtualMemory
  is now used instead of QueryWorkingSet to calculate USS memory.

5.6.0
=====

2019-03-05

**Enhancements**

- 1379_: [Windows] Process suspend() and resume() now use NtSuspendProcess
  and NtResumeProcess instead of stopping/resuming all threads of a process.
  This is faster and more reliable (aka this is what ProcessHacker does).
- 1420_: [Windows] in case of exception disk_usage() now also shows the path
  name.
- 1422_: [Windows] Windows APIs requiring to be dynamically loaded from DLL
  libraries are now loaded only once on startup (instead of on per function
  call) significantly speeding up different functions and methods.
- 1426_: [Windows] PAGESIZE and number of processors is now calculated on
  startup.
- 1428_: in case of error, the traceback message now shows the underlying C
  function called which failed.
- 1433_: new Process.parents() method.  (idea by Ghislain Le Meur)
- 1437_: pids() are returned in sorted order.
- 1442_: python3 is now the default interpreter used by Makefile.

**Bug fixes**

- 1353_: process_iter() is now thread safe (it rarely raised TypeError).
- 1394_: [Windows] Process name() and exe() may erroneously return "Registry".
  QueryFullProcessImageNameW is now used instead of GetProcessImageFileNameW
  in order to prevent that.
- 1411_: [BSD] lack of Py_DECREF could cause segmentation fault on process
  instantiation.
- 1419_: [Windows] Process.environ() raises NotImplementedError when querying
  a 64-bit process in 32-bit-WoW mode. Now it raises AccessDenied.
- 1427_: [OSX] Process cmdline() and environ() may erroneously raise OSError
  on failed malloc().
- 1429_: [Windows] SE DEBUG was not properly set for current process. It is
  now, and it should result in less AccessDenied exceptions for low-pid
  processes.
- 1432_: [Windows] Process.memory_info_ex()'s USS memory is miscalculated
  because we're not using the actual system PAGESIZE.
- 1439_: [NetBSD] Process.connections() may return incomplete results if using
  oneshot().
- 1447_: original exception wasn't turned into NSP/AD exceptions when using
  Process.oneshot() ctx manager.

**Incompatible API changes**

- 1291_: [OSX] Process.memory_maps() was removed because inherently broken
  (segfault) for years.

5.5.1
=====

2019-02-15

**Enhancements**

- 1348_: [Windows] on Windows >= 8.1 if Process.cmdline() fails due to
  ERROR_ACCESS_DENIED attempt using NtQueryInformationProcess +
  ProcessCommandLineInformation. (patch by EccoTheFlintstone)

**Bug fixes**

- 1394_: [Windows] Process.exe() returns "[Error 0] The operation completed
  successfully" when Python process runs in "Virtual Secure Mode".
- 1402_: psutil exceptions' repr() show the internal private module path.
- 1408_: [AIX] psutil won't compile on AIX 7.1 due to missing header.  (patch
  by Arnon Yaari)

5.5.0
=====

2019-01-23

**Enhancements**

- 1350_: [FreeBSD] added support for sensors_temperatures().  (patch by Alex
  Manuskin)
- 1352_: [FreeBSD] added support for CPU frequency.  (patch by Alex Manuskin)

**Bug fixes**

- 1111_: Process.oneshot() is now thread safe.
- 1354_: [Linux] disk_io_counters() fails on Linux kernel 4.18+.
- 1357_: [Linux] Process' memory_maps() and io_counters() method are no longer
  exposed if not supported by the kernel.
- 1368_: [Windows] fix psutil.Process().ionice(...) mismatch.  (patch by
  EccoTheFlintstone)
- 1370_: [Windows] improper usage of CloseHandle() may lead to override the
  original error code when raising an exception.
- 1373_: incorrect handling of cache in Process.oneshot() context causes
  Process instances to return incorrect results.
- 1376_: [Windows] OpenProcess() now uses PROCESS_QUERY_LIMITED_INFORMATION
  access rights wherever possible, resulting in less AccessDenied exceptions
  being thrown for system processes.
- 1376_: [Windows] check if variable is NULL before free()ing it.  (patch by
  EccoTheFlintstone)

5.4.8
=====

2018-10-30

**Enhancements**

- 1197_: [Linux] cpu_freq() is now implemented by parsing /proc/cpuinfo in case
  /sys/devices/system/cpu/* filesystem is not available.
- 1310_: [Linux] psutil.sensors_temperatures() now parses /sys/class/thermal
  in case /sys/class/hwmon fs is not available (e.g. Raspberry Pi).  (patch
  by Alex Manuskin)
- 1320_: [Posix] better compilation support when using g++ instead of gcc.
  (patch by Jaime Fullaondo)

**Bug fixes**

- 715_: do not print exception on import time in case cpu_times() fails.
- 1004_: [Linux] Process.io_counters() may raise ValueError.
- 1277_: [OSX] available and used memory (psutil.virtual_memory()) metrics are
  not accurate.
- 1294_: [Windows] psutil.Process().connections() may sometimes fail with
  intermittent 0xC0000001.  (patch by Sylvain Duchesne)
- 1307_: [Linux] disk_partitions() does not honour PROCFS_PATH.
- 1320_: [AIX] system CPU times (psutil.cpu_times()) were being reported with
  ticks unit as opposed to seconds.  (patch by Jaime Fullaondo)
- 1332_: [OSX] psutil debug messages are erroneously printed all the time.
  (patch by Ilya Yanok)
- 1346_: [SunOS] net_connections() returns an empty list.  (patch by Oleksii
  Shevchuk)

5.4.7
=====

2018-08-14

**Enhancements**

- 1286_: [macOS] psutil.OSX constant is now deprecated in favor of new
  psutil.MACOS.
- 1309_: [Linux] added psutil.STATUS_PARKED constant for Process.status().
- 1321_: [Linux] add disk_io_counters() dual implementation relying on
  /sys/block filesystem in case /proc/diskstats is not available. (patch by
  Lawrence Ye)

**Bug fixes**

- 1209_: [macOS] Process.memory_maps() may fail with EINVAL due to poor
  task_for_pid() syscall. AccessDenied is now raised instead.
- 1278_: [macOS] Process.threads() incorrectly return microseconds instead of
  seconds. (patch by Nikhil Marathe)
- 1279_: [Linux, macOS, BSD] net_if_stats() may return ENODEV.
- 1294_: [Windows] psutil.Process().connections() may sometime fail with
  MemoryError.  (patch by sylvainduchesne)
- 1305_: [Linux] disk_io_stats() may report inflated r/w bytes values.
- 1309_: [Linux] Process.status() is unable to recognize "idle" and "parked"
  statuses (returns '?').
- 1313_: [Linux] disk_io_counters() can report inflated IO counters due to
  erroneously counting base disk device and its partition(s) twice.
- 1323_: [Linux] sensors_temperatures() may fail with ValueError.

5.4.6
=====

2018-06-07

**Bug fixes**

- 1258_: [Windows] Process.username() may cause a segfault (Python interpreter
  crash).  (patch by Jean-Luc Migot)
- 1273_: net_if_addr() namedtuple's name has been renamed from "snic" to
  "snicaddr".
- 1274_: [Linux] there was a small chance Process.children() may swallow
  AccessDenied exceptions.

5.4.5
=====

2018-04-14

**Bug fixes**

- 1268_: setup.py's extra_require parameter requires latest setuptools version,
  breaking quite a lot of installations.

5.4.4
=====

2018-04-13

**Enhancements**

- 1239_: [Linux] expose kernel "slab" memory for psutil.virtual_memory().
  (patch by Maxime Mouial)

**Bug fixes**

- 694_: [SunOS] cmdline() could be truncated at the 15th character when
  reading it from /proc. An extra effort is made by reading it from process
  address space first.  (patch by Georg Sauthoff)
- 771_: [Windows] cpu_count() (both logical and physical) return a wrong
  (smaller) number on systems using process groups (> 64 cores).
- 771_: [Windows] cpu_times(percpu=True) return fewer CPUs on systems using
  process groups (> 64 cores).
- 771_: [Windows] cpu_stats() and cpu_freq() may return incorrect results on
  systems using process groups (> 64 cores).
- 1193_: [SunOS] Return uid/gid from /proc/pid/psinfo if there aren't
  enough permissions for /proc/pid/cred.  (patch by Georg Sauthoff)
- 1194_: [SunOS] Return nice value from psinfo as getpriority() doesn't
  support real-time processes.  (patch by Georg Sauthoff)
- 1194_: [SunOS] Fix double free in psutil_proc_cpu_num().  (patch by Georg
  Sauthoff)
- 1194_: [SunOS] Fix undefined behavior related to strict-aliasing rules
  and warnings.  (patch by Georg Sauthoff)
- 1210_: [Linux] cpu_percent() steal time may remain stuck at 100% due to Linux
  erroneously reporting a decreased steal time between calls. (patch by Arnon
  Yaari)
- 1216_: fix compatibility with python 2.6 on Windows (patch by Dan Vinakovsky)
- 1222_: [Linux] Process.memory_full_info() was erroneously summing "Swap:" and
  "SwapPss:". Same for "Pss:" and "SwapPss". Not anymore.
- 1224_: [Windows] Process.wait() may erroneously raise TimeoutExpired.
- 1238_: [Linux] sensors_battery() may return None in case battery is not
  listed as "BAT0" under /sys/class/power_supply.
- 1240_: [Windows] cpu_times() float loses accuracy in a long running system.
  (patch by stswandering)
- 1245_: [Linux] sensors_temperatures() may fail with IOError "no such file".
- 1255_: [FreeBSD] swap_memory() stats were erroneously represented in KB.
  (patch by Denis Krienbühl)

**Backward compatibility**

- 771_: [Windows] cpu_count(logical=False) on Windows XP and Vista is no
  longer supported and returns None.

5.4.3
=====

*2018-01-01*

**Enhancements**

- 775_: disk_partitions() on Windows return mount points.

**Bug fixes**

- 1193_: pids() may return False on macOS.

5.4.2
=====

*2017-12-07*

**Enhancements**

- 1173_: introduced PSUTIL_DEBUG environment variable which can be set in order
  to print useful debug messages on stderr (useful in case of nasty errors).
- 1177_: added support for sensors_battery() on macOS.  (patch by Arnon Yaari)
- 1183_: Process.children() is 2x faster on UNIX and 2.4x faster on Linux.
- 1188_: deprecated method Process.memory_info_ex() now warns by using
  FutureWarning instead of DeprecationWarning.

**Bug fixes**

- 1152_: [Windows] disk_io_counters() may return an empty dict.
- 1169_: [Linux] users() "hostname" returns username instead.  (patch by
  janderbrain)
- 1172_: [Windows] `make test` does not work.
- 1179_: [Linux] Process.cmdline() is now able to splits cmdline args for
  misbehaving processes which overwrite /proc/pid/cmdline and use spaces
  instead of null bytes as args separator.
- 1181_: [macOS] Process.memory_maps() may raise ENOENT.
- 1187_: [macOS] pids() does not return PID 0 on recent macOS versions.

5.4.1
=====

*2017-11-08*

**Enhancements**

- 1164_: [AIX] add support for Process.num_ctx_switches().  (patch by Arnon
  Yaari)
- 1053_: abandon Python 3.3 support (psutil still works but it's no longer
  tested).

**Bug fixes**

- 1150_: [Windows] when a process is terminate()d now the exit code is set to
  SIGTERM instead of 0.  (patch by Akos Kiss)
- 1151_: python -m psutil.tests fail
- 1154_: [AIX] psutil won't compile on AIX 6.1.0.  (patch by Arnon Yaari)
- 1167_: [Windows] net_io_counter() packets count now include also non-unicast
  packets.  (patch by Matthew Long)

5.4.0
=====

*2017-10-12*

**Enhancements**

- 1123_: [AIX] added support for AIX platform.  (patch by Arnon Yaari)

**Bug fixes**

- 1009_: [Linux] sensors_temperatures() may crash with IOError.
- 1012_: [Windows] disk_io_counters()'s read_time and write_time were expressed
  in tens of micro seconds instead of milliseconds.
- 1127_: [macOS] invalid reference counting in Process.open_files() may lead to
  segfault.  (patch by Jakub Bacic)
- 1129_: [Linux] sensors_fans() may crash with IOError.  (patch by Sebastian
  Saip)
- 1131_: [SunOS] fix compilation warnings.  (patch by Arnon Yaari)
- 1133_: [Windows] can't compile on newer versions of Visual Studio 2017 15.4.
  (patch by Max Bélanger)
- 1138_: [Linux] can't compile on CentOS 5.0 and RedHat 5.0.
  (patch by Prodesire)

5.3.1
=====

*2017-09-10*

**Enhancements**

- 1124_: documentation moved to http://psutil.readthedocs.io

**Bug fixes**

- 1105_: [FreeBSD] psutil does not compile on FreeBSD 12.
- 1125_: [BSD] net_connections() raises TypeError.

**Compatibility notes**

- 1120_: .exe files for Windows are no longer uploaded on PyPI as per PEP-527;
  only wheels are provided.

5.3.0
=====

*2017-09-01*

**Enhancements**

- 802_: disk_io_counters() and net_io_counters() numbers no longer wrap
  (restart from 0). Introduced a new "nowrap" argument.
- 928_: psutil.net_connections() and psutil.Process.connections() "laddr" and
  "raddr" are now named tuples.
- 1015_: swap_memory() now relies on /proc/meminfo instead of sysinfo() syscall
  so that it can be used in conjunction with PROCFS_PATH in order to retrieve
  memory info about Linux containers such as Docker and Heroku.
- 1022_: psutil.users() provides a new "pid" field.
- 1025_: process_iter() accepts two new parameters in order to invoke
  Process.as_dict(): "attrs" and "ad_value". With this you can iterate over all
  processes in one shot without needing to catch NoSuchProcess and do list/dict
  comprehensions.
- 1040_: implemented full unicode support.
- 1051_: disk_usage() on Python 3 is now able to accept bytes.
- 1058_: test suite now enables all warnings by default.
- 1060_: source distribution is dynamically generated so that it only includes
  relevant files.
- 1079_: [FreeBSD] net_connections()'s fd number is now being set for real
  (instead of -1).  (patch by Gleb Smirnoff)
- 1091_: [SunOS] implemented Process.environ().  (patch by Oleksii Shevchuk)

**Bug fixes**

- 989_: [Windows] boot_time() may return a negative value.
- 1007_: [Windows] boot_time() can have a 1 sec fluctuation between calls; the
  value of the first call is now cached so that boot_time() always returns the
  same value if fluctuation is <= 1 second.
- 1013_: [FreeBSD] psutil.net_connections() may return incorrect PID.  (patch
  by Gleb Smirnoff)
- 1014_: [Linux] Process class can mask legitimate ENOENT exceptions as
  NoSuchProcess.
- 1016_: disk_io_counters() raises RuntimeError on a system with no disks.
- 1017_: net_io_counters() raises RuntimeError on a system with no network
  cards installed.
- 1021_: [Linux] open_files() may erroneously raise NoSuchProcess instead of
  skipping a file which gets deleted while open files are retrieved.
- 1029_: [macOS, FreeBSD] Process.connections('unix') on Python 3 doesn't
  properly handle unicode paths and may raise UnicodeDecodeError.
- 1033_: [macOS, FreeBSD] memory leak for net_connections() and
  Process.connections() when retrieving UNIX sockets (kind='unix').
- 1040_: fixed many unicode related issues such as UnicodeDecodeError on
  Python 3 + UNIX and invalid encoded data on Windows.
- 1042_: [FreeBSD] psutil won't compile on FreeBSD 12.
- 1044_: [macOS] different Process methods incorrectly raise AccessDenied for
  zombie processes.
- 1046_: [Windows] disk_partitions() on Windows overrides user's SetErrorMode.
- 1047_: [Windows] Process username(): memory leak in case exception is thrown.
- 1048_: [Windows] users()'s host field report an invalid IP address.
- 1050_: [Windows] Process.memory_maps memory() leaks memory.
- 1055_: cpu_count() is no longer cached; this is useful on systems such as
  Linux where CPUs can be disabled at runtime. This also reflects on
  Process.cpu_percent() which no longer uses the cache.
- 1058_: fixed Python warnings.
- 1062_: disk_io_counters() and net_io_counters() raise TypeError if no disks
  or NICs are installed on the system.
- 1063_: [NetBSD] net_connections() may list incorrect sockets.
- 1064_: [NetBSD] swap_memory() may segfault in case of error.
- 1065_: [OpenBSD] Process.cmdline() may raise SystemError.
- 1067_: [NetBSD] Process.cmdline() leaks memory if process has terminated.
- 1069_: [FreeBSD] Process.cpu_num() may return 255 for certain kernel
  processes.
- 1071_: [Linux] cpu_freq() may raise IOError on old RedHat distros.
- 1074_: [FreeBSD] sensors_battery() raises OSError in case of no battery.
- 1075_: [Windows] net_if_addrs(): inet_ntop() return value is not checked.
- 1077_: [SunOS] net_if_addrs() shows garbage addresses on SunOS 5.10.
  (patch by Oleksii Shevchuk)
- 1077_: [SunOS] net_connections() does not work on SunOS 5.10. (patch by
  Oleksii Shevchuk)
- 1079_: [FreeBSD] net_connections() didn't list locally connected sockets.
  (patch by Gleb Smirnoff)
- 1085_: cpu_count() return value is now checked and forced to None if <= 1.
- 1087_: Process.cpu_percent() guard against cpu_count() returning None and
  assumes 1 instead.
- 1093_: [SunOS] memory_maps() shows wrong 64 bit addresses.
- 1094_: [Windows] psutil.pid_exists() may lie. Also, all process APIs relying
  on OpenProcess Windows API now check whether the PID is actually running.
- 1098_: [Windows] Process.wait() may erroneously return sooner, when the PID
  is still alive.
- 1099_: [Windows] Process.terminate() may raise AccessDenied even if the
  process already died.
- 1101_: [Linux] sensors_temperatures() may raise ENODEV.

**Porting notes**

- 1039_: returned types consolidation:
  - Windows / Process.cpu_times(): fields #3 and #4 were int instead of float
  - Linux / FreeBSD: connections('unix'): raddr is now set to "" instead of
    None
  - OpenBSD: connections('unix'): laddr and raddr are now set to "" instead of
    None
- 1040_: all strings are encoded by using OS fs encoding.
- 1040_: the following Windows APIs on Python 2 now return a string instead of
  unicode:
  - Process.memory_maps().path
  - WindowsService.bin_path()
  - WindowsService.description()
  - WindowsService.display_name()
  - WindowsService.username()

5.2.2
=====

*2017-04-10*

**Bug fixes**

- 1000_: fixed some setup.py warnings.
- 1002_: [SunOS] remove C macro which will not be available on new Solaris
  versions. (patch by Danek Duvall)
- 1004_: [Linux] Process.io_counters() may raise ValueError.
- 1006_: [Linux] cpu_freq() may return None on some Linux versions does not
  support the function; now the function is not declared instead.
- 1009_: [Linux] sensors_temperatures() may raise OSError.
- 1010_: [Linux] virtual_memory() may raise ValueError on Ubuntu 14.04.

5.2.1
=====

*2017-03-24*

**Bug fixes**

- 981_: [Linux] cpu_freq() may return an empty list.
- 993_: [Windows] Process.memory_maps() on Python 3 may raise
  UnicodeDecodeError.
- 996_: [Linux] sensors_temperatures() may not show all temperatures.
- 997_: [FreeBSD] virtual_memory() may fail due to missing sysctl parameter on
  FreeBSD 12.

5.2.0
=====

*2017-03-05*

**Enhancements**

- 971_: [Linux] Add psutil.sensors_fans() function.  (patch by Nicolas Hennion)
- 976_: [Windows] Process.io_counters() has 2 new fields: *other_count* and
  *other_bytes*.
- 976_: [Linux] Process.io_counters() has 2 new fields: *read_chars* and
  *write_chars*.

**Bug fixes**

- 872_: [Linux] can now compile on Linux by using MUSL C library.
- 985_: [Windows] Fix a crash in `Process.open_files` when the worker thread
  for `NtQueryObject` times out.
- 986_: [Linux] Process.cwd() may raise NoSuchProcess instead of ZombieProcess.

5.1.3
=====

**Bug fixes**

- 971_: [Linux] sensors_temperatures() didn't work on CentOS 7.
- 973_: cpu_percent() may raise ZeroDivisionError.

5.1.2
=====

*2017-02-03*

**Bug fixes**

- 966_: [Linux] sensors_battery().power_plugged may erroneously return None on
  Python 3.
- 968_: [Linux] disk_io_counters() raises TypeError on python 3.
- 970_: [Linux] sensors_battery()'s name and label fields on Python 3 are bytes
  instead of str.

5.1.1
=====

*2017-02-03*

**Enhancements**

- 966_: [Linux] sensors_battery().percent is a float and is more precise.

**Bug fixes**

- 964_: [Windows] Process.username() and psutil.users() may return badly
  decoding character on Python 3.
- 965_: [Linux] disk_io_counters() may miscalculate sector size and report the
  wrong number of bytes read and written.
- 966_: [Linux] sensors_battery() may fail with "no such file error".
- 966_: [Linux] sensors_battery().power_plugged may lie.

5.1.0
=====

*2017-02-01*

**Enhancements**

- 357_: added psutil.Process.cpu_num() (what CPU a process is on).
- 371_: added psutil.sensors_temperatures() (Linux only).
- 941_: added psutil.cpu_freq() (CPU frequency).
- 955_: added psutil.sensors_battery() (Linux, Windows, only).
- 956_: cpu_affinity([]) can now be used as an alias to set affinity against
  all eligible CPUs.

**Bug fixes**

- 687_: [Linux] pid_exists() no longer returns True if passed a process thread
  ID.
- 948_: cannot install psutil with PYTHONOPTIMIZE=2.
- 950_: [Windows] Process.cpu_percent() was calculated incorrectly and showed
  higher number than real usage.
- 951_: [Windows] the uploaded wheels for Python 3.6 64 bit didn't work.
- 959_: psutil exception objects could not be pickled.
- 960_: Popen.wait() did not return the correct negative exit status if process
  is ``kill()``ed by a signal.
- 961_: [Windows] WindowsService.description() may fail with
  ERROR_MUI_FILE_NOT_FOUND.

5.0.1
=====

*2016-12-21*

**Enhancements**

- 939_: tar.gz distribution went from 1.8M to 258K.
- 811_: [Windows] provide a more meaningful error message if trying to use
  psutil on unsupported Windows XP.

**Bug fixes**

- 609_: [SunOS] psutil does not compile on Solaris 10.
- 936_: [Windows] fix compilation error on VS 2013 (patch by Max Bélanger).
- 940_: [Linux] cpu_percent() and cpu_times_percent() was calculated
  incorrectly as "iowait", "guest" and "guest_nice" times were not properly
  taken into account.
- 944_: [OpenBSD] psutil.pids() was omitting PID 0.

5.0.0
=====

*2016-11-06*

**Enhncements**

- 799_: new Process.oneshot() context manager making Process methods around
  +2x faster in general and from +2x to +6x faster on Windows.
- 943_: better error message in case of version conflict on import.

**Bug fixes**

- 932_: [NetBSD] net_connections() and Process.connections() may fail without
  raising an exception.
- 933_: [Windows] memory leak in cpu_stats() and WindowsService.description().

4.4.2
=====

*2016-10-26*

**Bug fixes**

- 931_: psutil no longer compiles on Solaris.

4.4.1
=====

*2016-10-25*

**Bug fixes**

- 927_: ``Popen.__del__`` may cause maximum recursion depth error.

4.4.0
=====

*2016-10-23*

**Enhancements**

- 874_: [Windows] net_if_addrs() returns also the netmask.
- 887_: [Linux] virtual_memory()'s 'available' and 'used' values are more
  precise and match "free" cmdline utility.  "available" also takes into
  account LCX containers preventing "available" to overflow "total".
- 891_: procinfo.py script has been updated and provides a lot more info.

**Bug fixes**

- 514_: [macOS] possibly fix Process.memory_maps() segfault (critical!).
- 783_: [macOS] Process.status() may erroneously return "running" for zombie
  processes.
- 798_: [Windows] Process.open_files() returns and empty list on Windows 10.
- 825_: [Linux] cpu_affinity; fix possible double close and use of unopened
  socket.
- 880_: [Windows] Handle race condition inside psutil_net_connections.
- 885_: ValueError is raised if a negative integer is passed to cpu_percent()
  functions.
- 892_: [Linux] Process.cpu_affinity([-1]) raise SystemError with no error
  set; now ValueError is raised.
- 906_: [BSD] disk_partitions(all=False) returned an empty list. Now the
  argument is ignored and all partitions are always returned.
- 907_: [FreeBSD] Process.exe() may fail with OSError(ENOENT).
- 908_: [macOS, BSD] different process methods could errounesuly mask the real
  error for high-privileged PIDs and raise NoSuchProcess and AccessDenied
  instead of OSError and RuntimeError.
- 909_: [macOS] Process open_files() and connections() methods may raise
  OSError with no exception set if process is gone.
- 916_: [macOS] fix many compilation warnings.

4.3.1
=====

*2016-09-01*

**Enhancements**

- 881_: "make install" now works also when using a virtual env.

**Bug fixes**

- 854_: Process.as_dict() raises ValueError if passed an erroneous attrs name.
- 857_: [SunOS] Process cpu_times(), cpu_percent(), threads() amd memory_maps()
  may raise RuntimeError if attempting to query a 64bit process with a 32bit
  python. "Null" values are returned as a fallback.
- 858_: Process.as_dict() should not return memory_info_ex() because it's
  deprecated.
- 863_: [Windows] memory_map truncates addresses above 32 bits
- 866_: [Windows] win_service_iter() and services in general are not able to
  handle unicode service names / descriptions.
- 869_: [Windows] Process.wait() may raise TimeoutExpired with wrong timeout
  unit (ms instead of sec).
- 870_: [Windows] Handle leak inside psutil_get_process_data.

4.3.0
=====

*2016-06-18*

**Enhancements**

- 819_: [Linux] different speedup improvements:
  Process.ppid() is 20% faster
  Process.status() is 28% faster
  Process.name() is 25% faster
  Process.num_threads is 20% faster on Python 3

**Bug fixes**

- 810_: [Windows] Windows wheels are incompatible with pip 7.1.2.
- 812_: [NetBSD] fix compilation on NetBSD-5.x.
- 823_: [NetBSD] virtual_memory() raises TypeError on Python 3.
- 829_: [UNIX] psutil.disk_usage() percent field takes root reserved space
  into account.
- 816_: [Windows] fixed net_io_counter() values wrapping after 4.3GB in
  Windows Vista (NT 6.0) and above using 64bit values from newer win APIs.

4.2.0
=====

*2016-05-14*

**Enhancements**

- 795_: [Windows] new APIs to deal with Windows services: win_service_iter()
  and win_service_get().
- 800_: [Linux] psutil.virtual_memory() returns a new "shared" memory field.
- 819_: [Linux] speedup /proc parsing:
  - Process.ppid() is 20% faster
  - Process.status() is 28% faster
  - Process.name() is 25% faster
  - Process.num_threads is 20% faster on Python 3

**Bug fixes**

- 797_: [Linux] net_if_stats() may raise OSError for certain NIC cards.
- 813_: Process.as_dict() should ignore extraneous attribute names which gets
  attached to the Process instance.

4.1.0
=====

*2016-03-12*

**Enhancements**

- 777_: [Linux] Process.open_files() on Linux return 3 new fields: position,
  mode and flags.
- 779_: Process.cpu_times() returns two new fields, 'children_user' and
  'children_system' (always set to 0 on macOS and Windows).
- 789_: [Windows] psutil.cpu_times() return two new fields: "interrupt" and
  "dpc". Same for psutil.cpu_times_percent().
- 792_: new psutil.cpu_stats() function returning number of CPU ctx switches
  interrupts, soft interrupts and syscalls.

**Bug fixes**

- 774_: [FreeBSD] net_io_counters() dropout is no longer set to 0 if the kernel
  provides it.
- 776_: [Linux] Process.cpu_affinity() may erroneously raise NoSuchProcess.
  (patch by wxwright)
- 780_: [macOS] psutil does not compile with some gcc versions.
- 786_: net_if_addrs() may report incomplete MAC addresses.
- 788_: [NetBSD] virtual_memory()'s buffers and shared values were set to 0.
- 790_: [macOS] psutil won't compile on macOS 10.4.

4.0.0
=====

*2016-02-17*

**Enhancements**

- 523_: [Linux, FreeBSD] disk_io_counters() return a new "busy_time" field.
- 660_: [Windows] make.bat is smarter in finding alternative VS install
  locations.  (patch by mpderbec)
- 732_: Process.environ().  (patch by Frank Benkstein)
- 753_: [Linux, macOS, Windows] Process USS and PSS (Linux) "real" memory stats.
  (patch by Eric Rahm)
- 755_: Process.memory_percent() "memtype" parameter.
- 758_: tests now live in psutil namespace.
- 760_: expose OS constants (psutil.LINUX, psutil.macOS, etc.)
- 756_: [Linux] disk_io_counters() return 2 new fields: read_merged_count and
  write_merged_count.
- 762_: new scripts/procsmem.py script.

**Bug fixes**

- 685_: [Linux] virtual_memory() provides wrong results on systems with a lot
  of physical memory.
- 704_: [Solaris] psutil does not compile on Solaris sparc.
- 734_: on Python 3 invalid UTF-8 data is not correctly handled for process
  name(), cwd(), exe(), cmdline() and open_files() methods resulting in
  UnicodeDecodeError exceptions. 'surrogateescape' error handler is now
  used as a workaround for replacing the corrupted data.
- 737_: [Windows] when the bitness of psutil and the target process was
  different cmdline() and cwd() could return a wrong result or incorrectly
  report an AccessDenied error.
- 741_: [OpenBSD] psutil does not compile on mips64.
- 751_: [Linux] fixed call to Py_DECREF on possible Null object.
- 754_: [Linux] cmdline() can be wrong in case of zombie process.
- 759_: [Linux] Process.memory_maps() may return paths ending with " (deleted)"
- 761_: [Windows] psutil.boot_time() wraps to 0 after 49 days.
- 764_: [NetBSD] fix compilation on NetBSD-6.x.
- 766_: [Linux] net_connections() can't handle malformed /proc/net/unix file.
- 767_: [Linux] disk_io_counters() may raise ValueError on 2.6 kernels and it's
  broken on 2.4 kernels.
- 770_: [NetBSD] disk_io_counters() metrics didn't update.

3.4.2
=====

*2016-01-20*

**Enhancements**

- 728_: [Solaris] exposed psutil.PROCFS_PATH constant to change the default
  location of /proc filesystem.

**Bug fixes**

- 724_: [FreeBSD] psutil.virtual_memory().total is incorrect.
- 730_: [FreeBSD] psutil.virtual_memory() crashes.

3.4.1
=====

*2016-01-15*

**Enhancements**

- 557_: [NetBSD] added NetBSD support.  (contributed by Ryo Onodera and
  Thomas Klausner)
- 708_: [Linux] psutil.net_connections() and Process.connections() on Python 2
  can be up to 3x faster in case of many connections.
  Also psutil.Process.memory_maps() is slightly faster.
- 718_: process_iter() is now thread safe.

**Bug fixes**

- 714_: [OpenBSD] virtual_memory().cached value was always set to 0.
- 715_: don't crash at import time if cpu_times() fail for some reason.
- 717_: [Linux] Process.open_files fails if deleted files still visible.
- 722_: [Linux] swap_memory() no longer crashes if sin/sout can't be determined
  due to missing /proc/vmstat.
- 724_: [FreeBSD] virtual_memory().total is slightly incorrect.

3.3.0
=====

*2015-11-25*

**Enhancements**

- 558_: [Linux] exposed psutil.PROCFS_PATH constant to change the default
  location of /proc filesystem.
- 615_: [OpenBSD] added OpenBSD support.  (contributed by Landry Breuil)

**Bug fixes**

- 692_: [UNIX] Process.name() is no longer cached as it may change.

3.2.2
=====

*2015-10-04*

**Bug fixes**

- 517_: [SunOS] net_io_counters failed to detect network interfaces
  correctly on Solaris 10
- 541_: [FreeBSD] disk_io_counters r/w times were expressed in seconds instead
  of milliseconds.  (patch by dasumin)
- 610_: [SunOS] fix build and tests on Solaris 10
- 623_: [Linux] process or system connections raises ValueError if IPv6 is not
  supported by the system.
- 678_: [Linux] can't install psutil due to bug in setup.py.
- 688_: [Windows] compilation fails with MSVC 2015, Python 3.5. (patch by
  Mike Sarahan)

3.2.1
=====

*2015-09-03*

**Bug fixes**

- 677_: [Linux] can't install psutil due to bug in setup.py.

3.2.0
=====

*2015-09-02*

**Enhancements**

- 644_: [Windows] added support for CTRL_C_EVENT and CTRL_BREAK_EVENT signals
  to use with Process.send_signal().
- 648_: CI test integration for macOS. (patch by Jeff Tang)
- 663_: [UNIX] net_if_addrs() now returns point-to-point (VPNs) addresses.
- 655_: [Windows] different issues regarding unicode handling were fixed. On
  Python 2 all APIs returning a string will now return an encoded version of it
  by using sys.getfilesystemencoding() codec. The APIs involved are:
  - psutil.net_if_addrs()
  - psutil.net_if_stats()
  - psutil.net_io_counters()
  - psutil.Process.cmdline()
  - psutil.Process.name()
  - psutil.Process.username()
  - psutil.users()

**Bug fixes**

- 513_: [Linux] fixed integer overflow for RLIM_INFINITY.
- 641_: [Windows] fixed many compilation warnings.  (patch by Jeff Tang)
- 652_: [Windows] net_if_addrs() UnicodeDecodeError in case of non-ASCII NIC
  names.
- 655_: [Windows] net_if_stats() UnicodeDecodeError in case of non-ASCII NIC
  names.
- 659_: [Linux] compilation error on Suse 10. (patch by maozguttman)
- 664_: [Linux] compilation error on Alpine Linux. (patch by Bart van Kleef)
- 670_: [Windows] segfgault of net_if_addrs() in case of non-ASCII NIC names.
  (patch by sk6249)
- 672_: [Windows] compilation fails if using Windows SDK v8.0. (patch by
  Steven Winfield)
- 675_: [Linux] net_connections(); UnicodeDecodeError may occur when listing
  UNIX sockets.

3.1.1
=====

*2015-07-15*

**Bug fixes**

- 603_: [Linux] ionice_set value range is incorrect.  (patch by spacewander)
- 645_: [Linux] psutil.cpu_times_percent() may produce negative results.
- 656_: 'from psutil import *' does not work.

3.1.0
=====

*2015-07-15*

**Enhancements**

- 534_: [Linux] disk_partitions() added support for ZFS filesystems.
- 646_: continuous tests integration for Windows with
  https://ci.appveyor.com/project/giampaolo/psutil.
- 647_: new dev guide:
  https://github.com/giampaolo/psutil/blob/master/docs/DEVGUIDE.rst
- 651_: continuous code quality test integration with scrutinizer-ci.com

**Bug fixes**

- 340_: [Windows] Process.open_files() no longer hangs. Instead it uses a
  thred which times out and skips the file handle in case it's taking too long
  to be retrieved.  (patch by Jeff Tang, PR #597)
- 627_: [Windows] Process.name() no longer raises AccessDenied for pids owned
  by another user.
- 636_: [Windows] Process.memory_info() raise AccessDenied.
- 637_: [UNIX] raise exception if trying to send signal to Process PID 0 as it
  will affect os.getpid()'s process group instead of PID 0.
- 639_: [Linux] Process.cmdline() can be truncated.
- 640_: [Linux] *connections functions may swallow errors and return an
  incomplete list of connnections.
- 642_: repr() of exceptions is incorrect.
- 653_: [Windows] Add inet_ntop function for Windows XP to support IPv6.
- 641_: [Windows] Replace deprecated string functions with safe equivalents.

3.0.1
=====

*2015-06-18*

**Bug fixes**

- 632_: [Linux] better error message if cannot parse process UNIX connections.
- 634_: [Linux] Proces.cmdline() does not include empty string arguments.
- 635_: [UNIX] crash on module import if 'enum' package is installed on python
  < 3.4.

3.0.0
=====

*2015-06-13*

**Enhancements**

- 250_: new psutil.net_if_stats() returning NIC statistics (isup, duplex,
  speed, MTU).
- 376_: new psutil.net_if_addrs() returning all NIC addresses a-la ifconfig.
- 469_: on Python >= 3.4 ``IOPRIO_CLASS_*`` and ``*_PRIORITY_CLASS`` constants
  returned by psutil.Process' ionice() and nice() methods are enums instead of
  plain integers.
- 581_: add .gitignore. (patch by Gabi Davar)
- 582_: connection constants returned by psutil.net_connections() and
  psutil.Process.connections() were turned from int to enums on Python > 3.4.
- 587_: Move native extension into the package.
- 589_: Process.cpu_affinity() accepts any kind of iterable (set, tuple, ...),
  not only lists.
- 594_: all deprecated APIs were removed.
- 599_: [Windows] process name() can now be determined for all processes even
  when running as a limited user.
- 602_: pre-commit GIT hook.
- 629_: enhanced support for py.test and nose test discovery and tests run.
- 616_: [Windows] Add inet_ntop function for Windows XP.

**Bug fixes**

- 428_: [all UNIXes except Linux] correct handling of zombie processes;
  introduced new ZombieProcess exception class.
- 512_: [BSD] fix segfault in net_connections().
- 555_: [Linux] psutil.users() correctly handles ":0" as an alias for
  "localhost"
- 579_: [Windows] Fixed open_files() for PID>64K.
- 579_: [Windows] fixed many compiler warnings.
- 585_: [FreeBSD] net_connections() may raise KeyError.
- 586_: [FreeBSD] cpu_affinity() segfaults on set in case an invalid CPU
  number is provided.
- 593_: [FreeBSD] Process().memory_maps() segfaults.
- 606_: Process.parent() may swallow NoSuchProcess exceptions.
- 611_: [SunOS] net_io_counters has send and received swapped
- 614_: [Linux]: cpu_count(logical=False) return the number of physical CPUs
  instead of physical cores.
- 618_: [SunOS] swap tests fail on Solaris when run as normal user
- 628_: [Linux] Process.name() truncates process name in case it contains
  spaces or parentheses.

2.2.1
=====

*2015-02-02*

**Bug fixes**

- 496_: [Linux] fix "ValueError: ambiguos inode with multiple PIDs references"
  (patch by Bruno Binet)

2.2.0
=====

*2015-01-06*

**Enhancements**

- 521_: drop support for Python 2.4 and 2.5.
- 553_: new examples/pstree.py script.
- 564_: C extension version mismatch in case the user messed up with psutil
  installation or with sys.path is now detected at import time.
- 568_: New examples/pidof.py script.
- 569_: [FreeBSD] add support for process CPU affinity.

**Bug fixes**

- 496_: [Solaris] can't import psutil.
- 547_: [UNIX] Process.username() may raise KeyError if UID can't be resolved.
- 551_: [Windows] get rid of the unicode hack for net_io_counters() NIC names.
- 556_: [Linux] lots of file handles were left open.
- 561_: [Linux] net_connections() might skip some legitimate UNIX sockets.
  (patch by spacewander)
- 565_: [Windows] use proper encoding for psutil.Process.username() and
  psutil.users(). (patch by Sylvain Mouquet)
- 567_: [Linux] in the alternative implementation of CPU affinity PyList_Append
  and Py_BuildValue return values are not checked.
- 569_: [FreeBSD] fix memory leak in psutil.cpu_count(logical=False).
- 571_: [Linux] Process.open_files() might swallow AccessDenied exceptions and
  return an incomplete list of open files.

2.1.3
=====

*2014-09-26*

- 536_: [Linux]: fix "undefined symbol: CPU_ALLOC" compilation error.

2.1.2
=====

*2014-09-21*

**Enhancements**

- 407_: project moved from Google Code to Github; code moved from Mercurial
  to Git.
- 492_: use tox to run tests on multiple python versions.  (patch by msabramo)
- 505_: [Windows] distribution as wheel packages.
- 511_: new examples/ps.py sample code.

**Bug fixes**

- 340_: [Windows] Process.get_open_files() no longer hangs.  (patch by
  Jeff Tang)
- 501_: [Windows] disk_io_counters() may return negative values.
- 503_: [Linux] in rare conditions Process exe(), open_files() and
  connections() methods can raise OSError(ESRCH) instead of NoSuchProcess.
- 504_: [Linux] can't build RPM packages via setup.py
- 506_: [Linux] python 2.4 support was broken.
- 522_: [Linux] Process.cpu_affinity() might return EINVAL.  (patch by David
  Daeschler)
- 529_: [Windows] Process.exe() may raise unhandled WindowsError exception
  for PIDs 0 and 4.  (patch by Jeff Tang)
- 530_: [Linux] psutil.disk_io_counters() may crash on old Linux distros
  (< 2.6.5)  (patch by Yaolong Huang)
- 533_: [Linux] Process.memory_maps() may raise TypeError on old Linux distros.

2.1.1
=====

*2014-04-30*

**Bug fixes**

- 446_: [Windows] fix encoding error when using net_io_counters() on Python 3.
  (patch by Szigeti Gabor Niif)
- 460_: [Windows] net_io_counters() wraps after 4G.
- 491_: [Linux] psutil.net_connections() exceptions. (patch by Alexander Grothe)

2.1.0
=====

*2014-04-08*

**Enhancements**

- 387_: system-wide open connections a-la netstat.

**Bug fixes**

- 421_: [Solaris] psutil does not compile on SunOS 5.10 (patch by Naveed
  Roudsari)
- 489_: [Linux] psutil.disk_partitions() return an empty list.

2.0.0
=====

*2014-03-10*

**Enhancements**

- 424_: [Windows] installer for Python 3.X 64 bit.
- 427_: number of logical and physical CPUs (psutil.cpu_count()).
- 447_: psutil.wait_procs() timeout parameter is now optional.
- 452_: make Process instances hashable and usable with set()s.
- 453_: tests on Python < 2.7 require unittest2 module.
- 459_: add a make file for running tests and other repetitive tasks (also
  on Windows).
- 463_: make timeout parameter of cpu_percent* functions default to 0.0 'cause
  it's a common trap to introduce slowdowns.
- 468_: move documentation to readthedocs.com.
- 477_: process cpu_percent() is about 30% faster.  (suggested by crusaderky)
- 478_: [Linux] almost all APIs are about 30% faster on Python 3.X.
- 479_: long deprecated psutil.error module is gone; exception classes now
  live in "psutil" namespace only.

**Bug fixes**

- 193_: psutil.Popen constructor can throw an exception if the spawned process
  terminates quickly.
- 340_: [Windows] process get_open_files() no longer hangs.  (patch by
  jtang@vahna.net)
- 443_: [Linux] fix a potential overflow issue for Process.set_cpu_affinity()
  on systems with more than 64 CPUs.
- 448_: [Windows] get_children() and ppid() memory leak (patch by Ulrich
  Klank).
- 457_: [POSIX] pid_exists() always returns True for PID 0.
- 461_: namedtuples are not pickle-able.
- 466_: [Linux] process exe improper null bytes handling.  (patch by
  Gautam Singh)
- 470_: wait_procs() might not wait.  (patch by crusaderky)
- 471_: [Windows] process exe improper unicode handling. (patch by
  alex@mroja.net)
- 473_: psutil.Popen.wait() does not set returncode attribute.
- 474_: [Windows] Process.cpu_percent() is no longer capped at 100%.
- 476_: [Linux] encoding error for process name and cmdline.

**API changes**

For the sake of consistency a lot of psutil APIs have been renamed.
In most cases accessing the old names will work but it will cause a
DeprecationWarning.

- psutil.* module level constants have being replaced by functions:

  +-----------------------+-------------------------------+
  | Old name              | Replacement                   |
  +=======================+===============================+
  | psutil.NUM_CPUS       | psutil.cpu_cpunt()            |
  +-----------------------+-------------------------------+
  | psutil.BOOT_TIME      | psutil.boot_time()            |
  +-----------------------+-------------------------------+
  | psutil.TOTAL_PHYMEM   | psutil.virtual_memory().total |
  +-----------------------+-------------------------------+

- Renamed psutil.* functions:

  +--------------------------+-------------------------------+
  | Old name                 | Replacement                   |
  +==========================+===============================+
  | - psutil.get_pid_list()  | psutil.pids()                 |
  +--------------------------+-------------------------------+
  | - psutil.get_users()     | psutil.users()                |
  +--------------------------+-------------------------------+
  | - psutil.get_boot_time() | psutil.boot_time()            |
  +--------------------------+-------------------------------+

- All psutil.Process ``get_*`` methods lost the ``get_`` prefix.
  get_ext_memory_info() renamed to memory_info_ex().
  Assuming "p = psutil.Process()":

  +--------------------------+----------------------+
  | Old name                 | Replacement          |
  +==========================+======================+
  | p.get_children()         | p.children()         |
  +--------------------------+----------------------+
  | p.get_connections()      | p.connections()      |
  +--------------------------+----------------------+
  | p.get_cpu_affinity()     | p.cpu_affinity()     |
  +--------------------------+----------------------+
  | p.get_cpu_percent()      | p.cpu_percent()      |
  +--------------------------+----------------------+
  | p.get_cpu_times()        | p.cpu_times()        |
  +--------------------------+----------------------+
  | p.get_ext_memory_info()  | p.memory_info_ex()   |
  +--------------------------+----------------------+
  | p.get_io_counters()      | p.io_counters()      |
  +--------------------------+----------------------+
  | p.get_ionice()           | p.ionice()           |
  +--------------------------+----------------------+
  | p.get_memory_info()      | p.memory_info()      |
  +--------------------------+----------------------+
  | p.get_memory_maps()      | p.memory_maps()      |
  +--------------------------+----------------------+
  | p.get_memory_percent()   | p.memory_percent()   |
  +--------------------------+----------------------+
  | p.get_nice()             | p.nice()             |
  +--------------------------+----------------------+
  | p.get_num_ctx_switches() | p.num_ctx_switches() |
  +--------------------------+----------------------+
  | p.get_num_fds()          | p.num_fds()          |
  +--------------------------+----------------------+
  | p.get_num_threads()      | p.num_threads()      |
  +--------------------------+----------------------+
  | p.get_open_files()       | p.open_files()       |
  +--------------------------+----------------------+
  | p.get_rlimit()           | p.rlimit()           |
  +--------------------------+----------------------+
  | p.get_threads()          | p.threads()          |
  +--------------------------+----------------------+
  | p.getcwd()               | p.cwd()              |
  +--------------------------+----------------------+

- All psutil.Process ``set_*`` methods lost the ``set_`` prefix.
  Assuming "p = psutil.Process()":

  +----------------------+---------------------------------+
  | Old name             | Replacement                     |
  +======================+=================================+
  | p.set_nice()         | p.nice(value)                   |
  +----------------------+---------------------------------+
  | p.set_ionice()       | p.ionice(ioclass, value=None)   |
  +----------------------+---------------------------------+
  | p.set_cpu_affinity() | p.cpu_affinity(cpus)            |
  +----------------------+---------------------------------+
  | p.set_rlimit()       | p.rlimit(resource, limits=None) |
  +----------------------+---------------------------------+

- Except for 'pid' all psutil.Process class properties have been turned into
  methods. This is the only case which there are no aliases.
  Assuming "p = psutil.Process()":

  +---------------+-----------------+
  | Old name      | Replacement     |
  +===============+=================+
  | p.name        | p.name()        |
  +---------------+-----------------+
  | p.parent      | p.parent()      |
  +---------------+-----------------+
  | p.ppid        | p.ppid()        |
  +---------------+-----------------+
  | p.exe         | p.exe()         |
  +---------------+-----------------+
  | p.cmdline     | p.cmdline()     |
  +---------------+-----------------+
  | p.status      | p.status()      |
  +---------------+-----------------+
  | p.uids        | p.uids()        |
  +---------------+-----------------+
  | p.gids        | p.gids()        |
  +---------------+-----------------+
  | p.username    | p.username()    |
  +---------------+-----------------+
  | p.create_time | p.create_time() |
  +---------------+-----------------+

- timeout parameter of cpu_percent* functions defaults to 0.0 instead of 0.1.
- long deprecated psutil.error module is gone; exception classes now live in
  "psutil" namespace only.
- Process instances' "retcode" attribute returned by psutil.wait_procs() has
  been renamed to "returncode" for consistency with subprocess.Popen.

1.2.1
=====

*2013-11-25*

**Bug fixes**

- 348_: [Windows XP] fixed "ImportError: DLL load failed" occurring on module
  import.
- 425_: [Solaris] crash on import due to failure at determining BOOT_TIME.
- 443_: [Linux] can't set CPU affinity on systems with more than 64 cores.

1.2.0
=====

*2013-11-20*

**Enhancements**

- 439_: assume os.getpid() if no argument is passed to psutil.Process
  constructor.
- 440_: new psutil.wait_procs() utility function which waits for multiple
  processes to terminate.

**Bug fixes**

- 348_: [Windows XP/Vista] fix "ImportError: DLL load failed" occurring on
  module import.

1.1.3
=====

*2013-11-07*

**Bug fixes**

- 442_: [Linux] psutil won't compile on certain version of Linux because of
  missing prlimit(2) syscall.

1.1.2
=====

*2013-10-22*

**Bug fixes**

- 442_: [Linux] psutil won't compile on Debian 6.0 because of missing
  prlimit(2) syscall.

1.1.1
=====

*2013-10-08*

**Bug fixes**

- 442_: [Linux] psutil won't compile on kernels < 2.6.36 due to missing
  prlimit(2) syscall.

1.1.0
=====

*2013-09-28*

**Enhancements**

- 410_: host tar.gz and windows binary files are on PyPI.
- 412_: [Linux] get/set process resource limits.
- 415_: [Windows] Process.get_children() is an order of magnitude faster.
- 426_: [Windows] Process.name is an order of magnitude faster.
- 431_: [UNIX] Process.name is slightly faster because it unnecessarily
  retrieved also process cmdline.

**Bug fixes**

- 391_: [Windows] psutil.cpu_times_percent() returns negative percentages.
- 408_: STATUS_* and CONN_* constants don't properly serialize on JSON.
- 411_: [Windows] examples/disk_usage.py may pop-up a GUI error.
- 413_: [Windows] Process.get_memory_info() leaks memory.
- 414_: [Windows] Process.exe on Windows XP may raise ERROR_INVALID_PARAMETER.
- 416_: psutil.disk_usage() doesn't work well with unicode path names.
- 430_: [Linux] process IO counters report wrong number of r/w syscalls.
- 435_: [Linux] psutil.net_io_counters() might report erreneous NIC names.
- 436_: [Linux] psutil.net_io_counters() reports a wrong 'dropin' value.

**API changes**

- 408_: turn STATUS_* and CONN_* constants into plain Python strings.

1.0.1
=====

*2013-07-12*

**Bug fixes**

- 405_: network_io_counters(pernic=True) no longer works as intended in 1.0.0.

1.0.0
=====

*2013-07-10*

**Enhancements**

- 18_:  Solaris support (yay!)  (thanks Justin Venus)
- 367_: Process.get_connections() 'status' strings are now constants.
- 380_: test suite exits with non-zero on failure.  (patch by floppymaster)
- 391_: introduce unittest2 facilities and provide workarounds if unittest2
  is not installed (python < 2.7).

**Bug fixes**

- 374_: [Windows] negative memory usage reported if process uses a lot of
  memory.
- 379_: [Linux] Process.get_memory_maps() may raise ValueError.
- 394_: [macOS] Mapped memory regions report incorrect file name.
- 404_: [Linux] sched_*affinity() are implicitly declared. (patch by Arfrever)

**API changes**

- Process.get_connections() 'status' field is no longer a string but a
  constant object (psutil.CONN_*).
- Process.get_connections() 'local_address' and 'remote_address' fields
  renamed to 'laddr' and 'raddr'.
- psutil.network_io_counters() renamed to psutil.net_io_counters().

0.7.1
=====

*2013-05-03*

**Bug fixes**

- 325_: [BSD] psutil.virtual_memory() can raise SystemError.
  (patch by Jan Beich)
- 370_: [BSD] Process.get_connections() requires root.  (patch by John Baldwin)
- 372_: [BSD] different process methods raise NoSuchProcess instead of
  AccessDenied.

0.7.0
=====

*2013-04-12*

**Enhancements**

- 233_: code migrated to Mercurial (yay!)
- 246_: psutil.error module is deprecated and scheduled for removal.
- 328_: [Windows] process IO nice/priority support.
- 359_: psutil.get_boot_time()
- 361_: [Linux] psutil.cpu_times() now includes new 'steal', 'guest' and
  'guest_nice' fields available on recent Linux kernels.
  Also, psutil.cpu_percent() is more accurate.
- 362_: cpu_times_percent() (per-CPU-time utilization as a percentage)

**Bug fixes**

- 234_: [Windows] disk_io_counters() fails to list certain disks.
- 264_: [Windows] use of psutil.disk_partitions() may cause a message box to
  appear.
- 313_: [Linux] psutil.virtual_memory() and psutil.swap_memory() can crash on
  certain exotic Linux flavors having an incomplete /proc interface.
  If that's the case we now set the unretrievable stats to 0 and raise a
  RuntimeWarning.
- 315_: [macOS] fix some compilation warnings.
- 317_: [Windows] cannot set process CPU affinity above 31 cores.
- 319_: [Linux] process get_memory_maps() raises KeyError 'Anonymous' on Debian
  squeeze.
- 321_: [UNIX] Process.ppid property is no longer cached as the kernel may set
  the ppid to 1 in case of a zombie process.
- 323_: [macOS] disk_io_counters()'s read_time and write_time parameters were
  reporting microseconds not milliseconds.  (patch by Gregory Szorc)
- 331_: Process cmdline is no longer cached after first acces as it may change.
- 333_: [macOS] Leak of Mach ports on macOS (patch by rsesek@google.com)
- 337_: [Linux] process methods not working because of a poor /proc
  implementation will raise NotImplementedError rather than RuntimeError
  and Process.as_dict() will not blow up.  (patch by Curtin1060)
- 338_: [Linux] disk_io_counters() fails to find some disks.
- 339_: [FreeBSD] get_pid_list() can allocate all the memory on system.
- 341_: [Linux] psutil might crash on import due to error in retrieving system
  terminals map.
- 344_: [FreeBSD] swap_memory() might return incorrect results due to
  kvm_open(3) not being called. (patch by Jean Sebastien)
- 338_: [Linux] disk_io_counters() fails to find some disks.
- 351_: [Windows] if psutil is compiled with mingw32 (provided installers for
  py2.4 and py2.5 are) disk_io_counters() will fail. (Patch by m.malycha)
- 353_: [macOS] get_users() returns an empty list on macOS 10.8.
- 356_: Process.parent now checks whether parent PID has been reused in which
  case returns None.
- 365_: Process.set_nice() should check PID has not been reused by another
  process.
- 366_: [FreeBSD] get_memory_maps(), get_num_fds(), get_open_files() and
  getcwd() Process methods raise RuntimeError instead of AccessDenied.

**API changes**

- Process.cmdline property is no longer cached after first access.
- Process.ppid property is no longer cached after first access.
- [Linux] Process methods not working because of a poor /proc implementation
  will raise NotImplementedError instead of RuntimeError.
- psutil.error module is deprecated and scheduled for removal.

0.6.1
=====

*2012-08-16*

**Enhancements**

- 316_: process cmdline property now makes a better job at guessing the process
  executable from the cmdline.

**Bug fixes**

- 316_: process exe was resolved in case it was a symlink.
- 318_: python 2.4 compatibility was broken.

**API changes**

- process exe can now return an empty string instead of raising AccessDenied.
- process exe is no longer resolved in case it's a symlink.

0.6.0
=====

*2012-08-13*

**Enhancements**

- 216_: [POSIX] get_connections() UNIX sockets support.
- 220_: [FreeBSD] get_connections() has been rewritten in C and no longer
  requires lsof.
- 222_: [macOS] add support for process cwd.
- 261_: process extended memory info.
- 295_: [macOS] process executable path is now determined by asking the OS
  instead of being guessed from process cmdline.
- 297_: [macOS] the Process methods below were always raising AccessDenied for
  any process except the current one. Now this is no longer true. Also
  they are 2.5x faster.
  - name
  - get_memory_info()
  - get_memory_percent()
  - get_cpu_times()
  - get_cpu_percent()
  - get_num_threads()
- 300_: examples/pmap.py script.
- 301_: process_iter() now yields processes sorted by their PIDs.
- 302_: process number of voluntary and involuntary context switches.
- 303_: [Windows] the Process methods below were always raising AccessDenied
  for any process not owned by current user. Now this is no longer true:
  - create_time
  - get_cpu_times()
  - get_cpu_percent()
  - get_memory_info()
  - get_memory_percent()
  - get_num_handles()
  - get_io_counters()
- 305_: add examples/netstat.py script.
- 311_: system memory functions has been refactorized and rewritten and now
  provide a more detailed and consistent representation of the system
  memory. New psutil.virtual_memory() function provides the following
  memory amounts:
  - total
  - available
  - percent
  - used
  - active [POSIX]
  - inactive [POSIX]
  - buffers (BSD, Linux)
  - cached (BSD, macOS)
  - wired (macOS, BSD)
  - shared [FreeBSD]
  New psutil.swap_memory() provides:
  - total
  - used
  - free
  - percent
  - sin (no. of bytes the system has swapped in from disk (cumulative))
  - sout (no. of bytes the system has swapped out from disk (cumulative))
  All old memory-related functions are deprecated.
  Also two new example scripts were added:  free.py and meminfo.py.
- 312_: psutil.network_io_counters() namedtuple includes 4 new fields:
  errin, errout dropin and dropout, reflecting the number of packets
  dropped and with errors.

**Bug fixes**

- 298_: [macOS and BSD] memory leak in get_num_fds().
- 299_: potential memory leak every time PyList_New(0) is used.
- 303_: [Windows] potential heap corruption in get_num_threads() and
  get_status() Process methods.
- 305_: [FreeBSD] psutil can't compile on FreeBSD 9 due to removal of utmp.h.
- 306_: at C level, errors are not checked when invoking Py* functions which
  create or manipulate Python objects leading to potential memory related
  errors and/or segmentation faults.
- 307_: [FreeBSD] values returned by psutil.network_io_counters() are wrong.
- 308_: [BSD / Windows] psutil.virtmem_usage() wasn't actually returning
  information about swap memory usage as it was supposed to do. It does
  now.
- 309_: get_open_files() might not return files which can not be accessed
  due to limited permissions. AccessDenied is now raised instead.

**API changes**

- psutil.phymem_usage() is deprecated       (use psutil.virtual_memory())
- psutil.virtmem_usage() is deprecated      (use psutil.swap_memory())
- psutil.phymem_buffers() on Linux is deprecated  (use psutil.virtual_memory())
- psutil.cached_phymem() on Linux is deprecated   (use psutil.virtual_memory())
- [Windows and BSD] psutil.virtmem_usage() now returns information about swap
  memory instead of virtual memory.

0.5.1
=====

*2012-06-29*

**Enhancements**

- 293_: [Windows] process executable path is now determined by asking the OS
  instead of being guessed from process cmdline.

**Bug fixes**

- 292_: [Linux] race condition in process files/threads/connections.
- 294_: [Windows] Process CPU affinity is only able to set CPU #0.

0.5.0
=====

*2012-06-27*

**Enhancements**

- 195_: [Windows] number of handles opened by process.
- 209_: psutil.disk_partitions() now provides also mount options.
- 229_: list users currently connected on the system (psutil.get_users()).
- 238_: [Linux, Windows] process CPU affinity (get and set).
- 242_: Process.get_children(recursive=True): return all process
  descendants.
- 245_: [POSIX] Process.wait() incrementally consumes less CPU cycles.
- 257_: [Windows] removed Windows 2000 support.
- 258_: [Linux] Process.get_memory_info() is now 0.5x faster.
- 260_: process's mapped memory regions. (Windows patch by wj32.64, macOS patch
  by Jeremy Whitlock)
- 262_: [Windows] psutil.disk_partitions() was slow due to inspecting the
  floppy disk drive also when "all" argument was False.
- 273_: psutil.get_process_list() is deprecated.
- 274_: psutil no longer requires 2to3 at installation time in order to work
  with Python 3.
- 278_: new Process.as_dict() method.
- 281_: ppid, name, exe, cmdline and create_time properties of Process class
  are now cached after being accessed.
- 282_: psutil.STATUS_* constants can now be compared by using their string
  representation.
- 283_: speedup Process.is_running() by caching its return value in case the
  process is terminated.
- 284_: [POSIX] per-process number of opened file descriptors.
- 287_: psutil.process_iter() now caches Process instances between calls.
- 290_: Process.nice property is deprecated in favor of new get_nice() and
  set_nice() methods.

**Bug fixes**

- 193_: psutil.Popen constructor can throw an exception if the spawned process
  terminates quickly.
- 240_: [macOS] incorrect use of free() for Process.get_connections().
- 244_: [POSIX] Process.wait() can hog CPU resources if called against a
  process which is not our children.
- 248_: [Linux] psutil.network_io_counters() might return erroneous NIC names.
- 252_: [Windows] process getcwd() erroneously raise NoSuchProcess for
  processes owned by another user.  It now raises AccessDenied instead.
- 266_: [Windows] psutil.get_pid_list() only shows 1024 processes.
  (patch by Amoser)
- 267_: [macOS] Process.get_connections() - an erroneous remote address was
  returned. (Patch by Amoser)
- 272_: [Linux] Porcess.get_open_files() - potential race condition can lead to
  unexpected NoSuchProcess exception.  Also, we can get incorrect reports
  of not absolutized path names.
- 275_: [Linux] Process.get_io_counters() erroneously raise NoSuchProcess on
  old Linux versions. Where not available it now raises
  NotImplementedError.
- 286_: Process.is_running() doesn't actually check whether PID has been
  reused.
- 314_: Process.get_children() can sometimes return non-children.

**API changes**

- Process.nice property is deprecated in favor of new get_nice() and set_nice()
  methods.
- psutil.get_process_list() is deprecated.
- ppid, name, exe, cmdline and create_time properties of Process class are now
  cached after being accessed, meaning NoSuchProcess will no longer be raised
  in case the process is gone in the meantime.
- psutil.STATUS_* constants can now be compared by using their string
  representation.

0.4.1
=====

*2011-12-14*

**Bug fixes**

- 228_: some example scripts were not working with python 3.
- 230_: [Windows / macOS] memory leak in Process.get_connections().
- 232_: [Linux] psutil.phymem_usage() can report erroneous values which are
  different than "free" command.
- 236_: [Windows] memory/handle leak in Process's get_memory_info(),
  suspend() and resume() methods.

0.4.0
=====

*2011-10-29*

**Enhancements**

- 150_: network I/O counters. (macOS and Windows patch by Jeremy Whitlock)
- 154_: [FreeBSD] add support for process getcwd()
- 157_: [Windows] provide installer for Python 3.2 64-bit.
- 198_: Process.wait(timeout=0) can now be used to make wait() return
  immediately.
- 206_: disk I/O counters. (macOS and Windows patch by Jeremy Whitlock)
- 213_: examples/iotop.py script.
- 217_: Process.get_connections() now has a "kind" argument to filter
  for connections with different criteria.
- 221_: [FreeBSD] Process.get_open_files has been rewritten in C and no longer
  relies on lsof.
- 223_: examples/top.py script.
- 227_: examples/nettop.py script.

**Bug fixes**

- 135_: [macOS] psutil cannot create Process object.
- 144_: [Linux] no longer support 0 special PID.
- 188_: [Linux] psutil import error on Linux ARM architectures.
- 194_: [POSIX] psutil.Process.get_cpu_percent() now reports a percentage over
  100 on multicore processors.
- 197_: [Linux] Process.get_connections() is broken on platforms not
  supporting IPv6.
- 200_: [Linux] psutil.NUM_CPUS not working on armel and sparc architectures
  and causing crash on module import.
- 201_: [Linux] Process.get_connections() is broken on big-endian
  architectures.
- 211_: Process instance can unexpectedly raise NoSuchProcess if tested for
  equality with another object.
- 218_: [Linux] crash at import time on Debian 64-bit because of a missing
  line in /proc/meminfo.
- 226_: [FreeBSD] crash at import time on FreeBSD 7 and minor.

0.3.0
=====

*2011-07-08*

**Enhancements**

- 125_: system per-cpu percentage utilization and times.
- 163_: per-process associated terminal (TTY).
- 171_: added get_phymem() and get_virtmem() functions returning system
  memory information (total, used, free) and memory percent usage.
  total_* avail_* and used_* memory functions are deprecated.
- 172_: disk usage statistics.
- 174_: mounted disk partitions.
- 179_: setuptools is now used in setup.py

**Bug fixes**

- 159_: SetSeDebug() does not close handles or unset impersonation on return.
- 164_: [Windows] wait function raises a TimeoutException when a process
  returns -1 .
- 165_: process.status raises an unhandled exception.
- 166_: get_memory_info() leaks handles hogging system resources.
- 168_: psutil.cpu_percent() returns erroneous results when used in
  non-blocking mode.  (patch by Philip Roberts)
- 178_: macOS - Process.get_threads() leaks memory
- 180_: [Windows] Process's get_num_threads() and get_threads() methods can
  raise NoSuchProcess exception while process still exists.

0.2.1
=====

*2011-03-20*

**Enhancements**

- 64_: per-process I/O counters.
- 116_: per-process wait() (wait for process to terminate and return its exit
  code).
- 134_: per-process get_threads() returning information (id, user and kernel
  times) about threads opened by process.
- 136_: process executable path on FreeBSD is now determined by asking the
  kernel instead of guessing it from cmdline[0].
- 137_: per-process real, effective and saved user and group ids.
- 140_: system boot time.
- 142_: per-process get and set niceness (priority).
- 143_: per-process status.
- 147_: per-process I/O nice (priority) - Linux only.
- 148_: psutil.Popen class which tidies up subprocess.Popen and psutil.Process
  in a unique interface.
- 152_: [macOS] get_process_open_files() implementation has been rewritten
  in C and no longer relies on lsof resulting in a 3x speedup.
- 153_: [macOS] get_process_connection() implementation has been rewritten
  in C and no longer relies on lsof resulting in a 3x speedup.

**Bug fixes**

- 83_:  process cmdline is empty on macOS 64-bit.
- 130_: a race condition can cause IOError exception be raised on
  Linux if process disappears between open() and subsequent read() calls.
- 145_: WindowsError was raised instead of psutil.AccessDenied when using
  process resume() or suspend() on Windows.
- 146_: 'exe' property on Linux can raise TypeError if path contains NULL
  bytes.
- 151_: exe and getcwd() for PID 0 on Linux return inconsistent data.

**API changes**

- Process "uid" and "gid" properties are deprecated in favor of "uids" and
  "gids" properties.

0.2.0
=====

*2010-11-13*

**Enhancements**

- 79_: per-process open files.
- 88_: total system physical cached memory.
- 88_: total system physical memory buffers used by the kernel.
- 91_: per-process send_signal() and terminate() methods.
- 95_: NoSuchProcess and AccessDenied exception classes now provide "pid",
  "name" and "msg" attributes.
- 97_: per-process children.
- 98_: Process.get_cpu_times() and Process.get_memory_info now return
  a namedtuple instead of a tuple.
- 103_: per-process opened TCP and UDP connections.
- 107_: add support for Windows 64 bit. (patch by cjgohlke)
- 111_: per-process executable name.
- 113_: exception messages now include process name and pid.
- 114_: process username Windows implementation has been rewritten in pure
  C and no longer uses WMI resulting in a big speedup. Also, pywin32 is no
  longer required as a third-party dependancy. (patch by wj32)
- 117_: added support for Windows 2000.
- 123_: psutil.cpu_percent() and psutil.Process.cpu_percent() accept a
  new 'interval' parameter.
- 129_: per-process number of threads.

**Bug fixes**

- 80_: fixed warnings when installing psutil with easy_install.
- 81_: psutil fails to compile with Visual Studio.
- 94_: suspend() raises OSError instead of AccessDenied.
- 86_: psutil didn't compile against FreeBSD 6.x.
- 102_: orphaned process handles obtained by using OpenProcess in C were
  left behind every time Process class was instantiated.
- 111_: path and name Process properties report truncated or erroneous
  values on UNIX.
- 120_: cpu_percent() always returning 100% on macOS.
- 112_: uid and gid properties don't change if process changes effective
  user/group id at some point.
- 126_: ppid, uid, gid, name, exe, cmdline and create_time properties are
  no longer cached and correctly raise NoSuchProcess exception if the process
  disappears.

**API changes**

- psutil.Process.path property is deprecated and works as an alias for "exe"
  property.
- psutil.Process.kill(): signal argument was removed - to send a signal to the
  process use send_signal(signal) method instead.
- psutil.Process.get_memory_info() returns a nametuple instead of a tuple.
- psutil.cpu_times() returns a nametuple instead of a tuple.
- New psutil.Process methods: get_open_files(), get_connections(),
  send_signal() and terminate().
- ppid, uid, gid, name, exe, cmdline and create_time properties are no longer
  cached and raise NoSuchProcess exception if process disappears.
- psutil.cpu_percent() no longer returns immediately (see issue 123).
- psutil.Process.get_cpu_percent() and psutil.cpu_percent() no longer returns
  immediately by default (see issue 123).

0.1.3
=====

*2010-03-02*

**Enhancements**

- 14_: per-process username
- 51_: per-process current working directory (Windows and Linux only)
- 59_: Process.is_running() is now 10 times faster
- 61_: added supoprt for FreeBSD 64 bit
- 71_: implemented suspend/resume process
- 75_: python 3 support

**Bug fixes**

- 36_: process cpu_times() and memory_info() functions succeeded also for dead
  processes while a NoSuchProcess exception is supposed to be raised.
- 48_: incorrect size for mib array defined in getcmdargs for BSD
- 49_: possible memory leak due to missing free() on error condition on
- 50_: fixed getcmdargs() memory fragmentation on BSD
- 55_: test_pid_4 was failing on Windows Vista
- 57_: some unit tests were failing on systems where no swap memory is
  available
- 58_: is_running() is now called before kill() to make sure we are going
  to kill the correct process.
- 73_: virtual memory size reported on macOS includes shared library size
- 77_: NoSuchProcess wasn't raised on Process.create_time if kill() was
  used first.

0.1.2
=====

*2009-05-06*

**Enhancements**

- 32_: Per-process CPU user/kernel times
- 33_: Process create time
- 34_: Per-process CPU utilization percentage
- 38_: Per-process memory usage (bytes)
- 41_: Per-process memory utilization (percent)
- 39_: System uptime
- 43_: Total system virtual memory
- 46_: Total system physical memory
- 44_: Total system used/free virtual and physical memory

**Bug fixes**

- 36_: [Windows] NoSuchProcess not raised when accessing timing methods.
- 40_: test_get_cpu_times() failing on FreeBSD and macOS.
- 42_: [Windows] get_memory_percent() raises AccessDenied.

0.1.1
=====

*2009-03-06*

**Enhancements**

- 4_: FreeBSD support for all functions of psutil
- 9_: Process.uid and Process.gid now retrieve process UID and GID.
- 11_: Support for parent/ppid - Process.parent property returns a
  Process object representing the parent process, and Process.ppid returns
  the parent PID.
- 12_ & 15:
  NoSuchProcess exception now raised when creating an object
  for a nonexistent process, or when retrieving information about a process
  that has gone away.
- 21_: AccessDenied exception created for raising access denied errors
  from OSError or WindowsError on individual platforms.
- 26_: psutil.process_iter() function to iterate over processes as
  Process objects with a generator.
- Process objects can now also be compared with == operator for equality
  (PID, name, command line are compared).

**Bug fixes**

- 16_: [Windows] Special case for "System Idle Process" (PID 0) which
  otherwise would return an "invalid parameter" exception.
- 17_: get_process_list() ignores NoSuchProcess and AccessDenied
  exceptions during building of the list.
- 22_: [Windows] Process(0).kill() was failing with an unset exception.
- 23_: Special case for pid_exists(0)
- 24_: [Windows] Process(0).kill() now raises AccessDenied exception instead
  of WindowsError.
- 30_: psutil.get_pid_list() was returning two ins

.. _1: https://github.com/giampaolo/psutil/issues/1
.. _2: https://github.com/giampaolo/psutil/issues/2
.. _3: https://github.com/giampaolo/psutil/issues/3
.. _4: https://github.com/giampaolo/psutil/issues/4
.. _5: https://github.com/giampaolo/psutil/issues/5
.. _6: https://github.com/giampaolo/psutil/issues/6
.. _7: https://github.com/giampaolo/psutil/issues/7
.. _8: https://github.com/giampaolo/psutil/issues/8
.. _9: https://github.com/giampaolo/psutil/issues/9
.. _10: https://github.com/giampaolo/psutil/issues/10
.. _11: https://github.com/giampaolo/psutil/issues/11
.. _12: https://github.com/giampaolo/psutil/issues/12
.. _13: https://github.com/giampaolo/psutil/issues/13
.. _14: https://github.com/giampaolo/psutil/issues/14
.. _15: https://github.com/giampaolo/psutil/issues/15
.. _16: https://github.com/giampaolo/psutil/issues/16
.. _17: https://github.com/giampaolo/psutil/issues/17
.. _18: https://github.com/giampaolo/psutil/issues/18
.. _19: https://github.com/giampaolo/psutil/issues/19
.. _20: https://github.com/giampaolo/psutil/issues/20
.. _21: https://github.com/giampaolo/psutil/issues/21
.. _22: https://github.com/giampaolo/psutil/issues/22
.. _23: https://github.com/giampaolo/psutil/issues/23
.. _24: https://github.com/giampaolo/psutil/issues/24
.. _25: https://github.com/giampaolo/psutil/issues/25
.. _26: https://github.com/giampaolo/psutil/issues/26
.. _27: https://github.com/giampaolo/psutil/issues/27
.. _28: https://github.com/giampaolo/psutil/issues/28
.. _29: https://github.com/giampaolo/psutil/issues/29
.. _30: https://github.com/giampaolo/psutil/issues/30
.. _31: https://github.com/giampaolo/psutil/issues/31
.. _32: https://github.com/giampaolo/psutil/issues/32
.. _33: https://github.com/giampaolo/psutil/issues/33
.. _34: https://github.com/giampaolo/psutil/issues/34
.. _35: https://github.com/giampaolo/psutil/issues/35
.. _36: https://github.com/giampaolo/psutil/issues/36
.. _37: https://github.com/giampaolo/psutil/issues/37
.. _38: https://github.com/giampaolo/psutil/issues/38
.. _39: https://github.com/giampaolo/psutil/issues/39
.. _40: https://github.com/giampaolo/psutil/issues/40
.. _41: https://github.com/giampaolo/psutil/issues/41
.. _42: https://github.com/giampaolo/psutil/issues/42
.. _43: https://github.com/giampaolo/psutil/issues/43
.. _44: https://github.com/giampaolo/psutil/issues/44
.. _45: https://github.com/giampaolo/psutil/issues/45
.. _46: https://github.com/giampaolo/psutil/issues/46
.. _47: https://github.com/giampaolo/psutil/issues/47
.. _48: https://github.com/giampaolo/psutil/issues/48
.. _49: https://github.com/giampaolo/psutil/issues/49
.. _50: https://github.com/giampaolo/psutil/issues/50
.. _51: https://github.com/giampaolo/psutil/issues/51
.. _52: https://github.com/giampaolo/psutil/issues/52
.. _53: https://github.com/giampaolo/psutil/issues/53
.. _54: https://github.com/giampaolo/psutil/issues/54
.. _55: https://github.com/giampaolo/psutil/issues/55
.. _56: https://github.com/giampaolo/psutil/issues/56
.. _57: https://github.com/giampaolo/psutil/issues/57
.. _58: https://github.com/giampaolo/psutil/issues/58
.. _59: https://github.com/giampaolo/psutil/issues/59
.. _60: https://github.com/giampaolo/psutil/issues/60
.. _61: https://github.com/giampaolo/psutil/issues/61
.. _62: https://github.com/giampaolo/psutil/issues/62
.. _63: https://github.com/giampaolo/psutil/issues/63
.. _64: https://github.com/giampaolo/psutil/issues/64
.. _65: https://github.com/giampaolo/psutil/issues/65
.. _66: https://github.com/giampaolo/psutil/issues/66
.. _67: https://github.com/giampaolo/psutil/issues/67
.. _68: https://github.com/giampaolo/psutil/issues/68
.. _69: https://github.com/giampaolo/psutil/issues/69
.. _70: https://github.com/giampaolo/psutil/issues/70
.. _71: https://github.com/giampaolo/psutil/issues/71
.. _72: https://github.com/giampaolo/psutil/issues/72
.. _73: https://github.com/giampaolo/psutil/issues/73
.. _74: https://github.com/giampaolo/psutil/issues/74
.. _75: https://github.com/giampaolo/psutil/issues/75
.. _76: https://github.com/giampaolo/psutil/issues/76
.. _77: https://github.com/giampaolo/psutil/issues/77
.. _78: https://github.com/giampaolo/psutil/issues/78
.. _79: https://github.com/giampaolo/psutil/issues/79
.. _80: https://github.com/giampaolo/psutil/issues/80
.. _81: https://github.com/giampaolo/psutil/issues/81
.. _82: https://github.com/giampaolo/psutil/issues/82
.. _83: https://github.com/giampaolo/psutil/issues/83
.. _84: https://github.com/giampaolo/psutil/issues/84
.. _85: https://github.com/giampaolo/psutil/issues/85
.. _86: https://github.com/giampaolo/psutil/issues/86
.. _87: https://github.com/giampaolo/psutil/issues/87
.. _88: https://github.com/giampaolo/psutil/issues/88
.. _89: https://github.com/giampaolo/psutil/issues/89
.. _90: https://github.com/giampaolo/psutil/issues/90
.. _91: https://github.com/giampaolo/psutil/issues/91
.. _92: https://github.com/giampaolo/psutil/issues/92
.. _93: https://github.com/giampaolo/psutil/issues/93
.. _94: https://github.com/giampaolo/psutil/issues/94
.. _95: https://github.com/giampaolo/psutil/issues/95
.. _96: https://github.com/giampaolo/psutil/issues/96
.. _97: https://github.com/giampaolo/psutil/issues/97
.. _98: https://github.com/giampaolo/psutil/issues/98
.. _99: https://github.com/giampaolo/psutil/issues/99
.. _100: https://github.com/giampaolo/psutil/issues/100
.. _101: https://github.com/giampaolo/psutil/issues/101
.. _102: https://github.com/giampaolo/psutil/issues/102
.. _103: https://github.com/giampaolo/psutil/issues/103
.. _104: https://github.com/giampaolo/psutil/issues/104
.. _105: https://github.com/giampaolo/psutil/issues/105
.. _106: https://github.com/giampaolo/psutil/issues/106
.. _107: https://github.com/giampaolo/psutil/issues/107
.. _108: https://github.com/giampaolo/psutil/issues/108
.. _109: https://github.com/giampaolo/psutil/issues/109
.. _110: https://github.com/giampaolo/psutil/issues/110
.. _111: https://github.com/giampaolo/psutil/issues/111
.. _112: https://github.com/giampaolo/psutil/issues/112
.. _113: https://github.com/giampaolo/psutil/issues/113
.. _114: https://github.com/giampaolo/psutil/issues/114
.. _115: https://github.com/giampaolo/psutil/issues/115
.. _116: https://github.com/giampaolo/psutil/issues/116
.. _117: https://github.com/giampaolo/psutil/issues/117
.. _118: https://github.com/giampaolo/psutil/issues/118
.. _119: https://github.com/giampaolo/psutil/issues/119
.. _120: https://github.com/giampaolo/psutil/issues/120
.. _121: https://github.com/giampaolo/psutil/issues/121
.. _122: https://github.com/giampaolo/psutil/issues/122
.. _123: https://github.com/giampaolo/psutil/issues/123
.. _124: https://github.com/giampaolo/psutil/issues/124
.. _125: https://github.com/giampaolo/psutil/issues/125
.. _126: https://github.com/giampaolo/psutil/issues/126
.. _127: https://github.com/giampaolo/psutil/issues/127
.. _128: https://github.com/giampaolo/psutil/issues/128
.. _129: https://github.com/giampaolo/psutil/issues/129
.. _130: https://github.com/giampaolo/psutil/issues/130
.. _131: https://github.com/giampaolo/psutil/issues/131
.. _132: https://github.com/giampaolo/psutil/issues/132
.. _133: https://github.com/giampaolo/psutil/issues/133
.. _134: https://github.com/giampaolo/psutil/issues/134
.. _135: https://github.com/giampaolo/psutil/issues/135
.. _136: https://github.com/giampaolo/psutil/issues/136
.. _137: https://github.com/giampaolo/psutil/issues/137
.. _138: https://github.com/giampaolo/psutil/issues/138
.. _139: https://github.com/giampaolo/psutil/issues/139
.. _140: https://github.com/giampaolo/psutil/issues/140
.. _141: https://github.com/giampaolo/psutil/issues/141
.. _142: https://github.com/giampaolo/psutil/issues/142
.. _143: https://github.com/giampaolo/psutil/issues/143
.. _144: https://github.com/giampaolo/psutil/issues/144
.. _145: https://github.com/giampaolo/psutil/issues/145
.. _146: https://github.com/giampaolo/psutil/issues/146
.. _147: https://github.com/giampaolo/psutil/issues/147
.. _148: https://github.com/giampaolo/psutil/issues/148
.. _149: https://github.com/giampaolo/psutil/issues/149
.. _150: https://github.com/giampaolo/psutil/issues/150
.. _151: https://github.com/giampaolo/psutil/issues/151
.. _152: https://github.com/giampaolo/psutil/issues/152
.. _153: https://github.com/giampaolo/psutil/issues/153
.. _154: https://github.com/giampaolo/psutil/issues/154
.. _155: https://github.com/giampaolo/psutil/issues/155
.. _156: https://github.com/giampaolo/psutil/issues/156
.. _157: https://github.com/giampaolo/psutil/issues/157
.. _158: https://github.com/giampaolo/psutil/issues/158
.. _159: https://github.com/giampaolo/psutil/issues/159
.. _160: https://github.com/giampaolo/psutil/issues/160
.. _161: https://github.com/giampaolo/psutil/issues/161
.. _162: https://github.com/giampaolo/psutil/issues/162
.. _163: https://github.com/giampaolo/psutil/issues/163
.. _164: https://github.com/giampaolo/psutil/issues/164
.. _165: https://github.com/giampaolo/psutil/issues/165
.. _166: https://github.com/giampaolo/psutil/issues/166
.. _167: https://github.com/giampaolo/psutil/issues/167
.. _168: https://github.com/giampaolo/psutil/issues/168
.. _169: https://github.com/giampaolo/psutil/issues/169
.. _170: https://github.com/giampaolo/psutil/issues/170
.. _171: https://github.com/giampaolo/psutil/issues/171
.. _172: https://github.com/giampaolo/psutil/issues/172
.. _173: https://github.com/giampaolo/psutil/issues/173
.. _174: https://github.com/giampaolo/psutil/issues/174
.. _175: https://github.com/giampaolo/psutil/issues/175
.. _176: https://github.com/giampaolo/psutil/issues/176
.. _177: https://github.com/giampaolo/psutil/issues/177
.. _178: https://github.com/giampaolo/psutil/issues/178
.. _179: https://github.com/giampaolo/psutil/issues/179
.. _180: https://github.com/giampaolo/psutil/issues/180
.. _181: https://github.com/giampaolo/psutil/issues/181
.. _182: https://github.com/giampaolo/psutil/issues/182
.. _183: https://github.com/giampaolo/psutil/issues/183
.. _184: https://github.com/giampaolo/psutil/issues/184
.. _185: https://github.com/giampaolo/psutil/issues/185
.. _186: https://github.com/giampaolo/psutil/issues/186
.. _187: https://github.com/giampaolo/psutil/issues/187
.. _188: https://github.com/giampaolo/psutil/issues/188
.. _189: https://github.com/giampaolo/psutil/issues/189
.. _190: https://github.com/giampaolo/psutil/issues/190
.. _191: https://github.com/giampaolo/psutil/issues/191
.. _192: https://github.com/giampaolo/psutil/issues/192
.. _193: https://github.com/giampaolo/psutil/issues/193
.. _194: https://github.com/giampaolo/psutil/issues/194
.. _195: https://github.com/giampaolo/psutil/issues/195
.. _196: https://github.com/giampaolo/psutil/issues/196
.. _197: https://github.com/giampaolo/psutil/issues/197
.. _198: https://github.com/giampaolo/psutil/issues/198
.. _199: https://github.com/giampaolo/psutil/issues/199
.. _200: https://github.com/giampaolo/psutil/issues/200
.. _201: https://github.com/giampaolo/psutil/issues/201
.. _202: https://github.com/giampaolo/psutil/issues/202
.. _203: https://github.com/giampaolo/psutil/issues/203
.. _204: https://github.com/giampaolo/psutil/issues/204
.. _205: https://github.com/giampaolo/psutil/issues/205
.. _206: https://github.com/giampaolo/psutil/issues/206
.. _207: https://github.com/giampaolo/psutil/issues/207
.. _208: https://github.com/giampaolo/psutil/issues/208
.. _209: https://github.com/giampaolo/psutil/issues/209
.. _210: https://github.com/giampaolo/psutil/issues/210
.. _211: https://github.com/giampaolo/psutil/issues/211
.. _212: https://github.com/giampaolo/psutil/issues/212
.. _213: https://github.com/giampaolo/psutil/issues/213
.. _214: https://github.com/giampaolo/psutil/issues/214
.. _215: https://github.com/giampaolo/psutil/issues/215
.. _216: https://github.com/giampaolo/psutil/issues/216
.. _217: https://github.com/giampaolo/psutil/issues/217
.. _218: https://github.com/giampaolo/psutil/issues/218
.. _219: https://github.com/giampaolo/psutil/issues/219
.. _220: https://github.com/giampaolo/psutil/issues/220
.. _221: https://github.com/giampaolo/psutil/issues/221
.. _222: https://github.com/giampaolo/psutil/issues/222
.. _223: https://github.com/giampaolo/psutil/issues/223
.. _224: https://github.com/giampaolo/psutil/issues/224
.. _225: https://github.com/giampaolo/psutil/issues/225
.. _226: https://github.com/giampaolo/psutil/issues/226
.. _227: https://github.com/giampaolo/psutil/issues/227
.. _228: https://github.com/giampaolo/psutil/issues/228
.. _229: https://github.com/giampaolo/psutil/issues/229
.. _230: https://github.com/giampaolo/psutil/issues/230
.. _231: https://github.com/giampaolo/psutil/issues/231
.. _232: https://github.com/giampaolo/psutil/issues/232
.. _233: https://github.com/giampaolo/psutil/issues/233
.. _234: https://github.com/giampaolo/psutil/issues/234
.. _235: https://github.com/giampaolo/psutil/issues/235
.. _236: https://github.com/giampaolo/psutil/issues/236
.. _237: https://github.com/giampaolo/psutil/issues/237
.. _238: https://github.com/giampaolo/psutil/issues/238
.. _239: https://github.com/giampaolo/psutil/issues/239
.. _240: https://github.com/giampaolo/psutil/issues/240
.. _241: https://github.com/giampaolo/psutil/issues/241
.. _242: https://github.com/giampaolo/psutil/issues/242
.. _243: https://github.com/giampaolo/psutil/issues/243
.. _244: https://github.com/giampaolo/psutil/issues/244
.. _245: https://github.com/giampaolo/psutil/issues/245
.. _246: https://github.com/giampaolo/psutil/issues/246
.. _247: https://github.com/giampaolo/psutil/issues/247
.. _248: https://github.com/giampaolo/psutil/issues/248
.. _249: https://github.com/giampaolo/psutil/issues/249
.. _250: https://github.com/giampaolo/psutil/issues/250
.. _251: https://github.com/giampaolo/psutil/issues/251
.. _252: https://github.com/giampaolo/psutil/issues/252
.. _253: https://github.com/giampaolo/psutil/issues/253
.. _254: https://github.com/giampaolo/psutil/issues/254
.. _255: https://github.com/giampaolo/psutil/issues/255
.. _256: https://github.com/giampaolo/psutil/issues/256
.. _257: https://github.com/giampaolo/psutil/issues/257
.. _258: https://github.com/giampaolo/psutil/issues/258
.. _259: https://github.com/giampaolo/psutil/issues/259
.. _260: https://github.com/giampaolo/psutil/issues/260
.. _261: https://github.com/giampaolo/psutil/issues/261
.. _262: https://github.com/giampaolo/psutil/issues/262
.. _263: https://github.com/giampaolo/psutil/issues/263
.. _264: https://github.com/giampaolo/psutil/issues/264
.. _265: https://github.com/giampaolo/psutil/issues/265
.. _266: https://github.com/giampaolo/psutil/issues/266
.. _267: https://github.com/giampaolo/psutil/issues/267
.. _268: https://github.com/giampaolo/psutil/issues/268
.. _269: https://github.com/giampaolo/psutil/issues/269
.. _270: https://github.com/giampaolo/psutil/issues/270
.. _271: https://github.com/giampaolo/psutil/issues/271
.. _272: https://github.com/giampaolo/psutil/issues/272
.. _273: https://github.com/giampaolo/psutil/issues/273
.. _274: https://github.com/giampaolo/psutil/issues/274
.. _275: https://github.com/giampaolo/psutil/issues/275
.. _276: https://github.com/giampaolo/psutil/issues/276
.. _277: https://github.com/giampaolo/psutil/issues/277
.. _278: https://github.com/giampaolo/psutil/issues/278
.. _279: https://github.com/giampaolo/psutil/issues/279
.. _280: https://github.com/giampaolo/psutil/issues/280
.. _281: https://github.com/giampaolo/psutil/issues/281
.. _282: https://github.com/giampaolo/psutil/issues/282
.. _283: https://github.com/giampaolo/psutil/issues/283
.. _284: https://github.com/giampaolo/psutil/issues/284
.. _285: https://github.com/giampaolo/psutil/issues/285
.. _286: https://github.com/giampaolo/psutil/issues/286
.. _287: https://github.com/giampaolo/psutil/issues/287
.. _288: https://github.com/giampaolo/psutil/issues/288
.. _289: https://github.com/giampaolo/psutil/issues/289
.. _290: https://github.com/giampaolo/psutil/issues/290
.. _291: https://github.com/giampaolo/psutil/issues/291
.. _292: https://github.com/giampaolo/psutil/issues/292
.. _293: https://github.com/giampaolo/psutil/issues/293
.. _294: https://github.com/giampaolo/psutil/issues/294
.. _295: https://github.com/giampaolo/psutil/issues/295
.. _296: https://github.com/giampaolo/psutil/issues/296
.. _297: https://github.com/giampaolo/psutil/issues/297
.. _298: https://github.com/giampaolo/psutil/issues/298
.. _299: https://github.com/giampaolo/psutil/issues/299
.. _300: https://github.com/giampaolo/psutil/issues/300
.. _301: https://github.com/giampaolo/psutil/issues/301
.. _302: https://github.com/giampaolo/psutil/issues/302
.. _303: https://github.com/giampaolo/psutil/issues/303
.. _304: https://github.com/giampaolo/psutil/issues/304
.. _305: https://github.com/giampaolo/psutil/issues/305
.. _306: https://github.com/giampaolo/psutil/issues/306
.. _307: https://github.com/giampaolo/psutil/issues/307
.. _308: https://github.com/giampaolo/psutil/issues/308
.. _309: https://github.com/giampaolo/psutil/issues/309
.. _310: https://github.com/giampaolo/psutil/issues/310
.. _311: https://github.com/giampaolo/psutil/issues/311
.. _312: https://github.com/giampaolo/psutil/issues/312
.. _313: https://github.com/giampaolo/psutil/issues/313
.. _314: https://github.com/giampaolo/psutil/issues/314
.. _315: https://github.com/giampaolo/psutil/issues/315
.. _316: https://github.com/giampaolo/psutil/issues/316
.. _317: https://github.com/giampaolo/psutil/issues/317
.. _318: https://github.com/giampaolo/psutil/issues/318
.. _319: https://github.com/giampaolo/psutil/issues/319
.. _320: https://github.com/giampaolo/psutil/issues/320
.. _321: https://github.com/giampaolo/psutil/issues/321
.. _322: https://github.com/giampaolo/psutil/issues/322
.. _323: https://github.com/giampaolo/psutil/issues/323
.. _324: https://github.com/giampaolo/psutil/issues/324
.. _325: https://github.com/giampaolo/psutil/issues/325
.. _326: https://github.com/giampaolo/psutil/issues/326
.. _327: https://github.com/giampaolo/psutil/issues/327
.. _328: https://github.com/giampaolo/psutil/issues/328
.. _329: https://github.com/giampaolo/psutil/issues/329
.. _330: https://github.com/giampaolo/psutil/issues/330
.. _331: https://github.com/giampaolo/psutil/issues/331
.. _332: https://github.com/giampaolo/psutil/issues/332
.. _333: https://github.com/giampaolo/psutil/issues/333
.. _334: https://github.com/giampaolo/psutil/issues/334
.. _335: https://github.com/giampaolo/psutil/issues/335
.. _336: https://github.com/giampaolo/psutil/issues/336
.. _337: https://github.com/giampaolo/psutil/issues/337
.. _338: https://github.com/giampaolo/psutil/issues/338
.. _339: https://github.com/giampaolo/psutil/issues/339
.. _340: https://github.com/giampaolo/psutil/issues/340
.. _341: https://github.com/giampaolo/psutil/issues/341
.. _342: https://github.com/giampaolo/psutil/issues/342
.. _343: https://github.com/giampaolo/psutil/issues/343
.. _344: https://github.com/giampaolo/psutil/issues/344
.. _345: https://github.com/giampaolo/psutil/issues/345
.. _346: https://github.com/giampaolo/psutil/issues/346
.. _347: https://github.com/giampaolo/psutil/issues/347
.. _348: https://github.com/giampaolo/psutil/issues/348
.. _349: https://github.com/giampaolo/psutil/issues/349
.. _350: https://github.com/giampaolo/psutil/issues/350
.. _351: https://github.com/giampaolo/psutil/issues/351
.. _352: https://github.com/giampaolo/psutil/issues/352
.. _353: https://github.com/giampaolo/psutil/issues/353
.. _354: https://github.com/giampaolo/psutil/issues/354
.. _355: https://github.com/giampaolo/psutil/issues/355
.. _356: https://github.com/giampaolo/psutil/issues/356
.. _357: https://github.com/giampaolo/psutil/issues/357
.. _358: https://github.com/giampaolo/psutil/issues/358
.. _359: https://github.com/giampaolo/psutil/issues/359
.. _360: https://github.com/giampaolo/psutil/issues/360
.. _361: https://github.com/giampaolo/psutil/issues/361
.. _362: https://github.com/giampaolo/psutil/issues/362
.. _363: https://github.com/giampaolo/psutil/issues/363
.. _364: https://github.com/giampaolo/psutil/issues/364
.. _365: https://github.com/giampaolo/psutil/issues/365
.. _366: https://github.com/giampaolo/psutil/issues/366
.. _367: https://github.com/giampaolo/psutil/issues/367
.. _368: https://github.com/giampaolo/psutil/issues/368
.. _369: https://github.com/giampaolo/psutil/issues/369
.. _370: https://github.com/giampaolo/psutil/issues/370
.. _371: https://github.com/giampaolo/psutil/issues/371
.. _372: https://github.com/giampaolo/psutil/issues/372
.. _373: https://github.com/giampaolo/psutil/issues/373
.. _374: https://github.com/giampaolo/psutil/issues/374
.. _375: https://github.com/giampaolo/psutil/issues/375
.. _376: https://github.com/giampaolo/psutil/issues/376
.. _377: https://github.com/giampaolo/psutil/issues/377
.. _378: https://github.com/giampaolo/psutil/issues/378
.. _379: https://github.com/giampaolo/psutil/issues/379
.. _380: https://github.com/giampaolo/psutil/issues/380
.. _381: https://github.com/giampaolo/psutil/issues/381
.. _382: https://github.com/giampaolo/psutil/issues/382
.. _383: https://github.com/giampaolo/psutil/issues/383
.. _384: https://github.com/giampaolo/psutil/issues/384
.. _385: https://github.com/giampaolo/psutil/issues/385
.. _386: https://github.com/giampaolo/psutil/issues/386
.. _387: https://github.com/giampaolo/psutil/issues/387
.. _388: https://github.com/giampaolo/psutil/issues/388
.. _389: https://github.com/giampaolo/psutil/issues/389
.. _390: https://github.com/giampaolo/psutil/issues/390
.. _391: https://github.com/giampaolo/psutil/issues/391
.. _392: https://github.com/giampaolo/psutil/issues/392
.. _393: https://github.com/giampaolo/psutil/issues/393
.. _394: https://github.com/giampaolo/psutil/issues/394
.. _395: https://github.com/giampaolo/psutil/issues/395
.. _396: https://github.com/giampaolo/psutil/issues/396
.. _397: https://github.com/giampaolo/psutil/issues/397
.. _398: https://github.com/giampaolo/psutil/issues/398
.. _399: https://github.com/giampaolo/psutil/issues/399
.. _400: https://github.com/giampaolo/psutil/issues/400
.. _401: https://github.com/giampaolo/psutil/issues/401
.. _402: https://github.com/giampaolo/psutil/issues/402
.. _403: https://github.com/giampaolo/psutil/issues/403
.. _404: https://github.com/giampaolo/psutil/issues/404
.. _405: https://github.com/giampaolo/psutil/issues/405
.. _406: https://github.com/giampaolo/psutil/issues/406
.. _407: https://github.com/giampaolo/psutil/issues/407
.. _408: https://github.com/giampaolo/psutil/issues/408
.. _409: https://github.com/giampaolo/psutil/issues/409
.. _410: https://github.com/giampaolo/psutil/issues/410
.. _411: https://github.com/giampaolo/psutil/issues/411
.. _412: https://github.com/giampaolo/psutil/issues/412
.. _413: https://github.com/giampaolo/psutil/issues/413
.. _414: https://github.com/giampaolo/psutil/issues/414
.. _415: https://github.com/giampaolo/psutil/issues/415
.. _416: https://github.com/giampaolo/psutil/issues/416
.. _417: https://github.com/giampaolo/psutil/issues/417
.. _418: https://github.com/giampaolo/psutil/issues/418
.. _419: https://github.com/giampaolo/psutil/issues/419
.. _420: https://github.com/giampaolo/psutil/issues/420
.. _421: https://github.com/giampaolo/psutil/issues/421
.. _422: https://github.com/giampaolo/psutil/issues/422
.. _423: https://github.com/giampaolo/psutil/issues/423
.. _424: https://github.com/giampaolo/psutil/issues/424
.. _425: https://github.com/giampaolo/psutil/issues/425
.. _426: https://github.com/giampaolo/psutil/issues/426
.. _427: https://github.com/giampaolo/psutil/issues/427
.. _428: https://github.com/giampaolo/psutil/issues/428
.. _429: https://github.com/giampaolo/psutil/issues/429
.. _430: https://github.com/giampaolo/psutil/issues/430
.. _431: https://github.com/giampaolo/psutil/issues/431
.. _432: https://github.com/giampaolo/psutil/issues/432
.. _433: https://github.com/giampaolo/psutil/issues/433
.. _434: https://github.com/giampaolo/psutil/issues/434
.. _435: https://github.com/giampaolo/psutil/issues/435
.. _436: https://github.com/giampaolo/psutil/issues/436
.. _437: https://github.com/giampaolo/psutil/issues/437
.. _438: https://github.com/giampaolo/psutil/issues/438
.. _439: https://github.com/giampaolo/psutil/issues/439
.. _440: https://github.com/giampaolo/psutil/issues/440
.. _441: https://github.com/giampaolo/psutil/issues/441
.. _442: https://github.com/giampaolo/psutil/issues/442
.. _443: https://github.com/giampaolo/psutil/issues/443
.. _444: https://github.com/giampaolo/psutil/issues/444
.. _445: https://github.com/giampaolo/psutil/issues/445
.. _446: https://github.com/giampaolo/psutil/issues/446
.. _447: https://github.com/giampaolo/psutil/issues/447
.. _448: https://github.com/giampaolo/psutil/issues/448
.. _449: https://github.com/giampaolo/psutil/issues/449
.. _450: https://github.com/giampaolo/psutil/issues/450
.. _451: https://github.com/giampaolo/psutil/issues/451
.. _452: https://github.com/giampaolo/psutil/issues/452
.. _453: https://github.com/giampaolo/psutil/issues/453
.. _454: https://github.com/giampaolo/psutil/issues/454
.. _455: https://github.com/giampaolo/psutil/issues/455
.. _456: https://github.com/giampaolo/psutil/issues/456
.. _457: https://github.com/giampaolo/psutil/issues/457
.. _458: https://github.com/giampaolo/psutil/issues/458
.. _459: https://github.com/giampaolo/psutil/issues/459
.. _460: https://github.com/giampaolo/psutil/issues/460
.. _461: https://github.com/giampaolo/psutil/issues/461
.. _462: https://github.com/giampaolo/psutil/issues/462
.. _463: https://github.com/giampaolo/psutil/issues/463
.. _464: https://github.com/giampaolo/psutil/issues/464
.. _465: https://github.com/giampaolo/psutil/issues/465
.. _466: https://github.com/giampaolo/psutil/issues/466
.. _467: https://github.com/giampaolo/psutil/issues/467
.. _468: https://github.com/giampaolo/psutil/issues/468
.. _469: https://github.com/giampaolo/psutil/issues/469
.. _470: https://github.com/giampaolo/psutil/issues/470
.. _471: https://github.com/giampaolo/psutil/issues/471
.. _472: https://github.com/giampaolo/psutil/issues/472
.. _473: https://github.com/giampaolo/psutil/issues/473
.. _474: https://github.com/giampaolo/psutil/issues/474
.. _475: https://github.com/giampaolo/psutil/issues/475
.. _476: https://github.com/giampaolo/psutil/issues/476
.. _477: https://github.com/giampaolo/psutil/issues/477
.. _478: https://github.com/giampaolo/psutil/issues/478
.. _479: https://github.com/giampaolo/psutil/issues/479
.. _480: https://github.com/giampaolo/psutil/issues/480
.. _481: https://github.com/giampaolo/psutil/issues/481
.. _482: https://github.com/giampaolo/psutil/issues/482
.. _483: https://github.com/giampaolo/psutil/issues/483
.. _484: https://github.com/giampaolo/psutil/issues/484
.. _485: https://github.com/giampaolo/psutil/issues/485
.. _486: https://github.com/giampaolo/psutil/issues/486
.. _487: https://github.com/giampaolo/psutil/issues/487
.. _488: https://github.com/giampaolo/psutil/issues/488
.. _489: https://github.com/giampaolo/psutil/issues/489
.. _490: https://github.com/giampaolo/psutil/issues/490
.. _491: https://github.com/giampaolo/psutil/issues/491
.. _492: https://github.com/giampaolo/psutil/issues/492
.. _493: https://github.com/giampaolo/psutil/issues/493
.. _494: https://github.com/giampaolo/psutil/issues/494
.. _495: https://github.com/giampaolo/psutil/issues/495
.. _496: https://github.com/giampaolo/psutil/issues/496
.. _497: https://github.com/giampaolo/psutil/issues/497
.. _498: https://github.com/giampaolo/psutil/issues/498
.. _499: https://github.com/giampaolo/psutil/issues/499
.. _500: https://github.com/giampaolo/psutil/issues/500
.. _501: https://github.com/giampaolo/psutil/issues/501
.. _502: https://github.com/giampaolo/psutil/issues/502
.. _503: https://github.com/giampaolo/psutil/issues/503
.. _504: https://github.com/giampaolo/psutil/issues/504
.. _505: https://github.com/giampaolo/psutil/issues/505
.. _506: https://github.com/giampaolo/psutil/issues/506
.. _507: https://github.com/giampaolo/psutil/issues/507
.. _508: https://github.com/giampaolo/psutil/issues/508
.. _509: https://github.com/giampaolo/psutil/issues/509
.. _510: https://github.com/giampaolo/psutil/issues/510
.. _511: https://github.com/giampaolo/psutil/issues/511
.. _512: https://github.com/giampaolo/psutil/issues/512
.. _513: https://github.com/giampaolo/psutil/issues/513
.. _514: https://github.com/giampaolo/psutil/issues/514
.. _515: https://github.com/giampaolo/psutil/issues/515
.. _516: https://github.com/giampaolo/psutil/issues/516
.. _517: https://github.com/giampaolo/psutil/issues/517
.. _518: https://github.com/giampaolo/psutil/issues/518
.. _519: https://github.com/giampaolo/psutil/issues/519
.. _520: https://github.com/giampaolo/psutil/issues/520
.. _521: https://github.com/giampaolo/psutil/issues/521
.. _522: https://github.com/giampaolo/psutil/issues/522
.. _523: https://github.com/giampaolo/psutil/issues/523
.. _524: https://github.com/giampaolo/psutil/issues/524
.. _525: https://github.com/giampaolo/psutil/issues/525
.. _526: https://github.com/giampaolo/psutil/issues/526
.. _527: https://github.com/giampaolo/psutil/issues/527
.. _528: https://github.com/giampaolo/psutil/issues/528
.. _529: https://github.com/giampaolo/psutil/issues/529
.. _530: https://github.com/giampaolo/psutil/issues/530
.. _531: https://github.com/giampaolo/psutil/issues/531
.. _532: https://github.com/giampaolo/psutil/issues/532
.. _533: https://github.com/giampaolo/psutil/issues/533
.. _534: https://github.com/giampaolo/psutil/issues/534
.. _535: https://github.com/giampaolo/psutil/issues/535
.. _536: https://github.com/giampaolo/psutil/issues/536
.. _537: https://github.com/giampaolo/psutil/issues/537
.. _538: https://github.com/giampaolo/psutil/issues/538
.. _539: https://github.com/giampaolo/psutil/issues/539
.. _540: https://github.com/giampaolo/psutil/issues/540
.. _541: https://github.com/giampaolo/psutil/issues/541
.. _542: https://github.com/giampaolo/psutil/issues/542
.. _543: https://github.com/giampaolo/psutil/issues/543
.. _544: https://github.com/giampaolo/psutil/issues/544
.. _545: https://github.com/giampaolo/psutil/issues/545
.. _546: https://github.com/giampaolo/psutil/issues/546
.. _547: https://github.com/giampaolo/psutil/issues/547
.. _548: https://github.com/giampaolo/psutil/issues/548
.. _549: https://github.com/giampaolo/psutil/issues/549
.. _550: https://github.com/giampaolo/psutil/issues/550
.. _551: https://github.com/giampaolo/psutil/issues/551
.. _552: https://github.com/giampaolo/psutil/issues/552
.. _553: https://github.com/giampaolo/psutil/issues/553
.. _554: https://github.com/giampaolo/psutil/issues/554
.. _555: https://github.com/giampaolo/psutil/issues/555
.. _556: https://github.com/giampaolo/psutil/issues/556
.. _557: https://github.com/giampaolo/psutil/issues/557
.. _558: https://github.com/giampaolo/psutil/issues/558
.. _559: https://github.com/giampaolo/psutil/issues/559
.. _560: https://github.com/giampaolo/psutil/issues/560
.. _561: https://github.com/giampaolo/psutil/issues/561
.. _562: https://github.com/giampaolo/psutil/issues/562
.. _563: https://github.com/giampaolo/psutil/issues/563
.. _564: https://github.com/giampaolo/psutil/issues/564
.. _565: https://github.com/giampaolo/psutil/issues/565
.. _566: https://github.com/giampaolo/psutil/issues/566
.. _567: https://github.com/giampaolo/psutil/issues/567
.. _568: https://github.com/giampaolo/psutil/issues/568
.. _569: https://github.com/giampaolo/psutil/issues/569
.. _570: https://github.com/giampaolo/psutil/issues/570
.. _571: https://github.com/giampaolo/psutil/issues/571
.. _572: https://github.com/giampaolo/psutil/issues/572
.. _573: https://github.com/giampaolo/psutil/issues/573
.. _574: https://github.com/giampaolo/psutil/issues/574
.. _575: https://github.com/giampaolo/psutil/issues/575
.. _576: https://github.com/giampaolo/psutil/issues/576
.. _577: https://github.com/giampaolo/psutil/issues/577
.. _578: https://github.com/giampaolo/psutil/issues/578
.. _579: https://github.com/giampaolo/psutil/issues/579
.. _580: https://github.com/giampaolo/psutil/issues/580
.. _581: https://github.com/giampaolo/psutil/issues/581
.. _582: https://github.com/giampaolo/psutil/issues/582
.. _583: https://github.com/giampaolo/psutil/issues/583
.. _584: https://github.com/giampaolo/psutil/issues/584
.. _585: https://github.com/giampaolo/psutil/issues/585
.. _586: https://github.com/giampaolo/psutil/issues/586
.. _587: https://github.com/giampaolo/psutil/issues/587
.. _588: https://github.com/giampaolo/psutil/issues/588
.. _589: https://github.com/giampaolo/psutil/issues/589
.. _590: https://github.com/giampaolo/psutil/issues/590
.. _591: https://github.com/giampaolo/psutil/issues/591
.. _592: https://github.com/giampaolo/psutil/issues/592
.. _593: https://github.com/giampaolo/psutil/issues/593
.. _594: https://github.com/giampaolo/psutil/issues/594
.. _595: https://github.com/giampaolo/psutil/issues/595
.. _596: https://github.com/giampaolo/psutil/issues/596
.. _597: https://github.com/giampaolo/psutil/issues/597
.. _598: https://github.com/giampaolo/psutil/issues/598
.. _599: https://github.com/giampaolo/psutil/issues/599
.. _600: https://github.com/giampaolo/psutil/issues/600
.. _601: https://github.com/giampaolo/psutil/issues/601
.. _602: https://github.com/giampaolo/psutil/issues/602
.. _603: https://github.com/giampaolo/psutil/issues/603
.. _604: https://github.com/giampaolo/psutil/issues/604
.. _605: https://github.com/giampaolo/psutil/issues/605
.. _606: https://github.com/giampaolo/psutil/issues/606
.. _607: https://github.com/giampaolo/psutil/issues/607
.. _608: https://github.com/giampaolo/psutil/issues/608
.. _609: https://github.com/giampaolo/psutil/issues/609
.. _610: https://github.com/giampaolo/psutil/issues/610
.. _611: https://github.com/giampaolo/psutil/issues/611
.. _612: https://github.com/giampaolo/psutil/issues/612
.. _613: https://github.com/giampaolo/psutil/issues/613
.. _614: https://github.com/giampaolo/psutil/issues/614
.. _615: https://github.com/giampaolo/psutil/issues/615
.. _616: https://github.com/giampaolo/psutil/issues/616
.. _617: https://github.com/giampaolo/psutil/issues/617
.. _618: https://github.com/giampaolo/psutil/issues/618
.. _619: https://github.com/giampaolo/psutil/issues/619
.. _620: https://github.com/giampaolo/psutil/issues/620
.. _621: https://github.com/giampaolo/psutil/issues/621
.. _622: https://github.com/giampaolo/psutil/issues/622
.. _623: https://github.com/giampaolo/psutil/issues/623
.. _624: https://github.com/giampaolo/psutil/issues/624
.. _625: https://github.com/giampaolo/psutil/issues/625
.. _626: https://github.com/giampaolo/psutil/issues/626
.. _627: https://github.com/giampaolo/psutil/issues/627
.. _628: https://github.com/giampaolo/psutil/issues/628
.. _629: https://github.com/giampaolo/psutil/issues/629
.. _630: https://github.com/giampaolo/psutil/issues/630
.. _631: https://github.com/giampaolo/psutil/issues/631
.. _632: https://github.com/giampaolo/psutil/issues/632
.. _633: https://github.com/giampaolo/psutil/issues/633
.. _634: https://github.com/giampaolo/psutil/issues/634
.. _635: https://github.com/giampaolo/psutil/issues/635
.. _636: https://github.com/giampaolo/psutil/issues/636
.. _637: https://github.com/giampaolo/psutil/issues/637
.. _638: https://github.com/giampaolo/psutil/issues/638
.. _639: https://github.com/giampaolo/psutil/issues/639
.. _640: https://github.com/giampaolo/psutil/issues/640
.. _641: https://github.com/giampaolo/psutil/issues/641
.. _642: https://github.com/giampaolo/psutil/issues/642
.. _643: https://github.com/giampaolo/psutil/issues/643
.. _644: https://github.com/giampaolo/psutil/issues/644
.. _645: https://github.com/giampaolo/psutil/issues/645
.. _646: https://github.com/giampaolo/psutil/issues/646
.. _647: https://github.com/giampaolo/psutil/issues/647
.. _648: https://github.com/giampaolo/psutil/issues/648
.. _649: https://github.com/giampaolo/psutil/issues/649
.. _650: https://github.com/giampaolo/psutil/issues/650
.. _651: https://github.com/giampaolo/psutil/issues/651
.. _652: https://github.com/giampaolo/psutil/issues/652
.. _653: https://github.com/giampaolo/psutil/issues/653
.. _654: https://github.com/giampaolo/psutil/issues/654
.. _655: https://github.com/giampaolo/psutil/issues/655
.. _656: https://github.com/giampaolo/psutil/issues/656
.. _657: https://github.com/giampaolo/psutil/issues/657
.. _658: https://github.com/giampaolo/psutil/issues/658
.. _659: https://github.com/giampaolo/psutil/issues/659
.. _660: https://github.com/giampaolo/psutil/issues/660
.. _661: https://github.com/giampaolo/psutil/issues/661
.. _662: https://github.com/giampaolo/psutil/issues/662
.. _663: https://github.com/giampaolo/psutil/issues/663
.. _664: https://github.com/giampaolo/psutil/issues/664
.. _665: https://github.com/giampaolo/psutil/issues/665
.. _666: https://github.com/giampaolo/psutil/issues/666
.. _667: https://github.com/giampaolo/psutil/issues/667
.. _668: https://github.com/giampaolo/psutil/issues/668
.. _669: https://github.com/giampaolo/psutil/issues/669
.. _670: https://github.com/giampaolo/psutil/issues/670
.. _671: https://github.com/giampaolo/psutil/issues/671
.. _672: https://github.com/giampaolo/psutil/issues/672
.. _673: https://github.com/giampaolo/psutil/issues/673
.. _674: https://github.com/giampaolo/psutil/issues/674
.. _675: https://github.com/giampaolo/psutil/issues/675
.. _676: https://github.com/giampaolo/psutil/issues/676
.. _677: https://github.com/giampaolo/psutil/issues/677
.. _678: https://github.com/giampaolo/psutil/issues/678
.. _679: https://github.com/giampaolo/psutil/issues/679
.. _680: https://github.com/giampaolo/psutil/issues/680
.. _681: https://github.com/giampaolo/psutil/issues/681
.. _682: https://github.com/giampaolo/psutil/issues/682
.. _683: https://github.com/giampaolo/psutil/issues/683
.. _684: https://github.com/giampaolo/psutil/issues/684
.. _685: https://github.com/giampaolo/psutil/issues/685
.. _686: https://github.com/giampaolo/psutil/issues/686
.. _687: https://github.com/giampaolo/psutil/issues/687
.. _688: https://github.com/giampaolo/psutil/issues/688
.. _689: https://github.com/giampaolo/psutil/issues/689
.. _690: https://github.com/giampaolo/psutil/issues/690
.. _691: https://github.com/giampaolo/psutil/issues/691
.. _692: https://github.com/giampaolo/psutil/issues/692
.. _693: https://github.com/giampaolo/psutil/issues/693
.. _694: https://github.com/giampaolo/psutil/issues/694
.. _695: https://github.com/giampaolo/psutil/issues/695
.. _696: https://github.com/giampaolo/psutil/issues/696
.. _697: https://github.com/giampaolo/psutil/issues/697
.. _698: https://github.com/giampaolo/psutil/issues/698
.. _699: https://github.com/giampaolo/psutil/issues/699
.. _700: https://github.com/giampaolo/psutil/issues/700
.. _701: https://github.com/giampaolo/psutil/issues/701
.. _702: https://github.com/giampaolo/psutil/issues/702
.. _703: https://github.com/giampaolo/psutil/issues/703
.. _704: https://github.com/giampaolo/psutil/issues/704
.. _705: https://github.com/giampaolo/psutil/issues/705
.. _706: https://github.com/giampaolo/psutil/issues/706
.. _707: https://github.com/giampaolo/psutil/issues/707
.. _708: https://github.com/giampaolo/psutil/issues/708
.. _709: https://github.com/giampaolo/psutil/issues/709
.. _710: https://github.com/giampaolo/psutil/issues/710
.. _711: https://github.com/giampaolo/psutil/issues/711
.. _712: https://github.com/giampaolo/psutil/issues/712
.. _713: https://github.com/giampaolo/psutil/issues/713
.. _714: https://github.com/giampaolo/psutil/issues/714
.. _715: https://github.com/giampaolo/psutil/issues/715
.. _716: https://github.com/giampaolo/psutil/issues/716
.. _717: https://github.com/giampaolo/psutil/issues/717
.. _718: https://github.com/giampaolo/psutil/issues/718
.. _719: https://github.com/giampaolo/psutil/issues/719
.. _720: https://github.com/giampaolo/psutil/issues/720
.. _721: https://github.com/giampaolo/psutil/issues/721
.. _722: https://github.com/giampaolo/psutil/issues/722
.. _723: https://github.com/giampaolo/psutil/issues/723
.. _724: https://github.com/giampaolo/psutil/issues/724
.. _725: https://github.com/giampaolo/psutil/issues/725
.. _726: https://github.com/giampaolo/psutil/issues/726
.. _727: https://github.com/giampaolo/psutil/issues/727
.. _728: https://github.com/giampaolo/psutil/issues/728
.. _729: https://github.com/giampaolo/psutil/issues/729
.. _730: https://github.com/giampaolo/psutil/issues/730
.. _731: https://github.com/giampaolo/psutil/issues/731
.. _732: https://github.com/giampaolo/psutil/issues/732
.. _733: https://github.com/giampaolo/psutil/issues/733
.. _734: https://github.com/giampaolo/psutil/issues/734
.. _735: https://github.com/giampaolo/psutil/issues/735
.. _736: https://github.com/giampaolo/psutil/issues/736
.. _737: https://github.com/giampaolo/psutil/issues/737
.. _738: https://github.com/giampaolo/psutil/issues/738
.. _739: https://github.com/giampaolo/psutil/issues/739
.. _740: https://github.com/giampaolo/psutil/issues/740
.. _741: https://github.com/giampaolo/psutil/issues/741
.. _742: https://github.com/giampaolo/psutil/issues/742
.. _743: https://github.com/giampaolo/psutil/issues/743
.. _744: https://github.com/giampaolo/psutil/issues/744
.. _745: https://github.com/giampaolo/psutil/issues/745
.. _746: https://github.com/giampaolo/psutil/issues/746
.. _747: https://github.com/giampaolo/psutil/issues/747
.. _748: https://github.com/giampaolo/psutil/issues/748
.. _749: https://github.com/giampaolo/psutil/issues/749
.. _750: https://github.com/giampaolo/psutil/issues/750
.. _751: https://github.com/giampaolo/psutil/issues/751
.. _752: https://github.com/giampaolo/psutil/issues/752
.. _753: https://github.com/giampaolo/psutil/issues/753
.. _754: https://github.com/giampaolo/psutil/issues/754
.. _755: https://github.com/giampaolo/psutil/issues/755
.. _756: https://github.com/giampaolo/psutil/issues/756
.. _757: https://github.com/giampaolo/psutil/issues/757
.. _758: https://github.com/giampaolo/psutil/issues/758
.. _759: https://github.com/giampaolo/psutil/issues/759
.. _760: https://github.com/giampaolo/psutil/issues/760
.. _761: https://github.com/giampaolo/psutil/issues/761
.. _762: https://github.com/giampaolo/psutil/issues/762
.. _763: https://github.com/giampaolo/psutil/issues/763
.. _764: https://github.com/giampaolo/psutil/issues/764
.. _765: https://github.com/giampaolo/psutil/issues/765
.. _766: https://github.com/giampaolo/psutil/issues/766
.. _767: https://github.com/giampaolo/psutil/issues/767
.. _768: https://github.com/giampaolo/psutil/issues/768
.. _769: https://github.com/giampaolo/psutil/issues/769
.. _770: https://github.com/giampaolo/psutil/issues/770
.. _771: https://github.com/giampaolo/psutil/issues/771
.. _772: https://github.com/giampaolo/psutil/issues/772
.. _773: https://github.com/giampaolo/psutil/issues/773
.. _774: https://github.com/giampaolo/psutil/issues/774
.. _775: https://github.com/giampaolo/psutil/issues/775
.. _776: https://github.com/giampaolo/psutil/issues/776
.. _777: https://github.com/giampaolo/psutil/issues/777
.. _778: https://github.com/giampaolo/psutil/issues/778
.. _779: https://github.com/giampaolo/psutil/issues/779
.. _780: https://github.com/giampaolo/psutil/issues/780
.. _781: https://github.com/giampaolo/psutil/issues/781
.. _782: https://github.com/giampaolo/psutil/issues/782
.. _783: https://github.com/giampaolo/psutil/issues/783
.. _784: https://github.com/giampaolo/psutil/issues/784
.. _785: https://github.com/giampaolo/psutil/issues/785
.. _786: https://github.com/giampaolo/psutil/issues/786
.. _787: https://github.com/giampaolo/psutil/issues/787
.. _788: https://github.com/giampaolo/psutil/issues/788
.. _789: https://github.com/giampaolo/psutil/issues/789
.. _790: https://github.com/giampaolo/psutil/issues/790
.. _791: https://github.com/giampaolo/psutil/issues/791
.. _792: https://github.com/giampaolo/psutil/issues/792
.. _793: https://github.com/giampaolo/psutil/issues/793
.. _794: https://github.com/giampaolo/psutil/issues/794
.. _795: https://github.com/giampaolo/psutil/issues/795
.. _796: https://github.com/giampaolo/psutil/issues/796
.. _797: https://github.com/giampaolo/psutil/issues/797
.. _798: https://github.com/giampaolo/psutil/issues/798
.. _799: https://github.com/giampaolo/psutil/issues/799
.. _800: https://github.com/giampaolo/psutil/issues/800
.. _801: https://github.com/giampaolo/psutil/issues/801
.. _802: https://github.com/giampaolo/psutil/issues/802
.. _803: https://github.com/giampaolo/psutil/issues/803
.. _804: https://github.com/giampaolo/psutil/issues/804
.. _805: https://github.com/giampaolo/psutil/issues/805
.. _806: https://github.com/giampaolo/psutil/issues/806
.. _807: https://github.com/giampaolo/psutil/issues/807
.. _808: https://github.com/giampaolo/psutil/issues/808
.. _809: https://github.com/giampaolo/psutil/issues/809
.. _810: https://github.com/giampaolo/psutil/issues/810
.. _811: https://github.com/giampaolo/psutil/issues/811
.. _812: https://github.com/giampaolo/psutil/issues/812
.. _813: https://github.com/giampaolo/psutil/issues/813
.. _814: https://github.com/giampaolo/psutil/issues/814
.. _815: https://github.com/giampaolo/psutil/issues/815
.. _816: https://github.com/giampaolo/psutil/issues/816
.. _817: https://github.com/giampaolo/psutil/issues/817
.. _818: https://github.com/giampaolo/psutil/issues/818
.. _819: https://github.com/giampaolo/psutil/issues/819
.. _820: https://github.com/giampaolo/psutil/issues/820
.. _821: https://github.com/giampaolo/psutil/issues/821
.. _822: https://github.com/giampaolo/psutil/issues/822
.. _823: https://github.com/giampaolo/psutil/issues/823
.. _824: https://github.com/giampaolo/psutil/issues/824
.. _825: https://github.com/giampaolo/psutil/issues/825
.. _826: https://github.com/giampaolo/psutil/issues/826
.. _827: https://github.com/giampaolo/psutil/issues/827
.. _828: https://github.com/giampaolo/psutil/issues/828
.. _829: https://github.com/giampaolo/psutil/issues/829
.. _830: https://github.com/giampaolo/psutil/issues/830
.. _831: https://github.com/giampaolo/psutil/issues/831
.. _832: https://github.com/giampaolo/psutil/issues/832
.. _833: https://github.com/giampaolo/psutil/issues/833
.. _834: https://github.com/giampaolo/psutil/issues/834
.. _835: https://github.com/giampaolo/psutil/issues/835
.. _836: https://github.com/giampaolo/psutil/issues/836
.. _837: https://github.com/giampaolo/psutil/issues/837
.. _838: https://github.com/giampaolo/psutil/issues/838
.. _839: https://github.com/giampaolo/psutil/issues/839
.. _840: https://github.com/giampaolo/psutil/issues/840
.. _841: https://github.com/giampaolo/psutil/issues/841
.. _842: https://github.com/giampaolo/psutil/issues/842
.. _843: https://github.com/giampaolo/psutil/issues/843
.. _844: https://github.com/giampaolo/psutil/issues/844
.. _845: https://github.com/giampaolo/psutil/issues/845
.. _846: https://github.com/giampaolo/psutil/issues/846
.. _847: https://github.com/giampaolo/psutil/issues/847
.. _848: https://github.com/giampaolo/psutil/issues/848
.. _849: https://github.com/giampaolo/psutil/issues/849
.. _850: https://github.com/giampaolo/psutil/issues/850
.. _851: https://github.com/giampaolo/psutil/issues/851
.. _852: https://github.com/giampaolo/psutil/issues/852
.. _853: https://github.com/giampaolo/psutil/issues/853
.. _854: https://github.com/giampaolo/psutil/issues/854
.. _855: https://github.com/giampaolo/psutil/issues/855
.. _856: https://github.com/giampaolo/psutil/issues/856
.. _857: https://github.com/giampaolo/psutil/issues/857
.. _858: https://github.com/giampaolo/psutil/issues/858
.. _859: https://github.com/giampaolo/psutil/issues/859
.. _860: https://github.com/giampaolo/psutil/issues/860
.. _861: https://github.com/giampaolo/psutil/issues/861
.. _862: https://github.com/giampaolo/psutil/issues/862
.. _863: https://github.com/giampaolo/psutil/issues/863
.. _864: https://github.com/giampaolo/psutil/issues/864
.. _865: https://github.com/giampaolo/psutil/issues/865
.. _866: https://github.com/giampaolo/psutil/issues/866
.. _867: https://github.com/giampaolo/psutil/issues/867
.. _868: https://github.com/giampaolo/psutil/issues/868
.. _869: https://github.com/giampaolo/psutil/issues/869
.. _870: https://github.com/giampaolo/psutil/issues/870
.. _871: https://github.com/giampaolo/psutil/issues/871
.. _872: https://github.com/giampaolo/psutil/issues/872
.. _873: https://github.com/giampaolo/psutil/issues/873
.. _874: https://github.com/giampaolo/psutil/issues/874
.. _875: https://github.com/giampaolo/psutil/issues/875
.. _876: https://github.com/giampaolo/psutil/issues/876
.. _877: https://github.com/giampaolo/psutil/issues/877
.. _878: https://github.com/giampaolo/psutil/issues/878
.. _879: https://github.com/giampaolo/psutil/issues/879
.. _880: https://github.com/giampaolo/psutil/issues/880
.. _881: https://github.com/giampaolo/psutil/issues/881
.. _882: https://github.com/giampaolo/psutil/issues/882
.. _883: https://github.com/giampaolo/psutil/issues/883
.. _884: https://github.com/giampaolo/psutil/issues/884
.. _885: https://github.com/giampaolo/psutil/issues/885
.. _886: https://github.com/giampaolo/psutil/issues/886
.. _887: https://github.com/giampaolo/psutil/issues/887
.. _888: https://github.com/giampaolo/psutil/issues/888
.. _889: https://github.com/giampaolo/psutil/issues/889
.. _890: https://github.com/giampaolo/psutil/issues/890
.. _891: https://github.com/giampaolo/psutil/issues/891
.. _892: https://github.com/giampaolo/psutil/issues/892
.. _893: https://github.com/giampaolo/psutil/issues/893
.. _894: https://github.com/giampaolo/psutil/issues/894
.. _895: https://github.com/giampaolo/psutil/issues/895
.. _896: https://github.com/giampaolo/psutil/issues/896
.. _897: https://github.com/giampaolo/psutil/issues/897
.. _898: https://github.com/giampaolo/psutil/issues/898
.. _899: https://github.com/giampaolo/psutil/issues/899
.. _900: https://github.com/giampaolo/psutil/issues/900
.. _901: https://github.com/giampaolo/psutil/issues/901
.. _902: https://github.com/giampaolo/psutil/issues/902
.. _903: https://github.com/giampaolo/psutil/issues/903
.. _904: https://github.com/giampaolo/psutil/issues/904
.. _905: https://github.com/giampaolo/psutil/issues/905
.. _906: https://github.com/giampaolo/psutil/issues/906
.. _907: https://github.com/giampaolo/psutil/issues/907
.. _908: https://github.com/giampaolo/psutil/issues/908
.. _909: https://github.com/giampaolo/psutil/issues/909
.. _910: https://github.com/giampaolo/psutil/issues/910
.. _911: https://github.com/giampaolo/psutil/issues/911
.. _912: https://github.com/giampaolo/psutil/issues/912
.. _913: https://github.com/giampaolo/psutil/issues/913
.. _914: https://github.com/giampaolo/psutil/issues/914
.. _915: https://github.com/giampaolo/psutil/issues/915
.. _916: https://github.com/giampaolo/psutil/issues/916
.. _917: https://github.com/giampaolo/psutil/issues/917
.. _918: https://github.com/giampaolo/psutil/issues/918
.. _919: https://github.com/giampaolo/psutil/issues/919
.. _920: https://github.com/giampaolo/psutil/issues/920
.. _921: https://github.com/giampaolo/psutil/issues/921
.. _922: https://github.com/giampaolo/psutil/issues/922
.. _923: https://github.com/giampaolo/psutil/issues/923
.. _924: https://github.com/giampaolo/psutil/issues/924
.. _925: https://github.com/giampaolo/psutil/issues/925
.. _926: https://github.com/giampaolo/psutil/issues/926
.. _927: https://github.com/giampaolo/psutil/issues/927
.. _928: https://github.com/giampaolo/psutil/issues/928
.. _929: https://github.com/giampaolo/psutil/issues/929
.. _930: https://github.com/giampaolo/psutil/issues/930
.. _931: https://github.com/giampaolo/psutil/issues/931
.. _932: https://github.com/giampaolo/psutil/issues/932
.. _933: https://github.com/giampaolo/psutil/issues/933
.. _934: https://github.com/giampaolo/psutil/issues/934
.. _935: https://github.com/giampaolo/psutil/issues/935
.. _936: https://github.com/giampaolo/psutil/issues/936
.. _937: https://github.com/giampaolo/psutil/issues/937
.. _938: https://github.com/giampaolo/psutil/issues/938
.. _939: https://github.com/giampaolo/psutil/issues/939
.. _940: https://github.com/giampaolo/psutil/issues/940
.. _941: https://github.com/giampaolo/psutil/issues/941
.. _942: https://github.com/giampaolo/psutil/issues/942
.. _943: https://github.com/giampaolo/psutil/issues/943
.. _944: https://github.com/giampaolo/psutil/issues/944
.. _945: https://github.com/giampaolo/psutil/issues/945
.. _946: https://github.com/giampaolo/psutil/issues/946
.. _947: https://github.com/giampaolo/psutil/issues/947
.. _948: https://github.com/giampaolo/psutil/issues/948
.. _949: https://github.com/giampaolo/psutil/issues/949
.. _950: https://github.com/giampaolo/psutil/issues/950
.. _951: https://github.com/giampaolo/psutil/issues/951
.. _952: https://github.com/giampaolo/psutil/issues/952
.. _953: https://github.com/giampaolo/psutil/issues/953
.. _954: https://github.com/giampaolo/psutil/issues/954
.. _955: https://github.com/giampaolo/psutil/issues/955
.. _956: https://github.com/giampaolo/psutil/issues/956
.. _957: https://github.com/giampaolo/psutil/issues/957
.. _958: https://github.com/giampaolo/psutil/issues/958
.. _959: https://github.com/giampaolo/psutil/issues/959
.. _960: https://github.com/giampaolo/psutil/issues/960
.. _961: https://github.com/giampaolo/psutil/issues/961
.. _962: https://github.com/giampaolo/psutil/issues/962
.. _963: https://github.com/giampaolo/psutil/issues/963
.. _964: https://github.com/giampaolo/psutil/issues/964
.. _965: https://github.com/giampaolo/psutil/issues/965
.. _966: https://github.com/giampaolo/psutil/issues/966
.. _967: https://github.com/giampaolo/psutil/issues/967
.. _968: https://github.com/giampaolo/psutil/issues/968
.. _969: https://github.com/giampaolo/psutil/issues/969
.. _970: https://github.com/giampaolo/psutil/issues/970
.. _971: https://github.com/giampaolo/psutil/issues/971
.. _972: https://github.com/giampaolo/psutil/issues/972
.. _973: https://github.com/giampaolo/psutil/issues/973
.. _974: https://github.com/giampaolo/psutil/issues/974
.. _975: https://github.com/giampaolo/psutil/issues/975
.. _976: https://github.com/giampaolo/psutil/issues/976
.. _977: https://github.com/giampaolo/psutil/issues/977
.. _978: https://github.com/giampaolo/psutil/issues/978
.. _979: https://github.com/giampaolo/psutil/issues/979
.. _980: https://github.com/giampaolo/psutil/issues/980
.. _981: https://github.com/giampaolo/psutil/issues/981
.. _982: https://github.com/giampaolo/psutil/issues/982
.. _983: https://github.com/giampaolo/psutil/issues/983
.. _984: https://github.com/giampaolo/psutil/issues/984
.. _985: https://github.com/giampaolo/psutil/issues/985
.. _986: https://github.com/giampaolo/psutil/issues/986
.. _987: https://github.com/giampaolo/psutil/issues/987
.. _988: https://github.com/giampaolo/psutil/issues/988
.. _989: https://github.com/giampaolo/psutil/issues/989
.. _990: https://github.com/giampaolo/psutil/issues/990
.. _991: https://github.com/giampaolo/psutil/issues/991
.. _992: https://github.com/giampaolo/psutil/issues/992
.. _993: https://github.com/giampaolo/psutil/issues/993
.. _994: https://github.com/giampaolo/psutil/issues/994
.. _995: https://github.com/giampaolo/psutil/issues/995
.. _996: https://github.com/giampaolo/psutil/issues/996
.. _997: https://github.com/giampaolo/psutil/issues/997
.. _998: https://github.com/giampaolo/psutil/issues/998
.. _999: https://github.com/giampaolo/psutil/issues/999
.. _1000: https://github.com/giampaolo/psutil/issues/1000
.. _1001: https://github.com/giampaolo/psutil/issues/1001
.. _1002: https://github.com/giampaolo/psutil/issues/1002
.. _1003: https://github.com/giampaolo/psutil/issues/1003
.. _1004: https://github.com/giampaolo/psutil/issues/1004
.. _1005: https://github.com/giampaolo/psutil/issues/1005
.. _1006: https://github.com/giampaolo/psutil/issues/1006
.. _1007: https://github.com/giampaolo/psutil/issues/1007
.. _1008: https://github.com/giampaolo/psutil/issues/1008
.. _1009: https://github.com/giampaolo/psutil/issues/1009
.. _1010: https://github.com/giampaolo/psutil/issues/1010
.. _1011: https://github.com/giampaolo/psutil/issues/1011
.. _1012: https://github.com/giampaolo/psutil/issues/1012
.. _1013: https://github.com/giampaolo/psutil/issues/1013
.. _1014: https://github.com/giampaolo/psutil/issues/1014
.. _1015: https://github.com/giampaolo/psutil/issues/1015
.. _1016: https://github.com/giampaolo/psutil/issues/1016
.. _1017: https://github.com/giampaolo/psutil/issues/1017
.. _1018: https://github.com/giampaolo/psutil/issues/1018
.. _1019: https://github.com/giampaolo/psutil/issues/1019
.. _1020: https://github.com/giampaolo/psutil/issues/1020
.. _1021: https://github.com/giampaolo/psutil/issues/1021
.. _1022: https://github.com/giampaolo/psutil/issues/1022
.. _1023: https://github.com/giampaolo/psutil/issues/1023
.. _1024: https://github.com/giampaolo/psutil/issues/1024
.. _1025: https://github.com/giampaolo/psutil/issues/1025
.. _1026: https://github.com/giampaolo/psutil/issues/1026
.. _1027: https://github.com/giampaolo/psutil/issues/1027
.. _1028: https://github.com/giampaolo/psutil/issues/1028
.. _1029: https://github.com/giampaolo/psutil/issues/1029
.. _1030: https://github.com/giampaolo/psutil/issues/1030
.. _1031: https://github.com/giampaolo/psutil/issues/1031
.. _1032: https://github.com/giampaolo/psutil/issues/1032
.. _1033: https://github.com/giampaolo/psutil/issues/1033
.. _1034: https://github.com/giampaolo/psutil/issues/1034
.. _1035: https://github.com/giampaolo/psutil/issues/1035
.. _1036: https://github.com/giampaolo/psutil/issues/1036
.. _1037: https://github.com/giampaolo/psutil/issues/1037
.. _1038: https://github.com/giampaolo/psutil/issues/1038
.. _1039: https://github.com/giampaolo/psutil/issues/1039
.. _1040: https://github.com/giampaolo/psutil/issues/1040
.. _1041: https://github.com/giampaolo/psutil/issues/1041
.. _1042: https://github.com/giampaolo/psutil/issues/1042
.. _1043: https://github.com/giampaolo/psutil/issues/1043
.. _1044: https://github.com/giampaolo/psutil/issues/1044
.. _1045: https://github.com/giampaolo/psutil/issues/1045
.. _1046: https://github.com/giampaolo/psutil/issues/1046
.. _1047: https://github.com/giampaolo/psutil/issues/1047
.. _1048: https://github.com/giampaolo/psutil/issues/1048
.. _1049: https://github.com/giampaolo/psutil/issues/1049
.. _1050: https://github.com/giampaolo/psutil/issues/1050
.. _1051: https://github.com/giampaolo/psutil/issues/1051
.. _1052: https://github.com/giampaolo/psutil/issues/1052
.. _1053: https://github.com/giampaolo/psutil/issues/1053
.. _1054: https://github.com/giampaolo/psutil/issues/1054
.. _1055: https://github.com/giampaolo/psutil/issues/1055
.. _1056: https://github.com/giampaolo/psutil/issues/1056
.. _1057: https://github.com/giampaolo/psutil/issues/1057
.. _1058: https://github.com/giampaolo/psutil/issues/1058
.. _1059: https://github.com/giampaolo/psutil/issues/1059
.. _1060: https://github.com/giampaolo/psutil/issues/1060
.. _1061: https://github.com/giampaolo/psutil/issues/1061
.. _1062: https://github.com/giampaolo/psutil/issues/1062
.. _1063: https://github.com/giampaolo/psutil/issues/1063
.. _1064: https://github.com/giampaolo/psutil/issues/1064
.. _1065: https://github.com/giampaolo/psutil/issues/1065
.. _1066: https://github.com/giampaolo/psutil/issues/1066
.. _1067: https://github.com/giampaolo/psutil/issues/1067
.. _1068: https://github.com/giampaolo/psutil/issues/1068
.. _1069: https://github.com/giampaolo/psutil/issues/1069
.. _1070: https://github.com/giampaolo/psutil/issues/1070
.. _1071: https://github.com/giampaolo/psutil/issues/1071
.. _1072: https://github.com/giampaolo/psutil/issues/1072
.. _1073: https://github.com/giampaolo/psutil/issues/1073
.. _1074: https://github.com/giampaolo/psutil/issues/1074
.. _1075: https://github.com/giampaolo/psutil/issues/1075
.. _1076: https://github.com/giampaolo/psutil/issues/1076
.. _1077: https://github.com/giampaolo/psutil/issues/1077
.. _1078: https://github.com/giampaolo/psutil/issues/1078
.. _1079: https://github.com/giampaolo/psutil/issues/1079
.. _1080: https://github.com/giampaolo/psutil/issues/1080
.. _1081: https://github.com/giampaolo/psutil/issues/1081
.. _1082: https://github.com/giampaolo/psutil/issues/1082
.. _1083: https://github.com/giampaolo/psutil/issues/1083
.. _1084: https://github.com/giampaolo/psutil/issues/1084
.. _1085: https://github.com/giampaolo/psutil/issues/1085
.. _1086: https://github.com/giampaolo/psutil/issues/1086
.. _1087: https://github.com/giampaolo/psutil/issues/1087
.. _1088: https://github.com/giampaolo/psutil/issues/1088
.. _1089: https://github.com/giampaolo/psutil/issues/1089
.. _1090: https://github.com/giampaolo/psutil/issues/1090
.. _1091: https://github.com/giampaolo/psutil/issues/1091
.. _1092: https://github.com/giampaolo/psutil/issues/1092
.. _1093: https://github.com/giampaolo/psutil/issues/1093
.. _1094: https://github.com/giampaolo/psutil/issues/1094
.. _1095: https://github.com/giampaolo/psutil/issues/1095
.. _1096: https://github.com/giampaolo/psutil/issues/1096
.. _1097: https://github.com/giampaolo/psutil/issues/1097
.. _1098: https://github.com/giampaolo/psutil/issues/1098
.. _1099: https://github.com/giampaolo/psutil/issues/1099
.. _1100: https://github.com/giampaolo/psutil/issues/1100
.. _1101: https://github.com/giampaolo/psutil/issues/1101
.. _1102: https://github.com/giampaolo/psutil/issues/1102
.. _1103: https://github.com/giampaolo/psutil/issues/1103
.. _1104: https://github.com/giampaolo/psutil/issues/1104
.. _1105: https://github.com/giampaolo/psutil/issues/1105
.. _1106: https://github.com/giampaolo/psutil/issues/1106
.. _1107: https://github.com/giampaolo/psutil/issues/1107
.. _1108: https://github.com/giampaolo/psutil/issues/1108
.. _1109: https://github.com/giampaolo/psutil/issues/1109
.. _1110: https://github.com/giampaolo/psutil/issues/1110
.. _1111: https://github.com/giampaolo/psutil/issues/1111
.. _1112: https://github.com/giampaolo/psutil/issues/1112
.. _1113: https://github.com/giampaolo/psutil/issues/1113
.. _1114: https://github.com/giampaolo/psutil/issues/1114
.. _1115: https://github.com/giampaolo/psutil/issues/1115
.. _1116: https://github.com/giampaolo/psutil/issues/1116
.. _1117: https://github.com/giampaolo/psutil/issues/1117
.. _1118: https://github.com/giampaolo/psutil/issues/1118
.. _1119: https://github.com/giampaolo/psutil/issues/1119
.. _1120: https://github.com/giampaolo/psutil/issues/1120
.. _1121: https://github.com/giampaolo/psutil/issues/1121
.. _1122: https://github.com/giampaolo/psutil/issues/1122
.. _1123: https://github.com/giampaolo/psutil/issues/1123
.. _1124: https://github.com/giampaolo/psutil/issues/1124
.. _1125: https://github.com/giampaolo/psutil/issues/1125
.. _1126: https://github.com/giampaolo/psutil/issues/1126
.. _1127: https://github.com/giampaolo/psutil/issues/1127
.. _1128: https://github.com/giampaolo/psutil/issues/1128
.. _1129: https://github.com/giampaolo/psutil/issues/1129
.. _1130: https://github.com/giampaolo/psutil/issues/1130
.. _1131: https://github.com/giampaolo/psutil/issues/1131
.. _1132: https://github.com/giampaolo/psutil/issues/1132
.. _1133: https://github.com/giampaolo/psutil/issues/1133
.. _1134: https://github.com/giampaolo/psutil/issues/1134
.. _1135: https://github.com/giampaolo/psutil/issues/1135
.. _1136: https://github.com/giampaolo/psutil/issues/1136
.. _1137: https://github.com/giampaolo/psutil/issues/1137
.. _1138: https://github.com/giampaolo/psutil/issues/1138
.. _1139: https://github.com/giampaolo/psutil/issues/1139
.. _1140: https://github.com/giampaolo/psutil/issues/1140
.. _1141: https://github.com/giampaolo/psutil/issues/1141
.. _1142: https://github.com/giampaolo/psutil/issues/1142
.. _1143: https://github.com/giampaolo/psutil/issues/1143
.. _1144: https://github.com/giampaolo/psutil/issues/1144
.. _1145: https://github.com/giampaolo/psutil/issues/1145
.. _1146: https://github.com/giampaolo/psutil/issues/1146
.. _1147: https://github.com/giampaolo/psutil/issues/1147
.. _1148: https://github.com/giampaolo/psutil/issues/1148
.. _1149: https://github.com/giampaolo/psutil/issues/1149
.. _1150: https://github.com/giampaolo/psutil/issues/1150
.. _1151: https://github.com/giampaolo/psutil/issues/1151
.. _1152: https://github.com/giampaolo/psutil/issues/1152
.. _1153: https://github.com/giampaolo/psutil/issues/1153
.. _1154: https://github.com/giampaolo/psutil/issues/1154
.. _1155: https://github.com/giampaolo/psutil/issues/1155
.. _1156: https://github.com/giampaolo/psutil/issues/1156
.. _1157: https://github.com/giampaolo/psutil/issues/1157
.. _1158: https://github.com/giampaolo/psutil/issues/1158
.. _1159: https://github.com/giampaolo/psutil/issues/1159
.. _1160: https://github.com/giampaolo/psutil/issues/1160
.. _1161: https://github.com/giampaolo/psutil/issues/1161
.. _1162: https://github.com/giampaolo/psutil/issues/1162
.. _1163: https://github.com/giampaolo/psutil/issues/1163
.. _1164: https://github.com/giampaolo/psutil/issues/1164
.. _1165: https://github.com/giampaolo/psutil/issues/1165
.. _1166: https://github.com/giampaolo/psutil/issues/1166
.. _1167: https://github.com/giampaolo/psutil/issues/1167
.. _1168: https://github.com/giampaolo/psutil/issues/1168
.. _1169: https://github.com/giampaolo/psutil/issues/1169
.. _1170: https://github.com/giampaolo/psutil/issues/1170
.. _1171: https://github.com/giampaolo/psutil/issues/1171
.. _1172: https://github.com/giampaolo/psutil/issues/1172
.. _1173: https://github.com/giampaolo/psutil/issues/1173
.. _1174: https://github.com/giampaolo/psutil/issues/1174
.. _1175: https://github.com/giampaolo/psutil/issues/1175
.. _1176: https://github.com/giampaolo/psutil/issues/1176
.. _1177: https://github.com/giampaolo/psutil/issues/1177
.. _1178: https://github.com/giampaolo/psutil/issues/1178
.. _1179: https://github.com/giampaolo/psutil/issues/1179
.. _1180: https://github.com/giampaolo/psutil/issues/1180
.. _1181: https://github.com/giampaolo/psutil/issues/1181
.. _1182: https://github.com/giampaolo/psutil/issues/1182
.. _1183: https://github.com/giampaolo/psutil/issues/1183
.. _1184: https://github.com/giampaolo/psutil/issues/1184
.. _1185: https://github.com/giampaolo/psutil/issues/1185
.. _1186: https://github.com/giampaolo/psutil/issues/1186
.. _1187: https://github.com/giampaolo/psutil/issues/1187
.. _1188: https://github.com/giampaolo/psutil/issues/1188
.. _1189: https://github.com/giampaolo/psutil/issues/1189
.. _1190: https://github.com/giampaolo/psutil/issues/1190
.. _1191: https://github.com/giampaolo/psutil/issues/1191
.. _1192: https://github.com/giampaolo/psutil/issues/1192
.. _1193: https://github.com/giampaolo/psutil/issues/1193
.. _1194: https://github.com/giampaolo/psutil/issues/1194
.. _1195: https://github.com/giampaolo/psutil/issues/1195
.. _1196: https://github.com/giampaolo/psutil/issues/1196
.. _1197: https://github.com/giampaolo/psutil/issues/1197
.. _1198: https://github.com/giampaolo/psutil/issues/1198
.. _1199: https://github.com/giampaolo/psutil/issues/1199
.. _1200: https://github.com/giampaolo/psutil/issues/1200
.. _1201: https://github.com/giampaolo/psutil/issues/1201
.. _1202: https://github.com/giampaolo/psutil/issues/1202
.. _1203: https://github.com/giampaolo/psutil/issues/1203
.. _1204: https://github.com/giampaolo/psutil/issues/1204
.. _1205: https://github.com/giampaolo/psutil/issues/1205
.. _1206: https://github.com/giampaolo/psutil/issues/1206
.. _1207: https://github.com/giampaolo/psutil/issues/1207
.. _1208: https://github.com/giampaolo/psutil/issues/1208
.. _1209: https://github.com/giampaolo/psutil/issues/1209
.. _1210: https://github.com/giampaolo/psutil/issues/1210
.. _1211: https://github.com/giampaolo/psutil/issues/1211
.. _1212: https://github.com/giampaolo/psutil/issues/1212
.. _1213: https://github.com/giampaolo/psutil/issues/1213
.. _1214: https://github.com/giampaolo/psutil/issues/1214
.. _1215: https://github.com/giampaolo/psutil/issues/1215
.. _1216: https://github.com/giampaolo/psutil/issues/1216
.. _1217: https://github.com/giampaolo/psutil/issues/1217
.. _1218: https://github.com/giampaolo/psutil/issues/1218
.. _1219: https://github.com/giampaolo/psutil/issues/1219
.. _1220: https://github.com/giampaolo/psutil/issues/1220
.. _1221: https://github.com/giampaolo/psutil/issues/1221
.. _1222: https://github.com/giampaolo/psutil/issues/1222
.. _1223: https://github.com/giampaolo/psutil/issues/1223
.. _1224: https://github.com/giampaolo/psutil/issues/1224
.. _1225: https://github.com/giampaolo/psutil/issues/1225
.. _1226: https://github.com/giampaolo/psutil/issues/1226
.. _1227: https://github.com/giampaolo/psutil/issues/1227
.. _1228: https://github.com/giampaolo/psutil/issues/1228
.. _1229: https://github.com/giampaolo/psutil/issues/1229
.. _1230: https://github.com/giampaolo/psutil/issues/1230
.. _1231: https://github.com/giampaolo/psutil/issues/1231
.. _1232: https://github.com/giampaolo/psutil/issues/1232
.. _1233: https://github.com/giampaolo/psutil/issues/1233
.. _1234: https://github.com/giampaolo/psutil/issues/1234
.. _1235: https://github.com/giampaolo/psutil/issues/1235
.. _1236: https://github.com/giampaolo/psutil/issues/1236
.. _1237: https://github.com/giampaolo/psutil/issues/1237
.. _1238: https://github.com/giampaolo/psutil/issues/1238
.. _1239: https://github.com/giampaolo/psutil/issues/1239
.. _1240: https://github.com/giampaolo/psutil/issues/1240
.. _1241: https://github.com/giampaolo/psutil/issues/1241
.. _1242: https://github.com/giampaolo/psutil/issues/1242
.. _1243: https://github.com/giampaolo/psutil/issues/1243
.. _1244: https://github.com/giampaolo/psutil/issues/1244
.. _1245: https://github.com/giampaolo/psutil/issues/1245
.. _1246: https://github.com/giampaolo/psutil/issues/1246
.. _1247: https://github.com/giampaolo/psutil/issues/1247
.. _1248: https://github.com/giampaolo/psutil/issues/1248
.. _1249: https://github.com/giampaolo/psutil/issues/1249
.. _1250: https://github.com/giampaolo/psutil/issues/1250
.. _1251: https://github.com/giampaolo/psutil/issues/1251
.. _1252: https://github.com/giampaolo/psutil/issues/1252
.. _1253: https://github.com/giampaolo/psutil/issues/1253
.. _1254: https://github.com/giampaolo/psutil/issues/1254
.. _1255: https://github.com/giampaolo/psutil/issues/1255
.. _1256: https://github.com/giampaolo/psutil/issues/1256
.. _1257: https://github.com/giampaolo/psutil/issues/1257
.. _1258: https://github.com/giampaolo/psutil/issues/1258
.. _1259: https://github.com/giampaolo/psutil/issues/1259
.. _1260: https://github.com/giampaolo/psutil/issues/1260
.. _1261: https://github.com/giampaolo/psutil/issues/1261
.. _1262: https://github.com/giampaolo/psutil/issues/1262
.. _1263: https://github.com/giampaolo/psutil/issues/1263
.. _1264: https://github.com/giampaolo/psutil/issues/1264
.. _1265: https://github.com/giampaolo/psutil/issues/1265
.. _1266: https://github.com/giampaolo/psutil/issues/1266
.. _1267: https://github.com/giampaolo/psutil/issues/1267
.. _1268: https://github.com/giampaolo/psutil/issues/1268
.. _1269: https://github.com/giampaolo/psutil/issues/1269
.. _1270: https://github.com/giampaolo/psutil/issues/1270
.. _1271: https://github.com/giampaolo/psutil/issues/1271
.. _1272: https://github.com/giampaolo/psutil/issues/1272
.. _1273: https://github.com/giampaolo/psutil/issues/1273
.. _1274: https://github.com/giampaolo/psutil/issues/1274
.. _1275: https://github.com/giampaolo/psutil/issues/1275
.. _1276: https://github.com/giampaolo/psutil/issues/1276
.. _1277: https://github.com/giampaolo/psutil/issues/1277
.. _1278: https://github.com/giampaolo/psutil/issues/1278
.. _1279: https://github.com/giampaolo/psutil/issues/1279
.. _1280: https://github.com/giampaolo/psutil/issues/1280
.. _1281: https://github.com/giampaolo/psutil/issues/1281
.. _1282: https://github.com/giampaolo/psutil/issues/1282
.. _1283: https://github.com/giampaolo/psutil/issues/1283
.. _1284: https://github.com/giampaolo/psutil/issues/1284
.. _1285: https://github.com/giampaolo/psutil/issues/1285
.. _1286: https://github.com/giampaolo/psutil/issues/1286
.. _1287: https://github.com/giampaolo/psutil/issues/1287
.. _1288: https://github.com/giampaolo/psutil/issues/1288
.. _1289: https://github.com/giampaolo/psutil/issues/1289
.. _1290: https://github.com/giampaolo/psutil/issues/1290
.. _1291: https://github.com/giampaolo/psutil/issues/1291
.. _1292: https://github.com/giampaolo/psutil/issues/1292
.. _1293: https://github.com/giampaolo/psutil/issues/1293
.. _1294: https://github.com/giampaolo/psutil/issues/1294
.. _1295: https://github.com/giampaolo/psutil/issues/1295
.. _1296: https://github.com/giampaolo/psutil/issues/1296
.. _1297: https://github.com/giampaolo/psutil/issues/1297
.. _1298: https://github.com/giampaolo/psutil/issues/1298
.. _1299: https://github.com/giampaolo/psutil/issues/1299
.. _1300: https://github.com/giampaolo/psutil/issues/1300
.. _1301: https://github.com/giampaolo/psutil/issues/1301
.. _1302: https://github.com/giampaolo/psutil/issues/1302
.. _1303: https://github.com/giampaolo/psutil/issues/1303
.. _1304: https://github.com/giampaolo/psutil/issues/1304
.. _1305: https://github.com/giampaolo/psutil/issues/1305
.. _1306: https://github.com/giampaolo/psutil/issues/1306
.. _1307: https://github.com/giampaolo/psutil/issues/1307
.. _1308: https://github.com/giampaolo/psutil/issues/1308
.. _1309: https://github.com/giampaolo/psutil/issues/1309
.. _1310: https://github.com/giampaolo/psutil/issues/1310
.. _1311: https://github.com/giampaolo/psutil/issues/1311
.. _1312: https://github.com/giampaolo/psutil/issues/1312
.. _1313: https://github.com/giampaolo/psutil/issues/1313
.. _1314: https://github.com/giampaolo/psutil/issues/1314
.. _1315: https://github.com/giampaolo/psutil/issues/1315
.. _1316: https://github.com/giampaolo/psutil/issues/1316
.. _1317: https://github.com/giampaolo/psutil/issues/1317
.. _1318: https://github.com/giampaolo/psutil/issues/1318
.. _1319: https://github.com/giampaolo/psutil/issues/1319
.. _1320: https://github.com/giampaolo/psutil/issues/1320
.. _1321: https://github.com/giampaolo/psutil/issues/1321
.. _1322: https://github.com/giampaolo/psutil/issues/1322
.. _1323: https://github.com/giampaolo/psutil/issues/1323
.. _1324: https://github.com/giampaolo/psutil/issues/1324
.. _1325: https://github.com/giampaolo/psutil/issues/1325
.. _1326: https://github.com/giampaolo/psutil/issues/1326
.. _1327: https://github.com/giampaolo/psutil/issues/1327
.. _1328: https://github.com/giampaolo/psutil/issues/1328
.. _1329: https://github.com/giampaolo/psutil/issues/1329
.. _1330: https://github.com/giampaolo/psutil/issues/1330
.. _1331: https://github.com/giampaolo/psutil/issues/1331
.. _1332: https://github.com/giampaolo/psutil/issues/1332
.. _1333: https://github.com/giampaolo/psutil/issues/1333
.. _1334: https://github.com/giampaolo/psutil/issues/1334
.. _1335: https://github.com/giampaolo/psutil/issues/1335
.. _1336: https://github.com/giampaolo/psutil/issues/1336
.. _1337: https://github.com/giampaolo/psutil/issues/1337
.. _1338: https://github.com/giampaolo/psutil/issues/1338
.. _1339: https://github.com/giampaolo/psutil/issues/1339
.. _1340: https://github.com/giampaolo/psutil/issues/1340
.. _1341: https://github.com/giampaolo/psutil/issues/1341
.. _1342: https://github.com/giampaolo/psutil/issues/1342
.. _1343: https://github.com/giampaolo/psutil/issues/1343
.. _1344: https://github.com/giampaolo/psutil/issues/1344
.. _1345: https://github.com/giampaolo/psutil/issues/1345
.. _1346: https://github.com/giampaolo/psutil/issues/1346
.. _1347: https://github.com/giampaolo/psutil/issues/1347
.. _1348: https://github.com/giampaolo/psutil/issues/1348
.. _1349: https://github.com/giampaolo/psutil/issues/1349
.. _1350: https://github.com/giampaolo/psutil/issues/1350
.. _1351: https://github.com/giampaolo/psutil/issues/1351
.. _1352: https://github.com/giampaolo/psutil/issues/1352
.. _1353: https://github.com/giampaolo/psutil/issues/1353
.. _1354: https://github.com/giampaolo/psutil/issues/1354
.. _1355: https://github.com/giampaolo/psutil/issues/1355
.. _1356: https://github.com/giampaolo/psutil/issues/1356
.. _1357: https://github.com/giampaolo/psutil/issues/1357
.. _1358: https://github.com/giampaolo/psutil/issues/1358
.. _1359: https://github.com/giampaolo/psutil/issues/1359
.. _1360: https://github.com/giampaolo/psutil/issues/1360
.. _1361: https://github.com/giampaolo/psutil/issues/1361
.. _1362: https://github.com/giampaolo/psutil/issues/1362
.. _1363: https://github.com/giampaolo/psutil/issues/1363
.. _1364: https://github.com/giampaolo/psutil/issues/1364
.. _1365: https://github.com/giampaolo/psutil/issues/1365
.. _1366: https://github.com/giampaolo/psutil/issues/1366
.. _1367: https://github.com/giampaolo/psutil/issues/1367
.. _1368: https://github.com/giampaolo/psutil/issues/1368
.. _1369: https://github.com/giampaolo/psutil/issues/1369
.. _1370: https://github.com/giampaolo/psutil/issues/1370
.. _1371: https://github.com/giampaolo/psutil/issues/1371
.. _1372: https://github.com/giampaolo/psutil/issues/1372
.. _1373: https://github.com/giampaolo/psutil/issues/1373
.. _1374: https://github.com/giampaolo/psutil/issues/1374
.. _1375: https://github.com/giampaolo/psutil/issues/1375
.. _1376: https://github.com/giampaolo/psutil/issues/1376
.. _1377: https://github.com/giampaolo/psutil/issues/1377
.. _1378: https://github.com/giampaolo/psutil/issues/1378
.. _1379: https://github.com/giampaolo/psutil/issues/1379
.. _1380: https://github.com/giampaolo/psutil/issues/1380
.. _1381: https://github.com/giampaolo/psutil/issues/1381
.. _1382: https://github.com/giampaolo/psutil/issues/1382
.. _1383: https://github.com/giampaolo/psutil/issues/1383
.. _1384: https://github.com/giampaolo/psutil/issues/1384
.. _1385: https://github.com/giampaolo/psutil/issues/1385
.. _1386: https://github.com/giampaolo/psutil/issues/1386
.. _1387: https://github.com/giampaolo/psutil/issues/1387
.. _1388: https://github.com/giampaolo/psutil/issues/1388
.. _1389: https://github.com/giampaolo/psutil/issues/1389
.. _1390: https://github.com/giampaolo/psutil/issues/1390
.. _1391: https://github.com/giampaolo/psutil/issues/1391
.. _1392: https://github.com/giampaolo/psutil/issues/1392
.. _1393: https://github.com/giampaolo/psutil/issues/1393
.. _1394: https://github.com/giampaolo/psutil/issues/1394
.. _1395: https://github.com/giampaolo/psutil/issues/1395
.. _1396: https://github.com/giampaolo/psutil/issues/1396
.. _1397: https://github.com/giampaolo/psutil/issues/1397
.. _1398: https://github.com/giampaolo/psutil/issues/1398
.. _1399: https://github.com/giampaolo/psutil/issues/1399
.. _1400: https://github.com/giampaolo/psutil/issues/1400
.. _1401: https://github.com/giampaolo/psutil/issues/1401
.. _1402: https://github.com/giampaolo/psutil/issues/1402
.. _1403: https://github.com/giampaolo/psutil/issues/1403
.. _1404: https://github.com/giampaolo/psutil/issues/1404
.. _1405: https://github.com/giampaolo/psutil/issues/1405
.. _1406: https://github.com/giampaolo/psutil/issues/1406
.. _1407: https://github.com/giampaolo/psutil/issues/1407
.. _1408: https://github.com/giampaolo/psutil/issues/1408
.. _1409: https://github.com/giampaolo/psutil/issues/1409
.. _1410: https://github.com/giampaolo/psutil/issues/1410
.. _1411: https://github.com/giampaolo/psutil/issues/1411
.. _1412: https://github.com/giampaolo/psutil/issues/1412
.. _1413: https://github.com/giampaolo/psutil/issues/1413
.. _1414: https://github.com/giampaolo/psutil/issues/1414
.. _1415: https://github.com/giampaolo/psutil/issues/1415
.. _1416: https://github.com/giampaolo/psutil/issues/1416
.. _1417: https://github.com/giampaolo/psutil/issues/1417
.. _1418: https://github.com/giampaolo/psutil/issues/1418
.. _1419: https://github.com/giampaolo/psutil/issues/1419
.. _1420: https://github.com/giampaolo/psutil/issues/1420
.. _1421: https://github.com/giampaolo/psutil/issues/1421
.. _1422: https://github.com/giampaolo/psutil/issues/1422
.. _1423: https://github.com/giampaolo/psutil/issues/1423
.. _1424: https://github.com/giampaolo/psutil/issues/1424
.. _1425: https://github.com/giampaolo/psutil/issues/1425
.. _1426: https://github.com/giampaolo/psutil/issues/1426
.. _1427: https://github.com/giampaolo/psutil/issues/1427
.. _1428: https://github.com/giampaolo/psutil/issues/1428
.. _1429: https://github.com/giampaolo/psutil/issues/1429
.. _1430: https://github.com/giampaolo/psutil/issues/1430
.. _1431: https://github.com/giampaolo/psutil/issues/1431
.. _1432: https://github.com/giampaolo/psutil/issues/1432
.. _1433: https://github.com/giampaolo/psutil/issues/1433
.. _1434: https://github.com/giampaolo/psutil/issues/1434
.. _1435: https://github.com/giampaolo/psutil/issues/1435
.. _1436: https://github.com/giampaolo/psutil/issues/1436
.. _1437: https://github.com/giampaolo/psutil/issues/1437
.. _1438: https://github.com/giampaolo/psutil/issues/1438
.. _1439: https://github.com/giampaolo/psutil/issues/1439
.. _1440: https://github.com/giampaolo/psutil/issues/1440
.. _1441: https://github.com/giampaolo/psutil/issues/1441
.. _1442: https://github.com/giampaolo/psutil/issues/1442
.. _1443: https://github.com/giampaolo/psutil/issues/1443
.. _1444: https://github.com/giampaolo/psutil/issues/1444
.. _1445: https://github.com/giampaolo/psutil/issues/1445
.. _1446: https://github.com/giampaolo/psutil/issues/1446
.. _1447: https://github.com/giampaolo/psutil/issues/1447
.. _1448: https://github.com/giampaolo/psutil/issues/1448
.. _1449: https://github.com/giampaolo/psutil/issues/1449
.. _1450: https://github.com/giampaolo/psutil/issues/1450
.. _1451: https://github.com/giampaolo/psutil/issues/1451
.. _1452: https://github.com/giampaolo/psutil/issues/1452
.. _1453: https://github.com/giampaolo/psutil/issues/1453
.. _1454: https://github.com/giampaolo/psutil/issues/1454
.. _1455: https://github.com/giampaolo/psutil/issues/1455
.. _1456: https://github.com/giampaolo/psutil/issues/1456
.. _1457: https://github.com/giampaolo/psutil/issues/1457
.. _1458: https://github.com/giampaolo/psutil/issues/1458
.. _1459: https://github.com/giampaolo/psutil/issues/1459
.. _1460: https://github.com/giampaolo/psutil/issues/1460
.. _1461: https://github.com/giampaolo/psutil/issues/1461
.. _1462: https://github.com/giampaolo/psutil/issues/1462
.. _1463: https://github.com/giampaolo/psutil/issues/1463
.. _1464: https://github.com/giampaolo/psutil/issues/1464
.. _1465: https://github.com/giampaolo/psutil/issues/1465
.. _1466: https://github.com/giampaolo/psutil/issues/1466
.. _1467: https://github.com/giampaolo/psutil/issues/1467
.. _1468: https://github.com/giampaolo/psutil/issues/1468
.. _1469: https://github.com/giampaolo/psutil/issues/1469
.. _1470: https://github.com/giampaolo/psutil/issues/1470
.. _1471: https://github.com/giampaolo/psutil/issues/1471
.. _1472: https://github.com/giampaolo/psutil/issues/1472
.. _1473: https://github.com/giampaolo/psutil/issues/1473
.. _1474: https://github.com/giampaolo/psutil/issues/1474
.. _1475: https://github.com/giampaolo/psutil/issues/1475
.. _1476: https://github.com/giampaolo/psutil/issues/1476
.. _1477: https://github.com/giampaolo/psutil/issues/1477
.. _1478: https://github.com/giampaolo/psutil/issues/1478
.. _1479: https://github.com/giampaolo/psutil/issues/1479
.. _1480: https://github.com/giampaolo/psutil/issues/1480
.. _1481: https://github.com/giampaolo/psutil/issues/1481
.. _1482: https://github.com/giampaolo/psutil/issues/1482
.. _1483: https://github.com/giampaolo/psutil/issues/1483
.. _1484: https://github.com/giampaolo/psutil/issues/1484
.. _1485: https://github.com/giampaolo/psutil/issues/1485
.. _1486: https://github.com/giampaolo/psutil/issues/1486
.. _1487: https://github.com/giampaolo/psutil/issues/1487
.. _1488: https://github.com/giampaolo/psutil/issues/1488
.. _1489: https://github.com/giampaolo/psutil/issues/1489
.. _1490: https://github.com/giampaolo/psutil/issues/1490
.. _1491: https://github.com/giampaolo/psutil/issues/1491
.. _1492: https://github.com/giampaolo/psutil/issues/1492
.. _1493: https://github.com/giampaolo/psutil/issues/1493
.. _1494: https://github.com/giampaolo/psutil/issues/1494
.. _1495: https://github.com/giampaolo/psutil/issues/1495
.. _1496: https://github.com/giampaolo/psutil/issues/1496
.. _1497: https://github.com/giampaolo/psutil/issues/1497
.. _1498: https://github.com/giampaolo/psutil/issues/1498
.. _1499: https://github.com/giampaolo/psutil/issues/1499
.. _1500: https://github.com/giampaolo/psutil/issues/1500
.. _1501: https://github.com/giampaolo/psutil/issues/1501
.. _1502: https://github.com/giampaolo/psutil/issues/1502
.. _1503: https://github.com/giampaolo/psutil/issues/1503
.. _1504: https://github.com/giampaolo/psutil/issues/1504
.. _1505: https://github.com/giampaolo/psutil/issues/1505
.. _1506: https://github.com/giampaolo/psutil/issues/1506
.. _1507: https://github.com/giampaolo/psutil/issues/1507
.. _1508: https://github.com/giampaolo/psutil/issues/1508
.. _1509: https://github.com/giampaolo/psutil/issues/1509
.. _1510: https://github.com/giampaolo/psutil/issues/1510
.. _1511: https://github.com/giampaolo/psutil/issues/1511
.. _1512: https://github.com/giampaolo/psutil/issues/1512
.. _1513: https://github.com/giampaolo/psutil/issues/1513
.. _1514: https://github.com/giampaolo/psutil/issues/1514
.. _1515: https://github.com/giampaolo/psutil/issues/1515
.. _1516: https://github.com/giampaolo/psutil/issues/1516
.. _1517: https://github.com/giampaolo/psutil/issues/1517
.. _1518: https://github.com/giampaolo/psutil/issues/1518
.. _1519: https://github.com/giampaolo/psutil/issues/1519
.. _1520: https://github.com/giampaolo/psutil/issues/1520
.. _1521: https://github.com/giampaolo/psutil/issues/1521
.. _1522: https://github.com/giampaolo/psutil/issues/1522
.. _1523: https://github.com/giampaolo/psutil/issues/1523
.. _1524: https://github.com/giampaolo/psutil/issues/1524
.. _1525: https://github.com/giampaolo/psutil/issues/1525
.. _1526: https://github.com/giampaolo/psutil/issues/1526
.. _1527: https://github.com/giampaolo/psutil/issues/1527
.. _1528: https://github.com/giampaolo/psutil/issues/1528
.. _1529: https://github.com/giampaolo/psutil/issues/1529
.. _1530: https://github.com/giampaolo/psutil/issues/1530
.. _1531: https://github.com/giampaolo/psutil/issues/1531
.. _1532: https://github.com/giampaolo/psutil/issues/1532
.. _1533: https://github.com/giampaolo/psutil/issues/1533
.. _1534: https://github.com/giampaolo/psutil/issues/1534
.. _1535: https://github.com/giampaolo/psutil/issues/1535
.. _1536: https://github.com/giampaolo/psutil/issues/1536
.. _1537: https://github.com/giampaolo/psutil/issues/1537
.. _1538: https://github.com/giampaolo/psutil/issues/1538
.. _1539: https://github.com/giampaolo/psutil/issues/1539
.. _1540: https://github.com/giampaolo/psutil/issues/1540
.. _1541: https://github.com/giampaolo/psutil/issues/1541
.. _1542: https://github.com/giampaolo/psutil/issues/1542
.. _1543: https://github.com/giampaolo/psutil/issues/1543
.. _1544: https://github.com/giampaolo/psutil/issues/1544
.. _1545: https://github.com/giampaolo/psutil/issues/1545
.. _1546: https://github.com/giampaolo/psutil/issues/1546
.. _1547: https://github.com/giampaolo/psutil/issues/1547
.. _1548: https://github.com/giampaolo/psutil/issues/1548
.. _1549: https://github.com/giampaolo/psutil/issues/1549
.. _1550: https://github.com/giampaolo/psutil/issues/1550
.. _1551: https://github.com/giampaolo/psutil/issues/1551
.. _1552: https://github.com/giampaolo/psutil/issues/1552
.. _1553: https://github.com/giampaolo/psutil/issues/1553
.. _1554: https://github.com/giampaolo/psutil/issues/1554
.. _1555: https://github.com/giampaolo/psutil/issues/1555
.. _1556: https://github.com/giampaolo/psutil/issues/1556
.. _1557: https://github.com/giampaolo/psutil/issues/1557
.. _1558: https://github.com/giampaolo/psutil/issues/1558
.. _1559: https://github.com/giampaolo/psutil/issues/1559
.. _1560: https://github.com/giampaolo/psutil/issues/1560
.. _1561: https://github.com/giampaolo/psutil/issues/1561
.. _1562: https://github.com/giampaolo/psutil/issues/1562
.. _1563: https://github.com/giampaolo/psutil/issues/1563
.. _1564: https://github.com/giampaolo/psutil/issues/1564
.. _1565: https://github.com/giampaolo/psutil/issues/1565
.. _1566: https://github.com/giampaolo/psutil/issues/1566
.. _1567: https://github.com/giampaolo/psutil/issues/1567
.. _1568: https://github.com/giampaolo/psutil/issues/1568
.. _1569: https://github.com/giampaolo/psutil/issues/1569
.. _1570: https://github.com/giampaolo/psutil/issues/1570
.. _1571: https://github.com/giampaolo/psutil/issues/1571
.. _1572: https://github.com/giampaolo/psutil/issues/1572
.. _1573: https://github.com/giampaolo/psutil/issues/1573
.. _1574: https://github.com/giampaolo/psutil/issues/1574
.. _1575: https://github.com/giampaolo/psutil/issues/1575
.. _1576: https://github.com/giampaolo/psutil/issues/1576
.. _1577: https://github.com/giampaolo/psutil/issues/1577
.. _1578: https://github.com/giampaolo/psutil/issues/1578
.. _1579: https://github.com/giampaolo/psutil/issues/1579
.. _1580: https://github.com/giampaolo/psutil/issues/1580
.. _1581: https://github.com/giampaolo/psutil/issues/1581
.. _1582: https://github.com/giampaolo/psutil/issues/1582
.. _1583: https://github.com/giampaolo/psutil/issues/1583
.. _1584: https://github.com/giampaolo/psutil/issues/1584
.. _1585: https://github.com/giampaolo/psutil/issues/1585
.. _1586: https://github.com/giampaolo/psutil/issues/1586
.. _1587: https://github.com/giampaolo/psutil/issues/1587
.. _1588: https://github.com/giampaolo/psutil/issues/1588
.. _1589: https://github.com/giampaolo/psutil/issues/1589
.. _1590: https://github.com/giampaolo/psutil/issues/1590
.. _1591: https://github.com/giampaolo/psutil/issues/1591
.. _1592: https://github.com/giampaolo/psutil/issues/1592
.. _1593: https://github.com/giampaolo/psutil/issues/1593
.. _1594: https://github.com/giampaolo/psutil/issues/1594
.. _1595: https://github.com/giampaolo/psutil/issues/1595
.. _1596: https://github.com/giampaolo/psutil/issues/1596
.. _1597: https://github.com/giampaolo/psutil/issues/1597
.. _1598: https://github.com/giampaolo/psutil/issues/1598
.. _1599: https://github.com/giampaolo/psutil/issues/1599
.. _1600: https://github.com/giampaolo/psutil/issues/1600
.. _1601: https://github.com/giampaolo/psutil/issues/1601
.. _1602: https://github.com/giampaolo/psutil/issues/1602
.. _1603: https://github.com/giampaolo/psutil/issues/1603
.. _1604: https://github.com/giampaolo/psutil/issues/1604
.. _1605: https://github.com/giampaolo/psutil/issues/1605
.. _1606: https://github.com/giampaolo/psutil/issues/1606
.. _1607: https://github.com/giampaolo/psutil/issues/1607
.. _1608: https://github.com/giampaolo/psutil/issues/1608
.. _1609: https://github.com/giampaolo/psutil/issues/1609
.. _1610: https://github.com/giampaolo/psutil/issues/1610
.. _1611: https://github.com/giampaolo/psutil/issues/1611
.. _1612: https://github.com/giampaolo/psutil/issues/1612
.. _1613: https://github.com/giampaolo/psutil/issues/1613
.. _1614: https://github.com/giampaolo/psutil/issues/1614
.. _1615: https://github.com/giampaolo/psutil/issues/1615
.. _1616: https://github.com/giampaolo/psutil/issues/1616
.. _1617: https://github.com/giampaolo/psutil/issues/1617
.. _1618: https://github.com/giampaolo/psutil/issues/1618
.. _1619: https://github.com/giampaolo/psutil/issues/1619
.. _1620: https://github.com/giampaolo/psutil/issues/1620
.. _1621: https://github.com/giampaolo/psutil/issues/1621
.. _1622: https://github.com/giampaolo/psutil/issues/1622
.. _1623: https://github.com/giampaolo/psutil/issues/1623
.. _1624: https://github.com/giampaolo/psutil/issues/1624
.. _1625: https://github.com/giampaolo/psutil/issues/1625
.. _1626: https://github.com/giampaolo/psutil/issues/1626
.. _1627: https://github.com/giampaolo/psutil/issues/1627
.. _1628: https://github.com/giampaolo/psutil/issues/1628
.. _1629: https://github.com/giampaolo/psutil/issues/1629
.. _1630: https://github.com/giampaolo/psutil/issues/1630
.. _1631: https://github.com/giampaolo/psutil/issues/1631
.. _1632: https://github.com/giampaolo/psutil/issues/1632
.. _1633: https://github.com/giampaolo/psutil/issues/1633
.. _1634: https://github.com/giampaolo/psutil/issues/1634
.. _1635: https://github.com/giampaolo/psutil/issues/1635
.. _1636: https://github.com/giampaolo/psutil/issues/1636
.. _1637: https://github.com/giampaolo/psutil/issues/1637
.. _1638: https://github.com/giampaolo/psutil/issues/1638
.. _1639: https://github.com/giampaolo/psutil/issues/1639
.. _1640: https://github.com/giampaolo/psutil/issues/1640
.. _1641: https://github.com/giampaolo/psutil/issues/1641
.. _1642: https://github.com/giampaolo/psutil/issues/1642
.. _1643: https://github.com/giampaolo/psutil/issues/1643
.. _1644: https://github.com/giampaolo/psutil/issues/1644
.. _1645: https://github.com/giampaolo/psutil/issues/1645
.. _1646: https://github.com/giampaolo/psutil/issues/1646
.. _1647: https://github.com/giampaolo/psutil/issues/1647
.. _1648: https://github.com/giampaolo/psutil/issues/1648
.. _1649: https://github.com/giampaolo/psutil/issues/1649
.. _1650: https://github.com/giampaolo/psutil/issues/1650
.. _1651: https://github.com/giampaolo/psutil/issues/1651
.. _1652: https://github.com/giampaolo/psutil/issues/1652
.. _1653: https://github.com/giampaolo/psutil/issues/1653
.. _1654: https://github.com/giampaolo/psutil/issues/1654
.. _1655: https://github.com/giampaolo/psutil/issues/1655
.. _1656: https://github.com/giampaolo/psutil/issues/1656
.. _1657: https://github.com/giampaolo/psutil/issues/1657
.. _1658: https://github.com/giampaolo/psutil/issues/1658
.. _1659: https://github.com/giampaolo/psutil/issues/1659
.. _1660: https://github.com/giampaolo/psutil/issues/1660
.. _1661: https://github.com/giampaolo/psutil/issues/1661
.. _1662: https://github.com/giampaolo/psutil/issues/1662
.. _1663: https://github.com/giampaolo/psutil/issues/1663
.. _1664: https://github.com/giampaolo/psutil/issues/1664
.. _1665: https://github.com/giampaolo/psutil/issues/1665
.. _1666: https://github.com/giampaolo/psutil/issues/1666
.. _1667: https://github.com/giampaolo/psutil/issues/1667
.. _1668: https://github.com/giampaolo/psutil/issues/1668
.. _1669: https://github.com/giampaolo/psutil/issues/1669
.. _1670: https://github.com/giampaolo/psutil/issues/1670
.. _1671: https://github.com/giampaolo/psutil/issues/1671
.. _1672: https://github.com/giampaolo/psutil/issues/1672
.. _1673: https://github.com/giampaolo/psutil/issues/1673
.. _1674: https://github.com/giampaolo/psutil/issues/1674
.. _1675: https://github.com/giampaolo/psutil/issues/1675
.. _1676: https://github.com/giampaolo/psutil/issues/1676
.. _1677: https://github.com/giampaolo/psutil/issues/1677
.. _1678: https://github.com/giampaolo/psutil/issues/1678
.. _1679: https://github.com/giampaolo/psutil/issues/1679
.. _1680: https://github.com/giampaolo/psutil/issues/1680
.. _1681: https://github.com/giampaolo/psutil/issues/1681
.. _1682: https://github.com/giampaolo/psutil/issues/1682
.. _1683: https://github.com/giampaolo/psutil/issues/1683
.. _1684: https://github.com/giampaolo/psutil/issues/1684
.. _1685: https://github.com/giampaolo/psutil/issues/1685
.. _1686: https://github.com/giampaolo/psutil/issues/1686
.. _1687: https://github.com/giampaolo/psutil/issues/1687
.. _1688: https://github.com/giampaolo/psutil/issues/1688
.. _1689: https://github.com/giampaolo/psutil/issues/1689
.. _1690: https://github.com/giampaolo/psutil/issues/1690
.. _1691: https://github.com/giampaolo/psutil/issues/1691
.. _1692: https://github.com/giampaolo/psutil/issues/1692
.. _1693: https://github.com/giampaolo/psutil/issues/1693
.. _1694: https://github.com/giampaolo/psutil/issues/1694
.. _1695: https://github.com/giampaolo/psutil/issues/1695
.. _1696: https://github.com/giampaolo/psutil/issues/1696
.. _1697: https://github.com/giampaolo/psutil/issues/1697
.. _1698: https://github.com/giampaolo/psutil/issues/1698
.. _1699: https://github.com/giampaolo/psutil/issues/1699
.. _1700: https://github.com/giampaolo/psutil/issues/1700
.. _1701: https://github.com/giampaolo/psutil/issues/1701
.. _1702: https://github.com/giampaolo/psutil/issues/1702
.. _1703: https://github.com/giampaolo/psutil/issues/1703
.. _1704: https://github.com/giampaolo/psutil/issues/1704
.. _1705: https://github.com/giampaolo/psutil/issues/1705
.. _1706: https://github.com/giampaolo/psutil/issues/1706
.. _1707: https://github.com/giampaolo/psutil/issues/1707
.. _1708: https://github.com/giampaolo/psutil/issues/1708
.. _1709: https://github.com/giampaolo/psutil/issues/1709
.. _1710: https://github.com/giampaolo/psutil/issues/1710
.. _1711: https://github.com/giampaolo/psutil/issues/1711
.. _1712: https://github.com/giampaolo/psutil/issues/1712
.. _1713: https://github.com/giampaolo/psutil/issues/1713
.. _1714: https://github.com/giampaolo/psutil/issues/1714
.. _1715: https://github.com/giampaolo/psutil/issues/1715
.. _1716: https://github.com/giampaolo/psutil/issues/1716
.. _1717: https://github.com/giampaolo/psutil/issues/1717
.. _1718: https://github.com/giampaolo/psutil/issues/1718
.. _1719: https://github.com/giampaolo/psutil/issues/1719
.. _1720: https://github.com/giampaolo/psutil/issues/1720
.. _1721: https://github.com/giampaolo/psutil/issues/1721
.. _1722: https://github.com/giampaolo/psutil/issues/1722
.. _1723: https://github.com/giampaolo/psutil/issues/1723
.. _1724: https://github.com/giampaolo/psutil/issues/1724
.. _1725: https://github.com/giampaolo/psutil/issues/1725
.. _1726: https://github.com/giampaolo/psutil/issues/1726
.. _1727: https://github.com/giampaolo/psutil/issues/1727
.. _1728: https://github.com/giampaolo/psutil/issues/1728
.. _1729: https://github.com/giampaolo/psutil/issues/1729
.. _1730: https://github.com/giampaolo/psutil/issues/1730
.. _1731: https://github.com/giampaolo/psutil/issues/1731
.. _1732: https://github.com/giampaolo/psutil/issues/1732
.. _1733: https://github.com/giampaolo/psutil/issues/1733
.. _1734: https://github.com/giampaolo/psutil/issues/1734
.. _1735: https://github.com/giampaolo/psutil/issues/1735
.. _1736: https://github.com/giampaolo/psutil/issues/1736
.. _1737: https://github.com/giampaolo/psutil/issues/1737
.. _1738: https://github.com/giampaolo/psutil/issues/1738
.. _1739: https://github.com/giampaolo/psutil/issues/1739
.. _1740: https://github.com/giampaolo/psutil/issues/1740
.. _1741: https://github.com/giampaolo/psutil/issues/1741
.. _1742: https://github.com/giampaolo/psutil/issues/1742
.. _1743: https://github.com/giampaolo/psutil/issues/1743
.. _1744: https://github.com/giampaolo/psutil/issues/1744
.. _1745: https://github.com/giampaolo/psutil/issues/1745
.. _1746: https://github.com/giampaolo/psutil/issues/1746
.. _1747: https://github.com/giampaolo/psutil/issues/1747
.. _1748: https://github.com/giampaolo/psutil/issues/1748
.. _1749: https://github.com/giampaolo/psutil/issues/1749
.. _1750: https://github.com/giampaolo/psutil/issues/1750
.. _1751: https://github.com/giampaolo/psutil/issues/1751
.. _1752: https://github.com/giampaolo/psutil/issues/1752
.. _1753: https://github.com/giampaolo/psutil/issues/1753
.. _1754: https://github.com/giampaolo/psutil/issues/1754
.. _1755: https://github.com/giampaolo/psutil/issues/1755
.. _1756: https://github.com/giampaolo/psutil/issues/1756
.. _1757: https://github.com/giampaolo/psutil/issues/1757
.. _1758: https://github.com/giampaolo/psutil/issues/1758
.. _1759: https://github.com/giampaolo/psutil/issues/1759
.. _1760: https://github.com/giampaolo/psutil/issues/1760
.. _1761: https://github.com/giampaolo/psutil/issues/1761
.. _1762: https://github.com/giampaolo/psutil/issues/1762
.. _1763: https://github.com/giampaolo/psutil/issues/1763
.. _1764: https://github.com/giampaolo/psutil/issues/1764
.. _1765: https://github.com/giampaolo/psutil/issues/1765
.. _1766: https://github.com/giampaolo/psutil/issues/1766
.. _1767: https://github.com/giampaolo/psutil/issues/1767
.. _1768: https://github.com/giampaolo/psutil/issues/1768
.. _1769: https://github.com/giampaolo/psutil/issues/1769
.. _1770: https://github.com/giampaolo/psutil/issues/1770
.. _1771: https://github.com/giampaolo/psutil/issues/1771
.. _1772: https://github.com/giampaolo/psutil/issues/1772
.. _1773: https://github.com/giampaolo/psutil/issues/1773
.. _1774: https://github.com/giampaolo/psutil/issues/1774
.. _1775: https://github.com/giampaolo/psutil/issues/1775
.. _1776: https://github.com/giampaolo/psutil/issues/1776
.. _1777: https://github.com/giampaolo/psutil/issues/1777
.. _1778: https://github.com/giampaolo/psutil/issues/1778
.. _1779: https://github.com/giampaolo/psutil/issues/1779
.. _1780: https://github.com/giampaolo/psutil/issues/1780
.. _1781: https://github.com/giampaolo/psutil/issues/1781
.. _1782: https://github.com/giampaolo/psutil/issues/1782
.. _1783: https://github.com/giampaolo/psutil/issues/1783
.. _1784: https://github.com/giampaolo/psutil/issues/1784
.. _1785: https://github.com/giampaolo/psutil/issues/1785
.. _1786: https://github.com/giampaolo/psutil/issues/1786
.. _1787: https://github.com/giampaolo/psutil/issues/1787
.. _1788: https://github.com/giampaolo/psutil/issues/1788
.. _1789: https://github.com/giampaolo/psutil/issues/1789
.. _1790: https://github.com/giampaolo/psutil/issues/1790
.. _1791: https://github.com/giampaolo/psutil/issues/1791
.. _1792: https://github.com/giampaolo/psutil/issues/1792
.. _1793: https://github.com/giampaolo/psutil/issues/1793
.. _1794: https://github.com/giampaolo/psutil/issues/1794
.. _1795: https://github.com/giampaolo/psutil/issues/1795
.. _1796: https://github.com/giampaolo/psutil/issues/1796
.. _1797: https://github.com/giampaolo/psutil/issues/1797
.. _1798: https://github.com/giampaolo/psutil/issues/1798
.. _1799: https://github.com/giampaolo/psutil/issues/1799
.. _1800: https://github.com/giampaolo/psutil/issues/1800
.. _1801: https://github.com/giampaolo/psutil/issues/1801
.. _1802: https://github.com/giampaolo/psutil/issues/1802
.. _1803: https://github.com/giampaolo/psutil/issues/1803
.. _1804: https://github.com/giampaolo/psutil/issues/1804
.. _1805: https://github.com/giampaolo/psutil/issues/1805
.. _1806: https://github.com/giampaolo/psutil/issues/1806
.. _1807: https://github.com/giampaolo/psutil/issues/1807
.. _1808: https://github.com/giampaolo/psutil/issues/1808
.. _1809: https://github.com/giampaolo/psutil/issues/1809
.. _1810: https://github.com/giampaolo/psutil/issues/1810
.. _1811: https://github.com/giampaolo/psutil/issues/1811
.. _1812: https://github.com/giampaolo/psutil/issues/1812
.. _1813: https://github.com/giampaolo/psutil/issues/1813
.. _1814: https://github.com/giampaolo/psutil/issues/1814
.. _1815: https://github.com/giampaolo/psutil/issues/1815
.. _1816: https://github.com/giampaolo/psutil/issues/1816
.. _1817: https://github.com/giampaolo/psutil/issues/1817
.. _1818: https://github.com/giampaolo/psutil/issues/1818
.. _1819: https://github.com/giampaolo/psutil/issues/1819
.. _1820: https://github.com/giampaolo/psutil/issues/1820
.. _1821: https://github.com/giampaolo/psutil/issues/1821
.. _1822: https://github.com/giampaolo/psutil/issues/1822
.. _1823: https://github.com/giampaolo/psutil/issues/1823
.. _1824: https://github.com/giampaolo/psutil/issues/1824
.. _1825: https://github.com/giampaolo/psutil/issues/1825
.. _1826: https://github.com/giampaolo/psutil/issues/1826
.. _1827: https://github.com/giampaolo/psutil/issues/1827
.. _1828: https://github.com/giampaolo/psutil/issues/1828
.. _1829: https://github.com/giampaolo/psutil/issues/1829
.. _1830: https://github.com/giampaolo/psutil/issues/1830
.. _1831: https://github.com/giampaolo/psutil/issues/1831
.. _1832: https://github.com/giampaolo/psutil/issues/1832
.. _1833: https://github.com/giampaolo/psutil/issues/1833
.. _1834: https://github.com/giampaolo/psutil/issues/1834
.. _1835: https://github.com/giampaolo/psutil/issues/1835
.. _1836: https://github.com/giampaolo/psutil/issues/1836
.. _1837: https://github.com/giampaolo/psutil/issues/1837
.. _1838: https://github.com/giampaolo/psutil/issues/1838
.. _1839: https://github.com/giampaolo/psutil/issues/1839
.. _1840: https://github.com/giampaolo/psutil/issues/1840
.. _1841: https://github.com/giampaolo/psutil/issues/1841
.. _1842: https://github.com/giampaolo/psutil/issues/1842
.. _1843: https://github.com/giampaolo/psutil/issues/1843
.. _1844: https://github.com/giampaolo/psutil/issues/1844
.. _1845: https://github.com/giampaolo/psutil/issues/1845
.. _1846: https://github.com/giampaolo/psutil/issues/1846
.. _1847: https://github.com/giampaolo/psutil/issues/1847
.. _1848: https://github.com/giampaolo/psutil/issues/1848
.. _1849: https://github.com/giampaolo/psutil/issues/1849
.. _1850: https://github.com/giampaolo/psutil/issues/1850
.. _1851: https://github.com/giampaolo/psutil/issues/1851
.. _1852: https://github.com/giampaolo/psutil/issues/1852
.. _1853: https://github.com/giampaolo/psutil/issues/1853
.. _1854: https://github.com/giampaolo/psutil/issues/1854
.. _1855: https://github.com/giampaolo/psutil/issues/1855
.. _1856: https://github.com/giampaolo/psutil/issues/1856
.. _1857: https://github.com/giampaolo/psutil/issues/1857
.. _1858: https://github.com/giampaolo/psutil/issues/1858
.. _1859: https://github.com/giampaolo/psutil/issues/1859
.. _1860: https://github.com/giampaolo/psutil/issues/1860
.. _1861: https://github.com/giampaolo/psutil/issues/1861
.. _1862: https://github.com/giampaolo/psutil/issues/1862
.. _1863: https://github.com/giampaolo/psutil/issues/1863
.. _1864: https://github.com/giampaolo/psutil/issues/1864
.. _1865: https://github.com/giampaolo/psutil/issues/1865
.. _1866: https://github.com/giampaolo/psutil/issues/1866
.. _1867: https://github.com/giampaolo/psutil/issues/1867
.. _1868: https://github.com/giampaolo/psutil/issues/1868
.. _1869: https://github.com/giampaolo/psutil/issues/1869
.. _1870: https://github.com/giampaolo/psutil/issues/1870
.. _1871: https://github.com/giampaolo/psutil/issues/1871
.. _1872: https://github.com/giampaolo/psutil/issues/1872
.. _1873: https://github.com/giampaolo/psutil/issues/1873
.. _1874: https://github.com/giampaolo/psutil/issues/1874
.. _1875: https://github.com/giampaolo/psutil/issues/1875
.. _1876: https://github.com/giampaolo/psutil/issues/1876
.. _1877: https://github.com/giampaolo/psutil/issues/1877
.. _1878: https://github.com/giampaolo/psutil/issues/1878
.. _1879: https://github.com/giampaolo/psutil/issues/1879
.. _1880: https://github.com/giampaolo/psutil/issues/1880
.. _1881: https://github.com/giampaolo/psutil/issues/1881
.. _1882: https://github.com/giampaolo/psutil/issues/1882
.. _1883: https://github.com/giampaolo/psutil/issues/1883
.. _1884: https://github.com/giampaolo/psutil/issues/1884
.. _1885: https://github.com/giampaolo/psutil/issues/1885
.. _1886: https://github.com/giampaolo/psutil/issues/1886
.. _1887: https://github.com/giampaolo/psutil/issues/1887
.. _1888: https://github.com/giampaolo/psutil/issues/1888
.. _1889: https://github.com/giampaolo/psutil/issues/1889
.. _1890: https://github.com/giampaolo/psutil/issues/1890
.. _1891: https://github.com/giampaolo/psutil/issues/1891
.. _1892: https://github.com/giampaolo/psutil/issues/1892
.. _1893: https://github.com/giampaolo/psutil/issues/1893
.. _1894: https://github.com/giampaolo/psutil/issues/1894
.. _1895: https://github.com/giampaolo/psutil/issues/1895
.. _1896: https://github.com/giampaolo/psutil/issues/1896
.. _1897: https://github.com/giampaolo/psutil/issues/1897
.. _1898: https://github.com/giampaolo/psutil/issues/1898
.. _1899: https://github.com/giampaolo/psutil/issues/1899
.. _1900: https://github.com/giampaolo/psutil/issues/1900
.. _1901: https://github.com/giampaolo/psutil/issues/1901
.. _1902: https://github.com/giampaolo/psutil/issues/1902
.. _1903: https://github.com/giampaolo/psutil/issues/1903
.. _1904: https://github.com/giampaolo/psutil/issues/1904
.. _1905: https://github.com/giampaolo/psutil/issues/1905
.. _1906: https://github.com/giampaolo/psutil/issues/1906
.. _1907: https://github.com/giampaolo/psutil/issues/1907
.. _1908: https://github.com/giampaolo/psutil/issues/1908
.. _1909: https://github.com/giampaolo/psutil/issues/1909
.. _1910: https://github.com/giampaolo/psutil/issues/1910
.. _1911: https://github.com/giampaolo/psutil/issues/1911
.. _1912: https://github.com/giampaolo/psutil/issues/1912
.. _1913: https://github.com/giampaolo/psutil/issues/1913
.. _1914: https://github.com/giampaolo/psutil/issues/1914
.. _1915: https://github.com/giampaolo/psutil/issues/1915
.. _1916: https://github.com/giampaolo/psutil/issues/1916
.. _1917: https://github.com/giampaolo/psutil/issues/1917
.. _1918: https://github.com/giampaolo/psutil/issues/1918
.. _1919: https://github.com/giampaolo/psutil/issues/1919
.. _1920: https://github.com/giampaolo/psutil/issues/1920
.. _1921: https://github.com/giampaolo/psutil/issues/1921
.. _1922: https://github.com/giampaolo/psutil/issues/1922
.. _1923: https://github.com/giampaolo/psutil/issues/1923
.. _1924: https://github.com/giampaolo/psutil/issues/1924
.. _1925: https://github.com/giampaolo/psutil/issues/1925
.. _1926: https://github.com/giampaolo/psutil/issues/1926
.. _1927: https://github.com/giampaolo/psutil/issues/1927
.. _1928: https://github.com/giampaolo/psutil/issues/1928
.. _1929: https://github.com/giampaolo/psutil/issues/1929
.. _1930: https://github.com/giampaolo/psutil/issues/1930
.. _1931: https://github.com/giampaolo/psutil/issues/1931
.. _1932: https://github.com/giampaolo/psutil/issues/1932
.. _1933: https://github.com/giampaolo/psutil/issues/1933
.. _1934: https://github.com/giampaolo/psutil/issues/1934
.. _1935: https://github.com/giampaolo/psutil/issues/1935
.. _1936: https://github.com/giampaolo/psutil/issues/1936
.. _1937: https://github.com/giampaolo/psutil/issues/1937
.. _1938: https://github.com/giampaolo/psutil/issues/1938
.. _1939: https://github.com/giampaolo/psutil/issues/1939
.. _1940: https://github.com/giampaolo/psutil/issues/1940
.. _1941: https://github.com/giampaolo/psutil/issues/1941
.. _1942: https://github.com/giampaolo/psutil/issues/1942
.. _1943: https://github.com/giampaolo/psutil/issues/1943
.. _1944: https://github.com/giampaolo/psutil/issues/1944
.. _1945: https://github.com/giampaolo/psutil/issues/1945
.. _1946: https://github.com/giampaolo/psutil/issues/1946
.. _1947: https://github.com/giampaolo/psutil/issues/1947
.. _1948: https://github.com/giampaolo/psutil/issues/1948
.. _1949: https://github.com/giampaolo/psutil/issues/1949
.. _1950: https://github.com/giampaolo/psutil/issues/1950
.. _1951: https://github.com/giampaolo/psutil/issues/1951
.. _1952: https://github.com/giampaolo/psutil/issues/1952
.. _1953: https://github.com/giampaolo/psutil/issues/1953
.. _1954: https://github.com/giampaolo/psutil/issues/1954
.. _1955: https://github.com/giampaolo/psutil/issues/1955
.. _1956: https://github.com/giampaolo/psutil/issues/1956
.. _1957: https://github.com/giampaolo/psutil/issues/1957
.. _1958: https://github.com/giampaolo/psutil/issues/1958
.. _1959: https://github.com/giampaolo/psutil/issues/1959
.. _1960: https://github.com/giampaolo/psutil/issues/1960
.. _1961: https://github.com/giampaolo/psutil/issues/1961
.. _1962: https://github.com/giampaolo/psutil/issues/1962
.. _1963: https://github.com/giampaolo/psutil/issues/1963
.. _1964: https://github.com/giampaolo/psutil/issues/1964
.. _1965: https://github.com/giampaolo/psutil/issues/1965
.. _1966: https://github.com/giampaolo/psutil/issues/1966
.. _1967: https://github.com/giampaolo/psutil/issues/1967
.. _1968: https://github.com/giampaolo/psutil/issues/1968
.. _1969: https://github.com/giampaolo/psutil/issues/1969
.. _1970: https://github.com/giampaolo/psutil/issues/1970
.. _1971: https://github.com/giampaolo/psutil/issues/1971
.. _1972: https://github.com/giampaolo/psutil/issues/1972
.. _1973: https://github.com/giampaolo/psutil/issues/1973
.. _1974: https://github.com/giampaolo/psutil/issues/1974
.. _1975: https://github.com/giampaolo/psutil/issues/1975
.. _1976: https://github.com/giampaolo/psutil/issues/1976
.. _1977: https://github.com/giampaolo/psutil/issues/1977
.. _1978: https://github.com/giampaolo/psutil/issues/1978
.. _1979: https://github.com/giampaolo/psutil/issues/1979
.. _1980: https://github.com/giampaolo/psutil/issues/1980
.. _1981: https://github.com/giampaolo/psutil/issues/1981
.. _1982: https://github.com/giampaolo/psutil/issues/1982
.. _1983: https://github.com/giampaolo/psutil/issues/1983
.. _1984: https://github.com/giampaolo/psutil/issues/1984
.. _1985: https://github.com/giampaolo/psutil/issues/1985
.. _1986: https://github.com/giampaolo/psutil/issues/1986
.. _1987: https://github.com/giampaolo/psutil/issues/1987
.. _1988: https://github.com/giampaolo/psutil/issues/1988
.. _1989: https://github.com/giampaolo/psutil/issues/1989
.. _1990: https://github.com/giampaolo/psutil/issues/1990
.. _1991: https://github.com/giampaolo/psutil/issues/1991
.. _1992: https://github.com/giampaolo/psutil/issues/1992
.. _1993: https://github.com/giampaolo/psutil/issues/1993
.. _1994: https://github.com/giampaolo/psutil/issues/1994
.. _1995: https://github.com/giampaolo/psutil/issues/1995
.. _1996: https://github.com/giampaolo/psutil/issues/1996
.. _1997: https://github.com/giampaolo/psutil/issues/1997
.. _1998: https://github.com/giampaolo/psutil/issues/1998
.. _1999: https://github.com/giampaolo/psutil/issues/1999
.. _2000: https://github.com/giampaolo/psutil/issues/2000
