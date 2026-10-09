# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""bool subclasses int; numeric args must not silently accept True/False."""

import pytest

import psutil


def test_process_pid_rejects_bool():
    with pytest.raises(TypeError, match=r"pid.*bool"):
        psutil.Process(True)
    with pytest.raises(TypeError, match=r"pid.*bool"):
        psutil.Process(False)


def test_pid_exists_rejects_bool():
    with pytest.raises(TypeError, match=r"pid.*bool"):
        psutil.pid_exists(True)
    with pytest.raises(TypeError, match=r"pid.*bool"):
        psutil.pid_exists(False)


def test_nice_rejects_bool():
    p = psutil.Process()
    with pytest.raises(TypeError, match=r"nice value.*bool"):
        p.nice(True)
    with pytest.raises(TypeError, match=r"nice value.*bool"):
        p.nice(False)


def test_wait_timeout_rejects_bool():
    p = psutil.Process()
    with pytest.raises(TypeError, match=r"timeout"):
        p.wait(timeout=True)
    with pytest.raises(TypeError, match=r"timeout"):
        p.wait(timeout=False)


def test_wait_procs_timeout_rejects_bool():
    with pytest.raises(TypeError, match=r"timeout.*bool"):
        psutil.wait_procs([], timeout=True)
    with pytest.raises(TypeError, match=r"timeout.*bool"):
        psutil.wait_procs([], timeout=False)


def test_cpu_percent_interval_rejects_bool():
    with pytest.raises(TypeError, match=r"interval.*bool"):
        psutil.cpu_percent(interval=True)
    with pytest.raises(TypeError, match=r"interval.*bool"):
        psutil.cpu_percent(interval=False)
    p = psutil.Process()
    with pytest.raises(TypeError, match=r"interval.*bool"):
        p.cpu_percent(interval=True)


def test_cpu_times_percent_interval_rejects_bool():
    with pytest.raises(TypeError, match=r"interval.*bool"):
        psutil.cpu_times_percent(interval=True)
    with pytest.raises(TypeError, match=r"interval.*bool"):
        psutil.cpu_times_percent(interval=False)
