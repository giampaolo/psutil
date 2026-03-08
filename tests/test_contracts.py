#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Contracts tests. These tests mainly check API sanity in terms of
returned types and APIs availability.
Some of these are duplicates of tests test_system.py and test_process.py.
"""

import collections.abc
import platform
import types as builtin_types
import typing

import psutil
from psutil import AIX
from psutil import BSD
from psutil import FREEBSD
from psutil import LINUX
from psutil import MACOS
from psutil import NETBSD
from psutil import OPENBSD
from psutil import POSIX
from psutil import SUNOS
from psutil import WINDOWS
from psutil import BatteryTime
from psutil import ConnectionStatus
from psutil import NicDuplex
from psutil import ProcessStatus

from . import AARCH64
from . import GITHUB_ACTIONS
from . import HAS_CPU_FREQ
from . import HAS_NET_IO_COUNTERS
from . import HAS_SENSORS_FANS
from . import HAS_SENSORS_TEMPERATURES
from . import SKIP_SYSCONS
from . import PsutilTestCase
from . import check_ntuple_types
from . import create_sockets
from . import enum
from . import get_return_hint
from . import is_namedtuple
from . import kernel_version
from . import process_namespace
from . import pytest
from . import system_namespace

# ===================================================================
# --- APIs availability
# ===================================================================

# Make sure code reflects what doc promises in terms of APIs
# availability.


class TestAvailConstantsAPIs(PsutilTestCase):

    def check_constants(self, names, are_avail):
        for name in names:
            with self.subTest(name=name):
                # assert CONSTANT is/isn't in psutil namespace
                assert hasattr(psutil, name) == are_avail
                # assert CONSTANT is/isn't in psutil.__all__
                if are_avail:
                    assert name in psutil.__all__
                else:
                    assert name not in psutil.__all__

    def test_PROCFS_PATH(self):
        self.check_constants(("PROCFS_PATH",), LINUX or SUNOS or AIX)

    def test_proc_status(self):
        names = (
            "STATUS_RUNNING",
            "STATUS_SLEEPING",
            "STATUS_DISK_SLEEP",
            "STATUS_STOPPED",
            "STATUS_TRACING_STOP",
            "STATUS_ZOMBIE",
            "STATUS_DEAD",
            "STATUS_WAKE_KILL",
            "STATUS_WAKING",
            "STATUS_IDLE",
            "STATUS_LOCKED",
            "STATUS_WAITING",
            "STATUS_SUSPENDED",
            "STATUS_PARKED",
        )
        self.check_constants(names, True)
        assert sorted(ProcessStatus.__members__.keys()) == sorted(names)

    def test_proc_status_strenum(self):
        mapping = (
            (psutil.STATUS_RUNNING, "running"),
            (psutil.STATUS_SLEEPING, "sleeping"),
            (psutil.STATUS_DISK_SLEEP, "disk-sleep"),
            (psutil.STATUS_STOPPED, "stopped"),
            (psutil.STATUS_TRACING_STOP, "tracing-stop"),
            (psutil.STATUS_ZOMBIE, "zombie"),
            (psutil.STATUS_DEAD, "dead"),
            (psutil.STATUS_WAKE_KILL, "wake-kill"),
            (psutil.STATUS_WAKING, "waking"),
            (psutil.STATUS_IDLE, "idle"),
            (psutil.STATUS_LOCKED, "locked"),
            (psutil.STATUS_WAITING, "waiting"),
            (psutil.STATUS_SUSPENDED, "suspended"),
            (psutil.STATUS_PARKED, "parked"),
        )
        for en, str_ in mapping:
            assert en == str_
            assert str(en) == str_
            assert repr(en) != str_

    def test_conn_status(self):
        names = [
            "CONN_ESTABLISHED",
            "CONN_SYN_SENT",
            "CONN_SYN_RECV",
            "CONN_FIN_WAIT1",
            "CONN_FIN_WAIT2",
            "CONN_TIME_WAIT",
            "CONN_CLOSE",
            "CONN_CLOSE_WAIT",
            "CONN_LAST_ACK",
            "CONN_LISTEN",
            "CONN_CLOSING",
            "CONN_NONE",
        ]
        if WINDOWS:
            names.append("CONN_DELETE_TCB")
        if SUNOS:
            names.extend(["CONN_IDLE", "CONN_BOUND"])

        self.check_constants(names, True)
        assert sorted(ConnectionStatus.__members__.keys()) == sorted(names)

    def test_conn_status_strenum(self):
        mapping = (
            (psutil.CONN_ESTABLISHED, "ESTABLISHED"),
            (psutil.CONN_SYN_SENT, "SYN_SENT"),
            (psutil.CONN_SYN_RECV, "SYN_RECV"),
            (psutil.CONN_FIN_WAIT1, "FIN_WAIT1"),
            (psutil.CONN_FIN_WAIT2, "FIN_WAIT2"),
            (psutil.CONN_TIME_WAIT, "TIME_WAIT"),
            (psutil.CONN_CLOSE, "CLOSE"),
            (psutil.CONN_CLOSE_WAIT, "CLOSE_WAIT"),
            (psutil.CONN_LAST_ACK, "LAST_ACK"),
            (psutil.CONN_LISTEN, "LISTEN"),
            (psutil.CONN_CLOSING, "CLOSING"),
            (psutil.CONN_NONE, "NONE"),
        )
        for en, str_ in mapping:
            assert en == str_
            assert str(en) == str_
            assert repr(en) != str_

    def test_nic_duplex(self):
        names = ("NIC_DUPLEX_FULL", "NIC_DUPLEX_HALF", "NIC_DUPLEX_UNKNOWN")
        self.check_constants(names, True)
        assert sorted(NicDuplex.__members__.keys()) == sorted(names)

    def test_battery_time(self):
        names = ("POWER_TIME_UNKNOWN", "POWER_TIME_UNLIMITED")
        self.check_constants(names, True)
        assert sorted(BatteryTime.__members__.keys()) == sorted(names)

    def test_proc_ioprio_class_linux(self):
        names = (
            "IOPRIO_CLASS_NONE",
            "IOPRIO_CLASS_RT",
            "IOPRIO_CLASS_BE",
            "IOPRIO_CLASS_IDLE",
        )
        self.check_constants(names, LINUX)
        if LINUX:
            assert sorted(
                psutil.ProcessIOPriority.__members__.keys()
            ) == sorted(names)
        else:
            not hasattr(psutil, "ProcessIOPriority")

    def test_proc_ioprio_value_windows(self):
        names = (
            "IOPRIO_HIGH",
            "IOPRIO_NORMAL",
            "IOPRIO_LOW",
            "IOPRIO_VERYLOW",
        )
        self.check_constants(names, WINDOWS)
        if WINDOWS:
            assert sorted(
                psutil.ProcessIOPriority.__members__.keys()
            ) == sorted(names)

    def test_proc_priority_windows(self):
        names = (
            "ABOVE_NORMAL_PRIORITY_CLASS",
            "BELOW_NORMAL_PRIORITY_CLASS",
            "HIGH_PRIORITY_CLASS",
            "IDLE_PRIORITY_CLASS",
            "NORMAL_PRIORITY_CLASS",
            "REALTIME_PRIORITY_CLASS",
        )
        self.check_constants(names, WINDOWS)
        if WINDOWS:
            assert sorted(psutil.ProcessPriority.__members__.keys()) == sorted(
                names
            )
        else:
            not hasattr(psutil, "ProcessPriority")

    @pytest.mark.skipif(
        GITHUB_ACTIONS and LINUX,
        reason="unsupported on GITHUB_ACTIONS + LINUX",
    )
    def test_rlimit(self):
        names = (
            "RLIM_INFINITY",
            "RLIMIT_AS",
            "RLIMIT_CORE",
            "RLIMIT_CPU",
            "RLIMIT_DATA",
            "RLIMIT_FSIZE",
            "RLIMIT_MEMLOCK",
            "RLIMIT_NOFILE",
            "RLIMIT_NPROC",
            "RLIMIT_RSS",
            "RLIMIT_STACK",
        )
        self.check_constants(names, LINUX or FREEBSD)
        self.check_constants(("RLIMIT_LOCKS",), LINUX)
        self.check_constants(
            ("RLIMIT_SWAP", "RLIMIT_SBSIZE", "RLIMIT_NPTS"), FREEBSD
        )

        if POSIX:
            if kernel_version() >= (2, 6, 8):
                self.check_constants(("RLIMIT_MSGQUEUE",), LINUX)
            if kernel_version() >= (2, 6, 12):
                self.check_constants(("RLIMIT_NICE", "RLIMIT_RTPRIO"), LINUX)
            if kernel_version() >= (2, 6, 25):
                self.check_constants(("RLIMIT_RTTIME",), LINUX)
            if kernel_version() >= (2, 6, 8):
                self.check_constants(("RLIMIT_SIGPENDING",), LINUX)

    def test_enum_containers(self):
        self.check_constants(("ProcessStatus",), True)
        self.check_constants(("ProcessPriority",), WINDOWS)
        self.check_constants(("ProcessIOPriority",), LINUX or WINDOWS)
        self.check_constants(("ConnectionStatus",), True)
        self.check_constants(("NicDuplex",), True)
        self.check_constants(("BatteryTime",), True)


class TestAvailSystemAPIs(PsutilTestCase):
    def test_win_service_iter(self):
        assert hasattr(psutil, "win_service_iter") == WINDOWS

    def test_win_service_get(self):
        assert hasattr(psutil, "win_service_get") == WINDOWS

    @pytest.mark.skipif(
        MACOS and AARCH64 and not HAS_CPU_FREQ, reason="not supported"
    )
    def test_cpu_freq(self):
        assert hasattr(psutil, "cpu_freq") == (
            LINUX or MACOS or WINDOWS or FREEBSD or OPENBSD
        )

    def test_sensors_temperatures(self):
        assert hasattr(psutil, "sensors_temperatures") == (LINUX or FREEBSD)

    def test_sensors_fans(self):
        assert hasattr(psutil, "sensors_fans") == LINUX

    def test_battery(self):
        assert hasattr(psutil, "sensors_battery") == (
            LINUX or WINDOWS or FREEBSD or MACOS
        )

    def test_heap_info(self):
        hasit = hasattr(psutil, "heap_info")
        if LINUX:
            assert hasit == bool(platform.libc_ver() != ("", ""))
        else:
            assert hasit == MACOS or WINDOWS or BSD

    def test_heap_trim(self):
        hasit = hasattr(psutil, "heap_trim")
        if LINUX:
            assert hasit == bool(platform.libc_ver() != ("", ""))
        else:
            assert hasit == MACOS or WINDOWS or BSD


class TestAvailProcessAPIs(PsutilTestCase):
    def test_environ(self):
        assert hasattr(psutil.Process, "environ") == (
            LINUX
            or MACOS
            or WINDOWS
            or AIX
            or SUNOS
            or FREEBSD
            or OPENBSD
            or NETBSD
        )

    def test_uids(self):
        assert hasattr(psutil.Process, "uids") == POSIX

    def test_gids(self):
        assert hasattr(psutil.Process, "uids") == POSIX

    def test_terminal(self):
        assert hasattr(psutil.Process, "terminal") == POSIX

    def test_ionice(self):
        assert hasattr(psutil.Process, "ionice") == (LINUX or WINDOWS)

    @pytest.mark.skipif(
        GITHUB_ACTIONS and LINUX,
        reason="unsupported on GITHUB_ACTIONS + LINUX",
    )
    def test_rlimit(self):
        assert hasattr(psutil.Process, "rlimit") == (LINUX or FREEBSD)

    def test_io_counters(self):
        hasit = hasattr(psutil.Process, "io_counters")
        assert hasit == (not (MACOS or SUNOS))

    def test_num_fds(self):
        assert hasattr(psutil.Process, "num_fds") == POSIX

    def test_num_handles(self):
        assert hasattr(psutil.Process, "num_handles") == WINDOWS

    def test_cpu_affinity(self):
        assert hasattr(psutil.Process, "cpu_affinity") == (
            LINUX or WINDOWS or FREEBSD
        )

    def test_cpu_num(self):
        assert hasattr(psutil.Process, "cpu_num") == (
            LINUX or FREEBSD or SUNOS
        )

    def test_memory_maps(self):
        hasit = hasattr(psutil.Process, "memory_maps")
        assert hasit == (not (OPENBSD or NETBSD or AIX or MACOS))

    def test_memory_footprint(self):
        hasit = hasattr(psutil.Process, "memory_footprint")
        assert hasit == (LINUX or MACOS or WINDOWS)


# ===================================================================
# --- API types
# ===================================================================


class TestSystemAPITypes(PsutilTestCase):
    """Check the return types of system related APIs.
    https://github.com/giampaolo/psutil/issues/1039.
    """

    @classmethod
    def setUpClass(cls):
        cls.proc = psutil.Process()

    def assert_ntuple_of_nums(self, nt, type_=float, gezero=True):
        assert is_namedtuple(nt)
        for n in nt:
            assert isinstance(n, type_)
            if gezero:
                assert n >= 0

    def test_cpu_times(self):
        self.assert_ntuple_of_nums(psutil.cpu_times())
        for nt in psutil.cpu_times(percpu=True):
            self.assert_ntuple_of_nums(nt)

    def test_cpu_percent(self):
        assert isinstance(psutil.cpu_percent(interval=None), float)
        assert isinstance(psutil.cpu_percent(interval=0.00001), float)

    def test_cpu_times_percent(self):
        self.assert_ntuple_of_nums(psutil.cpu_times_percent(interval=None))
        self.assert_ntuple_of_nums(psutil.cpu_times_percent(interval=0.0001))

    def test_cpu_count(self):
        assert isinstance(psutil.cpu_count(), int)

    @pytest.mark.skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_cpu_freq(self):
        if psutil.cpu_freq() is None:
            return pytest.skip("cpu_freq() returns None")
        self.assert_ntuple_of_nums(psutil.cpu_freq(), type_=(float, int))

    def test_disk_io_counters(self):
        # Duplicate of test_system.py. Keep it anyway.
        for k, v in psutil.disk_io_counters(perdisk=True).items():
            assert isinstance(k, str)
            self.assert_ntuple_of_nums(v, type_=int)

    def test_disk_partitions(self):
        # Duplicate of test_system.py. Keep it anyway.
        for disk in psutil.disk_partitions():
            assert isinstance(disk.device, str)
            assert isinstance(disk.mountpoint, str)
            assert isinstance(disk.fstype, str)
            assert isinstance(disk.opts, str)

    @pytest.mark.skipif(SKIP_SYSCONS, reason="requires root")
    def test_net_connections(self):
        with create_sockets():
            ret = psutil.net_connections('all')
            assert len(ret) == len(set(ret))
            for conn in ret:
                assert is_namedtuple(conn)

    def test_net_if_addrs(self):
        # Duplicate of test_system.py. Keep it anyway.
        for ifname, addrs in psutil.net_if_addrs().items():
            assert isinstance(ifname, str)
            for addr in addrs:
                assert isinstance(addr.family, enum.IntEnum)
                assert isinstance(addr.address, str)
                assert isinstance(addr.netmask, (str, type(None)))
                assert isinstance(addr.broadcast, (str, type(None)))

    def test_net_if_stats(self):
        # Duplicate of test_system.py. Keep it anyway.
        for ifname, info in psutil.net_if_stats().items():
            assert isinstance(ifname, str)
            assert isinstance(info.isup, bool)
            assert isinstance(info.duplex, enum.IntEnum)
            assert isinstance(info.speed, int)
            assert isinstance(info.mtu, int)

    @pytest.mark.skipif(not HAS_NET_IO_COUNTERS, reason="not supported")
    def test_net_io_counters(self):
        # Duplicate of test_system.py. Keep it anyway.
        for ifname in psutil.net_io_counters(pernic=True):
            assert isinstance(ifname, str)

    @pytest.mark.skipif(not HAS_SENSORS_FANS, reason="not supported")
    def test_sensors_fans(self):
        # Duplicate of test_system.py. Keep it anyway.
        for name, units in psutil.sensors_fans().items():
            assert isinstance(name, str)
            for unit in units:
                assert isinstance(unit.label, str)
                assert isinstance(unit.current, (float, int, type(None)))

    @pytest.mark.skipif(not HAS_SENSORS_TEMPERATURES, reason="not supported")
    def test_sensors_temperatures(self):
        # Duplicate of test_system.py. Keep it anyway.
        for name, units in psutil.sensors_temperatures().items():
            assert isinstance(name, str)
            for unit in units:
                assert isinstance(unit.label, str)
                assert isinstance(unit.current, (float, int, type(None)))
                assert isinstance(unit.high, (float, int, type(None)))
                assert isinstance(unit.critical, (float, int, type(None)))

    def test_boot_time(self):
        # Duplicate of test_system.py. Keep it anyway.
        assert isinstance(psutil.boot_time(), float)

    def test_users(self):
        # Duplicate of test_system.py. Keep it anyway.
        for user in psutil.users():
            assert isinstance(user.name, str)
            assert isinstance(user.terminal, (str, type(None)))
            assert isinstance(user.host, (str, type(None)))
            assert isinstance(user.pid, (int, type(None)))
            if isinstance(user.pid, int):
                assert user.pid > 0


# ===================================================================
# --- namedtuple field types
# ===================================================================


class TestNtupleFieldTypes(PsutilTestCase):
    """Check that namedtuple field values match the type annotations
    defined in psutil/_ntuples.py.
    """

    def check_result(self, ret):
        if is_namedtuple(ret):
            check_ntuple_types(ret)
        elif isinstance(ret, list):
            for item in ret:
                if is_namedtuple(item):
                    check_ntuple_types(item)

    def test_system_ntuple_types(self):
        for fun, name in system_namespace.iter(system_namespace.getters):
            try:
                ret = fun()
            except psutil.Error:
                continue
            with self.subTest(name=name, fun=str(fun)):
                if isinstance(ret, dict):
                    for v in ret.values():
                        if isinstance(v, list):
                            for item in v:
                                self.check_result(item)
                        else:
                            self.check_result(v)
                else:
                    self.check_result(ret)

    def test_process_ntuple_types(self):
        p = psutil.Process()
        ns = process_namespace(p)
        for fun, name in ns.iter(ns.getters):
            with self.subTest(name=name, fun=str(fun)):
                try:
                    ret = fun()
                except psutil.Error:
                    continue
                self.check_result(ret)


# ===================================================================
# --- returned type hints
# ===================================================================


class TestReturnedTypes(PsutilTestCase):
    """Check that annotated return types in psutil/__init__.py match
    the actual values returned at runtime.
    """

    def _hint_to_types(self, hint):
        """Flatten a return type hint into a tuple of types for
        isinstance(). Returns None if the hint cannot be checked
        (e.g. Generator).
        """
        if hint is None:
            return None
        origin = typing.get_origin(hint)
        args = typing.get_args(hint)
        if origin is collections.abc.Generator:
            return None
        is_union = origin is typing.Union or (
            hasattr(builtin_types, 'UnionType')
            and origin is builtin_types.UnionType
        )
        if is_union:
            result = []
            for arg in args:
                inner = typing.get_origin(arg)
                if arg is type(None):
                    result.append(type(None))
                elif inner is not None:
                    result.append(inner)
                elif isinstance(arg, type):
                    result.append(arg)
            return tuple(result) if result else None
        if origin is not None:
            return (origin,)
        if isinstance(hint, type):
            return (hint,)
        return None

    def _check(self, fun, name):
        """Call fun() and check return value type against the hint."""
        try:
            ret = fun()
        except psutil.Error:
            return
        hint = get_return_hint(fun)
        types_ = self._hint_to_types(hint)
        if types_ is None:
            return
        assert isinstance(ret, types_), (name, ret, types_)

    def test_system_return_types(self):
        for fun, name in system_namespace.iter(system_namespace.getters):
            with self.subTest(name=name):
                self._check(fun, name)

    def test_process_return_types(self):
        p = psutil.Process()
        ns = process_namespace(p)
        for fun, name in ns.iter(ns.getters):
            with self.subTest(name=name):
                self._check(fun, name)
