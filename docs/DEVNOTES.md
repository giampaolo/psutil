A collection of ideas and notes about stuff to implement in future versions.

## Inconsistencies

(the "too late" section)

- `PROCFS_PATH` should have been `set_procfs_path()`.

- `virtual_memory()` should have been `memory_virtual()`.

- `swap_memory()` should have been `memory_swap()`.

- Named tuples are problematic. Positional unpacking of named tuples could be
  deprecated. Return frozen dataclasses (with a common base class) instead of
  `typing.NamedTuple`. The base class would keep `_fields`, `_asdict()` and
  `len()` for compat, but `__iter__` and `__getitem__` would emit
  DeprecationWarning. Main concern: `isinstance(x, tuple)` would break.

## Rejected ideas

- #550: threads per core
- #1667: `process_iter(new_only=True)`

## Features

- #2794: enrich `Process.wait()` return value with exit code enums.

- `net_if_addrs()` could return AF_BLUETOOTH interfaces. E.g.
  https://pypi.org/project/netifaces does this.

- Use `resource.getrusage()` to get current process CPU times (it has more
  precision).

- (UNIX) `Process.root()` (different from `cwd()`).

- (Linux) locked files via /proc/locks:
  https://www.centos.org/docs/5/html/5.2/Deployment_Guide/s2-proc-locks.html

- #269: NIC rx/tx queue. This should probably go into `net_if_stats()`. Figure
  out on what platforms this is supported. Linux: yes. Others?

- Asynchronous `psutil.Popen` (see http://bugs.python.org/issue1191964)

- (Windows) fall back on using WMIC for Process methods returning
  `AccessDenied`.

- #613: thread names; patch for macOS available at:
  https://code.google.com/p/plcrashreporter/issues/detail?id=65 Sample code:
  https://github.com/janmojzis/pstree/blob/master/proc_kvm.c

- `scripts/taskmgr-gui.py` (using tk).

- system-wide number of open file descriptors:
  - https://jira.hyperic.com/browse/SIGAR-30

- Number of system threads.
  - Windows:
    http://msdn.microsoft.com/en-us/library/windows/desktop/ms684824(v=vs.85).aspx

- `psutil.proc_tree()` something which obtains a `{pid:ppid, ...}` struct for
  all running processes in one shot. This can be factored out from
  `Process.children()` and exposed as a first class function. PROS: on Windows
  we can take advantage of `ppid_map()`, which is faster than iterating over
  all PIDs. CONS: `scripts/pstree.py` shows this can be easily done in the user
  code, so maybe it's not worth the addition.

- advanced cmdline interface exposing the whole API and providing different
  kind of outputs (e.g. pprinted, colorized, json).

- Linux: process cgroups (http://en.wikipedia.org/wiki/Cgroups). They look
  similar to `prlimit()` in terms of functionality but, uglier (they should
  allow limiting per-process network IO resources though, which is great).
  Needs further reading.

- Python 3.3. exposed different sched.h functions:
  http://docs.python.org/dev/whatsnew/3.3.html#os
  http://bugs.python.org/issue12655
  http://docs.python.org/dev/library/os.html#interface-to-the-scheduler It It
  might be worth to take a look and figure out whether we can include some of
  those in psutil.

- `os.times()` provides `elapsed` times (`Process.cpu_times()` might as well?).

- Enrich exception classes hierarchy on Python >= 3.3 / post PEP-3151 so that:
  - `NoSuchProcess` inherits from `ProcessLookupError`
  - `AccessDenied` inherits from `PermissionError`
  - `TimeoutExpired inherits` from TimeoutError (debatable) See:
    http://docs.python.org/3/library/exceptions.html#os-exceptions

- `Process.threads()` might grow an extra "id" parameter so that it can be used
  as:

  ```python
  >>> p = psutil.Process(os.getpid())
  >>> p.threads(id=psutil.current_thread_id())
  thread(id=2539, user_time=0.03, system_time=0.02)
  >>>
  ```

  Note: this leads to questions such as "should we have a custom `NoSuchThread`
  exception? Also see issue #418. Also note: this would work with `os.getpid()`
  only. `psutil.current_thread_id()` might be desirable as per issue #418
  though.

- should `TimeoutExpired` exception have a 'msg' kwarg similar to
  `NoSuchProcess` and `AccessDenied`? Not that we need it, but currently we
  cannot raise a `TimeoutExpired` exception with a specific error string.

- round `Process.memory_percent() result?

## Resources

- zabbix: https://zabbix.org/wiki/Get_Zabbix
- netdata: https://github.com/netdata/netdata

## System tools source code

Source code of system monitoring tools (ps, top, vmstat, etc.) on various
platforms. Useful as a reference when implementing or verifying psutil's
platform-specific code.

### Linux

- **procps-ng** (ps, top, free, vmstat, kill, uptime, w, who, pgrep, pmap,
  pstree, pwdx, watch): https://gitlab.com/procps-ng/procps
- **sysstat** (iostat, mpstat, pidstat, sar):
  https://github.com/sysstat/sysstat
- **iproute2** (ss, ip): https://github.com/iproute2/iproute2
- **net-tools** (ifconfig, netstat, arp, route):
  https://net-tools.sourceforge.io/
- **util-linux** (mount, findmnt, taskset, ionice, renice, prlimit, lscpu,
  lsblk): https://github.com/util-linux/util-linux
- **GNU coreutils** (df, nproc): https://github.com/coreutils/coreutils
- **lsof**: https://github.com/lsof-org/lsof
- **lm-sensors** (sensors): https://github.com/lm-sensors/lm-sensors
- **smem**: https://www.selenic.com/smem/

### macOS

Apple open-source distributions: https://github.com/apple-oss-distributions/

- **ps**: https://github.com/apple-oss-distributions/adv_cmds
- **top**: https://github.com/apple-oss-distributions/top
- **sysctl**: https://github.com/apple-oss-distributions/system_cmds
- **netstat, ifconfig**:
  https://github.com/apple-oss-distributions/network_cmds
- **lsof**: https://github.com/apple-oss-distributions/lsof

### FreeBSD

Repository: https://github.com/freebsd/freebsd-src

- **ps**: https://github.com/freebsd/freebsd-src/tree/main/bin/ps
- **top**: https://github.com/freebsd/freebsd-src/tree/main/usr.bin/top
- **vmstat**: https://github.com/freebsd/freebsd-src/tree/main/usr.bin/vmstat
- **systat**: https://github.com/freebsd/freebsd-src/tree/main/usr.bin/systat
- **netstat**: https://github.com/freebsd/freebsd-src/tree/main/usr.bin/netstat
- **iostat**: https://github.com/freebsd/freebsd-src/tree/main/usr.sbin/iostat
- **procstat**:
  https://github.com/freebsd/freebsd-src/tree/main/usr.bin/procstat
- **ifconfig**: https://github.com/freebsd/freebsd-src/tree/main/sbin/ifconfig
- **cpuset**: https://github.com/freebsd/freebsd-src/tree/main/bin/cpuset
- **pgrep**: https://github.com/freebsd/freebsd-src/tree/main/bin/pkill
- **swapinfo**:
  https://github.com/freebsd/freebsd-src/tree/main/usr.sbin/swapinfo

### NetBSD

Repository: https://github.com/NetBSD/src

- **ps**: https://github.com/NetBSD/src/tree/trunk/bin/ps
- **top**: https://github.com/NetBSD/src/tree/trunk/external/bsd/top
- **vmstat**: https://github.com/NetBSD/src/tree/trunk/usr.bin/vmstat
- **systat**: https://github.com/NetBSD/src/tree/trunk/usr.bin/systat
- **netstat**: https://github.com/NetBSD/src/tree/trunk/usr.bin/netstat
- **ifconfig**: https://github.com/NetBSD/src/tree/trunk/sbin/ifconfig
- **pgrep**: https://github.com/NetBSD/src/tree/trunk/bin/pgrep

### OpenBSD

Repository: https://github.com/openbsd/src

- **ps**: https://github.com/openbsd/src/tree/master/bin/ps
- **top**: https://github.com/openbsd/src/tree/master/usr.bin/top
- **vmstat**: https://github.com/openbsd/src/tree/master/usr.bin/vmstat
- **systat**: https://github.com/openbsd/src/tree/master/usr.bin/systat
- **netstat**: https://github.com/openbsd/src/tree/master/usr.bin/netstat
- **ifconfig**: https://github.com/openbsd/src/tree/master/sbin/ifconfig
- **pgrep**: https://github.com/openbsd/src/tree/master/bin/pgrep
- **swapctl**: https://github.com/openbsd/src/tree/master/sbin/swapctl

### Other tools

- **zabbix**: https://github.com/zabbix/zabbix/
- **htop**: https://github.com/htop-dev/htop
- **btop**: https://github.com/aristocratos/btop/

## Stats

- https://pepy.tech/projects/psutil
- https://clickpy.clickhouse.com/dashboard/psutil
- https://pypistats.org/packages/psutil

## Doc

### Blog

Example sites using sphinx ablog:

- ablog: https://ablog.readthedocs.io/en/stable/blog.html (dogfoods its own
  extension)
- SunPy (solar-physics Python library): https://sunpy.org/blog.html
- sgkit (genetics toolkit): https://sgkit-dev.github.io/sgkit/latest/blog.html
- Nuitka (Python-to-C compiler): https://nuitka.net/blog.html
- Executable Books Project (Jupyter Book / MyST):
  https://executablebooks.org/en/latest/blog/
- Adriaan Rol (quantum researcher personal site): https://adriaanrol.com/
- Jean-Pierre Chauvel (personal tech blog): https://www.chauvel.org/blog/

### Nice sites

- Nice home: https://pnpm.io/
- https://vite.dev/
