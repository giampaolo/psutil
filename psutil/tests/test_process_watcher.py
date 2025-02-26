#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Tests for psutil.ProcessWatcher class."""

import os
import time

import pytest

import psutil
from psutil.tests import PsutilTestCase


if psutil.LINUX:
    from psutil.tests import linux_set_proc_name


class TestProcessWatcher(PsutilTestCase):
    def setUp(self):
        self.pw = psutil.ProcessWatcher()

    def tearDown(self):
        self.pw.close()

    def read_until_pid(self, pid, timeout=2):
        stop_at = time.monotonic() + timeout
        while time.monotonic() < stop_at:
            event = self.pw.read(timeout=0.01)
            if event["pid"] == pid:
                return event
        raise TimeoutError("timed out")

    def test_fork_then_exit(self):
        proc = self.spawn_testproc()
        event = self.read_until_pid(proc.pid)
        assert event == {
            "pid": proc.pid,
            "event": psutil.PROC_EVENT_FORK,
            "parent_pid": os.getpid(),
        }

        event = self.read_until_pid(proc.pid)
        assert event == {"pid": proc.pid, "event": psutil.PROC_EVENT_EXEC}

        proc.terminate()
        proc.wait()
        event = self.read_until_pid(proc.pid)
        assert event == {
            "pid": proc.pid,
            "event": psutil.PROC_EVENT_EXIT,
            "exit_code": abs(proc.returncode),
        }

    @pytest.mark.skipif(not psutil.LINUX, reason="LINUX only")
    def test_change_proc_name(self):
        name = psutil.Process().name()
        linux_set_proc_name("hello there")
        try:
            event = self.read_until_pid(os.getpid())
            assert event == {
                "event": psutil.PROC_EVENT_COMM,
                "pid": os.getpid(),
            }
            assert psutil.Process().name() == "hello there"
        finally:
            if psutil.Process().name() != name:
                linux_set_proc_name(name)

    def test_ctx_manager(self):
        assert self.pw.sock is not None
        with self.pw as pw:
            assert pw is self.pw
        assert self.pw.sock is None

    def test_closed(self):
        self.pw.close()
        with pytest.raises(ValueError, match="already closed"):
            self.pw.read()
        with pytest.raises(ValueError, match="already closed"):
            with self.pw:
                pass
        with pytest.raises(ValueError, match="already closed"):
            for ev in self.pw:
                pass
