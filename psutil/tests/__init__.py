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
import os
import random
import re
import select
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import traceback
import warnings
from socket import AF_INET
from socket import AF_INET6
from socket import SOCK_STREAM

import psutil
from psutil import AIX
from psutil import MACOS
from psutil import POSIX
from psutil import SUNOS
from psutil import WINDOWS
from psutil._common import supports_ipv6
from psutil._compat import ChildProcessError
from psutil._compat import FileExistsError
from psutil._compat import FileNotFoundError
from psutil._compat import PY3
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
    'APPVEYOR', 'DEVNULL', 'GLOBAL_TIMEOUT', 'MEMORY_TOLERANCE', 'NO_RETRIES',
    'PYPY', 'PYTHON_EXE', 'ROOT_DIR', 'SCRIPTS_DIR', 'TESTFILE_PREFIX',
    'TESTFN', 'TESTFN_UNICODE', 'TOX', 'TRAVIS', 'CIRRUS', 'CI_TESTING',
    'VALID_PROC_STATUSES',
    "HAS_CPU_AFFINITY", "HAS_CPU_FREQ", "HAS_ENVIRON", "HAS_PROC_IO_COUNTERS",
    "HAS_IONICE", "HAS_MEMORY_MAPS", "HAS_PROC_CPU_NUM", "HAS_RLIMIT",
    "HAS_SENSORS_BATTERY", "HAS_BATTERY", "HAS_SENSORS_FANS",
    "HAS_SENSORS_TEMPERATURES", "HAS_MEMORY_FULL_INFO",
    # subprocesses
    'pyrun', 'reap_children', 'get_test_subprocess', 'create_zombie_proc',
    'create_proc_children_pair',
    # threads
    'ThreadTask'
    # test utils
    'unittest', 'skip_on_access_denied', 'skip_on_not_implemented',
    'retry_on_failure',
    # install utils
    'install_pip', 'install_test_deps',
    # fs utils
    'chdir', 'safe_rmpath', 'create_exe', 'decode_path', 'encode_path',
    'unique_filename',
    # os
    'get_winver', 'get_kernel_version',
    # sync primitives
    'call_until', 'wait_for_pid', 'wait_for_file',
    # network
    'check_net_address',
    'get_free_port', 'unix_socket_path', 'bind_socket', 'bind_unix_socket',
    'tcp_socketpair', 'unix_socketpair', 'create_sockets',
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
MEMORY_TOLERANCE = 500 * 1024  # 500KB
# the timeout used in functions which have to wait
GLOBAL_TIMEOUT = 5
# be more tolerant if we're on travis / appveyor in order to avoid
# false positives
if TRAVIS or APPVEYOR:
    NO_RETRIES *= 3
    GLOBAL_TIMEOUT *= 3

# --- files

TESTFILE_PREFIX = '$testfn'
if os.name == 'java':
    # Jython disallows @ in module names
    TESTFILE_PREFIX = '$psutil-test-'
else:
    TESTFILE_PREFIX = '@psutil-test-'
TESTFN = os.path.join(os.path.realpath(os.getcwd()), TESTFILE_PREFIX)
# Disambiguate TESTFN for parallel testing, while letting it remain a valid
# module name.
TESTFN = TESTFN + str(os.getpid())

_TESTFN = TESTFN + '-internal'
TESTFN_UNICODE = TESTFN + u("-ƒőő")
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
VALID_PROC_STATUSES = [getattr(psutil, x) for x in dir(psutil)
                       if x.startswith('STATUS_')]
AF_UNIX = getattr(socket, "AF_UNIX", object())

_subprocesses_started = set()
_pids_started = set()
_testfiles_created = set()


@atexit.register
def cleanup_test_files():
    DEVNULL.close()
    for name in os.listdir(u('.')):
        if isinstance(name, unicode):
            prefix = u(TESTFILE_PREFIX)
        else:
            prefix = TESTFILE_PREFIX
        if name.startswith(prefix):
            try:
                safe_rmpath(name)
            except Exception:
                traceback.print_exc()
    for path in _testfiles_created:
        try:
            safe_rmpath(path)
        except Exception:
            traceback.print_exc()


# this is executed first
@atexit.register
def cleanup_test_procs():
    reap_children(recursive=True)


# ===================================================================
# --- threads
# ===================================================================


class ThreadTask(threading.Thread):
    """A thread task which does nothing expect staying alive."""

    def __init__(self):
        threading.Thread.__init__(self)
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
def get_test_subprocess(cmd=None, **kwds):
    """Creates a python subprocess which does nothing for 60 secs and
    return it as subprocess.Popen instance.
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
        safe_rmpath(_TESTFN)
        pyline = "from time import sleep;" \
                 "open(r'%s', 'w').close();" \
                 "sleep(60);" % _TESTFN
        cmd = [PYTHON_EXE, "-c", pyline]
        sproc = subprocess.Popen(cmd, **kwds)
        _subprocesses_started.add(sproc)
        wait_for_file(_TESTFN, delete=True, empty=True)
    else:
        sproc = subprocess.Popen(cmd, **kwds)
        _subprocesses_started.add(sproc)
        wait_for_pid(sproc.pid)
    return sproc


@_reap_children_on_err
def create_proc_children_pair():
    """Create a subprocess which creates another one as in:
    A (us) -> B (child) -> C (grandchild).
    Return a (child, grandchild) tuple.
    The 2 processes are fully initialized and will live for 60 secs
    and are registered for cleanup on reap_children().
    """
    _TESTFN2 = os.path.basename(_TESTFN) + '2'  # need to be relative
    s = textwrap.dedent("""\
        import subprocess, os, sys, time
        s = "import os, time;"
        s += "f = open('%s', 'w');"
        s += "f.write(str(os.getpid()));"
        s += "f.close();"
        s += "time.sleep(60);"
        p = subprocess.Popen([r'%s', '-c', s])
        p.wait()
        """ % (_TESTFN2, PYTHON_EXE))
    # On Windows if we create a subprocess with CREATE_NO_WINDOW flag
    # set (which is the default) a "conhost.exe" extra process will be
    # spawned as a child. We don't want that.
    if WINDOWS:
        subp = pyrun(s, creationflags=0)
    else:
        subp = pyrun(s)
    child1 = psutil.Process(subp.pid)
    data = wait_for_file(_TESTFN2, delete=False, empty=False)
    safe_rmpath(_TESTFN2)
    child2_pid = int(data)
    _pids_started.add(child2_pid)
    child2 = psutil.Process(child2_pid)
    return (child1, child2)


def create_zombie_proc():
    """Create a zombie process and return its PID."""
    assert psutil.POSIX
    unix_file = tempfile.mktemp(prefix=TESTFILE_PREFIX) if MACOS else TESTFN
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
    with contextlib.closing(socket.socket(socket.AF_UNIX)) as sock:
        sock.settimeout(GLOBAL_TIMEOUT)
        sock.bind(unix_file)
        sock.listen(5)
        pyrun(src)
        conn, _ = sock.accept()
        try:
            select.select([conn.fileno()], [], [], GLOBAL_TIMEOUT)
            zpid = int(conn.recv(1024))
            _pids_started.add(zpid)
            zproc = psutil.Process(zpid)
            call_until(lambda: zproc.status(), "ret == psutil.STATUS_ZOMBIE")
            return zpid
        finally:
            conn.close()


@_reap_children_on_err
def pyrun(src, **kwds):
    """Run python 'src' code string in a separate interpreter.
    Returns a subprocess.Popen instance.
    """
    kwds.setdefault("stdout", None)
    kwds.setdefault("stderr", None)
    with tempfile.NamedTemporaryFile(
            prefix=TESTFILE_PREFIX, mode="wt", delete=False) as f:
        _testfiles_created.add(f.name)
        f.write(src)
        f.flush()
        subp = get_test_subprocess([PYTHON_EXE, f.name], **kwds)
        wait_for_pid(subp.pid)
    return subp


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


def reap_children(recursive=False):
    """Terminate and wait() any subprocess started by this test suite
    and ensure that no zombies stick around to hog resources and
    create problems  when looking for refleaks.

    If resursive is True it also tries to terminate and wait()
    all grandchildren started by this process.
    """
    # This is here to make sure wait_procs() behaves properly and
    # investigate:
    # https://ci.appveyor.com/project/giampaolo/psutil/build/job/
    #     jiq2cgd6stsbtn60
    def assert_gone(pid):
        assert not psutil.pid_exists(pid), pid
        assert pid not in psutil.pids(), pid
        try:
            p = psutil.Process(pid)
            assert not p.is_running(), pid
        except psutil.NoSuchProcess:
            pass
        else:
            assert 0, "pid %s is not gone" % pid

    # Get the children here, before terminating the children sub
    # processes as we don't want to lose the intermediate reference
    # in case of grandchildren.
    if recursive:
        children = set(psutil.Process().children(recursive=True))
    else:
        children = set()

    # Terminate subprocess.Popen instances "cleanly" by closing their
    # fds and wiat()ing for them in order to avoid zombies.
    while _subprocesses_started:
        subp = _subprocesses_started.pop()
        _pids_started.add(subp.pid)
        try:
            subp.terminate()
        except OSError as err:
            if WINDOWS and err.winerror == 6:  # "invalid handle"
                pass
            elif err.errno != errno.ESRCH:
                raise
        if subp.stdout:
            subp.stdout.close()
        if subp.stderr:
            subp.stderr.close()
        try:
            # Flushing a BufferedWriter may raise an error.
            if subp.stdin:
                subp.stdin.close()
        finally:
            # Wait for the process to terminate, to avoid zombies.
            try:
                subp.wait()
            except ChildProcessError:
                pass

    # Terminate started pids.
    while _pids_started:
        pid = _pids_started.pop()
        try:
            p = psutil.Process(pid)
        except psutil.NoSuchProcess:
            assert_gone(pid)
        else:
            children.add(p)

    # Terminate children.
    if children:
        for p in children:
            try:
                p.terminate()
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(children, timeout=GLOBAL_TIMEOUT)
        for p in alive:
            warn("couldn't terminate process %r; attempting kill()" % p)
            try:
                p.kill()
            except psutil.NoSuchProcess:
                pass
        gone, alive = psutil.wait_procs(alive, timeout=GLOBAL_TIMEOUT)
        if alive:
            for p in alive:
                warn("process %r survived kill()" % p)

        for p in children:
            assert_gone(p.pid)


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
        with tempfile.NamedTemporaryFile(
                suffix='.c', delete=False, mode='wt') as f:
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


def unique_filename(prefix=TESTFILE_PREFIX, suffix=""):
    return tempfile.mktemp(prefix=prefix, suffix=suffix)


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


# override default unittest.TestCase
unittest.TestCase = TestCase


def retry_on_failure(retries=NO_RETRIES):
    """Decorator which runs a test function and retries N times before
    actually failing.
    """
    def logfun(exc):
        print("%r, retrying" % exc, file=sys.stderr)

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


@contextlib.contextmanager
def unix_socket_path(suffix=""):
    """A context manager which returns a non-existent file name
    and tries to delete it on exit.
    """
    assert psutil.POSIX
    path = unique_filename(suffix=suffix)
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


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
            fname1 = unix_socket_path().__enter__()
            fname2 = unix_socket_path().__enter__()
            s1, s2 = unix_socketpair(fname1)
            s3 = bind_unix_socket(fname2, type=socket.SOCK_DGRAM)
            # self.addCleanup(safe_rmpath, fname1)
            # self.addCleanup(safe_rmpath, fname2)
            for s in (s1, s2, s3):
                socks.append(s)
        yield socks
    finally:
        for s in socks:
            s.close()
        if fname1 is not None:
            safe_rmpath(fname1)
        if fname2 is not None:
            safe_rmpath(fname2)


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
    def copyload_shared_lib(dst_prefix=TESTFILE_PREFIX):
        """Ctx manager which picks up a random shared CO lib used
        by this process, copies it in another location and loads it
        in memory via ctypes. Return the new absolutized path.
        """
        exe = 'pypy' if PYPY else 'python'
        ext = ".so"
        dst = tempfile.mktemp(prefix=dst_prefix, suffix=ext)
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
    def copyload_shared_lib(dst_prefix=TESTFILE_PREFIX):
        """Ctx manager which picks up a random shared DLL lib used
        by this process, copies it in another location and loads it
        in memory via ctypes.
        Return the new absolutized, normcased path.
        """
        from ctypes import wintypes
        from ctypes import WinError
        ext = ".dll"
        dst = tempfile.mktemp(prefix=dst_prefix, suffix=ext)
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
