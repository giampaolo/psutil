Bug tracker at https://github.com/giampaolo/psutil/issues

3.1.1 - 2015-07-15
==================

**Bug fixes**

- #645: [Linux] psutil.cpu_times_percent() may produce negative results.
- #656: 'from psutil import *' does not work.


3.1.0 - 2015-07-15
==================

**Enhancements**

- #534: [Linux] disk_partitions() added support for ZFS filesystems.
- #646: continuous tests integration for Windows with
  https://ci.appveyor.com/project/giampaolo/psutil.
- #647: new dev guide:
  https://github.com/giampaolo/psutil/blob/master/DEVGUIDE.rst
- #651: continuous code quality test integration with
  https://scrutinizer-ci.com/g/giampaolo/psutil/

**Bug fixes**

- #340: [Windows] Process.open_files() no longer hangs. Instead it uses a
  thred which times out and skips the file handle in case it's taking too long
  to be retrieved.  (patch by Jeff Tang, PR #597)
- #627: [Windows] Process.name() no longer raises AccessDenied for pids owned
  by another user.
- #636: [Windows] Process.memory_info() raise AccessDenied.
- #637: [UNIX] raise exception if trying to send signal to Process PID 0 as it
  will affect os.getpid()'s process group instead of PID 0.
- #639: [Linux] Process.cmdline() can be truncated.
- #640: [Linux] *connections functions may swallow errors and return an
  incomplete list of connnections.
- #642: repr() of exceptions is incorrect.
- #653: [Windows] Add inet_ntop function for Windows XP to support IPv6.
- #641: [Windows] Replace deprecated string functions with safe equivalents.


3.0.1 - 2015-06-18
==================

**Bug fixes**

- #632: [Linux] better error message if cannot parse process UNIX connections.
- #634: [Linux] Proces.cmdline() does not include empty string arguments.
- #635: [UNIX] crash on module import if 'enum' package is installed on python
  < 3.4.


3.0.0 - 2015-06-13
==================

**Enhancements**

- #250: new psutil.net_if_stats() returning NIC statistics (isup, duplex,
  speed, MTU).
- #376: new psutil.net_if_addrs() returning all NIC addresses a-la ifconfig.
- #469: on Python >= 3.4 ``IOPRIO_CLASS_*`` and ``*_PRIORITY_CLASS`` constants
  returned by psutil.Process' ionice() and nice() methods are enums instead of
  plain integers.
- #581: add .gitignore. (patch by Gabi Davar)
- #582: connection constants returned by psutil.net_connections() and
  psutil.Process.connections() were turned from int to enums on Python > 3.4.
- #587: Move native extension into the package.
- #589: Process.cpu_affinity() accepts any kind of iterable (set, tuple, ...),
  not only lists.
- #594: all deprecated APIs were removed.
- #599: [Windows] process name() can now be determined for all processes even
  when running as a limited user.
- #602: pre-commit GIT hook.
- #629: enhanced support for py.test and nose test discovery and tests run.
- #616: [Windows] Add inet_ntop function for Windows XP.

**Bug fixes**

- #428: [all UNIXes except Linux] correct handling of zombie processes;
  introduced new ZombieProcess exception class.
- #512: [BSD] fix segfault in net_connections().
- #555: [Linux] psutil.users() correctly handles ":0" as an alias for
  "localhost"
- #579: [Windows] Fixed open_files() for PID>64K.
- #579: [Windows] fixed many compiler warnings.
- #585: [FreeBSD] net_connections() may raise KeyError.
- #586: [FreeBSD] cpu_affinity() segfaults on set in case an invalid CPU
  number is provided.
- #593: [FreeBSD] Process().memory_maps() segfaults.
- #606: Process.parent() may swallow NoSuchProcess exceptions.
- #611: [SunOS] net_io_counters has send and received swapped
- #614: [Linux]: cpu_count(logical=False) return the number of physical CPUs
  instead of physical cores.
- #618: [SunOS] swap tests fail on Solaris when run as normal user
- #628: [Linux] Process.name() truncates process name in case it contains
  spaces or parentheses.


2.2.1 - 2015-02-02
==================

**Bug fixes**

- #496: [Linux] fix "ValueError: ambiguos inode with multiple PIDs references"
  (patch by Bruno Binet)


2.2.0 - 2015-01-06
==================

**Enhancements**

- #521: drop support for Python 2.4 and 2.5.
- #553: new examples/pstree.py script.
- #564: C extension version mismatch in case the user messed up with psutil
  installation or with sys.path is now detected at import time.
- #568: New examples/pidof.py script.
- #569: [FreeBSD] add support for process CPU affinity.

**Bug fixes**

- #496: [Solaris] can't import psutil.
- #547: [UNIX] Process.username() may raise KeyError if UID can't be resolved.
- #551: [Windows] get rid of the unicode hack for net_io_counters() NIC names.
- #556: [Linux] lots of file handles were left open.
- #561: [Linux] net_connections() might skip some legitimate UNIX sockets.
  (patch by spacewander)
- #565: [Windows] use proper encoding for psutil.Process.username() and
  psutil.users(). (patch by Sylvain Mouquet)
- #567: [Linux] in the alternative implementation of CPU affinity PyList_Append
  and Py_BuildValue return values are not checked.
- #569: [FreeBSD] fix memory leak in psutil.cpu_count(logical=False).
- #571: [Linux] Process.open_files() might swallow AccessDenied exceptions and
  return an incomplete list of open files.


2.1.3 - 2014-09-26
==================

- #536: [Linux]: fix "undefined symbol: CPU_ALLOC" compilation error.


2.1.2 - 2014-09-21
==================

**Enhancements**

- #407: project moved from Google Code to Github; code moved from Mercurial
  to Git.
- #492: use tox to run tests on multiple python versions.  (patch by msabramo)
- #505: [Windows] distribution as wheel packages.
- #511: new examples/ps.py sample code.

**Bug fixes**

- #340: [Windows] Process.get_open_files() no longer hangs.  (patch by
  Jeff Tang)
- #501: [Windows] disk_io_counters() may return negative values.
- #503: [Linux] in rare conditions Process exe(), open_files() and
  connections() methods can raise OSError(ESRCH) instead of NoSuchProcess.
- #504: [Linux] can't build RPM packages via setup.py
- #506: [Linux] python 2.4 support was broken.
- #522: [Linux] Process.cpu_affinity() might return EINVAL.  (patch by David
  Daeschler)
- #529: [Windows] Process.exe() may raise unhandled WindowsError exception
  for PIDs 0 and 4.  (patch by Jeff Tang)
- #530: [Linux] psutil.disk_io_counters() may crash on old Linux distros
  (< 2.6.5)  (patch by Yaolong Huang)
- #533: [Linux] Process.memory_maps() may raise TypeError on old Linux distros.


2.1.1 - 2014-04-30
==================

**Bug fixes**

- #446: [Windows] fix encoding error when using net_io_counters() on Python 3.
  (patch by Szigeti Gabor Niif)
- #460: [Windows] net_io_counters() wraps after 4G.
- #491: [Linux] psutil.net_connections() exceptions. (patch by Alexander Grothe)


2.1.0 - 2014-04-08
==================

**Enhancements**

- #387: system-wide open connections a-la netstat.

**Bug fixes**

- #421: [Solaris] psutil does not compile on SunOS 5.10 (patch by Naveed
  Roudsari)
- #489: [Linux] psutil.disk_partitions() return an empty list.


2.0.0 - 2014-03-10
==================

**Enhancements**

- #424: [Windows] installer for Python 3.X 64 bit.
- #427: number of logical and physical CPUs (psutil.cpu_count()).
- #447: psutil.wait_procs() timeout parameter is now optional.
- #452: make Process instances hashable and usable with set()s.
- #453: tests on Python < 2.7 require unittest2 module.
- #459: add a make file for running tests and other repetitive tasks (also
  on Windows).
- #463: make timeout parameter of cpu_percent* functions default to 0.0 'cause
  it's a common trap to introduce slowdowns.
- #468: move documentation to readthedocs.com.
- #477: process cpu_percent() is about 30% faster.  (suggested by crusaderky)
- #478: [Linux] almost all APIs are about 30% faster on Python 3.X.
- #479: long deprecated psutil.error module is gone; exception classes now
  live in "psutil" namespace only.

**Bug fixes**

- #193: psutil.Popen constructor can throw an exception if the spawned process
  terminates quickly.
- #340: [Windows] process get_open_files() no longer hangs.  (patch by
  jtang@vahna.net)
- #443: [Linux] fix a potential overflow issue for Process.set_cpu_affinity()
  on systems with more than 64 CPUs.
- #448: [Windows] get_children() and ppid() memory leak (patch by Ulrich
  Klank).
- #457: [POSIX] pid_exists() always returns True for PID 0.
- #461: namedtuples are not pickle-able.
- #466: [Linux] process exe improper null bytes handling.  (patch by
  Gautam Singh)
- #470: wait_procs() might not wait.  (patch by crusaderky)
- #471: [Windows] process exe improper unicode handling. (patch by
  alex@mroja.net)
- #473: psutil.Popen.wait() does not set returncode attribute.
- #474: [Windows] Process.cpu_percent() is no longer capped at 100%.
- #476: [Linux] encoding error for process name and cmdline.

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


1.2.1 - 2013-11-25
==================

**Bug fixes**

- #348: [Windows XP] fixed "ImportError: DLL load failed" occurring on module
  import.
- #425: [Solaris] crash on import due to failure at determining BOOT_TIME.
- #443: [Linux] can't set CPU affinity on systems with more than 64 cores.


1.2.0 - 2013-11-20
==================

**Enhancements**

- #439: assume os.getpid() if no argument is passed to psutil.Process
  constructor.
- #440: new psutil.wait_procs() utility function which waits for multiple
  processes to terminate.

**Bug fixes**

- #348: [Windows XP/Vista] fix "ImportError: DLL load failed" occurring on
  module import.


1.1.3 - 2013-11-07
==================

**Bug fixes**

- #442: [Linux] psutil won't compile on certain version of Linux because of
  missing prlimit(2) syscall.


1.1.2 - 2013-10-22
==================

**Bug fixes**

- #442: [Linux] psutil won't compile on Debian 6.0 because of missing
  prlimit(2) syscall.


1.1.1 - 2013-10-08
==================

**Bug fixes**

- #442: [Linux] psutil won't compile on kernels < 2.6.36 due to missing
  prlimit(2) syscall.


1.1.0 - 2013-09-28
==================

**Enhancements**

- #410: host tar.gz and windows binary files are on PYPI.
- #412: [Linux] get/set process resource limits.
- #415: [Windows] Process.get_children() is an order of magnitude faster.
- #426: [Windows] Process.name is an order of magnitude faster.
- #431: [UNIX] Process.name is slightly faster because it unnecessarily
  retrieved also process cmdline.

**Bug fixes**

- #391: [Windows] psutil.cpu_times_percent() returns negative percentages.
- #408: STATUS_* and CONN_* constants don't properly serialize on JSON.
- #411: [Windows] examples/disk_usage.py may pop-up a GUI error.
- #413: [Windows] Process.get_memory_info() leaks memory.
- #414: [Windows] Process.exe on Windows XP may raise ERROR_INVALID_PARAMETER.
- #416: psutil.disk_usage() doesn't work well with unicode path names.
- #430: [Linux] process IO counters report wrong number of r/w syscalls.
- #435: [Linux] psutil.net_io_counters() might report erreneous NIC names.
- #436: [Linux] psutil.net_io_counters() reports a wrong 'dropin' value.

**API changes**

- #408: turn STATUS_* and CONN_* constants into plain Python strings.


1.0.1 - 2013-07-12
==================

**Bug fixes**

- #405: network_io_counters(pernic=True) no longer works as intended in 1.0.0.


1.0.0 - 2013-07-10
==================

**Enhancements**

- #18:  Solaris support (yay!)  (thanks Justin Venus)
- #367: Process.get_connections() 'status' strings are now constants.
- #380: test suite exits with non-zero on failure.  (patch by floppymaster)
- #391: introduce unittest2 facilities and provide workarounds if unittest2
  is not installed (python < 2.7).

**Bug fixes**

- #374: [Windows] negative memory usage reported if process uses a lot of
  memory.
- #379: [Linux] Process.get_memory_maps() may raise ValueError.
- #394: [OSX] Mapped memory regions report incorrect file name.
- #404: [Linux] sched_*affinity() are implicitly declared. (patch by Arfrever)

**API changes**

- Process.get_connections() 'status' field is no longer a string but a
  constant object (psutil.CONN_*).
- Process.get_connections() 'local_address' and 'remote_address' fields
  renamed to 'laddr' and 'raddr'.
- psutil.network_io_counters() renamed to psutil.net_io_counters().


0.7.1 - 2013-05-03
==================

**Bug fixes**

- #325: [BSD] psutil.virtual_memory() can raise SystemError.
  (patch by Jan Beich)
- #370: [BSD] Process.get_connections() requires root.  (patch by John Baldwin)
- #372: [BSD] different process methods raise NoSuchProcess instead of
  AccessDenied.


0.7.0 - 2013-04-12
==================

**Enhancements**

- #233: code migrated to Mercurial (yay!)
- #246: psutil.error module is deprecated and scheduled for removal.
- #328: [Windows] process IO nice/priority support.
- #359: psutil.get_boot_time()
- #361: [Linux] psutil.cpu_times() now includes new 'steal', 'guest' and
  'guest_nice' fields available on recent Linux kernels.
  Also, psutil.cpu_percent() is more accurate.
- #362: cpu_times_percent() (per-CPU-time utilization as a percentage)

**Bug fixes**

- #234: [Windows] disk_io_counters() fails to list certain disks.
- #264: [Windows] use of psutil.disk_partitions() may cause a message box to
  appear.
- #313: [Linux] psutil.virtual_memory() and psutil.swap_memory() can crash on
  certain exotic Linux flavors having an incomplete /proc interface.
  If that's the case we now set the unretrievable stats to 0 and raise a
  RuntimeWarning.
- #315: [OSX] fix some compilation warnings.
- #317: [Windows] cannot set process CPU affinity above 31 cores.
- #319: [Linux] process get_memory_maps() raises KeyError 'Anonymous' on Debian
  squeeze.
- #321: [UNIX] Process.ppid property is no longer cached as the kernel may set
  the ppid to 1 in case of a zombie process.
- #323: [OSX] disk_io_counters()'s read_time and write_time parameters were
  reporting microseconds not milliseconds.  (patch by Gregory Szorc)
- #331: Process cmdline is no longer cached after first acces as it may change.
- #333: [OSX] Leak of Mach ports on OS X (patch by rsesek@google.com)
- #337: [Linux] process methods not working because of a poor /proc
  implementation will raise NotImplementedError rather than RuntimeError
  and Process.as_dict() will not blow up.  (patch by Curtin1060)
- #338: [Linux] disk_io_counters() fails to find some disks.
- #339: [FreeBSD] get_pid_list() can allocate all the memory on system.
- #341: [Linux] psutil might crash on import due to error in retrieving system
  terminals map.
- #344: [FreeBSD] swap_memory() might return incorrect results due to
  kvm_open(3) not being called. (patch by Jean Sebastien)
- #338: [Linux] disk_io_counters() fails to find some disks.
- #351: [Windows] if psutil is compiled with mingw32 (provided installers for
  py2.4 and py2.5 are) disk_io_counters() will fail. (Patch by m.malycha)
- #353: [OSX] get_users() returns an empty list on OSX 10.8.
- #356: Process.parent now checks whether parent PID has been reused in which
  case returns None.
- #365: Process.set_nice() should check PID has not been reused by another
  process.
- #366: [FreeBSD] get_memory_maps(), get_num_fds(), get_open_files() and
  getcwd() Process methods raise RuntimeError instead of AccessDenied.

**API changes**

- Process.cmdline property is no longer cached after first access.
- Process.ppid property is no longer cached after first access.
- [Linux] Process methods not working because of a poor /proc implementation
  will raise NotImplementedError instead of RuntimeError.
- psutil.error module is deprecated and scheduled for removal.


0.6.1 - 2012-08-16
==================

**Enhancements**

- #316: process cmdline property now makes a better job at guessing the process
  executable from the cmdline.

**Bug fixes**

- #316: process exe was resolved in case it was a symlink.
- #318: python 2.4 compatibility was broken.

**API changes**

- process exe can now return an empty string instead of raising AccessDenied.
- process exe is no longer resolved in case it's a symlink.


0.6.0 - 2012-08-13
==================

**Enhancements**

- #216: [POSIX] get_connections() UNIX sockets support.
- #220: [FreeBSD] get_connections() has been rewritten in C and no longer
  requires lsof.
- #222: [OSX] add support for process cwd.
- #261: process extended memory info.
- #295: [OSX] process executable path is now determined by asking the OS
  instead of being guessed from process cmdline.
- #297: [OSX] the Process methods below were always raising AccessDenied for
  any process except the current one. Now this is no longer true. Also
  they are 2.5x faster.
  - name
  - get_memory_info()
  - get_memory_percent()
  - get_cpu_times()
  - get_cpu_percent()
  - get_num_threads()
- #300: examples/pmap.py script.
- #301: process_iter() now yields processes sorted by their PIDs.
- #302: process number of voluntary and involuntary context switches.
- #303: [Windows] the Process methods below were always raising AccessDenied
  for any process not owned by current user. Now this is no longer true:
  - create_time
  - get_cpu_times()
  - get_cpu_percent()
  - get_memory_info()
  - get_memory_percent()
  - get_num_handles()
  - get_io_counters()
- #305: add examples/netstat.py script.
- #311: system memory functions has been refactorized and rewritten and now
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
  - cached (BSD, OSX)
  - wired (OSX, BSD)
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
- #312: psutil.network_io_counters() namedtuple includes 4 new fields:
  errin, errout dropin and dropout, reflecting the number of packets
  dropped and with errors.

**Bugfixes**

- #298: [OSX and BSD] memory leak in get_num_fds().
- #299: potential memory leak every time PyList_New(0) is used.
- #303: [Windows] potential heap corruption in get_num_threads() and
  get_status() Process methods.
- #305: [FreeBSD] psutil can't compile on FreeBSD 9 due to removal of utmp.h.
- #306: at C level, errors are not checked when invoking Py* functions which
  create or manipulate Python objects leading to potential memory related
  errors and/or segmentation faults.
- #307: [FreeBSD] values returned by psutil.network_io_counters() are wrong.
- #308: [BSD / Windows] psutil.virtmem_usage() wasn't actually returning
  information about swap memory usage as it was supposed to do. It does
  now.
- #309: get_open_files() might not return files which can not be accessed
  due to limited permissions. AccessDenied is now raised instead.

**API changes**

- psutil.phymem_usage() is deprecated       (use psutil.virtual_memory())
- psutil.virtmem_usage() is deprecated      (use psutil.swap_memory())
- psutil.phymem_buffers() on Linux is deprecated  (use psutil.virtual_memory())
- psutil.cached_phymem() on Linux is deprecated   (use psutil.virtual_memory())
- [Windows and BSD] psutil.virtmem_usage() now returns information about swap
  memory instead of virtual memory.


0.5.1 - 2012-06-29
==================

**Enhancements**

- #293: [Windows] process executable path is now determined by asking the OS
  instead of being guessed from process cmdline.

**Bugfixes**

- #292: [Linux] race condition in process files/threads/connections.
- #294: [Windows] Process CPU affinity is only able to set CPU #0.


0.5.0 - 2012-06-27
==================

**Enhancements**

- #195: [Windows] number of handles opened by process.
- #209: psutil.disk_partitions() now provides also mount options.
- #229: list users currently connected on the system (psutil.get_users()).
- #238: [Linux, Windows] process CPU affinity (get and set).
- #242: Process.get_children(recursive=True): return all process
  descendants.
- #245: [POSIX] Process.wait() incrementally consumes less CPU cycles.
- #257: [Windows] removed Windows 2000 support.
- #258: [Linux] Process.get_memory_info() is now 0.5x faster.
- #260: process's mapped memory regions. (Windows patch by wj32.64, OSX patch
  by Jeremy Whitlock)
- #262: [Windows] psutil.disk_partitions() was slow due to inspecting the
  floppy disk drive also when "all" argument was False.
- #273: psutil.get_process_list() is deprecated.
- #274: psutil no longer requires 2to3 at installation time in order to work
  with Python 3.
- #278: new Process.as_dict() method.
- #281: ppid, name, exe, cmdline and create_time properties of Process class
  are now cached after being accessed.
- #282: psutil.STATUS_* constants can now be compared by using their string
  representation.
- #283: speedup Process.is_running() by caching its return value in case the
  process is terminated.
- #284: [POSIX] per-process number of opened file descriptors.
- #287: psutil.process_iter() now caches Process instances between calls.
- #290: Process.nice property is deprecated in favor of new get_nice() and
  set_nice() methods.

**Bugfixes**

- #193: psutil.Popen constructor can throw an exception if the spawned process
  terminates quickly.
- #240: [OSX] incorrect use of free() for Process.get_connections().
- #244: [POSIX] Process.wait() can hog CPU resources if called against a
  process which is not our children.
- #248: [Linux] psutil.network_io_counters() might return erroneous NIC names.
- #252: [Windows] process getcwd() erroneously raise NoSuchProcess for
  processes owned by another user.  It now raises AccessDenied instead.
- #266: [Windows] psutil.get_pid_list() only shows 1024 processes.
  (patch by Amoser)
- #267: [OSX] Process.get_connections() - an erroneous remote address was
  returned. (Patch by Amoser)
- #272: [Linux] Porcess.get_open_files() - potential race condition can lead to
  unexpected NoSuchProcess exception.  Also, we can get incorrect reports
  of not absolutized path names.
- #275: [Linux] Process.get_io_counters() erroneously raise NoSuchProcess on
  old Linux versions. Where not available it now raises
  NotImplementedError.
- #286: Process.is_running() doesn't actually check whether PID has been
  reused.
- #314: Process.get_children() can sometimes return non-children.

**API changes**

- Process.nice property is deprecated in favor of new get_nice() and set_nice()
  methods.
- psutil.get_process_list() is deprecated.
- ppid, name, exe, cmdline and create_time properties of Process class are now
  cached after being accessed, meaning NoSuchProcess will no longer be raised
  in case the process is gone in the meantime.
- psutil.STATUS_* constants can now be compared by using their string
  representation.


0.4.1 - 2011-12-14
==================

**Bugfixes**

- #228: some example scripts were not working with python 3.
- #230: [Windows / OSX] memory leak in Process.get_connections().
- #232: [Linux] psutil.phymem_usage() can report erroneous values which are
  different than "free" command.
- #236: [Windows] memory/handle leak in Process's get_memory_info(),
  suspend() and resume() methods.


0.4.0 - 2011-10-29
==================

**Enhancements**

- #150: network I/O counters. (OSX and Windows patch by Jeremy Whitlock)
- #154: [FreeBSD] add support for process getcwd()
- #157: [Windows] provide installer for Python 3.2 64-bit.
- #198: Process.wait(timeout=0) can now be used to make wait() return
  immediately.
- #206: disk I/O counters. (OSX and Windows patch by Jeremy Whitlock)
- #213: examples/iotop.py script.
- #217: Process.get_connections() now has a "kind" argument to filter
  for connections with different criteria.
- #221: [FreeBSD] Process.get_open_files has been rewritten in C and no longer
  relies on lsof.
- #223: examples/top.py script.
- #227: examples/nettop.py script.

**Bugfixes**

- #135: [OSX] psutil cannot create Process object.
- #144: [Linux] no longer support 0 special PID.
- #188: [Linux] psutil import error on Linux ARM architectures.
- #194: [POSIX] psutil.Process.get_cpu_percent() now reports a percentage over
  100 on multicore processors.
- #197: [Linux] Process.get_connections() is broken on platforms not
  supporting IPv6.
- #200: [Linux] psutil.NUM_CPUS not working on armel and sparc architectures
  and causing crash on module import.
- #201: [Linux] Process.get_connections() is broken on big-endian
  architectures.
- #211: Process instance can unexpectedly raise NoSuchProcess if tested for
  equality with another object.
- #218: [Linux] crash at import time on Debian 64-bit because of a missing
  line in /proc/meminfo.
- #226: [FreeBSD] crash at import time on FreeBSD 7 and minor.


0.3.0 - 2011-07-08
==================

**Enhancements**

- #125: system per-cpu percentage utilization and times.
- #163: per-process associated terminal (TTY).
- #171: added get_phymem() and get_virtmem() functions returning system
  memory information (total, used, free) and memory percent usage.
  total_* avail_* and used_* memory functions are deprecated.
- #172: disk usage statistics.
- #174: mounted disk partitions.
- #179: setuptools is now used in setup.py

**Bugfixes**

- #159: SetSeDebug() does not close handles or unset impersonation on return.
- #164: [Windows] wait function raises a TimeoutException when a process
  returns -1 .
- #165: process.status raises an unhandled exception.
- #166: get_memory_info() leaks handles hogging system resources.
- #168: psutil.cpu_percent() returns erroneous results when used in
  non-blocking mode.  (patch by Philip Roberts)
- #178: OSX - Process.get_threads() leaks memory
- #180: [Windows] Process's get_num_threads() and get_threads() methods can
  raise NoSuchProcess exception while process still exists.


0.2.1 - 2011-03-20
==================

**Enhancements**

- #64: per-process I/O counters.
- #116: per-process wait() (wait for process to terminate and return its exit
  code).
- #134: per-process get_threads() returning information (id, user and kernel
  times) about threads opened by process.
- #136: process executable path on FreeBSD is now determined by asking the
  kernel instead of guessing it from cmdline[0].
- #137: per-process real, effective and saved user and group ids.
- #140: system boot time.
- #142: per-process get and set niceness (priority).
- #143: per-process status.
- #147: per-process I/O nice (priority) - Linux only.
- #148: psutil.Popen class which tidies up subprocess.Popen and psutil.Process
  in a unique interface.
- #152: [OSX] get_process_open_files() implementation has been rewritten
  in C and no longer relies on lsof resulting in a 3x speedup.
- #153: [OSX] get_process_connection() implementation has been rewritten
  in C and no longer relies on lsof resulting in a 3x speedup.

**Bugfixes**

- #83:  process cmdline is empty on OSX 64-bit.
- #130: a race condition can cause IOError exception be raised on
  Linux if process disappears between open() and subsequent read() calls.
- #145: WindowsError was raised instead of psutil.AccessDenied when using
  process resume() or suspend() on Windows.
- #146: 'exe' property on Linux can raise TypeError if path contains NULL
  bytes.
- #151: exe and getcwd() for PID 0 on Linux return inconsistent data.

**API changes**

- Process "uid" and "gid" properties are deprecated in favor of "uids" and
  "gids" properties.


0.2.0 - 2010-11-13
==================

**Enhancements**

- #79: per-process open files.
- #88: total system physical cached memory.
- #88: total system physical memory buffers used by the kernel.
- #91: per-process send_signal() and terminate() methods.
- #95: NoSuchProcess and AccessDenied exception classes now provide "pid",
  "name" and "msg" attributes.
- #97: per-process children.
- #98: Process.get_cpu_times() and Process.get_memory_info now return
  a namedtuple instead of a tuple.
- #103: per-process opened TCP and UDP connections.
- #107: add support for Windows 64 bit. (patch by cjgohlke)
- #111: per-process executable name.
- #113: exception messages now include process name and pid.
- #114: process username Windows implementation has been rewritten in pure
  C and no longer uses WMI resulting in a big speedup. Also, pywin32 is no
  longer required as a third-party dependancy. (patch by wj32)
- #117: added support for Windows 2000.
- #123: psutil.cpu_percent() and psutil.Process.cpu_percent() accept a
  new 'interval' parameter.
- #129: per-process number of threads.

**Bugfixes**

- #80: fixed warnings when installing psutil with easy_install.
- #81: psutil fails to compile with Visual Studio.
- #94: suspend() raises OSError instead of AccessDenied.
- #86: psutil didn't compile against FreeBSD 6.x.
- #102: orphaned process handles obtained by using OpenProcess in C were
  left behind every time Process class was instantiated.
- #111: path and name Process properties report truncated or erroneous
  values on UNIX.
- #120: cpu_percent() always returning 100% on OS X.
- #112: uid and gid properties don't change if process changes effective
  user/group id at some point.
- #126: ppid, uid, gid, name, exe, cmdline and create_time properties are
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


0.1.3 - 2010-03-02
==================

**Enhancements**

- #14: per-process username
- #51: per-process current working directory (Windows and Linux only)
- #59: Process.is_running() is now 10 times faster
- #61: added supoprt for FreeBSD 64 bit
- #71: implemented suspend/resume process
- #75: python 3 support

**Bugfixes**

- #36: process cpu_times() and memory_info() functions succeeded also for dead
  processes while a NoSuchProcess exception is supposed to be raised.
- #48: incorrect size for mib array defined in getcmdargs for BSD
- #49: possible memory leak due to missing free() on error condition on
- #50: fixed getcmdargs() memory fragmentation on BSD
- #55: test_pid_4 was failing on Windows Vista
- #57: some unit tests were failing on systems where no swap memory is
  available
- #58: is_running() is now called before kill() to make sure we are going
  to kill the correct process.
- #73: virtual memory size reported on OS X includes shared library size
- #77: NoSuchProcess wasn't raised on Process.create_time if kill() was
  used first.


0.1.2 - 2009-05-06
==================

**Enhancements**

- #32: Per-process CPU user/kernel times
- #33: Process create time
- #34: Per-process CPU utilization percentage
- #38: Per-process memory usage (bytes)
- #41: Per-process memory utilization (percent)
- #39: System uptime
- #43: Total system virtual memory
- #46: Total system physical memory
- #44: Total system used/free virtual and physical memory

**Bugfixes**

- #36: [Windows] NoSuchProcess not raised when accessing timing methods.
- #40: test_get_cpu_times() failing on FreeBSD and OS X.
- #42: [Windows] get_memory_percent() raises AccessDenied.


0.1.1 - 2009-03-06
==================

**Enhancements**

- #4: FreeBSD support for all functions of psutil
- #9: Process.uid and Process.gid now retrieve process UID and GID.
- #11: Support for parent/ppid - Process.parent property returns a
  Process object representing the parent process, and Process.ppid returns
  the parent PID.
- #12 & 15:
  NoSuchProcess exception now raised when creating an object
  for a nonexistent process, or when retrieving information about a process
  that has gone away.
- #21: AccessDenied exception created for raising access denied errors
  from OSError or WindowsError on individual platforms.
- #26: psutil.process_iter() function to iterate over processes as
  Process objects with a generator.
- #?:  Process objects can now also be compared with == operator for equality
  (PID, name, command line are compared).

**Bugfixes**

- #16: [Windows] Special case for "System Idle Process" (PID 0) which
  otherwise would return an "invalid parameter" exception.
- #17: get_process_list() ignores NoSuchProcess and AccessDenied
  exceptions during building of the list.
- #22: [Windows] Process(0).kill() was failing with an unset exception.
- #23: Special case for pid_exists(0)
- #24: [Windows] Process(0).kill() now raises AccessDenied exception instead
  of WindowsError.
- #30: psutil.get_pid_list() was returning two instances of PID 0 on OSX and
  FreeBSD platforms.


0.1.0 - 2009-01-27
==================

- Initial release.
