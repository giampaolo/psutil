#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Contracts tests. These tests mainly check API sanity in terms of
returned types and APIs availability.
Some of these are duplicates of tests test_system.py and test_process.py
"""

import errno
import os
import stat
import time
import traceback

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
from psutil._compat import long
from psutil.tests import create_sockets
from psutil.tests import enum
from psutil.tests import get_kernel_version
from psutil.tests import HAS_CPU_FREQ
from psutil.tests import HAS_NET_IO_COUNTERS
from psutil.tests import HAS_RLIMIT
from psutil.tests import HAS_SENSORS_FANS
from psutil.tests import HAS_SENSORS_TEMPERATURES
from psutil.tests import is_namedtuple
from psutil.tests import safe_rmpath
from psutil.tests import SKIP_SYSCONS
from psutil.tests import TESTFN
from psutil.tests import unittest
from psutil.tests import VALID_PROC_STATUSES
from psutil.tests import warn
import psutil


# ===================================================================
# --- APIs availability
# ===================================================================

# Make sure code reflects what doc promises in terms of APIs
# availability.

class TestAvailConstantsAPIs(unittest.TestCase):

    def test_PROCFS_PATH(self):
        self.assertEqual(hasattr(psutil, "PROCFS_PATH"),
                         LINUX or SUNOS or AIX)

    def test_win_priority(self):
        ae = self.assertEqual
        ae(hasattr(psutil, "ABOVE_NORMAL_PRIORITY_CLASS"), WINDOWS)
        ae(hasattr(psutil, "BELOW_NORMAL_PRIORITY_CLASS"), WINDOWS)
        ae(hasattr(psutil, "HIGH_PRIORITY_CLASS"), WINDOWS)
        ae(hasattr(psutil, "IDLE_PRIORITY_CLASS"), WINDOWS)
        ae(hasattr(psutil, "NORMAL_PRIORITY_CLASS"), WINDOWS)
        ae(hasattr(psutil, "REALTIME_PRIORITY_CLASS"), WINDOWS)

    def test_linux_ioprio_linux(self):
        ae = self.assertEqual
        ae(hasattr(psutil, "IOPRIO_CLASS_NONE"), LINUX)
        ae(hasattr(psutil, "IOPRIO_CLASS_RT"), LINUX)
        ae(hasattr(psutil, "IOPRIO_CLASS_BE"), LINUX)
        ae(hasattr(psutil, "IOPRIO_CLASS_IDLE"), LINUX)

    def test_linux_ioprio_windows(self):
        ae = self.assertEqual
        ae(hasattr(psutil, "IOPRIO_HIGH"), WINDOWS)
        ae(hasattr(psutil, "IOPRIO_NORMAL"), WINDOWS)
        ae(hasattr(psutil, "IOPRIO_LOW"), WINDOWS)
        ae(hasattr(psutil, "IOPRIO_VERYLOW"), WINDOWS)

    def test_linux_rlimit(self):
        ae = self.assertEqual
        hasit = LINUX and get_kernel_version() >= (2, 6, 36)
        ae(hasattr(psutil.Process, "rlimit"), hasit)
        ae(hasattr(psutil, "RLIM_INFINITY"), hasit)
        ae(hasattr(psutil, "RLIMIT_AS"), hasit)
        ae(hasattr(psutil, "RLIMIT_CORE"), hasit)
        ae(hasattr(psutil, "RLIMIT_CPU"), hasit)
        ae(hasattr(psutil, "RLIMIT_DATA"), hasit)
        ae(hasattr(psutil, "RLIMIT_FSIZE"), hasit)
        ae(hasattr(psutil, "RLIMIT_LOCKS"), hasit)
        ae(hasattr(psutil, "RLIMIT_MEMLOCK"), hasit)
        ae(hasattr(psutil, "RLIMIT_NOFILE"), hasit)
        ae(hasattr(psutil, "RLIMIT_NPROC"), hasit)
        ae(hasattr(psutil, "RLIMIT_RSS"), hasit)
        ae(hasattr(psutil, "RLIMIT_STACK"), hasit)

        hasit = LINUX and get_kernel_version() >= (3, 0)
        ae(hasattr(psutil, "RLIMIT_MSGQUEUE"), hasit)
        ae(hasattr(psutil, "RLIMIT_NICE"), hasit)
        ae(hasattr(psutil, "RLIMIT_RTPRIO"), hasit)
        ae(hasattr(psutil, "RLIMIT_RTTIME"), hasit)
        ae(hasattr(psutil, "RLIMIT_SIGPENDING"), hasit)


class TestAvailSystemAPIs(unittest.TestCase):

    def test_win_service_iter(self):
        self.assertEqual(hasattr(psutil, "win_service_iter"), WINDOWS)

    def test_win_service_get(self):
        self.assertEqual(hasattr(psutil, "win_service_get"), WINDOWS)

    def test_cpu_freq(self):
        linux = (LINUX and
                 (os.path.exists("/sys/devices/system/cpu/cpufreq") or
                  os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq")))
        self.assertEqual(hasattr(psutil, "cpu_freq"),
                         linux or MACOS or WINDOWS or FREEBSD)

    def test_sensors_temperatures(self):
        self.assertEqual(
            hasattr(psutil, "sensors_temperatures"), LINUX or FREEBSD)

    def test_sensors_fans(self):
        self.assertEqual(hasattr(psutil, "sensors_fans"), LINUX)

    def test_battery(self):
        self.assertEqual(hasattr(psutil, "sensors_battery"),
                         LINUX or WINDOWS or FREEBSD or MACOS)


class TestAvailProcessAPIs(unittest.TestCase):

    def test_environ(self):
        self.assertEqual(hasattr(psutil.Process, "environ"),
                         LINUX or MACOS or WINDOWS or AIX or SUNOS)

    def test_uids(self):
        self.assertEqual(hasattr(psutil.Process, "uids"), POSIX)

    def test_gids(self):
        self.assertEqual(hasattr(psutil.Process, "uids"), POSIX)

    def test_terminal(self):
        self.assertEqual(hasattr(psutil.Process, "terminal"), POSIX)

    def test_ionice(self):
        self.assertEqual(hasattr(psutil.Process, "ionice"), LINUX or WINDOWS)

    def test_rlimit(self):
        self.assertEqual(hasattr(psutil.Process, "rlimit"), LINUX)

    def test_io_counters(self):
        hasit = hasattr(psutil.Process, "io_counters")
        self.assertEqual(hasit, False if MACOS or SUNOS else True)

    def test_num_fds(self):
        self.assertEqual(hasattr(psutil.Process, "num_fds"), POSIX)

    def test_num_handles(self):
        self.assertEqual(hasattr(psutil.Process, "num_handles"), WINDOWS)

    def test_cpu_affinity(self):
        self.assertEqual(hasattr(psutil.Process, "cpu_affinity"),
                         LINUX or WINDOWS or FREEBSD)

    def test_cpu_num(self):
        self.assertEqual(hasattr(psutil.Process, "cpu_num"),
                         LINUX or FREEBSD or SUNOS)

    def test_memory_maps(self):
        hasit = hasattr(psutil.Process, "memory_maps")
        self.assertEqual(
            hasit, False if OPENBSD or NETBSD or AIX or MACOS else True)


# ===================================================================
# --- System API types
# ===================================================================


class TestSystemAPITypes(unittest.TestCase):
    """Check the return types of system related APIs.
    Mainly we want to test we never return unicode on Python 2, see:
    https://github.com/giampaolo/psutil/issues/1039
    """

    @classmethod
    def setUpClass(cls):
        cls.proc = psutil.Process()

    def tearDown(self):
        safe_rmpath(TESTFN)

    def assert_ntuple_of_nums(self, nt, type_=float, gezero=True):
        assert is_namedtuple(nt)
        for n in nt:
            self.assertIsInstance(n, type_)
            if gezero:
                self.assertGreaterEqual(n, 0)

    def test_cpu_times(self):
        self.assert_ntuple_of_nums(psutil.cpu_times())
        for nt in psutil.cpu_times(percpu=True):
            self.assert_ntuple_of_nums(nt)

    def test_cpu_percent(self):
        self.assertIsInstance(psutil.cpu_percent(interval=None), float)
        self.assertIsInstance(psutil.cpu_percent(interval=0.00001), float)

    def test_cpu_times_percent(self):
        self.assert_ntuple_of_nums(psutil.cpu_times_percent(interval=None))
        self.assert_ntuple_of_nums(psutil.cpu_times_percent(interval=0.0001))

    def test_cpu_count(self):
        self.assertIsInstance(psutil.cpu_count(), int)

    @unittest.skipIf(not HAS_CPU_FREQ, "not supported")
    def test_cpu_freq(self):
        if psutil.cpu_freq() is None:
            raise self.skipTest("cpu_freq() returns None")
        self.assert_ntuple_of_nums(psutil.cpu_freq(), type_=(float, int, long))

    def test_disk_io_counters(self):
        # Duplicate of test_system.py. Keep it anyway.
        for k, v in psutil.disk_io_counters(perdisk=True).items():
            self.assertIsInstance(k, str)
            self.assert_ntuple_of_nums(v, type_=(int, long))

    def test_disk_partitions(self):
        # Duplicate of test_system.py. Keep it anyway.
        for disk in psutil.disk_partitions():
            self.assertIsInstance(disk.device, str)
            self.assertIsInstance(disk.mountpoint, str)
            self.assertIsInstance(disk.fstype, str)
            self.assertIsInstance(disk.opts, str)

    @unittest.skipIf(SKIP_SYSCONS, "requires root")
    def test_net_connections(self):
        with create_sockets():
            ret = psutil.net_connections('all')
            self.assertEqual(len(ret), len(set(ret)))
            for conn in ret:
                assert is_namedtuple(conn)

    def test_net_if_addrs(self):
        # Duplicate of test_system.py. Keep it anyway.
        for ifname, addrs in psutil.net_if_addrs().items():
            self.assertIsInstance(ifname, str)
            for addr in addrs:
                if enum is not None:
                    assert isinstance(addr.family, enum.IntEnum), addr
                else:
                    assert isinstance(addr.family, int), addr
                self.assertIsInstance(addr.address, str)
                self.assertIsInstance(addr.netmask, (str, type(None)))
                self.assertIsInstance(addr.broadcast, (str, type(None)))

    def test_net_if_stats(self):
        # Duplicate of test_system.py. Keep it anyway.
        for ifname, info in psutil.net_if_stats().items():
            self.assertIsInstance(ifname, str)
            self.assertIsInstance(info.isup, bool)
            if enum is not None:
                self.assertIsInstance(info.duplex, enum.IntEnum)
            else:
                self.assertIsInstance(info.duplex, int)
            self.assertIsInstance(info.speed, int)
            self.assertIsInstance(info.mtu, int)

    @unittest.skipIf(not HAS_NET_IO_COUNTERS, 'not supported')
    def test_net_io_counters(self):
        # Duplicate of test_system.py. Keep it anyway.
        for ifname, _ in psutil.net_io_counters(pernic=True).items():
            self.assertIsInstance(ifname, str)

    @unittest.skipIf(not HAS_SENSORS_FANS, "not supported")
    def test_sensors_fans(self):
        # Duplicate of test_system.py. Keep it anyway.
        for name, units in psutil.sensors_fans().items():
            self.assertIsInstance(name, str)
            for unit in units:
                self.assertIsInstance(unit.label, str)
                self.assertIsInstance(unit.current, (float, int, type(None)))

    @unittest.skipIf(not HAS_SENSORS_TEMPERATURES, "not supported")
    def test_sensors_temperatures(self):
        # Duplicate of test_system.py. Keep it anyway.
        for name, units in psutil.sensors_temperatures().items():
            self.assertIsInstance(name, str)
            for unit in units:
                self.assertIsInstance(unit.label, str)
                self.assertIsInstance(unit.current, (float, int, type(None)))
                self.assertIsInstance(unit.high, (float, int, type(None)))
                self.assertIsInstance(unit.critical, (float, int, type(None)))

    def test_boot_time(self):
        # Duplicate of test_system.py. Keep it anyway.
        self.assertIsInstance(psutil.boot_time(), float)

    def test_users(self):
        # Duplicate of test_system.py. Keep it anyway.
        for user in psutil.users():
            self.assertIsInstance(user.name, str)
            self.assertIsInstance(user.terminal, (str, type(None)))
            self.assertIsInstance(user.host, (str, type(None)))
            self.assertIsInstance(user.pid, (int, type(None)))


# ===================================================================
# --- Featch all processes test
# ===================================================================


class TestFetchAllProcesses(unittest.TestCase):
    """Test which iterates over all running processes and performs
    some sanity checks against Process API's returned values.
    """

    def get_attr_names(self):
        excluded_names = set([
            'send_signal', 'suspend', 'resume', 'terminate', 'kill', 'wait',
            'as_dict', 'parent', 'parents', 'children', 'memory_info_ex',
            'oneshot',
        ])
        if LINUX and not HAS_RLIMIT:
            excluded_names.add('rlimit')
        attrs = []
        for name in dir(psutil.Process):
            if name.startswith("_"):
                continue
            if name in excluded_names:
                continue
            attrs.append(name)
        return attrs

    def iter_procs(self):
        attrs = self.get_attr_names()
        for p in psutil.process_iter():
            with p.oneshot():
                for name in attrs:
                    yield (p, name)

    def call_meth(self, p, name):
        args = ()
        kwargs = {}
        attr = getattr(p, name, None)
        if attr is not None and callable(attr):
            if name == 'rlimit':
                args = (psutil.RLIMIT_NOFILE,)
            elif name == 'memory_maps':
                kwargs = {'grouped': False}
            return attr(*args, **kwargs)
        else:
            return attr

    def test_fetch_all(self):
        valid_procs = 0
        default = object()
        failures = []
        for p, name in self.iter_procs():
            ret = default
            try:
                ret = self.call_meth(p, name)
            except NotImplementedError:
                msg = "%r was skipped because not implemented" % (
                    self.__class__.__name__ + '.test_' + name)
                warn(msg)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as err:
                self.assertEqual(err.pid, p.pid)
                if err.name:
                    # make sure exception's name attr is set
                    # with the actual process name
                    self.assertEqual(err.name, p.name())
                assert str(err)
                assert err.msg
            except Exception:
                s = '\n' + '=' * 70 + '\n'
                s += "FAIL: test_%s (proc=%s" % (name, p)
                if ret != default:
                    s += ", ret=%s)" % repr(ret)
                s += ')\n'
                s += '-' * 70
                s += "\n%s" % traceback.format_exc()
                s = "\n".join((" " * 4) + i for i in s.splitlines())
                s += '\n'
                failures.append(s)
                break
            else:
                valid_procs += 1
                if ret not in (0, 0.0, [], None, '', {}):
                    assert ret, ret
                meth = getattr(self, name)
                meth(ret, p)

        if failures:
            self.fail(''.join(failures))

        # we should always have a non-empty list, not including PID 0 etc.
        # special cases.
        assert valid_procs

    def cmdline(self, ret, proc):
        self.assertIsInstance(ret, list)
        for part in ret:
            self.assertIsInstance(part, str)

    def exe(self, ret, proc):
        self.assertIsInstance(ret, (str, type(None)))
        if not ret:
            self.assertEqual(ret, '')
        else:
            if WINDOWS and not ret.endswith('.exe'):
                return  # May be "Registry", "MemCompression", ...
            assert os.path.isabs(ret), ret
            # Note: os.stat() may return False even if the file is there
            # hence we skip the test, see:
            # http://stackoverflow.com/questions/3112546/os-path-exists-lies
            if POSIX and os.path.isfile(ret):
                if hasattr(os, 'access') and hasattr(os, "X_OK"):
                    # XXX may fail on MACOS
                    assert os.access(ret, os.X_OK)

    def pid(self, ret, proc):
        self.assertIsInstance(ret, int)
        self.assertGreaterEqual(ret, 0)

    def ppid(self, ret, proc):
        self.assertIsInstance(ret, (int, long))
        self.assertGreaterEqual(ret, 0)

    def name(self, ret, proc):
        self.assertIsInstance(ret, str)
        # on AIX, "<exiting>" processes don't have names
        if not AIX:
            assert ret

    def create_time(self, ret, proc):
        self.assertIsInstance(ret, float)
        try:
            self.assertGreaterEqual(ret, 0)
        except AssertionError:
            # XXX
            if OPENBSD and proc.status() == psutil.STATUS_ZOMBIE:
                pass
            else:
                raise
        # this can't be taken for granted on all platforms
        # self.assertGreaterEqual(ret, psutil.boot_time())
        # make sure returned value can be pretty printed
        # with strftime
        time.strftime("%Y %m %d %H:%M:%S", time.localtime(ret))

    def uids(self, ret, proc):
        assert is_namedtuple(ret)
        for uid in ret:
            self.assertIsInstance(uid, int)
            self.assertGreaterEqual(uid, 0)

    def gids(self, ret, proc):
        assert is_namedtuple(ret)
        # note: testing all gids as above seems not to be reliable for
        # gid == 30 (nodoby); not sure why.
        for gid in ret:
            self.assertIsInstance(gid, int)
            if not MACOS and not NETBSD:
                self.assertGreaterEqual(gid, 0)

    def username(self, ret, proc):
        self.assertIsInstance(ret, str)
        assert ret

    def status(self, ret, proc):
        self.assertIsInstance(ret, str)
        assert ret
        self.assertNotEqual(ret, '?')  # XXX
        self.assertIn(ret, VALID_PROC_STATUSES)

    def io_counters(self, ret, proc):
        assert is_namedtuple(ret)
        for field in ret:
            self.assertIsInstance(field, (int, long))
            if field != -1:
                self.assertGreaterEqual(field, 0)

    def ionice(self, ret, proc):
        if LINUX:
            self.assertIsInstance(ret.ioclass, int)
            self.assertIsInstance(ret.value, int)
            self.assertGreaterEqual(ret.ioclass, 0)
            self.assertGreaterEqual(ret.value, 0)
        else:  # Windows, Cygwin
            choices = [
                psutil.IOPRIO_VERYLOW,
                psutil.IOPRIO_LOW,
                psutil.IOPRIO_NORMAL,
                psutil.IOPRIO_HIGH]
            self.assertIsInstance(ret, int)
            self.assertGreaterEqual(ret, 0)
            self.assertIn(ret, choices)

    def num_threads(self, ret, proc):
        self.assertIsInstance(ret, int)
        self.assertGreaterEqual(ret, 1)

    def threads(self, ret, proc):
        self.assertIsInstance(ret, list)
        for t in ret:
            assert is_namedtuple(t)
            self.assertGreaterEqual(t.id, 0)
            self.assertGreaterEqual(t.user_time, 0)
            self.assertGreaterEqual(t.system_time, 0)
            for field in t:
                self.assertIsInstance(field, (int, float))

    def cpu_times(self, ret, proc):
        assert is_namedtuple(ret)
        for n in ret:
            self.assertIsInstance(n, float)
            self.assertGreaterEqual(n, 0)
        # TODO: check ntuple fields

    def cpu_percent(self, ret, proc):
        self.assertIsInstance(ret, float)
        assert 0.0 <= ret <= 100.0, ret

    def cpu_num(self, ret, proc):
        self.assertIsInstance(ret, int)
        if FREEBSD and ret == -1:
            return
        self.assertGreaterEqual(ret, 0)
        if psutil.cpu_count() == 1:
            self.assertEqual(ret, 0)
        self.assertIn(ret, list(range(psutil.cpu_count())))

    def memory_info(self, ret, proc):
        assert is_namedtuple(ret)
        for value in ret:
            self.assertIsInstance(value, (int, long))
            self.assertGreaterEqual(value, 0)
        if WINDOWS:
            self.assertGreaterEqual(ret.peak_wset, ret.wset)
            self.assertGreaterEqual(ret.peak_paged_pool, ret.paged_pool)
            self.assertGreaterEqual(ret.peak_nonpaged_pool, ret.nonpaged_pool)
            self.assertGreaterEqual(ret.peak_pagefile, ret.pagefile)

    def memory_full_info(self, ret, proc):
        assert is_namedtuple(ret)
        total = psutil.virtual_memory().total
        for name in ret._fields:
            value = getattr(ret, name)
            self.assertIsInstance(value, (int, long))
            self.assertGreaterEqual(value, 0, msg=(name, value))
            if LINUX or OSX and name in ('vms', 'data'):
                # On Linux there are processes (e.g. 'goa-daemon') whose
                # VMS is incredibly high for some reason.
                continue
            self.assertLessEqual(value, total, msg=(name, value, total))

        if LINUX:
            self.assertGreaterEqual(ret.pss, ret.uss)

    def open_files(self, ret, proc):
        self.assertIsInstance(ret, list)
        for f in ret:
            self.assertIsInstance(f.fd, int)
            self.assertIsInstance(f.path, str)
            if WINDOWS:
                self.assertEqual(f.fd, -1)
            elif LINUX:
                self.assertIsInstance(f.position, int)
                self.assertIsInstance(f.mode, str)
                self.assertIsInstance(f.flags, int)
                self.assertGreaterEqual(f.position, 0)
                self.assertIn(f.mode, ('r', 'w', 'a', 'r+', 'a+'))
                self.assertGreater(f.flags, 0)
            elif BSD and not f.path:
                # XXX see: https://github.com/giampaolo/psutil/issues/595
                continue
            assert os.path.isabs(f.path), f
            assert os.path.isfile(f.path), f

    def num_fds(self, ret, proc):
        self.assertIsInstance(ret, int)
        self.assertGreaterEqual(ret, 0)

    def connections(self, ret, proc):
        with create_sockets():
            self.assertEqual(len(ret), len(set(ret)))
            for conn in ret:
                assert is_namedtuple(conn)

    def cwd(self, ret, proc):
        if ret:     # 'ret' can be None or empty
            self.assertIsInstance(ret, str)
            assert os.path.isabs(ret), ret
            try:
                st = os.stat(ret)
            except OSError as err:
                if WINDOWS and err.errno in \
                        psutil._psplatform.ACCESS_DENIED_SET:
                    pass
                # directory has been removed in mean time
                elif err.errno != errno.ENOENT:
                    raise
            else:
                assert stat.S_ISDIR(st.st_mode)

    def memory_percent(self, ret, proc):
        self.assertIsInstance(ret, float)
        assert 0 <= ret <= 100, ret

    def is_running(self, ret, proc):
        self.assertIsInstance(ret, bool)

    def cpu_affinity(self, ret, proc):
        self.assertIsInstance(ret, list)
        assert ret != [], ret
        cpus = range(psutil.cpu_count())
        for n in ret:
            self.assertIsInstance(n, int)
            self.assertIn(n, cpus)

    def terminal(self, ret, proc):
        self.assertIsInstance(ret, (str, type(None)))
        if ret is not None:
            assert os.path.isabs(ret), ret
            assert os.path.exists(ret), ret

    def memory_maps(self, ret, proc):
        for nt in ret:
            self.assertIsInstance(nt.addr, str)
            self.assertIsInstance(nt.perms, str)
            self.assertIsInstance(nt.path, str)
            for fname in nt._fields:
                value = getattr(nt, fname)
                if fname == 'path':
                    if not value.startswith('['):
                        assert os.path.isabs(nt.path), nt.path
                        # commented as on Linux we might get
                        # '/foo/bar (deleted)'
                        # assert os.path.exists(nt.path), nt.path
                elif fname == 'addr':
                    assert value, repr(value)
                elif fname == 'perms':
                    if not WINDOWS:
                        assert value, repr(value)
                else:
                    self.assertIsInstance(value, (int, long))
                    self.assertGreaterEqual(value, 0)

    def num_handles(self, ret, proc):
        self.assertIsInstance(ret, int)
        self.assertGreaterEqual(ret, 0)

    def nice(self, ret, proc):
        self.assertIsInstance(ret, int)
        if POSIX:
            assert -20 <= ret <= 20, ret
        else:
            priorities = [getattr(psutil, x) for x in dir(psutil)
                          if x.endswith('_PRIORITY_CLASS')]
            self.assertIn(ret, priorities)

    def num_ctx_switches(self, ret, proc):
        assert is_namedtuple(ret)
        for value in ret:
            self.assertIsInstance(value, (int, long))
            self.assertGreaterEqual(value, 0)

    def rlimit(self, ret, proc):
        self.assertIsInstance(ret, tuple)
        self.assertEqual(len(ret), 2)
        self.assertGreaterEqual(ret[0], -1)
        self.assertGreaterEqual(ret[1], -1)

    def environ(self, ret, proc):
        self.assertIsInstance(ret, dict)
        for k, v in ret.items():
            self.assertIsInstance(k, str)
            self.assertIsInstance(v, str)


if __name__ == '__main__':
    from psutil.tests.runner import run
    run(__file__)
