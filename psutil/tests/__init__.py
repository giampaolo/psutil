#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""
Test utilities.
"""

import atexit
import contextlib
import errno
import functools
import os
import re
import shutil
import socket
import stat
import subprocess
import sys
import tempfile
import threading
import time
import warnings
from socket import AF_INET
from socket import SOCK_DGRAM
from socket import SOCK_STREAM
try:
    import ipaddress  # python >= 3.3
except ImportError:
    ipaddress = None
try:
    from unittest import mock  # py3
except ImportError:
    import mock  # NOQA - requires "pip install mock"

import psutil
from psutil import LINUX
from psutil import OSX
from psutil import POSIX
from psutil import WINDOWS
from psutil._compat import PY3
from psutil._compat import unicode
from psutil._compat import which

if sys.version_info < (2, 7):
    import unittest2 as unittest  # requires "pip install unittest2"
else:
    import unittest
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


# ===================================================================
# --- Constants
# ===================================================================

# conf for retry_before_failing() decorator
NO_RETRIES = 10
# bytes tolerance for OS memory related tests
MEMORY_TOLERANCE = 500 * 1024  # 500KB
# the timeout used in functions which have to wait
GLOBAL_TIMEOUT = 3

AF_INET6 = getattr(socket, "AF_INET6")
AF_UNIX = getattr(socket, "AF_UNIX", None)
PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')
TESTFN = os.path.join(os.getcwd(), "$testfile")
TESTFN_UNICODE = TESTFN + "ƒőő"
TESTFILE_PREFIX = 'psutil-test-suite-'
TOX = os.getenv('TOX') or '' in ('1', 'true')
PYPY = '__pypy__' in sys.builtin_module_names
if not PY3:
    try:
        TESTFN_UNICODE = unicode(TESTFN_UNICODE, sys.getfilesystemencoding())
    except UnicodeDecodeError:
        TESTFN_UNICODE = TESTFN + "???"

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__),
                           '..', '..'))
SCRIPTS_DIR = os.path.join(ROOT_DIR, 'scripts')

WIN_VISTA = (6, 0, 0) if WINDOWS else None
VALID_PROC_STATUSES = [getattr(psutil, x) for x in dir(psutil)
                       if x.startswith('STATUS_')]
# whether we're running this test suite on Travis (https://travis-ci.org/)
TRAVIS = bool(os.environ.get('TRAVIS'))
# whether we're running this test suite on Appveyor for Windows
# (http://www.appveyor.com/)
APPVEYOR = bool(os.environ.get('APPVEYOR'))

if TRAVIS or 'tox' in sys.argv[0]:
    import ipaddress
if TRAVIS or APPVEYOR:
    GLOBAL_TIMEOUT = GLOBAL_TIMEOUT * 4
VERBOSITY = 1 if os.getenv('SILENT') or TOX else 2


# ===================================================================
# --- Classes
# ===================================================================

class ThreadTask(threading.Thread):
    """A thread object used for running process thread tests."""

    def __init__(self):
        threading.Thread.__init__(self)
        self._running = False
        self._interval = None
        self._flag = threading.Event()

    def __repr__(self):
        name = self.__class__.__name__
        return '<%s running=%s at %#x>' % (name, self._running, id(self))

    def start(self, interval=0.001):
        """Start thread and keep it running until an explicit
        stop() request. Polls for shutdown every 'timeout' seconds.
        """
        if self._running:
            raise ValueError("already started")
        self._interval = interval
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
# --- Utility functions
# ===================================================================

def cleanup():
    reap_children(search_all=True)
    safe_remove(TESTFN)
    try:
        safe_rmdir(TESTFN_UNICODE)
    except UnicodeEncodeError:
        pass
    for path in _testfiles:
        safe_remove(path)

atexit.register(cleanup)
atexit.register(lambda: DEVNULL.close())


_subprocesses_started = set()


def get_test_subprocess(cmd=None, wait=False, **kwds):
    """Return a subprocess.Popen object to use in tests.
    By default stdout and stderr are redirected to /dev/null and the
    python interpreter is used as test process.
    If 'wait' is True attemps to make sure the process is in a
    reasonably initialized state.
    """
    if cmd is None:
        pyline = ""
        if wait:
            pyline += "open(r'%s', 'w'); " % TESTFN
        # A process living for 30 secs. We sleep N times (as opposed to
        # once) in order to be nicer towards Windows which doesn't handle
        # interrupt signals properly.
        pyline += "import time; [time.sleep(0.01) for x in range(3000)];"
        cmd_ = [PYTHON, "-c", pyline]
    else:
        cmd_ = cmd
    kwds.setdefault("stdin", DEVNULL)
    kwds.setdefault("stdout", DEVNULL)
    kwds.setdefault("stderr", DEVNULL)
    sproc = subprocess.Popen(cmd_, **kwds)
    if wait:
        if cmd is None:
            stop_at = time.time() + 3
            while stop_at > time.time():
                if os.path.exists(TESTFN):
                    break
                time.sleep(0.001)
            else:
                warn("couldn't make sure test file was actually created")
        else:
            wait_for_pid(sproc.pid)
    _subprocesses_started.add(psutil.Process(sproc.pid))
    return sproc


_testfiles = []


def pyrun(src):
    """Run python code 'src' in a separate interpreter.
    Return interpreter subprocess.
    """
    if PY3:
        src = bytes(src, 'ascii')
    with tempfile.NamedTemporaryFile(
            prefix=TESTFILE_PREFIX, delete=False) as f:
        _testfiles.append(f.name)
        f.write(src)
        f.flush()
        subp = get_test_subprocess([PYTHON, f.name], stdout=None,
                                   stderr=None)
        wait_for_pid(subp.pid)
        return subp


def warn(msg):
    """Raise a warning msg."""
    warnings.warn(msg, UserWarning)


def sh(cmdline, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """run cmd in a subprocess and return its output.
    raises RuntimeError on error.
    """
    p = subprocess.Popen(cmdline, shell=True, stdout=stdout, stderr=stderr)
    stdout, stderr = p.communicate()
    if p.returncode != 0:
        raise RuntimeError(stderr)
    if stderr:
        if PY3:
            stderr = str(stderr, sys.stderr.encoding or
                         sys.getfilesystemencoding())
        warn(stderr)
    if PY3:
        stdout = str(stdout, sys.stdout.encoding or
                     sys.getfilesystemencoding())
    return stdout.strip()


if POSIX:
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
else:
    def get_kernel_version():
        return ()


if LINUX:
    RLIMIT_SUPPORT = get_kernel_version() >= (2, 6, 36)
else:
    RLIMIT_SUPPORT = False


def wait_for_pid(pid, timeout=GLOBAL_TIMEOUT):
    """Wait for pid to show up in the process list then return.
    Used in the test suite to give time the sub process to initialize.
    """
    raise_at = time.time() + timeout
    while True:
        if pid in psutil.pids():
            # give it one more iteration to allow full initialization
            time.sleep(0.01)
            return
        time.sleep(0.0001)
        if time.time() >= raise_at:
            raise RuntimeError("Timed out")


def wait_for_file(fname, timeout=GLOBAL_TIMEOUT, delete_file=True):
    """Wait for a file to be written on disk."""
    stop_at = time.time() + 3
    while time.time() < stop_at:
        try:
            with open(fname, "r") as f:
                data = f.read()
            if not data:
                continue
            if delete_file:
                os.remove(fname)
            return data
        except IOError:
            time.sleep(0.001)
    raise RuntimeError("timed out (couldn't read file)")


def reap_children(search_all=False):
    """Kill any subprocess started by this test suite and ensure that
    no zombies stick around to hog resources and create problems when
    looking for refleaks.
    """
    global _subprocesses_started
    procs = _subprocesses_started.copy()
    if search_all:
        this_process = psutil.Process()
        for p in this_process.children(recursive=True):
            procs.add(p)
    for p in procs:
        try:
            p.terminate()
        except psutil.NoSuchProcess:
            pass
    gone, alive = psutil.wait_procs(procs, timeout=GLOBAL_TIMEOUT)
    for p in alive:
        warn("couldn't terminate process %s" % p)
        try:
            p.kill()
        except psutil.NoSuchProcess:
            pass
    _, alive = psutil.wait_procs(alive, timeout=GLOBAL_TIMEOUT)
    if alive:
        warn("couldn't not kill processes %s" % str(alive))
    _subprocesses_started = set(alive)


def check_net_address(addr, family):
    """Check a net address validity. Supported families are IPv4,
    IPv6 and MAC addresses.
    """
    if enum and PY3:
        assert isinstance(family, enum.IntEnum), family
    if family == AF_INET:
        octs = [int(x) for x in addr.split('.')]
        assert len(octs) == 4, addr
        for num in octs:
            assert 0 <= num <= 255, addr
        if ipaddress:
            if not PY3:
                addr = unicode(addr)
            ipaddress.IPv4Address(addr)
    elif family == AF_INET6:
        assert isinstance(addr, str), addr
        if ipaddress:
            if not PY3:
                addr = unicode(addr)
            ipaddress.IPv6Address(addr)
    elif family == psutil.AF_LINK:
        assert re.match('([a-fA-F0-9]{2}[:|\-]?){6}', addr) is not None, addr
    else:
        raise ValueError("unknown family %r", family)


def check_connection_ntuple(conn):
    """Check validity of a connection namedtuple."""
    valid_conn_states = [getattr(psutil, x) for x in dir(psutil) if
                         x.startswith('CONN_')]
    assert conn[0] == conn.fd
    assert conn[1] == conn.family
    assert conn[2] == conn.type
    assert conn[3] == conn.laddr
    assert conn[4] == conn.raddr
    assert conn[5] == conn.status
    assert conn.type in (SOCK_STREAM, SOCK_DGRAM), repr(conn.type)
    assert conn.family in (AF_INET, AF_INET6, AF_UNIX), repr(conn.family)
    assert conn.status in valid_conn_states, conn.status

    # check IP address and port sanity
    for addr in (conn.laddr, conn.raddr):
        if not addr:
            continue
        if conn.family in (AF_INET, AF_INET6):
            assert isinstance(addr, tuple), addr
            ip, port = addr
            assert isinstance(port, int), port
            assert 0 <= port <= 65535, port
            check_net_address(ip, conn.family)
        elif conn.family == AF_UNIX:
            assert isinstance(addr, (str, None)), addr
        else:
            raise ValueError("unknown family %r", conn.family)

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
        assert not conn.raddr, repr(conn.raddr)
        assert conn.status == psutil.CONN_NONE, conn.status

    if getattr(conn, 'fd', -1) != -1:
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


def safe_remove(file):
    "Convenience function for removing temporary test files"
    try:
        os.remove(file)
    except OSError as err:
        if err.errno != errno.ENOENT:
            # # file is being used by another process
            # if WINDOWS and isinstance(err, WindowsError) and err.errno == 13:
            #     return
            raise


def safe_rmdir(dir):
    "Convenience function for removing temporary test directories"
    try:
        os.rmdir(dir)
    except OSError as err:
        if err.errno != errno.ENOENT:
            raise


@contextlib.contextmanager
def chdir(dirname):
    """Context manager which temporarily changes the current directory."""
    curdir = os.getcwd()
    try:
        os.chdir(dirname)
        yield
    finally:
        os.chdir(curdir)


def call_until(fun, expr, timeout=GLOBAL_TIMEOUT):
    """Keep calling function for timeout secs and exit if eval()
    expression is True.
    """
    stop_at = time.time() + timeout
    while time.time() < stop_at:
        ret = fun()
        if eval(expr):
            return ret
        time.sleep(0.001)
    raise RuntimeError('timed out (ret=%r)' % ret)


def retry_before_failing(ntimes=None):
    """Decorator which runs a test function and retries N times before
    actually failing.
    """
    def decorator(fun):
        @functools.wraps(fun)
        def wrapper(*args, **kwargs):
            times = ntimes or NO_RETRIES
            assert times, times
            for x in range(times):
                try:
                    return fun(*args, **kwargs)
                except AssertionError as _:
                    err = _
            raise err
        return wrapper
    return decorator


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


def create_temp_executable_file(suffix, code="void main() { pause(); }"):
    tmpdir = None
    if TRAVIS and OSX:
        tmpdir = "/private/tmp"
    fd, path = tempfile.mkstemp(
        prefix='psu', suffix=suffix, dir=tmpdir)
    os.close(fd)

    if which("gcc"):
        fd, c_file = tempfile.mkstemp(
            prefix='psu', suffix='.c', dir=tmpdir)
        os.close(fd)
        with open(c_file, "w") as f:
            f.write(code)
        subprocess.check_call(["gcc", c_file, "-o", path])
        safe_remove(c_file)
    else:
        # fallback - use python's executable
        shutil.copyfile(sys.executable, path)
        if POSIX:
            st = os.stat(path)
            os.chmod(path, st.st_mode | stat.S_IEXEC)
    return path


if WINDOWS:
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
else:
    def get_winver():
        raise NotImplementedError("not a Windows OS")


# In Python 3 paths are unicode objects by default.  Surrogate escapes
# are used to handle non-character data.
def encode_path(path):
    if PY3:
        return path.encode(sys.getfilesystemencoding(),
                           errors="surrogateescape")
    else:
        return path


def decode_path(path):
    if PY3:
        return path.decode(sys.getfilesystemencoding(),
                           errors="surrogateescape")
    else:
        return path


def run_test_module_by_name(name):
    # testmodules = [os.path.splitext(x)[0] for x in os.listdir(HERE)
    #                if x.endswith('.py') and x.startswith('test_')]
    name = os.path.splitext(os.path.basename(name))[0]
    suite = unittest.TestSuite()
    suite.addTest(unittest.defaultTestLoader.loadTestsFromName(name))
    result = unittest.TextTestRunner(verbosity=VERBOSITY).run(suite)
    success = result.wasSuccessful()
    sys.exit(0 if success else 1)
