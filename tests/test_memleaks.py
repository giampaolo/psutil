#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Regression test suite for detecting memory leaks in the underlying C
extension. Requires https://github.com/giampaolo/psleak.
"""

import inspect
import os

from psleak import LeakTest
from psleak import MemoryLeakTestCase

import psutil
from psutil import FREEBSD
from psutil import LINUX
from psutil import MACOS
from psutil import OPENBSD
from psutil import POSIX
from psutil import SUNOS
from psutil import WINDOWS
from psutil import _psutil

from . import HAS_CPU_FREQ
from . import HAS_HEAP_INFO
from . import HAS_NET_IO_COUNTERS
from . import HAS_PROC_CPU_AFFINITY
from . import HAS_PROC_CPU_NUM
from . import HAS_PROC_ENVIRON
from . import HAS_PROC_IO_COUNTERS
from . import HAS_PROC_IONICE
from . import HAS_PROC_MEMORY_FOOTPRINT
from . import HAS_PROC_MEMORY_MAPS
from . import HAS_PROC_RLIMIT
from . import HAS_SENSORS_BATTERY
from . import HAS_SENSORS_FANS
from . import HAS_SENSORS_TEMPERATURES
from . import create_sockets
from . import get_testfn
from . import process_namespace
from . import pytest
from . import skip_on_access_denied
from . import spawn_subproc
from . import system_namespace
from . import terminate

thisproc = psutil.Process()


MemoryLeakTestCase.retries = 30  # minimize false positives
MemoryLeakTestCase.verbosity = 1

TIMES = MemoryLeakTestCase.times
FEW_TIMES = int(TIMES / 10)

# ===================================================================
# Process class
# ===================================================================


class TestProcess(MemoryLeakTestCase):
    """Test leaks of Process class methods."""

    proc = thisproc

    def test_coverage(self):
        ns = process_namespace(None)
        ns.test_class_coverage(self, ns.getters + ns.setters)

    def test_name(self):
        self.execute(self.proc.name)

    def test_cmdline(self):
        if WINDOWS and self.proc.is_running():
            self.proc.cmdline()
        self.execute(self.proc.cmdline)

    def test_exe(self):
        self.execute(self.proc.exe)

    def test_ppid(self):
        self.execute(self.proc.ppid)

    @pytest.mark.skipif(not POSIX, reason="POSIX only")
    def test_uids(self):
        self.execute(self.proc.uids)

    @pytest.mark.skipif(not POSIX, reason="POSIX only")
    def test_gids(self):
        self.execute(self.proc.gids)

    def test_status(self):
        self.execute(self.proc.status)

    def test_nice(self):
        self.execute(self.proc.nice)

    def test_nice_set(self):
        niceness = thisproc.nice()
        self.execute(lambda: self.proc.nice(niceness))

    @pytest.mark.skipif(not HAS_PROC_IONICE, reason="not supported")
    def test_ionice(self):
        self.execute(self.proc.ionice)

    @pytest.mark.skipif(not HAS_PROC_IONICE, reason="not supported")
    def test_ionice_set(self):
        if WINDOWS:
            value = thisproc.ionice()
            self.execute(lambda: self.proc.ionice(value))
        else:
            self.execute(lambda: self.proc.ionice(psutil.IOPRIO_CLASS_NONE))

    @pytest.mark.skipif(not HAS_PROC_IO_COUNTERS, reason="not supported")
    def test_io_counters(self):
        self.execute(self.proc.io_counters)

    @pytest.mark.skipif(POSIX, reason="worthless on POSIX")
    def test_username(self):
        # always open 1 handle on Windows (only once)
        psutil.Process().username()
        self.execute(self.proc.username)

    def test_create_time(self):
        self.execute(self.proc.create_time)

    @skip_on_access_denied(only_if=OPENBSD)
    def test_num_threads(self):
        self.execute(self.proc.num_threads)

    @pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
    def test_num_handles(self):
        self.execute(self.proc.num_handles)

    @pytest.mark.skipif(not POSIX, reason="POSIX only")
    def test_num_fds(self):
        self.execute(self.proc.num_fds)

    def test_num_ctx_switches(self):
        self.execute(self.proc.num_ctx_switches)

    @skip_on_access_denied(only_if=OPENBSD)
    def test_threads(self):
        kw = {"times": 50} if WINDOWS else {}
        self.execute(self.proc.threads, **kw)

    def test_cpu_times(self):
        self.execute(self.proc.cpu_times)

    @pytest.mark.skipif(not HAS_PROC_CPU_NUM, reason="not supported")
    def test_cpu_num(self):
        self.execute(self.proc.cpu_num)

    def test_memory_info(self):
        self.execute(self.proc.memory_info)

    def test_memory_info_ex(self):
        self.execute(self.proc.memory_info_ex)

    @pytest.mark.skipif(not HAS_PROC_MEMORY_FOOTPRINT, reason="not supported")
    def test_memory_footprint(self):
        self.execute(self.proc.memory_footprint)

    @pytest.mark.skipif(not POSIX, reason="POSIX only")
    def test_terminal(self):
        self.execute(self.proc.terminal)

    def test_resume(self):
        times = FEW_TIMES if POSIX else self.times
        self.execute(self.proc.resume, times=times)

    def test_cwd(self):
        self.execute(self.proc.cwd)

    @pytest.mark.skipif(not HAS_PROC_CPU_AFFINITY, reason="not supported")
    def test_cpu_affinity(self):
        self.execute(self.proc.cpu_affinity)

    @pytest.mark.skipif(not HAS_PROC_CPU_AFFINITY, reason="not supported")
    def test_cpu_affinity_set(self):
        affinity = thisproc.cpu_affinity()
        self.execute(lambda: self.proc.cpu_affinity(affinity))

    def test_open_files(self):
        kw = {"times": 10, "retries": 30} if WINDOWS else {}
        with open(get_testfn(), 'w'):
            self.execute(self.proc.open_files, **kw)

    @pytest.mark.skipif(not HAS_PROC_MEMORY_MAPS, reason="not supported")
    @pytest.mark.skipif(LINUX, reason="too slow on LINUX")
    def test_memory_maps(self):
        self.execute(self.proc.memory_maps, times=60, retries=10)

    def test_page_faults(self):
        self.execute(self.proc.page_faults)

    @pytest.mark.skipif(not LINUX, reason="LINUX only")
    @pytest.mark.skipif(not HAS_PROC_RLIMIT, reason="not supported")
    def test_rlimit(self):
        self.execute(lambda: self.proc.rlimit(psutil.RLIMIT_NOFILE))

    @pytest.mark.skipif(not LINUX, reason="LINUX only")
    @pytest.mark.skipif(not HAS_PROC_RLIMIT, reason="not supported")
    def test_rlimit_set(self):
        limit = thisproc.rlimit(psutil.RLIMIT_NOFILE)
        self.execute(lambda: self.proc.rlimit(psutil.RLIMIT_NOFILE, limit))

    # Windows implementation is based on a single system-wide
    # function (tested later).
    @pytest.mark.skipif(WINDOWS, reason="worthless on WINDOWS")
    def test_net_connections(self):
        # TODO: UNIX sockets are temporarily implemented by parsing
        # 'pfiles' cmd  output; we don't want that part of the code to
        # be executed.
        times = FEW_TIMES if LINUX else self.times
        with create_sockets():
            kind = 'inet' if SUNOS else 'all'
            self.execute(lambda: self.proc.net_connections(kind), times=times)

    @pytest.mark.skipif(not HAS_PROC_ENVIRON, reason="not supported")
    def test_environ(self):
        self.execute(self.proc.environ)

    @pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
    def test_proc_oneshot(self):
        self.execute(lambda: _psutil.proc_oneshot(os.getpid()))


class TestTerminatedProcess(TestProcess):
    """Repeat the tests above looking for leaks occurring when dealing
    with terminated processes raising NoSuchProcess exception.
    The C functions are still invoked but will follow different code
    paths. We'll check those code paths.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.subp = spawn_subproc()
        cls.proc = psutil.Process(cls.subp.pid)
        cls.proc.kill()
        cls.proc.wait()

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        terminate(cls.subp)

    def call(self, fun):
        try:
            fun()
        except psutil.NoSuchProcess:
            pass

    if WINDOWS:

        def test_kill(self):
            self.execute(self.proc.kill)

        def test_terminate(self):
            self.execute(self.proc.terminate)

        def test_suspend(self):
            self.execute(self.proc.suspend)

        def test_resume(self):
            self.execute(self.proc.resume)

        def test_wait(self):
            self.execute(self.proc.wait)

        def test_proc_oneshot(self):
            # test dual implementation
            def call():
                try:
                    return _psutil.proc_oneshot(self.proc.pid)
                except ProcessLookupError:
                    pass

            self.execute(call)


@pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
class TestProcessDualImplementation(MemoryLeakTestCase):
    def test_cmdline_peb_true(self):
        self.execute(lambda: _psutil.proc_cmdline(os.getpid(), use_peb=True))

    def test_cmdline_peb_false(self):
        self.execute(lambda: _psutil.proc_cmdline(os.getpid(), use_peb=False))


# ===================================================================
# system APIs
# ===================================================================


class TestModuleFunctions(MemoryLeakTestCase):
    """Test leaks of psutil module functions."""

    def test_coverage(self):
        ns = system_namespace()
        ns.test_class_coverage(self, ns.all)

    # --- cpu

    def test_cpu_count(self):  # logical
        self.execute(lambda: psutil.cpu_count(logical=True))

    def test_cpu_count_cores(self):
        self.execute(lambda: psutil.cpu_count(logical=False))

    def test_cpu_times(self):
        self.execute(psutil.cpu_times)

    def test_per_cpu_times(self):
        self.execute(lambda: psutil.cpu_times(percpu=True))

    def test_cpu_stats(self):
        self.execute(psutil.cpu_stats)

    @pytest.mark.skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_cpu_freq(self):
        times = FEW_TIMES if LINUX else self.times
        self.execute(psutil.cpu_freq, times=times)

    @pytest.mark.skipif(not WINDOWS, reason="WINDOWS only")
    def test_getloadavg(self):
        psutil.getloadavg()
        self.execute(psutil.getloadavg)

    # --- mem

    def test_virtual_memory(self):
        self.execute(psutil.virtual_memory)

    # TODO: remove this skip when this gets fixed
    @pytest.mark.skipif(SUNOS, reason="worthless on SUNOS (uses a subprocess)")
    def test_swap_memory(self):
        self.execute(psutil.swap_memory)

    def test_pid_exists(self):
        times = FEW_TIMES if POSIX else self.times
        self.execute(lambda: psutil.pid_exists(os.getpid()), times=times)

    # --- disk

    def test_disk_usage(self):
        times = FEW_TIMES if POSIX else self.times
        self.execute(lambda: psutil.disk_usage('.'), times=times)

    def test_disk_partitions(self):
        self.execute(psutil.disk_partitions)

    @pytest.mark.skipif(
        LINUX and not os.path.exists('/proc/diskstats'),
        reason="/proc/diskstats not available on this Linux version",
    )
    def test_disk_io_counters(self):
        self.execute(lambda: psutil.disk_io_counters(nowrap=False))

    # --- proc

    def test_pids(self):
        self.execute(psutil.pids)

    # --- net

    @pytest.mark.skipif(not HAS_NET_IO_COUNTERS, reason="not supported")
    def test_net_io_counters(self):
        self.execute(lambda: psutil.net_io_counters(nowrap=False))

    @pytest.mark.skipif(MACOS and os.getuid() != 0, reason="need root access")
    def test_net_connections(self):
        # always opens and handle on Windows() (once)
        psutil.net_connections(kind='all')
        times = FEW_TIMES if LINUX else self.times
        with create_sockets():
            self.execute(
                lambda: psutil.net_connections(kind='all'), times=times
            )

    def test_net_if_addrs(self):
        if WINDOWS:
            # Calling GetAdaptersAddresses() for the first time
            # allocates internal OS handles. These handles persist for
            # the lifetime of the process, causing psleak to report
            # "unclosed handles". Call it here first to avoid false
            # positives.
            psutil.net_if_addrs()

        # Note: verified that on Windows this was a false positive.
        tolerance = 80 * 1024 if WINDOWS else self.tolerance
        self.execute(psutil.net_if_addrs, tolerance=tolerance)

    def test_net_if_stats(self):
        self.execute(psutil.net_if_stats)

    # --- sensors

    @pytest.mark.skipif(not HAS_SENSORS_BATTERY, reason="not supported")
    def test_sensors_battery(self):
        self.execute(psutil.sensors_battery)

    @pytest.mark.skipif(not HAS_SENSORS_TEMPERATURES, reason="not supported")
    @pytest.mark.skipif(LINUX, reason="too slow on LINUX")
    def test_sensors_temperatures(self):
        times = FEW_TIMES if LINUX else self.times
        self.execute(psutil.sensors_temperatures, times=times)

    @pytest.mark.skipif(not HAS_SENSORS_FANS, reason="not supported")
    def test_sensors_fans(self):
        times = FEW_TIMES if LINUX else self.times
        self.execute(psutil.sensors_fans, times=times)

    # --- others

    def test_boot_time(self):
        self.execute(psutil.boot_time)

    def test_users(self):
        if WINDOWS:
            # The first time this is called it allocates internal OS
            # handles. These handles persist for the lifetime of the
            # process, causing psleak to report "unclosed handles".
            # Call it here first to avoid false positives.
            psutil.users()
        self.execute(psutil.users)

    def test_set_debug(self):
        self.execute(lambda: psutil._set_debug(False))

    @pytest.mark.skipif(not HAS_HEAP_INFO, reason="not supported")
    def test_heap_info(self):
        self.execute(psutil.heap_info)

    @pytest.mark.skipif(not HAS_HEAP_INFO, reason="not supported")
    def test_heap_trim(self):
        self.execute(psutil.heap_trim)

    if WINDOWS:

        # --- win services

        def test_win_service_iter(self):
            self.execute(_psutil.winservice_enumerate)

        def test_win_service_get(self):
            pass

        def test_win_service_get_config(self):
            name = next(psutil.win_service_iter()).name()
            self.execute(lambda: _psutil.winservice_query_config(name))

        def test_win_service_get_status(self):
            name = next(psutil.win_service_iter()).name()
            self.execute(lambda: _psutil.winservice_query_status(name))

        def test_win_service_get_description(self):
            name = next(psutil.win_service_iter()).name()
            self.execute(lambda: _psutil.winservice_query_descr(name))


# ===================================================================
# bad arguments
# ===================================================================


class TestBadargs(MemoryLeakTestCase):
    """Pass a bad argument to each C function that accepts one, and make
    sure the resulting `PyArg_ParseTuple` failure path doesn't leak
    memory: a C function may allocate its return object before parsing
    its arguments, see: https://github.com/giampaolo/psutil/pull/2857/.
    """

    retries = 20
    badargs = (object(),) * 20

    def execute(self, fun, *args, **kwargs):
        # Every function here is called with a bad arg and must raise
        # TypeError (the parse-failure path we check for leaks).
        def call():
            try:
                fun(*args)
            except TypeError:
                pass
            else:
                pytest.fail(f"{fun} did not raise TypeError")

        super().execute(call, **kwargs)

    @classmethod
    def cext_arg_funcs(cls):
        # Names of the C functions that actually parse at least one
        # argument.
        names = []
        for name in dir(_psutil):
            if name.startswith("_"):
                continue
            func = getattr(_psutil, name)
            if not inspect.isbuiltin(func):  # skip exception classes
                continue
            try:
                func(*cls.badargs)
            except NotImplementedError:
                pass
            except TypeError as err:
                # "takes no arguments" => METH_NOARGS (no arg to test).
                if "takes no arguments" not in str(err):
                    names.append(name)
        return names

    @classmethod
    def auto_generate(cls):
        return {
            name: LeakTest(getattr(_psutil, name), *cls.badargs)
            for name in cls.cext_arg_funcs()
        }


def cext_has(name):
    return pytest.mark.skipif(
        not hasattr(_psutil, name), reason=f"no _psutil.{name}()"
    )


class TestBadargs2(MemoryLeakTestCase):
    """Like TestBadargsMemleaks, but for the error paths reached
    *after* `PyArg_ParseTuple` succeeds, by passing an invalid arg like
    a negative PID, a bogus NIC name etc., making the C function fail
    deeper.
    """

    retries = 20
    pid = os.getpid()

    # --- portable: same signature and error everywhere they exist

    @cext_has("proc_priority_get")
    def test_proc_priority_get(self):
        self.execute_w_exc(OSError, _psutil.proc_priority_get, -1)

    @cext_has("proc_priority_set")
    def test_proc_priority_set(self):
        self.execute_w_exc(OSError, _psutil.proc_priority_set, -1, 0)

    @cext_has("proc_cpu_affinity_get")
    def test_proc_cpu_affinity_get(self):
        # FreeBSD's cpuset_getaffinity() reads -1 as "the current
        # process", so it succeeds. Use another negative PID.
        pid = -2 if FREEBSD else -1
        self.execute_w_exc(OSError, _psutil.proc_cpu_affinity_get, pid)

    @cext_has("net_if_flags")
    def test_net_if_flags(self):
        self.execute_w_exc(OSError, _psutil.net_if_flags, "nonexistent0")

    @cext_has("net_if_mtu")
    def test_net_if_mtu(self):
        self.execute_w_exc(OSError, _psutil.net_if_mtu, "nonexistent0")

    @cext_has("net_if_is_running")
    def test_net_if_is_running(self):
        self.execute_w_exc(OSError, _psutil.net_if_is_running, "nonexistent0")

    # --- Linux only

    @cext_has("proc_ioprio_set")
    def test_proc_ioprio_set(self):
        self.execute_w_exc(OSError, _psutil.proc_ioprio_set, self.pid, -1, 0)

    @cext_has("proc_ioprio_get")
    def test_proc_ioprio_get(self):
        self.execute_w_exc(OSError, _psutil.proc_ioprio_get, -1)

    @pytest.mark.skipif(not LINUX, reason="LINUX only")
    def test_disk_partitions(self):
        self.execute_w_exc(OSError, _psutil.disk_partitions, "/does/not/exist")

    @pytest.mark.skipif(not LINUX, reason="LINUX only")
    def test_net_if_duplex_speed(self):
        self.execute_w_exc(
            OSError, _psutil.net_if_duplex_speed, "nonexistent0"
        )

    # --- other platform-specific behavior

    @pytest.mark.skipif(not LINUX, reason="LINUX only")
    def test_proc_cpu_affinity_set(self):
        self.execute_w_exc(
            ValueError, _psutil.proc_cpu_affinity_set, self.pid, [-1]
        )

    @pytest.mark.skipif(not POSIX, reason="POSIX only")
    def test_check_pid_range(self):
        self.execute_w_exc(ValueError, _psutil.check_pid_range, -1)
