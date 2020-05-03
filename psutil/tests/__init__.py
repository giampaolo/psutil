# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Test utilities.
"""

from __future__ import print_function
import atexit
import contextlib
import ctypes
import errno
import functools
import gc
import inspect
import os
import random
import re
import select
import shutil
import signal
import socket
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import warnings
from socket import AF_INET
from socket import AF_INET6
from socket import SOCK_STREAM

import psutil
from psutil import AIX
from psutil import LINUX
from psutil import MACOS
from psutil import POSIX
from psutil import SUNOS
from psutil import WINDOWS
from psutil._common import bytes2human
from psutil._common import print_color
from psutil._common import supports_ipv6
from psutil._compat import FileExistsError
from psutil._compat import FileNotFoundError
from psutil._compat import PY3
from psutil._compat import range
from psutil._compat import super
from psutil._compat import u
from psutil._compat import unicode
from psutil._compat import which

if sys.version_info < (2, 7):
    import unittest2 as unittest  # requires "pip install unittest2"
else:
    import unittest

try:
    from unittest import mock  # py3
except ImportError:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        import mock  # NOQA - requires "pip install mock"

if sys.version_info >= (3, 4):
    import enum
else:
    enum = None


__all__ = [
    # constants
    'APPVEYOR', 'DEVNULL', 'GLOBAL_TIMEOUT', 'SYSMEM_TOLERANCE', 'NO_RETRIES',
    'PYPY', 'PYTHON_EXE', 'ROOT_DIR', 'SCRIPTS_DIR', 'TESTFN_PREFIX',
    'UNICODE_SUFFIX', 'INVALID_UNICODE_SUFFIX', 'TOX', 'TRAVIS', 'CIRRUS',
    'CI_TESTING', 'VALID_PROC_STATUSES',
    "HAS_CPU_AFFINITY", "HAS_CPU_FREQ", "HAS_ENVIRON", "HAS_PROC_IO_COUNTERS",
    "HAS_IONICE", "HAS_MEMORY_MAPS", "HAS_PROC_CPU_NUM", "HAS_RLIMIT",
    "HAS_SENSORS_BATTERY", "HAS_BATTERY", "HAS_SENSORS_FANS",
    "HAS_SENSORS_TEMPERATURES", "HAS_MEMORY_FULL_INFO",
    # subprocesses
    'pyrun', 'terminate', 'reap_children', 'spawn_testproc', 'spawn_zombie',
    'spawn_children_pair',
    # threads
    'ThreadTask'
    # test utils
    'unittest', 'skip_on_access_denied', 'skip_on_not_implemented',
    'retry_on_failure', 'TestMemoryLeak', 'PsutilTestCase',
    'process_namespace',
    # install utils
    'install_pip', 'install_test_deps',
    # fs utils
    'chdir', 'safe_rmpath', 'create_exe', 'decode_path', 'encode_path',
    'get_testfn',
    # os
    'get_winver', 'get_kernel_version',
    # sync primitives
    'call_until', 'wait_for_pid', 'wait_for_file',
    # network
    'check_net_address',
    'get_free_port', 'bind_socket', 'bind_unix_socket', 'tcp_socketpair',
    'unix_socketpair', 'create_sockets',
    # compat
    'reload_module', 'import_module_by_path',
    # others
    'warn', 'copyload_shared_lib', 'is_namedtuple',
]


# ===================================================================
# --- constants
# ===================================================================

# --- platforms

TOX = os.getenv('TOX') or '' in ('1', 'true')
PYPY = '__pypy__' in sys.builtin_module_names
# whether we're running this test suite on a Continuous Integration service
TRAVIS = bool(os.environ.get('TRAVIS'))
APPVEYOR = bool(os.environ.get('APPVEYOR'))
CIRRUS = bool(os.environ.get('CIRRUS'))
CI_TESTING = TRAVIS or APPVEYOR or CIRRUS

# --- configurable defaults

# how many times retry_on_failure() decorator will retry
NO_RETRIES = 10
# bytes tolerance for system-wide memory related tests
SYSMEM_TOLERANCE = 500 * 1024  # 500KB
# the timeout used in functions which have to wait
GLOBAL_TIMEOUT = 5
# be more tolerant if we're on travis / appveyor in order to avoid
# false positives
if TRAVIS or APPVEYOR:
    NO_RETRIES *= 3
    GLOBAL_TIMEOUT *= 3

# --- file names

# Disambiguate TESTFN for parallel testing.
if os.name == 'java':
    # Jython disallows @ in module names
    TESTFN_PREFIX = '$psutil-%s-' % os.getpid()
else:
    TESTFN_PREFIX = '@psutil-%s-' % os.getpid()
UNICODE_SUFFIX = u("-ƒőő")
# An invalid unicode string.
if PY3:
    INVALID_UNICODE_SUFFIX = b"f\xc0\x80".decode('utf8', 'surrogateescape')
else:
    INVALID_UNICODE_SUFFIX = "f\xc0\x80"

ASCII_FS = sys.getfilesystemencoding().lower() in ('ascii', 'us-ascii')

# --- paths

ROOT_DIR = os.path.realpath(
    os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')
HERE = os.path.realpath(os.path.dirname(__file__))

# --- support

HAS_CONNECTIONS_UNIX = POSIX and not SUNOS
HAS_CPU_AFFINITY = hasattr(psutil.Process, "cpu_affinity")
HAS_CPU_FREQ = hasattr(psutil, "cpu_freq")
HAS_GETLOADAVG = hasattr(psutil, "getloadavg")
HAS_ENVIRON = hasattr(psutil.Process, "environ")
HAS_IONICE = hasattr(psutil.Process, "ionice")
HAS_MEMORY_MAPS = hasattr(psutil.Process, "memory_maps")
HAS_NET_IO_COUNTERS = hasattr(psutil, "net_io_counters")
HAS_PROC_CPU_NUM = hasattr(psutil.Process, "cpu_num")
HAS_PROC_IO_COUNTERS = hasattr(psutil.Process, "io_counters")
HAS_RLIMIT = hasattr(psutil.Process, "rlimit")
HAS_SENSORS_BATTERY = hasattr(psutil, "sensors_battery")
try:
    HAS_BATTERY = HAS_SENSORS_BATTERY and bool(psutil.sensors_battery())
except Exception:
    HAS_BATTERY = True
HAS_SENSORS_FANS = hasattr(psutil, "sensors_fans")
HAS_SENSORS_TEMPERATURES = hasattr(psutil, "sensors_temperatures")
HAS_THREADS = hasattr(psutil.Process, "threads")
SKIP_SYSCONS = (MACOS or AIX) and os.getuid() != 0

# --- misc


def _get_py_exe():
    def attempt(exe):
        try:
            subprocess.check_call(
                [exe, "-V"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except Exception:
            return None
        else:
            return exe

    if MACOS:
        exe = \
            attempt(sys.executable) or \
            attempt(os.path.realpath(sys.executable)) or \
            attempt(which("python%s.%s" % sys.version_info[:2])) or \
            attempt(psutil.Process().exe())
        if not exe:
            raise ValueError("can't find python exe real abspath")
        return exe
    else:
        exe = os.path.realpath(sys.executable)
        assert os.path.exists(exe), exe
        return exe


PYTHON_EXE = _get_py_exe()
DEVNULL = open(os.devnull, 'r+')
atexit.register(DEVNULL.close)

VALID_PROC_STATUSES = [getattr(psutil, x) for x in dir(psutil)
                       if x.startswith('STATUS_')]
AF_UNIX = getattr(socket, "AF_UNIX", object())

_subprocesses_started = set()
_pids_started = set()


# ===================================================================
# --- threads
# ===================================================================


class ThreadTask(threading.Thread):
    """A thread task which does nothing expect staying alive."""

    def __init__(self):
        super().__init__()
        self._running = False
        self._interval = 0.001
        self._flag = threading.Event()

    def __repr__(self):
        name = self.__class__.__name__
        return '<%s running=%s at %#x>' % (name, self._running, id(self))

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args, **kwargs):
        self.stop()

    def start(self):
        """Start thread and keep it running until an explicit
        stop() request. Polls for shutdown every 'timeout' seconds.
        """
        if self._running:
            raise ValueError("already started")
        threading.Thread.start(self)
        self._flag.wait()

    def run(self):
        self._running = True
        self._flag.set()
        while self._running:
            time.sleep(self._interval)

    def stop(self):
        """Stop thread execution and and waits until it is stopped."""
        if not self._running:
            raise ValueError("already stopped")
        self._running = False
        self.join()


# ===================================================================
# --- subprocesses
# ===================================================================


def _reap_children_on_err(fun):
    @functools.wraps(fun)
    def wrapper(*args, **kwargs):
        try:
            return fun(*args, **kwargs)
        except Exception:
            reap_children()
            raise
    return wrapper


@_reap_children_on_err
def spawn_testproc(cmd=None, **kwds):
    """Creates a python subprocess which does nothing for 60 secs and
    return it as a subprocess.Popen instance.
    If "cmd" is specified that is used instead of python.
    By default stdin and stdout are redirected to /dev/null.
    It also attemps to make sure the process is in a reasonably
    initialized state.
    The process is registered for cleanup on reap_children().
    """
    kwds.setdefault("stdin", DEVNULL)
    kwds.setdefault("stdout", DEVNULL)
    kwds.setdefault("cwd", os.getcwd())
    kwds.setdefault("env", os.environ)
    if WINDOWS:
        # Prevents the subprocess to open error dialogs. This will also
        # cause stderr to be suppressed, which is suboptimal in order
        # to debug broken tests.
        CREATE_NO_WINDOW = 0x8000000
        kwds.setdefault("creationflags", CREATE_NO_WINDOW)
    if cmd is None:
        testfn = get_testfn()
        try:
            safe_rmpath(testfn)
            pyline = "from time import sleep;" \
                     "open(r'%s', 'w').close();" \
                     "sleep(60);" % testfn
            cmd = [PYTHON_EXE, "-c", pyline]
            sproc = subprocess.Popen(cmd, **kwds)
            _subprocesses_started.add(sproc)
            wait_for_file(testfn, delete=True, empty=True)
        finally:
            safe_rmpath(testfn)
    else:
        sproc = subprocess.Popen(cmd, **kwds)
        _subprocesses_started.add(sproc)
        wait_for_pid(sproc.pid)
    return sproc


@_reap_children_on_err
def spawn_children_pair():
    """Create a subprocess which creates another one as in:
    A (us) -> B (child) -> C (grandchild).
    Return a (child, grandchild) tuple.
    The 2 processes are fully initialized and will live for 60 secs
    and are registered for cleanup on reap_children().
    """
    tfile = None
    testfn = get_testfn(dir=os.getcwd())
    try:
        s = textwrap.dedent("""\
            import subprocess, os, sys, time
            s = "import os, time;"
            s += "f = open('%s', 'w');"
            s += "f.write(str(os.getpid()));"
            s += "f.close();"
            s += "time.sleep(60);"
            p = subprocess.Popen([r'%s', '-c', s])
            p.wait()
            """ % (os.path.basename(testfn), PYTHON_EXE))
        # On Windows if we create a subprocess with CREATE_NO_WINDOW flag
        # set (which is the default) a "conhost.exe" extra process will be
        # spawned as a child. We don't want that.
        if WINDOWS:
            subp, tfile = pyrun(s, creationflags=0)
        else:
            subp, tfile = pyrun(s)
        child = psutil.Process(subp.pid)
        grandchild_pid = int(wait_for_file(testfn, delete=True, empty=False))
        _pids_started.add(grandchild_pid)
        grandchild = psutil.Process(grandchild_pid)
        return (child, grandchild)
    finally:
        safe_rmpath(testfn)
        if tfile is not None:
            safe_rmpath(tfile)


def spawn_zombie():
    """Create a zombie process and return a (parent, zombie) process tuple.
    In order to kill the zombie parent must be terminate()d first, then
    zombie must be wait()ed on.
    """
    assert psutil.POSIX
    unix_file = get_testfn()
    src = textwrap.dedent("""\
        import os, sys, time, socket, contextlib
        child_pid = os.fork()
        if child_pid > 0:
            time.sleep(3000)
        else:
            # this is the zombie process
            s = socket.socket(socket.AF_UNIX)
            with contextlib.closing(s):
                s.connect('%s')
                if sys.version_info < (3, ):
                    pid = str(os.getpid())
                else:
                    pid = bytes(str(os.getpid()), 'ascii')
                s.sendall(pid)
        """ % unix_file)
    tfile = None
    sock = bind_unix_socket(unix_file)
    try:
        sock.settimeout(GLOBAL_TIMEOUT)
        parent, tfile = pyrun(src)
        conn, _ = sock.accept()
        try:
            select.select([conn.fileno()], [], [], GLOBAL_TIMEOUT)
            zpid = int(conn.recv(1024))
            _pids_started.add(zpid)
            zombie = psutil.Process(zpid)
            call_until(lambda: zombie.status(), "ret == psutil.STATUS_ZOMBIE")
            return (parent, zombie)
        finally:
            conn.close()
    finally:
        sock.close()
        safe_rmpath(unix_file)
        if tfile is not None:
            safe_rmpath(tfile)


@_reap_children_on_err
def pyrun(src, **kwds):
    """Run python 'src' code string in a separate interpreter.
    Returns a subprocess.Popen instance and the test file where the source
    code was written.
    """
    kwds.setdefault("stdout", None)
    kwds.setdefault("stderr", None)
    srcfile = get_testfn()
    try:
        with open(srcfile, 'wt') as f:
            f.write(src)
        subp = spawn_testproc([PYTHON_EXE, f.name], **kwds)
        wait_for_pid(subp.pid)
        return (subp, srcfile)
    except Exception:
        safe_rmpath(srcfile)
        raise


@_reap_children_on_err
def sh(cmd, **kwds):
    """run cmd in a subprocess and return its output.
    raises RuntimeError on error.
    """
    shell = True if isinstance(cmd, (str, unicode)) else False
    # Prevents subprocess to open error dialogs in case of error.
    flags = 0x8000000 if WINDOWS and shell else 0
    kwds.setdefault("shell", shell)
    kwds.setdefault("stdout", subprocess.PIPE)
    kwds.setdefault("stderr", subprocess.PIPE)
    kwds.setdefault("universal_newlines", True)
    kwds.setdefault("creationflags", flags)
    p = subprocess.Popen(cmd, **kwds)
    _subprocesses_started.add(p)
    if PY3:
        stdout, stderr = p.communicate(timeout=GLOBAL_TIMEOUT)
    else:
        stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr)
    if stderr:
        warn(stderr)
    if stdout.endswith('\n'):
        stdout = stdout[:-1]
    return stdout


def terminate(proc_or_pid, sig=signal.SIGTERM, wait_timeout=GLOBAL_TIMEOUT):
    """Terminate a process and wait() for it.
    Process can be a PID or an instance of psutil.Process(),
    subprocess.Popen() or psutil.Popen().
    If it's a subprocess.Popen() or psutil.Popen() instance also closes
    its stdin / stdout / stderr fds.
    PID is wait()ed even if the process is already gone (kills zombies).
    Does nothing if the process does not exist.
    Return process exit status.
    """
    if POSIX:
        from psutil._psposix import wait_pid

    def wait(proc, timeout):
        try:
            return psutil.Process(proc.pid).wait(timeout)
        except psutil.NoSuchProcess:
            # Needed to kill zombies.
            if POSIX:
                return wait_pid(proc.pid, timeout)

    def sendsig(proc, sig):
        # If the process received SIGSTOP, SIGCONT is necessary first,
        # otherwise SIGTERM won't work.
        if POSIX and sig != signal.SIGKILL:
            proc.send_signal(signal.SIGCONT)
        proc.send_signal(sig)

    def term_subproc(proc, timeout):
        try:
            sendsig(proc, sig)
        except OSError as err:
            if WINDOWS and err.winerror == 6:  # "invalid handle"
                pass
            elif err.errno != errno.ESRCH:
                raise
        return wait(proc, timeout)

    def term_psproc(proc, timeout):
        try:
            sendsig(proc, sig)
        except psutil.NoSuchProcess:
            pass
        return wait(proc, timeout)

    def term_pid(pid, timeout):
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            # Needed to kill zombies.
            if POSIX:
                return wait_pid(pid, timeout)
        else:
            return term_psproc(proc, timeout)

    def flush_popen(proc):
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()
        # Flushing a BufferedWriter may raise an error.
        if proc.stdin:
            proc.stdin.close()

    p = proc_or_pid
    try:
        if isinstance(p, int):
            return term_pid(p, wait_timeout)
        elif isinstance(p, (psutil.Process, psutil.Popen)):
            return term_psproc(p, wait_timeout)
        elif isinstance(p, subprocess.Popen):
            return term_subproc(p, wait_timeout)
        else:
            raise TypeError("wrong type %r" % p)
    finally:
        if isinstance(p, (subprocess.Popen, psutil.Popen)):
            flush_popen(p)
        pid = p if isinstance(p, int) else p.pid
        assert not psutil.pid_exists(pid), pid


def reap_children(recursive=False):
    """Terminate and wait() any subprocess started by this test suite
    and any children currently running, ensuring that no processes stick
    around to hog resources.
    If resursive is True it also tries to terminate and wait()
    all grandchildren started by this process.
    """
    # Get the children here before terminating them, as in case of
    # recursive=True we don't want to lose the intermediate reference
    # pointing to the grandchildren.
    children = psutil.Process().children(recursive=recursive)

    # Terminate subprocess.Popen.
    while _subprocesses_started:
        subp = _subprocesses_started.pop()
        terminate(subp)

    # Collect started pids.
    while _pids_started:
        pid = _pids_started.pop()
        terminate(pid)

    # Terminate children.
    if children:
        for p in children:
            terminate(p, wait_timeout=None)
        gone, alive = psutil.wait_procs(children, timeout=GLOBAL_TIMEOUT)
        for p in alive:
            warn("couldn't terminate process %r; attempting kill()" % p)
            terminate(p, sig=signal.SIGKILL)


# ===================================================================
# --- OS
# ===================================================================


def get_kernel_version():
    """Return a tuple such as (2, 6, 36)."""
    if not POSIX:
        raise NotImplementedError("not POSIX")
    s = ""
    uname = os.uname()[2]
    for c in uname:
        if c.isdigit() or c == '.':
            s += c
        else:
            break
    if not s:
        raise ValueError("can't parse %r" % uname)
    minor = 0
    micro = 0
    nums = s.split('.')
    major = int(nums[0])
    if len(nums) >= 2:
        minor = int(nums[1])
    if len(nums) >= 3:
        micro = int(nums[2])
    return (major, minor, micro)


def get_winver():
    if not WINDOWS:
        raise NotImplementedError("not WINDOWS")
    wv = sys.getwindowsversion()
    if hasattr(wv, 'service_pack_major'):  # python >= 2.7
        sp = wv.service_pack_major or 0
    else:
        r = re.search(r"\s\d$", wv[4])
        if r:
            sp = int(r.group(0))
        else:
            sp = 0
    return (wv[0], wv[1], sp)


# ===================================================================
# --- sync primitives
# ===================================================================


class retry(object):
    """A retry decorator."""

    def __init__(self,
                 exception=Exception,
                 timeout=None,
                 retries=None,
                 interval=0.001,
                 logfun=None,
                 ):
        if timeout and retries:
            raise ValueError("timeout and retries args are mutually exclusive")
        self.exception = exception
        self.timeout = timeout
        self.retries = retries
        self.interval = interval
        self.logfun = logfun

    def __iter__(self):
        if self.timeout:
            stop_at = time.time() + self.timeout
            while time.time() < stop_at:
                yield
        elif self.retries:
            for _ in range(self.retries):
                yield
        else:
            while True:
                yield

    def sleep(self):
        if self.interval is not None:
            time.sleep(self.interval)

    def __call__(self, fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            exc = None
            for _ in self:
                try:
                    return fun(*args, **kwargs)
                except self.exception as _:  # NOQA
                    exc = _
                    if self.logfun is not None:
                        self.logfun(exc)
                    self.sleep()
                    continue
            if PY3:
                raise exc
            else:
                raise

        # This way the user of the decorated function can change config
        # parameters.
        wrapper.decorator = self
        return wrapper


@retry(exception=psutil.NoSuchProcess, logfun=None, timeout=GLOBAL_TIMEOUT,
       interval=0.001)
def wait_for_pid(pid):
    """Wait for pid to show up in the process list then return.
    Used in the test suite to give time the sub process to initialize.
    """
    psutil.Process(pid)
    if WINDOWS:
        # give it some more time to allow better initialization
        time.sleep(0.01)


@retry(exception=(EnvironmentError, AssertionError), logfun=None,
       timeout=GLOBAL_TIMEOUT, interval=0.001)
def wait_for_file(fname, delete=True, empty=False):
    """Wait for a file to be written on disk with some content."""
    with open(fname, "rb") as f:
        data = f.read()
    if not empty:
        assert data
    if delete:
        safe_rmpath(fname)
    return data


@retry(exception=AssertionError, logfun=None, timeout=GLOBAL_TIMEOUT,
       interval=0.001)
def call_until(fun, expr):
    """Keep calling function for timeout secs and exit if eval()
    expression is True.
    """
    ret = fun()
    assert eval(expr)
    return ret


# ===================================================================
# --- fs
# ===================================================================


def safe_rmpath(path):
    "Convenience function for removing temporary test files or dirs"
    def retry_fun(fun):
        # On Windows it could happen that the file or directory has
        # open handles or references preventing the delete operation
        # to succeed immediately, so we retry for a while. See:
        # https://bugs.python.org/issue33240
        stop_at = time.time() + 1
        while time.time() < stop_at:
            try:
                return fun()
            except FileNotFoundError:
                pass
            except WindowsError as _:
                err = _
                warn("ignoring %s" % (str(err)))
            time.sleep(0.01)
        raise err

    try:
        st = os.stat(path)
        if stat.S_ISDIR(st.st_mode):
            fun = functools.partial(shutil.rmtree, path)
        else:
            fun = functools.partial(os.remove, path)
        if POSIX:
            fun()
        else:
            retry_fun(fun)
    except FileNotFoundError:
        pass


def safe_mkdir(dir):
    "Convenience function for creating a directory"
    try:
        os.mkdir(dir)
    except FileExistsError:
        pass


@contextlib.contextmanager
def chdir(dirname):
    "Context manager which temporarily changes the current directory."
    curdir = os.getcwd()
    try:
        os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


def create_exe(outpath, c_code=None):
    """Creates an executable file in the given location."""
    assert not os.path.exists(outpath), outpath
    if c_code:
        if not which("gcc"):
            raise ValueError("gcc is not installed")
        if isinstance(c_code, bool):        # c_code is True
            c_code = textwrap.dedent(
                """
                #include <unistd.h>
                int main() {
                    pause();
                    return 1;
                }
                """)
        assert isinstance(c_code, str), c_code
        with open(get_testfn(suffix='.c'), 'wt') as f:
            f.write(c_code)
        try:
            subprocess.check_call(["gcc", f.name, "-o", outpath])
        finally:
            safe_rmpath(f.name)
    else:
        # copy python executable
        shutil.copyfile(PYTHON_EXE, outpath)
        if POSIX:
            st = os.stat(outpath)
            os.chmod(outpath, st.st_mode | stat.S_IEXEC)


def get_testfn(suffix="", dir=None):
    """Return an absolute pathname of a file or dir that did not
    exist at the time this call is made. Also schedule it for safe
    deletion at interpreter exit. It's technically racy but probably
    not really due to the time variant.
    """
    timer = getattr(time, 'perf_counter', time.time)
    while True:
        prefix = "%s%.9f-" % (TESTFN_PREFIX, timer())
        name = tempfile.mktemp(prefix=prefix, suffix=suffix, dir=dir)
        if not os.path.exists(name):  # also include dirs
            return os.path.realpath(name)  # needed for OSX


# ===================================================================
# --- testing
# ===================================================================


class TestCase(unittest.TestCase):

    # Print a full path representation of the single unit tests
    # being run.
    def __str__(self):
        fqmod = self.__class__.__module__
        if not fqmod.startswith('psutil.'):
            fqmod = 'psutil.tests.' + fqmod
        return "%s.%s.%s" % (
            fqmod, self.__class__.__name__, self._testMethodName)

    # assertRaisesRegexp renamed to assertRaisesRegex in 3.3;
    # add support for the new name.
    if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
        assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


# monkey patch default unittest.TestCase
unittest.TestCase = TestCase


class PsutilTestCase(TestCase):
    """Test class providing auto-cleanup wrappers on top of process
    test utilities.
    """

    def get_testfn(self, suffix="", dir=None):
        fname = get_testfn(suffix=suffix, dir=dir)
        self.addCleanup(safe_rmpath, fname)
        return fname

    def spawn_testproc(self, *args, **kwds):
        sproc = spawn_testproc(*args, **kwds)
        self.addCleanup(terminate, sproc)
        return sproc

    def spawn_children_pair(self):
        child1, child2 = spawn_children_pair()
        self.addCleanup(terminate, child2)
        self.addCleanup(terminate, child1)  # executed first
        return (child1, child2)

    def spawn_zombie(self):
        parent, zombie = spawn_zombie()
        self.addCleanup(terminate, zombie)
        self.addCleanup(terminate, parent)  # executed first
        return (parent, zombie)

    def pyrun(self, *args, **kwds):
        sproc, srcfile = pyrun(*args, **kwds)
        self.addCleanup(safe_rmpath, srcfile)
        self.addCleanup(terminate, sproc)  # executed first
        return sproc

    def assertProcessGone(self, proc):
        self.assertRaises(psutil.NoSuchProcess, psutil.Process, proc.pid)
        if isinstance(proc, (psutil.Process, psutil.Popen)):
            assert not proc.is_running()
            self.assertRaises(psutil.NoSuchProcess, proc.status)
            proc.wait(timeout=0)  # assert not raise TimeoutExpired
        assert not psutil.pid_exists(proc.pid), proc.pid
        self.assertNotIn(proc.pid, psutil.pids())


@unittest.skipIf(PYPY, "unreliable on PYPY")
class TestMemoryLeak(PsutilTestCase):
    """Test framework class for detecting function memory leaks (typically
    functions implemented in C).
    It does so by calling a function many times, and checks whether the
    process memory usage increased before and after having called the
    function repeadetly.
    Note that sometimes this may produce false positives.
    PyPy appears to be completely unstable for this framework, probably
    because of how its JIT handles memory, so tests on PYPY are
    automatically skipped.
    """
    # Configurable class attrs.
    times = 1200
    warmup_times = 10
    tolerance = 4096  # memory
    retry_for = 3.0  # seconds
    verbose = True

    def setUp(self):
        self._thisproc = psutil.Process()
        gc.collect()

    def _get_mem(self):
        # USS is the closest thing we have to "real" memory usage and it
        # should be less likely to produce false positives.
        mem = self._thisproc.memory_full_info()
        return getattr(mem, "uss", mem.rss)

    def _call(self, fun):
        return fun()

    def _itercall(self, fun, iterator):
        """Get 2 distinct memory samples, before and after having
        called fun repeadetly, and return the memory difference.
        """
        ncalls = 0
        gc.collect()
        mem1 = self._get_mem()
        for x in iterator:
            ret = self._call(fun)
            ncalls += 1
            del x, ret
        gc.collect()
        mem2 = self._get_mem()
        self.assertEqual(gc.garbage, [])
        diff = mem2 - mem1
        if diff < 0:
            self._log("negative memory diff -%s" % (bytes2human(abs(diff))))
        return (diff, ncalls)

    def _call_ntimes(self, fun, times):
        return self._itercall(fun, range(times))[0]

    def _call_for(self, fun, secs):
        def iterator(secs):
            stop_at = time.time() + secs
            while time.time() < stop_at:
                yield
        return self._itercall(fun, iterator(secs))

    def _log(self, msg):
        if self.verbose:
            print_color(msg, color="yellow", file=sys.stderr)

    def execute(self, fun, times=times, warmup_times=warmup_times,
                tolerance=tolerance, retry_for=retry_for):
        """Test a callable."""
        if times <= 0:
            raise ValueError("times must be > 0")
        if warmup_times < 0:
            raise ValueError("warmup_times must be >= 0")
        if tolerance is not None and tolerance < 0:
            raise ValueError("tolerance must be >= 0")
        if retry_for is not None and retry_for < 0:
            raise ValueError("retry_for must be >= 0")

        # warm up
        self._call_ntimes(fun, warmup_times)
        mem1 = self._call_ntimes(fun, times)

        if mem1 > tolerance:
            # This doesn't necessarily mean we have a leak yet.
            # At this point we assume that after having called the
            # function so many times the memory usage is stabilized
            # and if there are no leaks it should not increase
            # anymore. Let's keep calling fun for N more seconds and
            # fail if we notice any difference (ignore tolerance).
            msg = "+%s after %s calls; try calling fun for another %s secs" % (
                bytes2human(mem1), times, retry_for)
            if not retry_for:
                raise self.fail(msg)
            else:
                self._log(msg)

            mem2, ncalls = self._call_for(fun, retry_for)
            if mem2 > mem1:
                # failure
                msg = "+%s memory increase after %s calls; " % (
                    bytes2human(mem1), times)
                msg += "+%s after another %s calls over %s secs" % (
                    bytes2human(mem2), ncalls, retry_for)
                raise self.fail(msg)

    def execute_w_exc(self, exc, fun, **kwargs):
        """Convenience method to test a callable while making sure it
        raises an exception on every call.
        """
        def call():
            self.assertRaises(exc, fun)

        self.execute(call, **kwargs)


class process_namespace:
    """A container that lists all the method names of the Process class
    + some reasonable parameters to be called with.
    Utilities such as parent(), children() and as_dict() are excluded.
    Used by those tests who wish to call all Process methods in one shot
    (and e.g. make sure they all raise NoSuchProcess).
    """

    getters = []
    for _name in psutil._as_dict_attrnames:
        if _name == 'rlimit':
            getters.append((_name, (psutil.RLIMIT_NOFILE, ), {}))
        elif _name == 'memory_maps':
            getters.append((_name, (), {'grouped': False}))
        elif _name == 'connections':
            getters.append((_name, (), {'kind': 'all'}))
        elif _name == 'pid':
            continue
        else:
            getters.append((_name, (), {}))

    setters = []
    if POSIX:
        setters.append(('nice', (0, ), {}))
    else:
        setters.append(('nice', (psutil.NORMAL_PRIORITY_CLASS, ), {}))
    if HAS_RLIMIT:
        setters.append(('rlimit', (psutil.RLIMIT_NOFILE, (255, 255)), {}))
    if HAS_IONICE:
        if LINUX:
            setters.append(('ionice', (), {'ioclass': psutil.IOPRIO_CLASS_IDLE,
                                           'value': 0}))
        else:
            setters.append(('ionice', (psutil.IOPRIO_HIGH, ), {}))
    if HAS_CPU_AFFINITY:
        setters.append(('cpu_affinity', ([0], ), {}))

    killers = [
        ('send_signal', (signal.SIGTERM, ), {}),
        ('suspend', (), {}),
        ('resume', (), {}),
        ('terminate', (), {}),
        ('kill', (), {})]
    if WINDOWS:
        killers.append(('send_signal', (signal.CTRL_C_EVENT, ), {}))
        killers.append(('send_signal', (signal.CTRL_BREAK_EVENT, ), {}))

    ignored = [
        ('as_dict', (), {}),
        ('children', (), {'recursive': True}),
        ('is_running', (), {}),
        ('memory_info_ex', (), {}),
        ('oneshot', (), {}),
        ('parent', (), {}),
        ('parents', (), {}),
        ('pid', (), {}),
        ('wait', (), {'timeout': 0}),
    ]

    all = getters + setters + killers
    del _name

    @staticmethod
    def clear_cache(proc):
        """Clear the cache of a Process instance."""
        proc._init(proc.pid, _ignore_nsp=True)

    @classmethod
    def _test_this(cls):
        all_names = set(x[0] for x in cls.all)
        ignored_names = set(x[0] for x in cls.ignored)
        for n in [x for x in dir(psutil.Process) if not x.startswith('_') and
                  x not in ignored_names]:
            if n not in all_names:
                raise RuntimeError('Process.%s is uncovered' % n)


process_namespace._test_this()


def serialrun(klass):
    """A decorator to mark a TestCase class. When running parallel tests,
    class' unit tests will be run serially (1 process).
    """
    # assert issubclass(klass, unittest.TestCase), klass
    assert inspect.isclass(klass), klass
    klass._serialrun = True
    return klass


def retry_on_failure(retries=NO_RETRIES):
    """Decorator which runs a test function and retries N times before
    actually failing.
    """
    def logfun(exc):
        print("%r, retrying" % exc, file=sys.stderr)  # NOQA

    return retry(exception=AssertionError, timeout=None, retries=retries,
                 logfun=logfun)


def skip_on_access_denied(only_if=None):
    """Decorator to Ignore AccessDenied exceptions."""
    def decorator(fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            except psutil.AccessDenied:
                if only_if is not None:
                    if not only_if:
                        raise
                raise unittest.SkipTest("raises AccessDenied")
        return wrapper
    return decorator


def skip_on_not_implemented(only_if=None):
    """Decorator to Ignore NotImplementedError exceptions."""
    def decorator(fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            try:
                return fun(*args, **kwargs)
            except NotImplementedError:
                if only_if is not None:
                    if not only_if:
                        raise
                msg = "%r was skipped because it raised NotImplementedError" \
                      % fun.__name__
                raise unittest.SkipTest(msg)
        return wrapper
    return decorator


# ===================================================================
# --- network
# ===================================================================


def get_free_port(host='127.0.0.1'):
    """Return an unused TCP port."""
    with contextlib.closing(socket.socket()) as sock:
        sock.bind((host, 0))
        return sock.getsockname()[1]


def bind_socket(family=AF_INET, type=SOCK_STREAM, addr=None):
    """Binds a generic socket."""
    if addr is None and family in (AF_INET, AF_INET6):
        addr = ("", 0)
    sock = socket.socket(family, type)
    try:
        if os.name not in ('nt', 'cygwin'):
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        if type == socket.SOCK_STREAM:
            sock.listen(5)
        return sock
    except Exception:
        sock.close()
        raise


def bind_unix_socket(name, type=socket.SOCK_STREAM):
    """Bind a UNIX socket."""
    assert psutil.POSIX
    assert not os.path.exists(name), name
    sock = socket.socket(socket.AF_UNIX, type)
    try:
        sock.bind(name)
        if type == socket.SOCK_STREAM:
            sock.listen(5)
    except Exception:
        sock.close()
        raise
    return sock


def tcp_socketpair(family, addr=("", 0)):
    """Build a pair of TCP sockets connected to each other.
    Return a (server, client) tuple.
    """
    with contextlib.closing(socket.socket(family, SOCK_STREAM)) as ll:
        ll.bind(addr)
        ll.listen(5)
        addr = ll.getsockname()
        c = socket.socket(family, SOCK_STREAM)
        try:
            c.connect(addr)
            caddr = c.getsockname()
            while True:
                a, addr = ll.accept()
                # check that we've got the correct client
                if addr == caddr:
                    return (a, c)
                a.close()
        except OSError:
            c.close()
            raise


def unix_socketpair(name):
    """Build a pair of UNIX sockets connected to each other through
    the same UNIX file name.
    Return a (server, client) tuple.
    """
    assert psutil.POSIX
    server = client = None
    try:
        server = bind_unix_socket(name, type=socket.SOCK_STREAM)
        server.setblocking(0)
        client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        client.setblocking(0)
        client.connect(name)
        # new = server.accept()
    except Exception:
        if server is not None:
            server.close()
        if client is not None:
            client.close()
        raise
    return (server, client)


@contextlib.contextmanager
def create_sockets():
    """Open as many socket families / types as possible."""
    socks = []
    fname1 = fname2 = None
    try:
        socks.append(bind_socket(socket.AF_INET, socket.SOCK_STREAM))
        socks.append(bind_socket(socket.AF_INET, socket.SOCK_DGRAM))
        if supports_ipv6():
            socks.append(bind_socket(socket.AF_INET6, socket.SOCK_STREAM))
            socks.append(bind_socket(socket.AF_INET6, socket.SOCK_DGRAM))
        if POSIX and HAS_CONNECTIONS_UNIX:
            fname1 = get_testfn()
            fname2 = get_testfn()
            s1, s2 = unix_socketpair(fname1)
            s3 = bind_unix_socket(fname2, type=socket.SOCK_DGRAM)
            for s in (s1, s2, s3):
                socks.append(s)
        yield socks
    finally:
        for s in socks:
            s.close()
        for fname in (fname1, fname2):
            if fname is not None:
                safe_rmpath(fname)


def check_net_address(addr, family):
    """Check a net address validity. Supported families are IPv4,
    IPv6 and MAC addresses.
    """
    import ipaddress  # python >= 3.3 / requires "pip install ipaddress"
    if enum and PY3:
        assert isinstance(family, enum.IntEnum), family
    if family == socket.AF_INET:
        octs = [int(x) for x in addr.split('.')]
        assert len(octs) == 4, addr
        for num in octs:
            assert 0 <= num <= 255, addr
        if not PY3:
            addr = unicode(addr)
        ipaddress.IPv4Address(addr)
    elif family == socket.AF_INET6:
        assert isinstance(addr, str), addr
        if not PY3:
            addr = unicode(addr)
        ipaddress.IPv6Address(addr)
    elif family == psutil.AF_LINK:
        assert re.match(r'([a-fA-F0-9]{2}[:|\-]?){6}', addr) is not None, addr
    else:
        raise ValueError("unknown family %r", family)


# ===================================================================
# --- compatibility
# ===================================================================


def reload_module(module):
    """Backport of importlib.reload of Python 3.3+."""
    try:
        import importlib
        if not hasattr(importlib, 'reload'):  # python <=3.3
            raise ImportError
    except ImportError:
        import imp
        return imp.reload(module)
    else:
        return importlib.reload(module)


def import_module_by_path(path):
    name = os.path.splitext(os.path.basename(path))[0]
    if sys.version_info[0] == 2:
        import imp
        return imp.load_source(name, path)
    elif sys.version_info[:2] <= (3, 4):
        from importlib.machinery import SourceFileLoader
        return SourceFileLoader(name, path).load_module()
    else:
        import importlib.util
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod


# ===================================================================
# --- others
# ===================================================================


def warn(msg):
    """Raise a warning msg."""
    warnings.warn(msg, UserWarning)


def is_namedtuple(x):
    """Check if object is an instance of namedtuple."""
    t = type(x)
    b = t.__bases__
    if len(b) != 1 or b[0] != tuple:
        return False
    f = getattr(t, '_fields', None)
    if not isinstance(f, tuple):
        return False
    return all(type(n) == str for n in f)


if POSIX:
    @contextlib.contextmanager
    def copyload_shared_lib(suffix=""):
        """Ctx manager which picks up a random shared CO lib used
        by this process, copies it in another location and loads it
        in memory via ctypes. Return the new absolutized path.
        """
        exe = 'pypy' if PYPY else 'python'
        ext = ".so"
        dst = get_testfn(suffix=suffix + ext)
        libs = [x.path for x in psutil.Process().memory_maps() if
                os.path.splitext(x.path)[1] == ext and
                exe in x.path.lower()]
        src = random.choice(libs)
        shutil.copyfile(src, dst)
        try:
            ctypes.CDLL(dst)
            yield dst
        finally:
            safe_rmpath(dst)
else:
    @contextlib.contextmanager
    def copyload_shared_lib(suffix=""):
        """Ctx manager which picks up a random shared DLL lib used
        by this process, copies it in another location and loads it
        in memory via ctypes.
        Return the new absolutized, normcased path.
        """
        from ctypes import wintypes
        from ctypes import WinError
        ext = ".dll"
        dst = get_testfn(suffix=suffix + ext)
        libs = [x.path for x in psutil.Process().memory_maps() if
                x.path.lower().endswith(ext) and
                'python' in os.path.basename(x.path).lower() and
                'wow64' not in x.path.lower()]
        if PYPY and not libs:
            libs = [x.path for x in psutil.Process().memory_maps() if
                    'pypy' in os.path.basename(x.path).lower()]
        src = random.choice(libs)
        shutil.copyfile(src, dst)
        cfile = None
        try:
            cfile = ctypes.WinDLL(dst)
            yield dst
        finally:
            # Work around OverflowError:
            # - https://ci.appveyor.com/project/giampaolo/psutil/build/1207/
            #       job/o53330pbnri9bcw7
            # - http://bugs.python.org/issue30286
            # - http://stackoverflow.com/questions/23522055
            if cfile is not None:
                FreeLibrary = ctypes.windll.kernel32.FreeLibrary
                FreeLibrary.argtypes = [wintypes.HMODULE]
                ret = FreeLibrary(cfile._handle)
                if ret == 0:
                    WinError()
            safe_rmpath(dst)


# ===================================================================
# --- Exit funs (first is executed last)
# ===================================================================


# this is executed first
@atexit.register
def cleanup_test_procs():
    reap_children(recursive=True)


# atexit module does not execute exit functions in case of SIGTERM, which
# gets sent to test subprocesses, which is a problem if they import this
# module. With this it will. See:
# http://grodola.blogspot.com/
#     2016/02/how-to-always-execute-exit-functions-in-py.html
if POSIX:
    signal.signal(signal.SIGTERM, lambda sig, frame: sys.exit(sig))
