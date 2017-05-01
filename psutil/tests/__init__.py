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
import re
import shutil
import socket
import ssl
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
from socket import SOCK_DGRAM
from socket import SOCK_STREAM

try:
    from urllib.request import urlopen  # py3
except ImportError:
    from urllib2 import urlopen

import psutil
from psutil import POSIX
from psutil import WINDOWS
from psutil._common import supports_ipv6
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
    import mock  # NOQA - requires "pip install mock"

if sys.version_info >= (3, 4):
    import enum
else:
    enum = None

if PY3:
    import importlib
    # python <=3.3
    if not hasattr(importlib, 'reload'):
        import imp as importlib
else:
    import imp as importlib


__all__ = [
    # constants
    'APPVEYOR', 'DEVNULL', 'GLOBAL_TIMEOUT', 'MEMORY_TOLERANCE', 'NO_RETRIES',
    'PYPY', 'PYTHON', 'ROOT_DIR', 'SCRIPTS_DIR', 'TESTFILE_PREFIX',
    'TESTFN', 'TESTFN_UNICODE', 'TOX', 'TRAVIS', 'VALID_PROC_STATUSES',
    'VERBOSITY',
    "HAS_CPU_AFFINITY", "HAS_CPU_FREQ", "HAS_ENVIRON", "HAS_PROC_IO_COUNTERS",
    "HAS_IONICE", "HAS_MEMORY_MAPS", "HAS_PROC_CPU_NUM", "HAS_RLIMIT",
    "HAS_SENSORS_BATTERY", "HAS_BATTERY""HAS_SENSORS_FANS",
    "HAS_SENSORS_TEMPERATURES", "HAS_MEMORY_FULL_INFO",
    # classes
    'ThreadTask'
    # test utils
    'unittest', 'cleanup', 'skip_on_access_denied', 'skip_on_not_implemented',
    'retry_before_failing', 'run_test_module_by_name',
    # install utils
    'install_pip', 'install_test_deps',
    # fs utils
    'chdir', 'safe_rmpath', 'create_exe', 'decode_path', 'encode_path',
    # subprocesses
    'pyrun', 'reap_children', 'get_test_subprocess',
    'create_proc_children_pair',
    # os
    'get_winver', 'get_kernel_version',
    # sync primitives
    'call_until', 'wait_for_pid', 'wait_for_file',
    # network
    'check_connection_ntuple', 'check_net_address',
    'get_free_port', 'unix_socket_path', 'bind_socket', 'bind_unix_socket',
    'tcp_socketpair', 'unix_socketpair', 'create_sockets',
    # others
    'warn', 'copyload_shared_lib', 'is_namedtuple',
]


# ===================================================================
# --- constants
# ===================================================================

# --- platforms

TOX = os.getenv('TOX') or '' in ('1', 'true')
PYPY = '__pypy__' in sys.builtin_module_names
WIN_VISTA = (6, 0, 0) if WINDOWS else None
# whether we're running this test suite on Travis (https://travis-ci.org/)
TRAVIS = bool(os.environ.get('TRAVIS'))
# whether we're running this test suite on Appveyor for Windows
# (http://www.appveyor.com/)
APPVEYOR = bool(os.environ.get('APPVEYOR'))

# --- configurable defaults

# how many times retry_before_failing() decorator will retry
NO_RETRIES = 10
# bytes tolerance for system-wide memory related tests
MEMORY_TOLERANCE = 500 * 1024  # 500KB
# the timeout used in functions which have to wait
GLOBAL_TIMEOUT = 3
# test output verbosity
VERBOSITY = 1 if os.getenv('SILENT') or TOX else 2
# be more tolerant if we're on travis / appveyor in order to avoid
# false positives
if TRAVIS or APPVEYOR:
    NO_RETRIES *= 3
    GLOBAL_TIMEOUT *= 3

# --- files

TESTFILE_PREFIX = '$testfn'
TESTFN = os.path.join(os.path.realpath(os.getcwd()), TESTFILE_PREFIX)
_TESTFN = TESTFN + '-internal'
TESTFN_UNICODE = TESTFN + u("-ƒőő")
ASCII_FS = sys.getfilesystemencoding().lower() in ('ascii', 'us-ascii')

# --- paths

HERE = os.path.abspath(os.path.dirname(__file__))
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')

# --- support

HAS_CPU_AFFINITY = hasattr(psutil.Process, "cpu_affinity")
HAS_CPU_FREQ = hasattr(psutil, "cpu_freq")
HAS_ENVIRON = hasattr(psutil.Process, "environ")
HAS_PROC_IO_COUNTERS = hasattr(psutil.Process, "io_counters")
HAS_IONICE = hasattr(psutil.Process, "ionice")
HAS_MEMORY_FULL_INFO = 'uss' in psutil.Process().memory_full_info()._fields
HAS_MEMORY_MAPS = hasattr(psutil.Process, "memory_maps")
HAS_PROC_CPU_NUM = hasattr(psutil.Process, "cpu_num")
HAS_RLIMIT = hasattr(psutil.Process, "rlimit")
HAS_SENSORS_BATTERY = hasattr(psutil, "sensors_battery")
HAS_BATTERY = HAS_SENSORS_BATTERY and psutil.sensors_battery()
HAS_SENSORS_FANS = hasattr(psutil, "sensors_fans")
HAS_SENSORS_TEMPERATURES = hasattr(psutil, "sensors_temperatures")

# --- misc

PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')
VALID_PROC_STATUSES = [getattr(psutil, x) for x in dir(psutil)
                       if x.startswith('STATUS_')]
GET_PIP_URL = "https://bootstrap.pypa.io/get-pip.py"
AF_UNIX = getattr(socket, "AF_UNIX", object())
SOCK_SEQPACKET = getattr(socket, "SOCK_SEQPACKET", object())

TEST_DEPS = []
if sys.version_info[:2] == (2, 6):
    TEST_DEPS.extend(["ipaddress", "unittest2", "argparse", "mock==1.0.1"])
elif sys.version_info[:2] == (2, 7) or sys.version_info[:2] <= (3, 2):
    TEST_DEPS.extend(["ipaddress", "mock"])
elif sys.version_info[:2] == (3, 3):
    TEST_DEPS.extend(["ipaddress"])

_subprocesses_started = set()
_pids_started = set()
_testfiles = set()


# ===================================================================
# --- classes
# ===================================================================


class ThreadTask(threading.Thread):
    """A thread object used for running process thread tests."""

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = False
        self._interval = 0.001
        self._flag = threading.Event()

    def __repr__(self):
        name = self.__class__.__name__
        return '<%s running=%s at %#x>' % (name, self._running, id(self))

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


def get_test_subprocess(cmd=None, **kwds):
    """Creates a python subprocess which does nothing for 60 secs and
    return it as subprocess.Popen instance.
    If "cmd" is specified that is used instead of python.
    By default stdout and stderr are redirected to /dev/null.
    It also attemps to make sure the process is in a reasonably
    initialized state.
    """
    kwds.setdefault("stdin", DEVNULL)
    kwds.setdefault("stdout", DEVNULL)
    if cmd is None:
        safe_rmpath(_TESTFN)
        pyline = "from time import sleep;"
        pyline += "open(r'%s', 'w').close();" % _TESTFN
        pyline += "sleep(60);"
        cmd = [PYTHON, "-c", pyline]
        sproc = subprocess.Popen(cmd, **kwds)
        _subprocesses_started.add(sproc)
        wait_for_file(_TESTFN, delete=True, empty=True)
    else:
        sproc = subprocess.Popen(cmd, **kwds)
        _subprocesses_started.add(sproc)
        wait_for_pid(sproc.pid)
    return sproc


def create_proc_children_pair():
    """Create a subprocess which creates another one as in:
    A (us) -> B (child) -> C (grandchild).
    Return a (child, grandchild) tuple.
    The 2 processes are fully initialized and will live for 60 secs.
    """
    s = textwrap.dedent("""\
        import subprocess, os, sys, time
        PYTHON = os.path.realpath(sys.executable)
        s = "import os, time;"
        s += "f = open('%s', 'w');"
        s += "f.write(str(os.getpid()));"
        s += "f.close();"
        s += "time.sleep(60);"
        subprocess.Popen([PYTHON, '-c', s])
        time.sleep(60)
        """ % _TESTFN)
    child1 = psutil.Process(pyrun(s).pid)
    data = wait_for_file(_TESTFN, delete=False, empty=False)
    os.remove(_TESTFN)
    child2_pid = int(data)
    _pids_started.add(child2_pid)
    child2 = psutil.Process(child2_pid)
    return (child1, child2)


def pyrun(src):
    """Run python 'src' code in a separate interpreter.
    Returns a subprocess.Popen instance.
    """
    if PY3:
        src = bytes(src, 'ascii')
    with tempfile.NamedTemporaryFile(
            prefix=TESTFILE_PREFIX, delete=False) as f:
        _testfiles.add(f.name)
        f.write(src)
        f.flush()
        subp = get_test_subprocess([PYTHON, f.name], stdout=None,
                                   stderr=None)
        wait_for_pid(subp.pid)
        return subp


def sh(cmd):
    """run cmd in a subprocess and return its output.
    raises RuntimeError on error.
    """
    shell = True if isinstance(cmd, (str, unicode)) else False
    p = subprocess.Popen(cmd, shell=shell, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE, universal_newlines=True)
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
    # Get the children here, before terminating the children sub
    # processes as we don't want to lose the intermediate reference
    # in case of grandchildren.
    if recursive:
        children = set(psutil.Process().children(recursive=True))
    else:
        children = set()

    # Terminate subprocess.Popen instances "cleanly" by closing their
    # fds and wiat()ing for them in order to avoid zombies.
    subprocs = _subprocesses_started.copy()
    _subprocesses_started.clear()
    for subp in subprocs:
        try:
            subp.terminate()
        except OSError as err:
            if err.errno != errno.ESRCH:
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
            except OSError as err:
                if err.errno != errno.ECHILD:
                    raise

    # Terminate started pids.
    for pid in _pids_started:
        try:
            p = psutil.Process(pid)
        except psutil.NoSuchProcess:
            pass
        else:
            children.add(p)
    _pids_started.clear()

    # Terminate grandchildren.
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


# ===================================================================
# --- OS
# ===================================================================


if not POSIX:
    def get_kernel_version():
        return ()
else:
    def get_kernel_version():
        """Return a tuple such as (2, 6, 36)."""
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


if not WINDOWS:
    def get_winver():
        raise NotImplementedError("not a Windows OS")
else:
    def get_winver():
        wv = sys.getwindowsversion()
        if hasattr(wv, 'service_pack_major'):  # python >= 2.7
            sp = wv.service_pack_major or 0
        else:
            r = re.search("\s\d$", wv[4])
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
                 logfun=lambda s: print(s, file=sys.stderr),
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
                except self.exception as _:
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
        os.remove(fname)
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
    try:
        st = os.stat(path)
        if stat.S_ISDIR(st.st_mode):
            os.rmdir(path)
        else:
            os.remove(path)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise


def safe_mkdir(dir):
    "Convenience function for creating a directory"
    try:
        os.mkdir(dir)
    except OSError as err:
        if err.errno != errno.EEXIST:
            raise


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
        if c_code is None:
            c_code = textwrap.dedent(
                """
                #include <unistd.h>
                int main() {
                    pause();
                    return 1;
                }
                """)
        with tempfile.NamedTemporaryFile(
                suffix='.c', delete=False, mode='wt') as f:
            f.write(c_code)
        try:
            subprocess.check_call(["gcc", f.name, "-o", outpath])
        finally:
            safe_rmpath(f.name)
    else:
        # copy python executable
        shutil.copyfile(sys.executable, outpath)
        if POSIX:
            st = os.stat(outpath)
            os.chmod(outpath, st.st_mode | stat.S_IEXEC)


# ===================================================================
# --- testing
# ===================================================================


class TestCase(unittest.TestCase):

    # Print a full path representation of the single unit tests
    # being run.
    def __str__(self):
        return "%s.%s.%s" % (
            self.__class__.__module__, self.__class__.__name__,
            self._testMethodName)

    # assertRaisesRegexp renamed to assertRaisesRegex in 3.3;
    # add support for the new name.
    if not hasattr(unittest.TestCase, 'assertRaisesRegex'):
        assertRaisesRegex = unittest.TestCase.assertRaisesRegexp


# override default unittest.TestCase
unittest.TestCase = TestCase


def get_suite():
    testmodules = [os.path.splitext(x)[0] for x in os.listdir(HERE)
                   if x.endswith('.py') and x.startswith('test_') and not
                   x.startswith('test_memory_leaks')]
    suite = unittest.TestSuite()
    for tm in testmodules:
        # ...so that the full test paths are printed on screen
        tm = "psutil.tests.%s" % tm
        suite.addTest(unittest.defaultTestLoader.loadTestsFromName(tm))
    return suite


def run_suite():
    """Run unit tests."""
    result = unittest.TextTestRunner(verbosity=VERBOSITY).run(get_suite())
    success = result.wasSuccessful()
    sys.exit(0 if success else 1)


def run_test_module_by_name(name):
    # testmodules = [os.path.splitext(x)[0] for x in os.listdir(HERE)
    #                if x.endswith('.py') and x.startswith('test_')]
    name = os.path.splitext(os.path.basename(name))[0]
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)
    success = result.wasSuccessful()
    sys.exit(0 if success else 1)


def retry_before_failing(retries=NO_RETRIES):
    """Decorator which runs a test function and retries N times before
    actually failing.
    """
    return retry(exception=AssertionError, timeout=None, retries=retries)


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
                msg = "%r was skipped because it raised AccessDenied" \
                      % fun.__name__
                raise unittest.SkipTest(msg)
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


def cleanup():
    for name in os.listdir('.'):
        if name.startswith(TESTFILE_PREFIX):
            try:
                safe_rmpath(name)
            except UnicodeEncodeError as exc:
                warn(exc)
    for path in _testfiles:
        safe_rmpath(path)


atexit.register(cleanup)
atexit.register(lambda: DEVNULL.close())


# ===================================================================
# --- install
# ===================================================================


def install_pip():
    """Install pip. Returns the exit code of the subprocess."""
    try:
        import pip  # NOQA
    except ImportError:
        f = tempfile.NamedTemporaryFile(suffix='.py')
        with contextlib.closing(f):
            print("downloading %s to %s" % (GET_PIP_URL, f.name))
            if hasattr(ssl, '_create_unverified_context'):
                ctx = ssl._create_unverified_context()
            else:
                ctx = None
            kwargs = dict(context=ctx) if ctx else {}
            req = urlopen(GET_PIP_URL, **kwargs)
            data = req.read()
            f.write(data)
            f.flush()

            print("installing pip")
            code = os.system('%s %s --user' % (sys.executable, f.name))
            return code


def install_test_deps(deps=None):
    """Install test dependencies via pip."""
    if deps is None:
        deps = TEST_DEPS
    deps = set(deps)
    if deps:
        is_venv = hasattr(sys, 'real_prefix')
        opts = "--user" if not is_venv else ""
        install_pip()
        code = os.system('%s -m pip install %s --upgrade %s' % (
            sys.executable, opts, " ".join(deps)))
        return code


# ===================================================================
# --- network
# ===================================================================


def get_free_port(host='127.0.0.1'):
    """Return an unused TCP port."""
    with contextlib.closing(socket.socket()) as sock:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, 0))
        return sock.getsockname()[1]


@contextlib.contextmanager
def unix_socket_path(suffix=""):
    """A context manager which returns a non-existent file name
    and tries to delete it on exit.
    """
    assert psutil.POSIX
    path = tempfile.mktemp(prefix=TESTFILE_PREFIX, suffix=suffix)
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
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind(addr)
        if type == socket.SOCK_STREAM:
            sock.listen(10)
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
            sock.listen(10)
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
        ll.listen(10)
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
        if POSIX:
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
        assert re.match('([a-fA-F0-9]{2}[:|\-]?){6}', addr) is not None, addr
    else:
        raise ValueError("unknown family %r", family)


def check_connection_ntuple(conn):
    """Check validity of a connection namedtuple."""
    # check ntuple
    assert len(conn) in (6, 7), conn
    has_pid = len(conn) == 7
    has_fd = getattr(conn, 'fd', -1) != -1
    assert conn[0] == conn.fd
    assert conn[1] == conn.family
    assert conn[2] == conn.type
    assert conn[3] == conn.laddr
    assert conn[4] == conn.raddr
    assert conn[5] == conn.status
    if has_pid:
        assert conn[6] == conn.pid

    # check fd
    if has_fd:
        assert conn.fd > 0, conn
        if hasattr(socket, 'fromfd') and not WINDOWS:
            try:
                dupsock = socket.fromfd(conn.fd, conn.family, conn.type)
            except (socket.error, OSError) as err:
                if err.args[0] != errno.EBADF:
                    raise
            else:
                with contextlib.closing(dupsock):
                    assert dupsock.family == conn.family
                    assert dupsock.type == conn.type

    # check family
    assert conn.family in (AF_INET, AF_INET6, AF_UNIX), repr(conn.family)
    if conn.family in (AF_INET, AF_INET6):
        # actually try to bind the local socket; ignore IPv6
        # sockets as their address might be represented as
        # an IPv4-mapped-address (e.g. "::127.0.0.1")
        # and that's rejected by bind()
        if conn.family == AF_INET:
            s = socket.socket(conn.family, conn.type)
            with contextlib.closing(s):
                try:
                    s.bind((conn.laddr[0], 0))
                except socket.error as err:
                    if err.errno != errno.EADDRNOTAVAIL:
                        raise
    elif conn.family == AF_UNIX:
        assert conn.status == psutil.CONN_NONE, conn.status

    # check type (SOCK_SEQPACKET may happen in case of AF_UNIX socks)
    assert conn.type in (SOCK_STREAM, SOCK_DGRAM, SOCK_SEQPACKET), \
        repr(conn.type)
    if conn.type == SOCK_DGRAM:
        assert conn.status == psutil.CONN_NONE, conn.status

    # check laddr (IP address and port sanity)
    for addr in (conn.laddr, conn.raddr):
        if conn.family in (AF_INET, AF_INET6):
            assert isinstance(addr, tuple), addr
            if not addr:
                continue
            ip, port = addr
            assert isinstance(port, int), port
            assert 0 <= port <= 65535, port
            check_net_address(ip, conn.family)
        elif conn.family == AF_UNIX:
            assert isinstance(addr, str), addr

    # check status
    assert isinstance(conn.status, str), conn
    valids = [getattr(psutil, x) for x in dir(psutil) if x.startswith('CONN_')]
    assert conn.status in valids, conn


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


def copyload_shared_lib(src, dst_prefix=TESTFILE_PREFIX):
    """Given an existing shared so / DLL library copies it in
    another location and loads it via ctypes.
    Return the new path.
    """
    newpath = tempfile.mktemp(prefix=dst_prefix,
                              suffix=os.path.splitext(src)[1])
    shutil.copyfile(src, newpath)
    ctypes.CDLL(newpath)
    return newpath
