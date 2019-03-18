# Copyright (c) 2009, Giampaolo Rodola'
# Copyright (c) 2017, Arnon Yaari
# All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""IBM i platform implementation."""

import errno
import glob
import os
import re
import subprocess
import sys
import ibm_db_dbi as dbi
import traceback
import math
from collections import namedtuple
from socket import AF_INET

from . import _common
from . import _psposix
from . import _psutil_ibmi as cext
from . import _psutil_posix as cext_posix
from ._common import AF_INET6
from ._common import memoize_when_activated
from ._common import NIC_DUPLEX_FULL
from ._common import NIC_DUPLEX_HALF
from ._common import NIC_DUPLEX_UNKNOWN
from ._common import sockfam_to_enum
from ._common import socktype_to_enum
from ._common import usage_percent
from ._compat import PY3
import datetime

__extra__all__ = []

# =====================================================================
# --- globals
# =====================================================================


HAS_THREADS = hasattr(cext, "proc_threads")

PAGE_SIZE = os.sysconf('SC_PAGE_SIZE')
AF_LINK = cext_posix.AF_LINK

PROC_STATUSES = {
    cext.SIDL: _common.STATUS_IDLE,
    cext.SZOMB: _common.STATUS_ZOMBIE,
    cext.SACTIVE: _common.STATUS_RUNNING,
    cext.SSWAP: _common.STATUS_RUNNING,      # TODO what status is this?
    cext.SSTOP: _common.STATUS_STOPPED,
}

TCP_STATUSES = {
    "ESTABLISHED": _common.CONN_ESTABLISHED,
    "SYN-SENT": _common.CONN_SYN_SENT,
    "SYN-RECEIVED": _common.CONN_SYN_RECV,
    "FIN-WAIT-1": _common.CONN_FIN_WAIT1,
    "FIN-WAIT-2": _common.CONN_FIN_WAIT2,
    "TIME-WAIT": _common.CONN_TIME_WAIT,
    "CLOSED": _common.CONN_CLOSE,
    "CLOSE-WAIT": _common.CONN_CLOSE_WAIT,
    "LAST-ACK": _common.CONN_LAST_ACK,
    "LISTEN": _common.CONN_LISTEN,
    "CLOSING": _common.CONN_CLOSING,
    None: _common.CONN_NONE,
}

proc_info_map = dict(
    ppid=0,
    rss=1,
    vms=2,
    create_time=3,
    nice=4,
    num_threads=5,
    status=6,
    ttynr=7)

# These objects get set on "import psutil" from the __init__.py
# file, see: https://github.com/giampaolo/psutil/issues/1402
NoSuchProcess = None
ZombieProcess = None
AccessDenied = None
TimeoutExpired = None

_conn = dbi.connect()

# =====================================================================
# --- named tuples
# =====================================================================


# psutil.Process.memory_info()
pmem = namedtuple('pmem', ['rss', 'vms'])
# psutil.Process.memory_full_info()
pfullmem = pmem
# psutil.Process.cpu_times()
scputimes = namedtuple('scputimes', ['user', 'system', 'idle', 'iowait'])
# psutil.virtual_memory()
svmem = namedtuple('svmem', ['total', 'available', 'percent', 'used', 'free'])
# psutil.Process.memory_maps(grouped=True)
pmmap_grouped = namedtuple('pmmap_grouped', ['path', 'rss', 'anon', 'locked'])
# psutil.Process.memory_maps(grouped=False)
pmmap_ext = namedtuple(
    'pmmap_ext', 'addr perms ' + ' '.join(pmmap_grouped._fields))
#jobname to pid cache
jobname_pid_cache = {}

# =====================================================================
# --- IBM i runs an AIX variant but a number of things are unsupported
# =====================================================================
def _not_supported(*args, **kw):
    raise NotImplementedError("not supported on this platform")
# =====================================================================
# --- IBM i utility funcs
# =====================================================================
def jobname_to_pid(_jobname=None):
    if _jobname is None:
        return -1
    if _jobname in jobname_pid_cache:
        return jobname_pid_cache[_jobname]
    p = subprocess.Popen(["/QOpenSys/usr/bin/getjobid", "-jv", _jobname], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output = p.communicate()[0]
    try:
        line = output.decode("utf-8") .splitlines()[-1].strip()
        pid = int(line.strip().split(" ")[0])
        jobname_pid_cache[_jobname] = pid
        return pid
    except:
        jobname_pid_cache[_jobname] = -1
        return -1

# =====================================================================
# --- memory
# =====================================================================


def virtual_memory():
    cursor = _conn.cursor()
    cursor.execute("select MAIN_STORAGE_SIZE, CURRENT_TEMPORARY_STORAGE from table (QSYS2.SYSTEM_STATUS()) x")
    minfo = cursor.fetchone()
    cursor.close()
    total = minfo[0]
    inuse = minfo[1]
    avail = total - inuse
    free = avail 
    percent = usage_percent((total - avail), total, round_=1)
    return svmem(total, avail, percent, inuse, free)


def swap_memory():
    if not hasattr(cext, 'swap_mem'):
        _not_supported()
    """Swap system memory as a (total, used, free, sin, sout) tuple."""
    total, free, sin, sout = cext.swap_mem()
    used = total - free
    percent = usage_percent(used, total, round_=1)
    return _common.sswap(total, used, free, percent, sin, sout)


# =====================================================================
# --- CPU
# =====================================================================


def cpu_times():
    """Return system-wide CPU times as a named tuple"""
    ret = cext.per_cpu_times()
    return scputimes(*[sum(x) for x in zip(*ret)])


def per_cpu_times():
    if not hasattr(cext, 'per_cpu_times'):
        _not_supported()
    """Return system per-CPU times as a list of named tuples"""
    ret = cext.per_cpu_times()
    return [scputimes(*x) for x in ret]


def cpu_count_logical():
    # if hasattr(cext, 'cpu_count_online'):
    #     return cext.cpu_count_online()
    """Return the number of logical CPUs in the system."""
    cursor = _conn.cursor()
    cursor.execute("select CURRENT_CPU_CAPACITY from table (QSYS2.SYSTEM_STATUS()) x")
    #print("Executed query for logical CPUs")
    ncpus = math.ceil(cursor.fetchone()[0])
    #print("Determined logical CPU count to be ", ncpus)
    cursor.close()
    return ncpus


def cpu_count_physical():
    if hasattr(cext, 'cpu_count'):
        return cext.cpu_count()
    cursor = _conn.cursor()
    cursor.execute("select CONFIGURED_CPUS from table (QSYS2.SYSTEM_STATUS()) x")
    ncpus = cursor.fetchone()[0]
    cursor.close()
    return ncpus


def cpu_stats():
    """Return various CPU stats as a named tuple."""
    return _common.scpustats(0,0,0,0) #TODO: Any way to implement on IBM i?

# =====================================================================
# --- disks
# =====================================================================

def disk_usage(path='/'):
    cursor = _conn.cursor()
    cursor.execute("SELECT SUM(UNIT_STORAGE_CAPACITY) as TOTAL, SUM(UNIT_SPACE_AVAILABLE) as AVAIL FROM QSYS2.SYSDISKSTAT")
    for row in cursor:
        total = row[0]
        avail = row[1]
        used = total - avail
        percent = (float(100.00*used)/float(total))
        cursor.close()
        return _common.sdiskusage(total, used, avail, percent)

def disk_io_counters(all=False): #TODO
    cursor = _conn.cursor()
    cursor.execute("SELECT UNIT_NUMBER FROM QSYS2.SYSDISKSTAT")
    counters = {}
    for row in cursor:
        print("adding ", row[0])
        counters["unit:"+str(row[0])] = (0,0,0,0,0,0) #TODO: query system performance data to get this
    cursor.close()
    return counters

def disk_partitions(all=False):
    cursor = _conn.cursor()
    cursor.execute("SELECT UNIT_NUMBER,ASP_NUMBER,UNIT_TYPE,DISK_TYPE FROM QSYS2.SYSDISKSTAT")
    ret = []
    for row in cursor:
        if(row[2] == 0):
            unit_type = "not_solid_state"
        else:
            unit_type = "solid_state"
        ret.append(_common.sdiskpart("unit:"+str(row[0]),"/",unit_type, "asp:"+str(row[1])))
    cursor.close()
    return ret


# =====================================================================
# --- network
# =====================================================================


net_if_addrs = cext_posix.net_if_addrs

def net_io_counters(pernic=True):
    cursor = _conn.cursor()
    cursor.execute("SELECT LINE_DESCRIPTION FROM QSYS2.NETSTAT_INTERFACE_INFO")
    counters = {}
    for row in cursor:
        print("adding ", row[0])
        counters[row[0]] = (0,0,0,0,0,0,0,0) #TODO: investigate ways to get proper data
    cursor.close()
    return counters


def net_connections(kind, _pid=-1):
    """Return socket connections.  If pid == -1 return system-wide
    connections (as opposed to connections opened by one process only).
    """
    ret = list()
    cursor = _conn.cursor()
    querystring = """ 
                        SELECT j.CONNECTION_TYPE,j.LOCAL_ADDRESS,j.LOCAL_PORT,j.REMOTE_ADDRESS,j.REMOTE_PORT,j.JOB_NAME,i.TCP_STATE
                        FROM QSYS2.NETSTAT_INFO i
                        INNER JOIN QSYS2.NETSTAT_JOB_INFO j ON
                        i.local_port = j.local_port and
                        i.remote_port = j.remote_port
                        ORDER BY i.TCP_STATE ASC, j.CONNECTION_TYPE DESC """
    cursor.execute(querystring)
    for row in cursor:
        type_ = AF_INET6 if row[0] == "IPV6" else AF_INET
        laddr = _common.addr(row[1], row[2])
        raddr = _common.addr(row[3], row[4])
        jobname = row[5]
        status = TCP_STATUSES[row[6]]
        fam = AF_INET
        fd = -1
        if _pid == -1 and jobname is None:
            nt = _common.pconn(fd, fam, type_, laddr, raddr, status)
        elif jobname is None:
            continue
        else: 
            pid = jobname_to_pid(jobname)
            if _pid != -1 and _pid != pid:
                continue
            if pid == -1:
                nt = _common.pconn(fd, fam, type_, laddr, raddr, status)
            else: 
                nt = _common.sconn(fd, fam, type_, laddr, raddr, status, pid)
        ret.append(nt)
    cursor.close()
    return ret


def net_if_stats():
    """Get NIC stats (isup, duplex, speed, mtu)."""
    cursor = _conn.cursor()
    cursor.execute("SELECT LINE_DESCRIPTION,INTERFACE_STATUS,MAXIMUM_TRANSMISSION_UNIT FROM QSYS2.NETSTAT_INTERFACE_INFO")
    ret = {}
    for row in cursor:
        name = row[0]
        isup = row[1] == "ACTIVE"
        duplex = NIC_DUPLEX_FULL
        mtu = row[2]
        speed = 0 if name == "*LOOPBACK" else 100
        print("adding ", name)
        ret[name] = _common.snicstats(isup, duplex, speed, mtu)
    cursor.close()
    return ret


# =====================================================================
# --- other system functions
# =====================================================================


def boot_time():
    cursor = _conn.cursor()
    cursor.execute("SELECT JOB_ACTIVE_TIME FROM TABLE(QSYS2.JOB_INFO(JOB_USER_FILTER => 'QSYS')) A WHERE JOB_NAME = '000000/QSYS/SCPF'")
    for row in cursor:
        ret = row[0].timestamp()
        cursor.close()
        return ret


def users():
    """Return currently connected users as a list of namedtuples."""
    retlist = []
    ttylist = []

    p = subprocess.Popen(["/QOpenSys/usr/bin/ps", "-Af", "-o", "tty,pid,user"], stdout=subprocess.PIPE)
    output = p.communicate()[0]
    for line in output.decode("utf-8") .splitlines()[1:]:
        tokens = line.split()
        tty = tokens[0]
        pid = int(tokens[1])
        user = tokens[2] 
        if(tty == "-"):
            continue
        if(tty in ttylist):
            continue
        try:
            nt = _common.suser(user, tty, "", Process(pid).create_time(), pid)
            ttylist.append(tty)
            retlist.append(nt)
        except NoSuchProcess:
            #expected 
            continue
    return retlist


# =====================================================================
# --- processes
# =====================================================================


def pids():
    """Returns a list of PIDs currently running on the system."""
    return cext.list_pids()


def pid_exists(pid):
    """Check for the existence of a unix pid."""
    return pid in cext.list_pids()


def wrap_exceptions(fun):
    """Call callable into a try/except clause and translate ENOENT,
    EACCES and EPERM in NoSuchProcess or AccessDenied exceptions.
    """

    def wrapper(self, *args, **kwargs):
        try:
            return fun(self, *args, **kwargs)
        except EnvironmentError as err:
            # support for private module import
            if (NoSuchProcess is None or AccessDenied is None or
                    ZombieProcess is None):
                raise
            # ENOENT (no such file or directory) gets raised on open().
            # ESRCH (no such process) can get raised on read() if
            # process is gone in meantime.
            if err.errno in (errno.ENOENT, errno.ESRCH):
                if not pid_exists(self.pid):
                    raise NoSuchProcess(self.pid, self._name)
                else:
                    raise ZombieProcess(self.pid, self._name, self._ppid)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(self.pid, self._name)
            raise
    return wrapper


class Process(object):
    """Wrapper class around underlying C implementation."""

    __slots__ = ["pid", "_name", "_ppid", "_cache", "_conn"]

    def __init__(self, pid):
        self.pid = pid
        self._name = None
        self._ppid = None

    def oneshot_enter(self):
        self._proc_name_and_args.cache_activate(self)
        self._proc_basic_info.cache_activate(self)
        self._proc_cred.cache_activate(self)

    def oneshot_exit(self):
        self._proc_name_and_args.cache_deactivate(self)
        self._proc_basic_info.cache_deactivate(self)
        self._proc_cred.cache_deactivate(self)

    @memoize_when_activated
    def _proc_name_and_args(self):
        return cext.proc_name_and_args(self.pid)

    @memoize_when_activated
    def _proc_basic_info(self):
        return cext.proc_basic_info(self.pid)

    @memoize_when_activated
    def _proc_cred(self):
        return cext.proc_cred(self.pid)

    @wrap_exceptions
    def name(self):
        if self.pid == 0:
            return "swapper"
        # note: this is limited to 15 characters
        return self._proc_name_and_args()[0].rstrip("\x00")

    @wrap_exceptions
    def exe(self):
        # there is no way to get executable path in AIX other than to guess,
        # and guessing is more complex than what's in the wrapping class
        #TODO: we can add logic here to use the target process's PATH rather than this one's
        exe = self.cmdline()[0]
        if os.path.sep in exe:
            # relative or absolute path
            if not os.path.isabs(exe):
                # if cwd has changed, we're out of luck - this may be wrong!
                exe = os.path.abspath(os.path.join(self.cwd(), exe))
            if (os.path.isabs(exe) and
               os.path.isfile(exe) and
               os.access(exe, os.X_OK)):
                return exe
            # not found, move to search in PATH using basename only
            exe = os.path.basename(exe)
        # search for exe name PATH
        for path in os.environ["PATH"].split(":"):
            possible_exe = os.path.abspath(os.path.join(path, exe))
            if (os.path.isfile(possible_exe) and
               os.access(possible_exe, os.X_OK)):
                return possible_exe
        return ''

    @wrap_exceptions
    def cmdline(self):
        return self._proc_name_and_args()

    @wrap_exceptions
    def create_time(self):
        return self._proc_basic_info()[proc_info_map['create_time']]

    @wrap_exceptions
    def num_threads(self):
        return self._proc_basic_info()[proc_info_map['num_threads']]

    if HAS_THREADS:
        @wrap_exceptions
        def threads(self):
            rawlist = cext.proc_threads(self.pid)
            retlist = []
            for thread_id, utime, stime in rawlist:
                ntuple = _common.pthread(thread_id, utime, stime)
                retlist.append(ntuple)
            # The underlying C implementation retrieves all OS threads
            # and filters them by PID.  At this point we can't tell whether
            # an empty list means there were no connections for process or
            # process is no longer active so we force NSP in case the PID
            # is no longer there.
            # TODO figure out what to do on IBM i here
            # if not retlist:
            #     # will raise NSP if process is gone
            #     os.stat('%s/%s' % (self._procfs_path, self.pid))
            return retlist

    @wrap_exceptions
    def connections(self, kind='inet'):
        ret = net_connections(kind, _pid=self.pid)
        # The underlying C implementation retrieves all OS connections
        # and filters them by PID.  At this point we can't tell whether
        # an empty list means there were no connections for process or
        # process is no longer active so we force NSP in case the PID
        # is no longer there.
        #TODO IBM i implementation
        # if not ret:
        #     # will raise NSP if process is gone
        #     os.stat('%s/%s' % (self._procfs_path, self.pid))
        return ret

    @wrap_exceptions
    def nice_get(self):
        return cext_posix.getpriority(self.pid)

    @wrap_exceptions
    def nice_set(self, value):
        return cext_posix.setpriority(self.pid, value)

    @wrap_exceptions
    def ppid(self):
        self._ppid = self._proc_basic_info()[proc_info_map['ppid']]
        return self._ppid

    @wrap_exceptions
    def uids(self):
        real, effective, saved, _, _, _ = self._proc_cred()
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def gids(self):
        _, _, _, real, effective, saved = self._proc_cred()
        return _common.puids(real, effective, saved)

    @wrap_exceptions
    def cpu_times(self):
        cpu_times = cext.proc_cpu_times(self.pid)
        return _common.pcputimes(*cpu_times)

    @wrap_exceptions
    def terminal(self):

        p = subprocess.Popen(["/QOpenSys/usr/bin/ps", "-Af", "-o", "tty,pid,user", "-p", str(self.pid)], stdout=subprocess.PIPE)
        output = p.communicate()[0]
        for line in output.decode("utf-8") .splitlines()[1:]:
            tokens = line.split()
            tty = tokens[0]
            pid = int(tokens[1])
            user = tokens[2] 
            if(tty == "-"):
                continue
            if(pid == int(self.pid)):
                return "/dev/"+tty
        return None

    @wrap_exceptions
    def cwd(self):
        _not_supported(); #TODO

    @wrap_exceptions
    def memory_info(self):
        ret = self._proc_basic_info()
        rss = ret[proc_info_map['rss']] * 1024
        vms = ret[proc_info_map['vms']] * 1024
        return pmem(rss, vms)

    memory_full_info = memory_info

    @wrap_exceptions
    def status(self):
        code = self._proc_basic_info()[proc_info_map['status']]
        # XXX is '?' legit? (we're not supposed to return it anyway)
        return PROC_STATUSES.get(code, '?')

    def open_files(self):
        # TODO rewrite without using procfiles (stat /proc/pid/fd/* and then
        # find matching name of the inode)
        p = subprocess.Popen(["/usr/bin/procfiles", "-n", str(self.pid)],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = p.communicate()
        if PY3:
            stdout, stderr = [x.decode(sys.stdout.encoding)
                              for x in (stdout, stderr)]
        if "no such process" in stderr.lower():
            raise NoSuchProcess(self.pid, self._name)
        procfiles = re.findall(r"(\d+): S_IFREG.*\s*.*name:(.*)\n", stdout)
        retlist = []
        for fd, path in procfiles:
            path = path.strip()
            if path.startswith("//"):
                path = path[1:]
            if path.lower() == "cannot be retrieved":
                continue
            retlist.append(_common.popenfile(path, int(fd)))
        return retlist

    @wrap_exceptions
    def num_fds(self):
        if self.pid == 0:       # no /proc/0/fd
            return 0
        _not_supported() # TODO

    @wrap_exceptions
    def num_ctx_switches(self):
        return _common.pctxsw(
            *cext.proc_num_ctx_switches(self.pid))

    @wrap_exceptions
    def wait(self, timeout=None):
        return _psposix.wait_pid(self.pid, timeout, self._name)

    @wrap_exceptions
    def io_counters(self):
        if not hasattr(cext, 'proc_io_counters'):
            _not_supported()
        try:
            rc, wc, rb, wb = cext.proc_io_counters(self.pid)
        except OSError:
            # if process is terminated, proc_io_counters returns OSError
            # instead of NSP
            if not pid_exists(self.pid):
                raise NoSuchProcess(self.pid, self._name)
            raise
        return _common.pio(rc, wc, rb, wb)
