#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.Process class."""

import collections
import contextlib
import enum
import errno
import getpass
import io
import itertools
import mmap
import os
import random
import select
import signal
import socket
import stat
import string
import subprocess
import sys
import textwrap
import time
from unittest import mock

import psutil
from psutil import AIX
from psutil import BSD
from psutil import FREEBSD
from psutil import LINUX
from psutil import MACOS
from psutil import NETBSD
from psutil import OPENBSD
from psutil import OSX
from psutil import POSIX
from psutil import SUNOS
from psutil import WINDOWS
from psutil import _psutil
from psutil._common import open_text

from . import CI_TESTING
from . import GITHUB_ACTIONS
from . import GLOBAL_TIMEOUT
from . import HAS_PROC_CPU_AFFINITY
from . import HAS_PROC_CPU_NUM
from . import HAS_PROC_ENVIRON
from . import HAS_PROC_IO_COUNTERS
from . import HAS_PROC_IONICE
from . import HAS_PROC_MEMORY_EXTRAS
from . import HAS_PROC_MEMORY_FOOTPRINT
from . import HAS_PROC_MEMORY_MAPS
from . import HAS_PROC_OPEN_FILES_PATH
from . import HAS_PROC_RLIMIT
from . import HAS_PROC_THREADS
from . import PYPY
from . import PYTHON_EXE
from . import PYTHON_EXE_ENV
from . import PsutilTestCase
from . import ThreadTask
from . import call_until
from . import copyload_shared_lib
from . import create_py_exe
from . import filter_alien_children
from . import isolated
from . import process_namespace
from . import pytest
from . import reap_children
from . import retry_on_failure
from . import sh
from . import skip_on_access_denied
from . import skip_on_not_implemented
from . import skipif
from . import wait_for_file

# ===================================================================
# --- psutil.Process class tests
# ===================================================================


class TestProcess(PsutilTestCase):
    """Tests for psutil.Process class."""

    def test_ppid(self):
        p = psutil.Process()
        if hasattr(os, 'getppid'):
            assert p.ppid() == os.getppid()
        p = self.spawn_psproc()
        assert p.ppid() == os.getpid()

    def test_parent(self):
        p = self.spawn_psproc()
        assert p.parent().pid == os.getpid()

        lowest_pid = psutil.pids()[0]
        assert psutil.Process(lowest_pid).parent() is None

    def test_parent_mocked_ctime(self):
        # Make sure we get a fresh copy of the ctime before processing
        # parent().We make the assumption that the parent pid MUST have
        # a creation time < than the child. If system clock is updated
        # this assumption was broken.
        # https://github.com/giampaolo/psutil/issues/2542
        p = self.spawn_psproc()
        p.create_time()  # trigger cache
        assert p._create_time
        p._create_time = 1
        assert p.parent().pid == os.getpid()

    def test_parent_multi(self):
        parent = psutil.Process()
        child, grandchild = self.spawn_children_pair()
        assert grandchild.parent() == child
        assert child.parent() == parent

    @retry_on_failure
    def test_parents(self):
        parent = psutil.Process()
        assert parent.parents()
        child, grandchild = self.spawn_children_pair()
        assert child.parents()[0] == parent
        assert grandchild.parents()[0] == child
        assert grandchild.parents()[1] == parent

    def test_children(self):
        parent = psutil.Process()
        assert not filter_alien_children(parent.children())
        assert not filter_alien_children(parent.children(recursive=True))
        # On Windows we set the flag to 0 in order to cancel out the
        # CREATE_NO_WINDOW flag (enabled by default) which creates
        # an extra "conhost.exe" child.
        child = self.spawn_psproc(creationflags=0)
        children1 = filter_alien_children(parent.children())
        children2 = filter_alien_children(parent.children(recursive=True))
        for children in (children1, children2):
            assert len(children) == 1
            assert children[0].pid == child.pid
            assert children[0].ppid() == parent.pid

    def test_children_mocked_ctime(self):
        # Make sure we get a fresh copy of the ctime before processing
        # children(). We make the assumption that process children MUST
        # have a creation time > than the parent. If system clock is
        # updated this assumption was broken.
        # https://github.com/giampaolo/psutil/issues/2542
        parent = psutil.Process()
        parent.create_time()  # trigger cache
        assert parent._create_time
        parent._create_time += 100000

        assert not filter_alien_children(parent.children())
        assert not filter_alien_children(parent.children(recursive=True))
        # On Windows we set the flag to 0 in order to cancel out the
        # CREATE_NO_WINDOW flag (enabled by default) which creates
        # an extra "conhost.exe" child.
        child = self.spawn_psproc(creationflags=0)
        children1 = filter_alien_children(parent.children())
        children2 = filter_alien_children(parent.children(recursive=True))
        for children in (children1, children2):
            assert len(children) == 1
            assert children[0].pid == child.pid
            assert children[0].ppid() == parent.pid

    def test_children_recursive(self):
        # Test children() against two sub processes, p1 and p2, where
        # p1 (our child) spawned p2 (our grandchild).
        parent = psutil.Process()
        child, grandchild = self.spawn_children_pair()
        assert parent.children() == [child]
        assert parent.children(recursive=True) == [child, grandchild]
        # If the intermediate process is gone there's no way for
        # children() to recursively find it.
        child.terminate()
        child.wait()
        assert not parent.children(recursive=True)

    def test_children_duplicates(self):
        # find the process which has the highest number of children
        table = collections.defaultdict(int)
        for p in psutil.process_iter():
            try:
                table[p.ppid()] += 1
            except psutil.Error:
                pass
        # this is the one, now let's make sure there are no duplicates
        pid = max(table.items(), key=lambda x: x[1])[0]
        if LINUX and pid == 0:
            return pytest.skip("PID 0")
        p = psutil.Process(pid)
        try:
            c = p.children(recursive=True)
        except psutil.AccessDenied:  # windows
            pass
        else:
            assert len(c) == len(set(c))

    def test_parents_and_children(self):
        parent = psutil.Process()
        child, grandchild = self.spawn_children_pair()
        # forward
        children = filter_alien_children(parent.children(recursive=True))
        assert len(children) == 2
        assert children[0] == child
        assert children[1] == grandchild
        # backward
        parents = grandchild.parents()
        assert parents[0] == child
        assert parents[1] == parent

    def test_suspend_resume(self):
        p = self.spawn_psproc()
        p.suspend()
        for _ in range(100):
            if p.status() == psutil.STATUS_STOPPED:
                break
            time.sleep(0.01)
        p.resume()
        assert p.status() != psutil.STATUS_STOPPED


# ===================================================================
# --- PID reuse detection and process identity
# ===================================================================


class TestProcessPidReuse(PsutilTestCase):
    """Tests for PID reuse detection and process identity
    (__eq__, __ne__, __hash__).
    """

    def test_ident(self):
        p = psutil.Process()
        assert p._ident[0] == p.pid
        if FREEBSD or OPENBSD or SUNOS or AIX:
            # PID reuse detection is disabled on these platforms, see
            # Process._get_ident().
            assert p._ident[1] is None
        else:
            assert p._ident[1] is not None

    def test_eq(self):
        def proc(pid, ctime):
            p = psutil.Process()
            p._ident = (pid, ctime)
            p._hash = None
            return p

        # same pid, same ctime
        assert proc(100, 50.0) == proc(100, 50.0)
        # same pid, different ctime: the PID has been reused
        assert proc(100, 50.0) != proc(100, 60.0)
        # different pid always means different process
        assert proc(100, 50.0) != proc(101, 50.0)
        assert proc(100, None) != proc(101, None)
        assert proc(100, 0.0) != proc(101, 0.0)
        # a null ctime on either side means identity is unknown,
        # which is not proof of a different process
        for null_value in (0.0, None):
            assert proc(100, 50.0) == proc(100, null_value)
            assert proc(100, null_value) == proc(100, 50.0)
            assert proc(100, null_value) == proc(100, null_value)
        # comparison with a non-Process object
        assert proc(100, 50.0) != "foo"

    def test_hash(self):
        def proc(pid, ctime):
            p = psutil.Process()
            p._ident = (pid, ctime)
            p._hash = None
            return p

        # a == b implies hash(a) == hash(b)
        pairs = [
            (proc(100, 50.0), proc(100, 50.0)),
            (proc(100, 50.0), proc(100, None)),
            (proc(100, 50.0), proc(100, 0.0)),
            (proc(100, None), proc(100, 0.0)),
        ]
        for a, b in pairs:
            assert a == b
            assert hash(a) == hash(b)
            assert len({a, b}) == 1
            assert {a: "x"}[b] == "x"
        # same pid but different ctime (PID reuse): unequal, and a set
        # must keep both
        a, b = proc(100, 50.0), proc(100, 60.0)
        assert a != b
        assert len({a, b}) == 2
        # sanity check against the real world
        p1 = psutil.Process()
        p2 = psutil.Process(p1.pid)
        assert p1 == p2
        assert hash(p1) == hash(p2)
        assert len({p1, p2}) == 1

    @skipif(
        FREEBSD or OPENBSD or SUNOS or AIX,
        reason="PID reuse detection disabled on this platform",
    )
    def test_reused_pid(self):
        # Emulate a case where PID has been reused by another process.
        subp = self.spawn_subproc()
        p = psutil.Process(subp.pid)
        p._ident = (p.pid, p.create_time() + 100)

        list(psutil.process_iter())
        assert p.pid in psutil._pmap
        assert not p.is_running()

        # make sure is_running() removed PID from process_iter()
        # internal cache
        with mock.patch.object(psutil._common, "PSUTIL_DEBUG", True):
            with contextlib.redirect_stderr(io.StringIO()) as f:
                list(psutil.process_iter())
        assert (
            f"refreshing Process instance for reused PID {p.pid}"
            in f.getvalue()
        )
        assert p.pid not in psutil._pmap

        assert p != psutil.Process(subp.pid)
        msg = "process no longer exists and its PID has been reused"
        ns = process_namespace(p)
        for fun, name in ns.iter(ns.setters + ns.killers, clear_cache=False):
            with self.subTest(name=name):
                with pytest.raises(psutil.NoSuchProcess, match=msg):
                    fun()

        assert "terminated + PID reused" in str(p)
        assert "terminated + PID reused" in repr(p)

        with pytest.raises(psutil.NoSuchProcess, match=msg):
            p.ppid()
        with pytest.raises(psutil.NoSuchProcess, match=msg):
            p.parent()
        with pytest.raises(psutil.NoSuchProcess, match=msg):
            p.parents()
        with pytest.raises(psutil.NoSuchProcess, match=msg):
            p.children()

    @skipif(
        FREEBSD or OPENBSD or SUNOS or AIX,
        reason="PID reuse detection disabled on this platform",
    )
    def test_reused_pid_detected_by_ppid(self):
        subp = self.spawn_subproc()
        p = psutil.Process(subp.pid)
        assert p._ident[1] is not None
        self.addCleanup(psutil._pids_reused.discard, p.pid)
        p._ident = (p.pid, p._ident[1] + 100)
        assert not p._pid_reused
        msg = "process no longer exists and its PID has been reused"
        with pytest.raises(psutil.NoSuchProcess, match=msg):
            p.ppid()

    def test_reused_pid_with_null_ctime(self):
        # A null create time on either side must not count as PID
        # reuse, see: https://github.com/giampaolo/psutil/issues/2895.
        subp = self.spawn_subproc()
        p = psutil.Process(subp.pid)

        for null_value in (0.0, None):
            p._ident = (p.pid, null_value)
            assert p.is_running()
            assert not p._pid_reused

        for null_value in (0.0, None):
            p = psutil.Process(subp.pid)
            with mock.patch.object(
                psutil.Process,
                "_get_ident",
                return_value=(subp.pid, null_value),
            ):
                assert p.is_running()
            assert not p._pid_reused

    def test_ad_on_process_creation(self):
        # We are supposed to be able to instantiate Process also in case
        # of zombie processes or access denied.
        with mock.patch.object(
            psutil.Process, '_get_ident', side_effect=psutil.AccessDenied
        ) as meth:
            psutil.Process()
            assert meth.called

        with mock.patch.object(
            psutil.Process, '_get_ident', side_effect=psutil.ZombieProcess(1)
        ) as meth:
            psutil.Process()
            assert meth.called

        with mock.patch.object(
            psutil.Process, '_get_ident', side_effect=ValueError
        ) as meth:
            with pytest.raises(ValueError):
                psutil.Process()
            assert meth.called

        with mock.patch.object(
            psutil.Process, '_get_ident', side_effect=psutil.NoSuchProcess(1)
        ) as meth:
            with pytest.raises(psutil.NoSuchProcess):
                psutil.Process()
            assert meth.called


# ===================================================================
# --- psutil.Process.wait tests
# ===================================================================


class TestProcessWait(PsutilTestCase):

    def test_wait_exited(self):
        # Test waitpid() + WIFEXITED -> WEXITSTATUS.
        # normal return, same as exit(0)
        cmd = [PYTHON_EXE, "-c", "pass"]
        p = self.spawn_psproc(cmd)
        code = p.wait()
        assert code == 0
        self.assert_proc_gone(p)
        # exit(1), implicit in case of error
        cmd = [PYTHON_EXE, "-c", "1 / 0"]
        p = self.spawn_psproc(cmd, stderr=subprocess.PIPE)
        code = p.wait()
        assert code == 1
        self.assert_proc_gone(p)
        # via sys.exit()
        cmd = [PYTHON_EXE, "-c", "import sys; sys.exit(5);"]
        p = self.spawn_psproc(cmd)
        code = p.wait()
        assert code == 5
        self.assert_proc_gone(p)
        # via os._exit()
        cmd = [PYTHON_EXE, "-c", "import os; os._exit(5);"]
        p = self.spawn_psproc(cmd)
        code = p.wait()
        assert code == 5
        self.assert_proc_gone(p)

    @skipif(not WINDOWS, reason="WINDOWS only")
    def test_wait_exited_ntstatus(self):
        code = "import ctypes; ctypes.windll.kernel32.ExitProcess(0xC0000005)"
        p = self.spawn_psproc([PYTHON_EXE, "-c", code])
        assert p.wait() == 0xC0000005
        self.assert_proc_gone(p)

    @skipif(not POSIX, reason="not POSIX")
    def test_wait_signaled(self):
        p = psutil.Process(self.spawn_subproc().pid)
        p.terminate()
        code = p.wait()
        assert code == -signal.SIGTERM
        assert isinstance(code, enum.IntEnum)
        # second call is cached
        assert code == -signal.SIGTERM
        # Call the underlying implementation. Done to exercise the
        # poll/kqueue machinery on a gone PID. Also, waitpid() is
        # supposed to fail with ESRCH.
        assert p._proc.wait() is None

    def test_wait_stopped(self):
        p = self.spawn_psproc()
        if POSIX:
            # Test waitpid() + WIFSTOPPED and WIFCONTINUED.
            # Note: if a process is stopped it ignores SIGTERM.
            p.send_signal(signal.SIGSTOP)
            with pytest.raises(psutil.TimeoutExpired):
                p.wait(timeout=0.001)
            p.send_signal(signal.SIGCONT)
            with pytest.raises(psutil.TimeoutExpired):
                p.wait(timeout=0.001)
            p.send_signal(signal.SIGTERM)
            assert p.wait() == -signal.SIGTERM
            assert p.wait() == -signal.SIGTERM
        else:
            p.suspend()
            with pytest.raises(psutil.TimeoutExpired):
                p.wait(timeout=0.001)
            p.resume()
            with pytest.raises(psutil.TimeoutExpired):
                p.wait(timeout=0.001)
            p.terminate()
            assert p.wait() == signal.SIGTERM
            assert p.wait() == signal.SIGTERM

    def test_wait_non_children(self):
        # Test wait() against a process which is not our direct
        # child.
        child, grandchild = self.spawn_children_pair()
        with pytest.raises(psutil.TimeoutExpired):
            child.wait(0.01)
        with pytest.raises(psutil.TimeoutExpired):
            grandchild.wait(0.01)
        # We also terminate the direct child otherwise the
        # grandchild will hang until the parent is gone.
        child.terminate()
        grandchild.terminate()
        child_ret = child.wait()
        grandchild_ret = grandchild.wait()
        if POSIX:
            assert child_ret == -signal.SIGTERM
            # For processes which are not our children we're supposed
            # to get None.
            assert grandchild_ret is None
        else:
            assert child_ret == signal.SIGTERM
            assert child_ret == signal.SIGTERM

    def test_wait_timeout(self):
        p = self.spawn_psproc()
        p.name()
        with pytest.raises(psutil.TimeoutExpired):
            p.wait(0.01)
        with pytest.raises(psutil.TimeoutExpired):
            p.wait(0)

    def test_wait_timeout_nonblocking(self):
        p = self.spawn_psproc()
        with pytest.raises(psutil.TimeoutExpired):
            p.wait(0)
        p.kill()
        stop_at = time.monotonic() + GLOBAL_TIMEOUT
        while time.monotonic() < stop_at:
            try:
                code = p.wait(0)
                break
            except psutil.TimeoutExpired:
                pass
        else:
            return pytest.fail('timeout')
        if POSIX:
            assert code == -signal.SIGKILL
        else:
            assert code == signal.SIGTERM
        self.assert_proc_gone(p)

    def test_wait_errors(self):
        p = psutil.Process()
        with pytest.raises(TypeError, match="must be an int or float"):
            p.wait("foo")
        with pytest.raises(ValueError, match="must be positive or zero"):
            p.wait(-1)
        p._pid = 0
        with pytest.raises(ValueError, match="can't wait for PID 0"):
            p.wait()

    @skipif(not POSIX, reason="POSIX only")
    def test_wait_zombie(self):
        parent, zombie = self.spawn_zombie()
        with pytest.raises(psutil.TimeoutExpired):
            zombie.wait(0.001)
        parent.terminate()
        parent.wait()
        zombie.wait()

    # --- tests for wait_pid_posix()

    @skipif(not POSIX, reason="POSIX only")
    def test_os_waitpid_error(self):
        # os.waitpid() is supposed to catch ECHILD only.
        # Test that any other errno results in an exception.
        with mock.patch(
            "os.waitpid", side_effect=OSError(errno.EBADF, "")
        ) as m:
            with pytest.raises(OSError):
                psutil._psposix.wait_pid_posix(os.getpid())
            assert m.called

    @skipif(not POSIX, reason="POSIX only")
    def test_os_waitpid_bad_ret_status(self):
        # Simulate os.waitpid() returning a bad status.
        with mock.patch("os.waitpid", return_value=(1, -1)) as m:
            with pytest.raises(ValueError):
                psutil._psposix.wait_pid_posix(os.getpid())
            assert m.called

    # --- tests for pidfd_open() and kqueue()

    def assert_wait_pid_errors(self, patch_target, wait_func, errors):
        # Test that all errors are caught and wait_pid_posix()
        # fallback is used.
        sproc = self.spawn_subproc()
        sproc.terminate()

        errors = list(errors)
        random.shuffle(errors)
        for idx, err in enumerate(errors):
            with mock.patch(
                patch_target,
                side_effect=OSError(err, os.strerror(err)),
            ) as m:
                # the second time waitpid() does not return the exit code
                code = -signal.SIGTERM if idx == 0 else None
                assert wait_func(sproc.pid) == code
            assert m.called

    @skipif(
        not hasattr(os, "pidfd_open"),
        reason="LINUX only" if not LINUX else "not supported",
    )
    def test_pidfd_open_errors(self):
        from psutil._psposix import wait_pid_pidfd_open

        self.assert_wait_pid_errors(
            "os.pidfd_open",
            wait_pid_pidfd_open,
            [errno.ESRCH, errno.EMFILE, errno.ENFILE, errno.EBADF],
        )

    @skipif(not hasattr(select, "kqueue"), reason="MACOS and BSD only")
    def test_kqueue_errors(self):
        from psutil._psposix import wait_pid_kqueue

        self.assert_wait_pid_errors(
            "select.kqueue",
            wait_pid_kqueue,
            [errno.EMFILE, errno.ENFILE, errno.EBADF],
        )

    def assert_wait_pid_race(self, patch_target, real_func):
        # Kill process after patch_target succeeds but before wait()
        # completes, then verify Process.wait() still works.
        sproc = self.spawn_subproc()
        psproc = psutil.Process(sproc.pid)

        def wrapper(*args, **kwargs):
            ret = real_func(*args, **kwargs)
            sproc.terminate()
            sproc.wait()
            return ret

        with mock.patch(patch_target, side_effect=wrapper) as m:
            psproc.wait()
        assert m.called

    @skipif(
        not hasattr(os, "pidfd_open"),
        reason="LINUX only" if not LINUX else "not supported",
    )
    def test_pidfd_open_race(self):
        self.assert_wait_pid_race("os.pidfd_open", os.pidfd_open)

    @skipif(not hasattr(select, "kqueue"), reason="MACOS and BSD only")
    def test_kqueue_race(self):
        self.assert_wait_pid_race("select.kqueue", select.kqueue)

    @skipif(not hasattr(select, "kqueue"), reason="MACOS and BSD only")
    def test_kqueue_control_errors(self):
        # Test that kqueue.control() errors are caught and fallback is used.
        from psutil._psposix import wait_pid_kqueue

        sproc = self.spawn_subproc()
        sproc.terminate()

        errors = [errno.EACCES, errno.EPERM, errno.ESRCH]
        random.shuffle(errors)
        for idx, err in enumerate(errors):
            kq_mock = mock.Mock()
            kq_mock.control.side_effect = OSError(err, os.strerror(err))
            kq_mock.close = mock.Mock()

            with mock.patch("select.kqueue", return_value=kq_mock):
                # the second time waitpid() does not return the exit code
                code = -signal.SIGTERM if idx == 0 else None
                assert wait_pid_kqueue(sproc.pid) == code
            assert kq_mock.control.called

        # illegitimate error
        kq_mock = mock.Mock()
        kq_mock.control.side_effect = OSError(
            errno.EBADF, os.strerror(errno.EBADF)
        )
        kq_mock.close = mock.Mock()
        with mock.patch("select.kqueue", return_value=kq_mock):
            with pytest.raises(OSError):
                wait_pid_kqueue(sproc.pid)


# ===================================================================
# --- psutil.Popen tests
# ===================================================================


class TestPopen(PsutilTestCase):
    """Tests for psutil.Popen class."""

    @classmethod
    def tearDownClass(cls):
        reap_children()

    def test_misc(self):
        # XXX this test causes a ResourceWarning because
        # psutil.__subproc instance doesn't get properly freed.
        # Not sure what to do though.
        cmd = [
            PYTHON_EXE,
            "-c",
            (
                "print('ready', flush=True);"
                "import time; [time.sleep(0.1) for x in range(100)];"
            ),
        ]
        with psutil.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=PYTHON_EXE_ENV,
        ) as proc:
            proc.name()
            proc.cpu_times()
            proc.stdin  # noqa: B018
            assert dir(proc)
            with pytest.raises(AttributeError):
                proc.foo  # noqa: B018

            assert proc.stdout.readline().strip() == b"ready"
            proc.terminate()

            expected = -signal.SIGTERM if POSIX else signal.SIGTERM
            # Wait longer than the child sleeps (10 secs). If SIGTERM
            # gets lost (seen on NetBSD) we want the child to run to
            # completion, so that wait() returns and we can print the
            # evidence below, instead of just timing out.
            status = ""
            try:
                ret = proc.wait(20)
            except psutil.TimeoutExpired:
                ret = "<timeout>"
                with contextlib.suppress(psutil.Error):
                    status = f" child status: {proc.status()};"
            if ret != expected:
                return pytest.fail(
                    f"wait() returned {ret} instead of {expected};"
                    f"{status}"
                    f" child stderr: {proc.stderr.read()}"
                )

    def test_ctx_manager(self):
        with psutil.Popen(
            [PYTHON_EXE, "-V"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            env=PYTHON_EXE_ENV,
        ) as proc:
            proc.communicate()
        assert proc.stdout.closed
        assert proc.stderr.closed
        assert proc.stdin.closed
        assert proc.returncode == 0

    def test_kill_terminate(self):
        # subprocess.Popen()'s terminate(), kill() and send_signal() do
        # not raise exception after the process is gone. psutil.Popen
        # diverges from that.
        cmd = [
            PYTHON_EXE,
            "-c",
            "import time; [time.sleep(0.1) for x in range(100)];",
        ]
        with psutil.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=PYTHON_EXE_ENV,
        ) as proc:
            proc.terminate()
            proc.wait()
            with pytest.raises(psutil.NoSuchProcess):
                proc.terminate()
            with pytest.raises(psutil.NoSuchProcess):
                proc.kill()
            with pytest.raises(psutil.NoSuchProcess):
                proc.send_signal(signal.SIGTERM)
            if WINDOWS:
                with pytest.raises(psutil.NoSuchProcess):
                    proc.send_signal(signal.CTRL_C_EVENT)
                with pytest.raises(psutil.NoSuchProcess):
                    proc.send_signal(signal.CTRL_BREAK_EVENT)

    def test__getattribute__(self):
        cmd = [
            PYTHON_EXE,
            "-c",
            "import time; [time.sleep(0.1) for x in range(100)];",
        ]
        with psutil.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=PYTHON_EXE_ENV,
        ) as proc:
            proc.terminate()
            proc.wait()
            with pytest.raises(AttributeError):
                proc.foo  # noqa: B018
