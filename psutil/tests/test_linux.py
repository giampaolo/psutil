#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux specific tests."""

import contextlib
import errno
import io
import os
import pprint
import re
import shutil
import socket
import struct
import tempfile
import textwrap
import time
import warnings

try:
    from unittest import mock  # py3
except ImportError:
    import mock  # requires "pip install mock"

import psutil
from psutil import LINUX
from psutil._compat import PY3
from psutil._compat import u
from psutil.tests import call_until
from psutil.tests import get_kernel_version
from psutil.tests import importlib
from psutil.tests import MEMORY_TOLERANCE
from psutil.tests import PYPY
from psutil.tests import pyrun
from psutil.tests import reap_children
from psutil.tests import retry_before_failing
from psutil.tests import run_test_module_by_name
from psutil.tests import safe_remove
from psutil.tests import sh
from psutil.tests import skip_on_not_implemented
from psutil.tests import TESTFN
from psutil.tests import TRAVIS
from psutil.tests import unittest
from psutil.tests import which


HERE = os.path.abspath(os.path.dirname(__file__))
SIOCGIFADDR = 0x8915
SIOCGIFCONF = 0x8912
SIOCGIFHWADDR = 0x8927
if LINUX:
    SECTOR_SIZE = psutil._psplatform.SECTOR_SIZE


# =====================================================================
# utils
# =====================================================================

def get_ipv4_address(ifname):
    import fcntl
    ifname = ifname[:15]
    if PY3:
        ifname = bytes(ifname, 'ascii')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with contextlib.closing(s):
        return socket.inet_ntoa(
            fcntl.ioctl(s.fileno(),
                        SIOCGIFADDR,
                        struct.pack('256s', ifname))[20:24])


def get_mac_address(ifname):
    import fcntl
    ifname = ifname[:15]
    if PY3:
        ifname = bytes(ifname, 'ascii')
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    with contextlib.closing(s):
        info = fcntl.ioctl(
            s.fileno(), SIOCGIFHWADDR, struct.pack('256s', ifname))
        if PY3:
            def ord(x):
                return x
        else:
            import __builtin__
            ord = __builtin__.ord
        return ''.join(['%02x:' % ord(char) for char in info[18:24]])[:-1]


def free_swap():
    """Parse 'free' cmd and return swap memory's s total, used and free
    values.
    """
    lines = sh('free').split('\n')
    for line in lines:
        if line.startswith('Swap'):
            _, total, used, free = line.split()
            return (int(total) * 1024, int(used) * 1024, int(free) * 1024)
    raise ValueError(
        "can't find 'Swap' in 'free' output:\n%s" % '\n'.join(lines))


def free_physmem():
    """Parse 'free' cmd and return physical memory's total, used
    and free values.
    """
    # Note: free can have 2 different formats, invalidating 'shared'
    # and 'cached' memory which may have different positions so we
    # do not return them.
    # https://github.com/giampaolo/psutil/issues/538#issuecomment-57059946
    lines = sh('free').split('\n')
    for line in lines:
        if line.startswith('Mem'):
            total, used, free, shared = \
                [int(x) * 1024 for x in line.split()[1:5]]
            return (total, used, free, shared)
    raise ValueError(
        "can't find 'Mem' in 'free' output:\n%s" % '\n'.join(lines))


# =====================================================================
# system virtual memory
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestSystemVirtualMemory(unittest.TestCase):

    def test_total(self):
        total, used, free, shared = free_physmem()
        self.assertEqual(total, psutil.virtual_memory().total)

    @retry_before_failing()
    def test_used(self):
        total, used, free, shared = free_physmem()
        self.assertAlmostEqual(used, psutil.virtual_memory().used,
                               delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_free(self):
        total, used, free, shared = free_physmem()
        self.assertAlmostEqual(free, psutil.virtual_memory().free,
                               delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_buffers(self):
        buffers = int(sh('vmstat').split('\n')[2].split()[4]) * 1024
        self.assertAlmostEqual(buffers, psutil.virtual_memory().buffers,
                               delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_cached(self):
        cached = int(sh('vmstat').split('\n')[2].split()[5]) * 1024
        self.assertAlmostEqual(cached, psutil.virtual_memory().cached,
                               delta=MEMORY_TOLERANCE)

    # --- mocked tests

    def test_warnings_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ret = psutil._pslinux.virtual_memory()
                assert m.called
                self.assertEqual(len(ws), 1)
                w = ws[0]
                self.assertTrue(w.filename.endswith('psutil/_pslinux.py'))
                self.assertIn(
                    "'cached', 'active' and 'inactive' memory stats couldn't "
                    "be determined", str(w.message))
                self.assertEqual(ret.cached, 0)
                self.assertEqual(ret.active, 0)
                self.assertEqual(ret.inactive, 0)


# =====================================================================
# system swap memory
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestSystemSwapMemory(unittest.TestCase):

    def test_total(self):
        total, used, free = free_swap()
        return self.assertAlmostEqual(total, psutil.swap_memory().total,
                                      delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_used(self):
        total, used, free = free_swap()
        return self.assertAlmostEqual(used, psutil.swap_memory().used,
                                      delta=MEMORY_TOLERANCE)

    @retry_before_failing()
    def test_free(self):
        total, used, free = free_swap()
        return self.assertAlmostEqual(free, psutil.swap_memory().free,
                                      delta=MEMORY_TOLERANCE)

    def test_warnings_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ret = psutil._pslinux.swap_memory()
                assert m.called
                self.assertEqual(len(ws), 1)
                w = ws[0]
                self.assertTrue(w.filename.endswith('psutil/_pslinux.py'))
                self.assertIn(
                    "'sin' and 'sout' swap memory stats couldn't "
                    "be determined", str(w.message))
                self.assertEqual(ret.sin, 0)
                self.assertEqual(ret.sout, 0)

    def test_no_vmstat_mocked(self):
        # see https://github.com/giampaolo/psutil/issues/722
        with mock.patch('psutil._pslinux.open', create=True,
                        side_effect=IOError) as m:
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ret = psutil.swap_memory()
                assert m.called
                self.assertEqual(len(ws), 1)
                w = ws[0]
                self.assertTrue(w.filename.endswith('psutil/_pslinux.py'))
                self.assertIn(
                    "'sin' and 'sout' swap memory stats couldn't "
                    "be determined and were set to 0",
                    str(w.message))
                self.assertEqual(ret.sin, 0)
                self.assertEqual(ret.sout, 0)


# =====================================================================
# system CPU
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestSystemCPU(unittest.TestCase):

    @unittest.skipIf(TRAVIS, "unknown failure on travis")
    def test_cpu_times(self):
        fields = psutil.cpu_times()._fields
        kernel_ver = re.findall('\d+\.\d+\.\d+', os.uname()[2])[0]
        kernel_ver_info = tuple(map(int, kernel_ver.split('.')))
        if kernel_ver_info >= (2, 6, 11):
            self.assertIn('steal', fields)
        else:
            self.assertNotIn('steal', fields)
        if kernel_ver_info >= (2, 6, 24):
            self.assertIn('guest', fields)
        else:
            self.assertNotIn('guest', fields)
        if kernel_ver_info >= (3, 2, 0):
            self.assertIn('guest_nice', fields)
        else:
            self.assertNotIn('guest_nice', fields)

    @unittest.skipUnless(which("nproc"), "nproc utility not available")
    def test_cpu_count_logical_w_nproc(self):
        num = int(sh("nproc --all"))
        self.assertEqual(psutil.cpu_count(logical=True), num)

    @unittest.skipUnless(which("lscpu"), "lscpu utility not available")
    def test_cpu_count_logical_w_lscpu(self):
        out = sh("lscpu -p")
        num = len([x for x in out.split('\n') if not x.startswith('#')])
        self.assertEqual(psutil.cpu_count(logical=True), num)

    def test_cpu_count_logical_mocked(self):
        import psutil._pslinux
        original = psutil._pslinux.cpu_count_logical()
        # Here we want to mock os.sysconf("SC_NPROCESSORS_ONLN") in
        # order to cause the parsing of /proc/cpuinfo and /proc/stat.
        with mock.patch(
                'psutil._pslinux.os.sysconf', side_effect=ValueError) as m:
            self.assertEqual(psutil._pslinux.cpu_count_logical(), original)
            assert m.called

            # Let's have open() return emtpy data and make sure None is
            # returned ('cause we mimick os.cpu_count()).
            with mock.patch('psutil._pslinux.open', create=True) as m:
                self.assertIsNone(psutil._pslinux.cpu_count_logical())
                self.assertEqual(m.call_count, 2)
                # /proc/stat should be the last one
                self.assertEqual(m.call_args[0][0], '/proc/stat')

            # Let's push this a bit further and make sure /proc/cpuinfo
            # parsing works as expected.
            with open('/proc/cpuinfo', 'rb') as f:
                cpuinfo_data = f.read()
            fake_file = io.BytesIO(cpuinfo_data)
            with mock.patch('psutil._pslinux.open',
                            return_value=fake_file, create=True) as m:
                self.assertEqual(psutil._pslinux.cpu_count_logical(), original)

            # Finally, let's make /proc/cpuinfo return meaningless data;
            # this way we'll fall back on relying on /proc/stat
            def open_mock(name, *args, **kwargs):
                if name.startswith('/proc/cpuinfo'):
                    return io.BytesIO(b"")
                else:
                    return orig_open(name, *args, **kwargs)

            orig_open = open
            patch_point = 'builtins.open' if PY3 else '__builtin__.open'
            with mock.patch(patch_point, side_effect=open_mock, create=True):
                self.assertEqual(psutil._pslinux.cpu_count_logical(), original)

    def test_cpu_count_physical_mocked(self):
        # Have open() return emtpy data and make sure None is returned
        # ('cause we want to mimick os.cpu_count())
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertIsNone(psutil._pslinux.cpu_count_physical())
            assert m.called


# =====================================================================
# system network
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestSystemNetwork(unittest.TestCase):

    def test_net_if_addrs_ips(self):
        for name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    self.assertEqual(addr.address, get_mac_address(name))
                elif addr.family == socket.AF_INET:
                    self.assertEqual(addr.address, get_ipv4_address(name))
                # TODO: test for AF_INET6 family

    def test_net_if_stats(self):
        for name, stats in psutil.net_if_stats().items():
            try:
                out = sh("ifconfig %s" % name)
            except RuntimeError:
                pass
            else:
                self.assertEqual(stats.isup, 'RUNNING' in out)
                self.assertEqual(stats.mtu,
                                 int(re.findall('MTU:(\d+)', out)[0]))

    def test_net_io_counters(self):
        def ifconfig(nic):
            ret = {}
            out = sh("ifconfig %s" % name)
            ret['packets_recv'] = int(re.findall('RX packets:(\d+)', out)[0])
            ret['packets_sent'] = int(re.findall('TX packets:(\d+)', out)[0])
            ret['errin'] = int(re.findall('errors:(\d+)', out)[0])
            ret['errout'] = int(re.findall('errors:(\d+)', out)[1])
            ret['dropin'] = int(re.findall('dropped:(\d+)', out)[0])
            ret['dropout'] = int(re.findall('dropped:(\d+)', out)[1])
            ret['bytes_recv'] = int(re.findall('RX bytes:(\d+)', out)[0])
            ret['bytes_sent'] = int(re.findall('TX bytes:(\d+)', out)[0])
            return ret

        for name, stats in psutil.net_io_counters(pernic=True).items():
            try:
                ifconfig_ret = ifconfig(name)
            except RuntimeError:
                continue
            self.assertAlmostEqual(
                stats.bytes_recv, ifconfig_ret['bytes_recv'], delta=1024)
            self.assertAlmostEqual(
                stats.bytes_sent, ifconfig_ret['bytes_sent'], delta=1024)
            self.assertAlmostEqual(
                stats.packets_recv, ifconfig_ret['packets_recv'], delta=512)
            self.assertAlmostEqual(
                stats.packets_sent, ifconfig_ret['packets_sent'], delta=512)
            self.assertAlmostEqual(
                stats.errin, ifconfig_ret['errin'], delta=10)
            self.assertAlmostEqual(
                stats.errout, ifconfig_ret['errout'], delta=10)
            self.assertAlmostEqual(
                stats.dropin, ifconfig_ret['dropin'], delta=10)
            self.assertAlmostEqual(
                stats.dropout, ifconfig_ret['dropout'], delta=10)

    @unittest.skipUnless(which('ip'), "'ip' utility not available")
    @unittest.skipIf(TRAVIS, "skipped on Travis")
    def test_net_if_names(self):
        out = sh("ip addr").strip()
        nics = [x for x in psutil.net_if_addrs().keys() if ':' not in x]
        found = 0
        for line in out.split('\n'):
            line = line.strip()
            if re.search("^\d+:", line):
                found += 1
                name = line.split(':')[1].strip()
                self.assertIn(name, nics)
        self.assertEqual(len(nics), found, msg="%s\n---\n%s" % (
            pprint.pformat(nics), out))

    @mock.patch('psutil._pslinux.socket.inet_ntop', side_effect=ValueError)
    @mock.patch('psutil._pslinux.supports_ipv6', return_value=False)
    def test_net_connections_ipv6_unsupported(self, supports_ipv6, inet_ntop):
        # see: https://github.com/giampaolo/psutil/issues/623
        try:
            s = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            self.addCleanup(s.close)
            s.bind(("::1", 0))
        except socket.error:
            pass
        psutil.net_connections(kind='inet6')

    def test_net_connections_mocked(self):
        def open_mock(name, *args, **kwargs):
            if name == '/proc/net/unix':
                return io.StringIO(textwrap.dedent(u"""\
                    0: 00000003 000 000 0001 03 462170 @/tmp/dbus-Qw2hMPIU3n
                    0: 00000003 000 000 0001 03 35010 @/tmp/dbus-tB2X8h69BQ
                    0: 00000003 000 000 0001 03 34424 @/tmp/dbus-cHy80Y8O
                    000000000000000000000000000000000000000000000000000000
                    """))
            else:
                return orig_open(name, *args, **kwargs)
            return orig_open(name, *args)

        orig_open = open
        patch_point = 'builtins.open' if PY3 else '__builtin__.open'
        with mock.patch(patch_point, side_effect=open_mock) as m:
            psutil.net_connections(kind='unix')
            assert m.called


# =====================================================================
# system disk
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestSystemDisks(unittest.TestCase):

    @unittest.skipUnless(
        hasattr(os, 'statvfs'), "os.statvfs() function not available")
    @skip_on_not_implemented()
    def test_disk_partitions_and_usage(self):
        # test psutil.disk_usage() and psutil.disk_partitions()
        # against "df -a"
        def df(path):
            out = sh('df -P -B 1 "%s"' % path).strip()
            lines = out.split('\n')
            lines.pop(0)
            line = lines.pop(0)
            dev, total, used, free = line.split()[:4]
            if dev == 'none':
                dev = ''
            total, used, free = int(total), int(used), int(free)
            return dev, total, used, free

        for part in psutil.disk_partitions(all=False):
            usage = psutil.disk_usage(part.mountpoint)
            dev, total, used, free = df(part.mountpoint)
            self.assertEqual(usage.total, total)
            # 10 MB tollerance
            if abs(usage.free - free) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % (usage.free, free))
            if abs(usage.used - used) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % (usage.used, used))

    def test_disk_partitions_mocked(self):
        # Test that ZFS partitions are returned.
        with open("/proc/filesystems", "r") as f:
            data = f.read()
        if 'zfs' in data:
            for part in psutil.disk_partitions():
                if part.fstype == 'zfs':
                    break
            else:
                self.fail("couldn't find any ZFS partition")
        else:
            # No ZFS partitions on this system. Let's fake one.
            fake_file = io.StringIO(u("nodev\tzfs\n"))
            with mock.patch('psutil._pslinux.open',
                            return_value=fake_file, create=True) as m1:
                with mock.patch(
                        'psutil._pslinux.cext.disk_partitions',
                        return_value=[('/dev/sdb3', '/', 'zfs', 'rw')]) as m2:
                    ret = psutil.disk_partitions()
                    assert m1.called
                    assert m2.called
                    assert ret
                    self.assertEqual(ret[0].fstype, 'zfs')

    def test_disk_io_counters_kernel_2_4_mocked(self):
        # Tests /proc/diskstats parsing format for 2.4 kernels, see:
        # https://github.com/giampaolo/psutil/issues/767
        def open_mock(name, *args, **kwargs):
            if name == '/proc/partitions':
                return io.StringIO(textwrap.dedent(u"""\
                    major minor  #blocks  name

                       8        0  488386584 hda
                    """))
            elif name == '/proc/diskstats':
                return io.StringIO(
                    u("   3     0   1 hda 2 3 4 5 6 7 8 9 10 11 12"))
            else:
                return orig_open(name, *args, **kwargs)
            return orig_open(name, *args)

        orig_open = open
        patch_point = 'builtins.open' if PY3 else '__builtin__.open'
        with mock.patch(patch_point, side_effect=open_mock) as m:
            ret = psutil.disk_io_counters()
            assert m.called
            self.assertEqual(ret.read_count, 1)
            self.assertEqual(ret.read_merged_count, 2)
            self.assertEqual(ret.read_bytes, 3 * SECTOR_SIZE)
            self.assertEqual(ret.read_time, 4)
            self.assertEqual(ret.write_count, 5)
            self.assertEqual(ret.write_merged_count, 6)
            self.assertEqual(ret.write_bytes, 7 * SECTOR_SIZE)
            self.assertEqual(ret.write_time, 8)
            self.assertEqual(ret.busy_time, 10)

    def test_disk_io_counters_kernel_2_6_full_mocked(self):
        # Tests /proc/diskstats parsing format for 2.6 kernels,
        # lines reporting all metrics:
        # https://github.com/giampaolo/psutil/issues/767
        def open_mock(name, *args, **kwargs):
            if name == '/proc/partitions':
                return io.StringIO(textwrap.dedent(u"""\
                    major minor  #blocks  name

                       8        0  488386584 hda
                    """))
            elif name == '/proc/diskstats':
                return io.StringIO(
                    u("   3    0   hda 1 2 3 4 5 6 7 8 9 10 11"))
            else:
                return orig_open(name, *args, **kwargs)
            return orig_open(name, *args)

        orig_open = open
        patch_point = 'builtins.open' if PY3 else '__builtin__.open'
        with mock.patch(patch_point, side_effect=open_mock) as m:
            ret = psutil.disk_io_counters()
            assert m.called
            self.assertEqual(ret.read_count, 1)
            self.assertEqual(ret.read_merged_count, 2)
            self.assertEqual(ret.read_bytes, 3 * SECTOR_SIZE)
            self.assertEqual(ret.read_time, 4)
            self.assertEqual(ret.write_count, 5)
            self.assertEqual(ret.write_merged_count, 6)
            self.assertEqual(ret.write_bytes, 7 * SECTOR_SIZE)
            self.assertEqual(ret.write_time, 8)
            self.assertEqual(ret.busy_time, 10)

    def test_disk_io_counters_kernel_2_6_limited_mocked(self):
        # Tests /proc/diskstats parsing format for 2.6 kernels,
        # where one line of /proc/partitions return a limited
        # amount of metrics when it bumps into a partition
        # (instead of a disk). See:
        # https://github.com/giampaolo/psutil/issues/767
        def open_mock(name, *args, **kwargs):
            if name == '/proc/partitions':
                return io.StringIO(textwrap.dedent(u"""\
                    major minor  #blocks  name

                       8        0  488386584 hda
                    """))
            elif name == '/proc/diskstats':
                return io.StringIO(
                    u("   3    1   hda 1 2 3 4"))
            else:
                return orig_open(name, *args, **kwargs)
            return orig_open(name, *args)

        orig_open = open
        patch_point = 'builtins.open' if PY3 else '__builtin__.open'
        with mock.patch(patch_point, side_effect=open_mock) as m:
            ret = psutil.disk_io_counters()
            assert m.called
            self.assertEqual(ret.read_count, 1)
            self.assertEqual(ret.read_bytes, 2 * SECTOR_SIZE)
            self.assertEqual(ret.write_count, 3)
            self.assertEqual(ret.write_bytes, 4 * SECTOR_SIZE)

            self.assertEqual(ret.read_merged_count, 0)
            self.assertEqual(ret.read_time, 0)
            self.assertEqual(ret.write_merged_count, 0)
            self.assertEqual(ret.write_time, 0)
            self.assertEqual(ret.busy_time, 0)


# =====================================================================
# misc
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestMisc(unittest.TestCase):

    @mock.patch('psutil.traceback.print_exc')
    def test_no_procfs_on_import(self, tb):
        my_procfs = tempfile.mkdtemp()

        with open(os.path.join(my_procfs, 'stat'), 'w') as f:
            f.write('cpu   0 0 0 0 0 0 0 0 0 0\n')
            f.write('cpu0  0 0 0 0 0 0 0 0 0 0\n')
            f.write('cpu1  0 0 0 0 0 0 0 0 0 0\n')

        try:
            orig_open = open

            def open_mock(name, *args, **kwargs):
                if name.startswith('/proc'):
                    raise IOError(errno.ENOENT, 'rejecting access for test')
                return orig_open(name, *args, **kwargs)

            patch_point = 'builtins.open' if PY3 else '__builtin__.open'
            with mock.patch(patch_point, side_effect=open_mock):
                importlib.reload(psutil)
                assert tb.called

                self.assertRaises(IOError, psutil.cpu_times)
                self.assertRaises(IOError, psutil.cpu_times, percpu=True)
                self.assertRaises(IOError, psutil.cpu_percent)
                self.assertRaises(IOError, psutil.cpu_percent, percpu=True)
                self.assertRaises(IOError, psutil.cpu_times_percent)
                self.assertRaises(
                    IOError, psutil.cpu_times_percent, percpu=True)

                psutil.PROCFS_PATH = my_procfs

                self.assertEqual(psutil.cpu_percent(), 0)
                self.assertEqual(sum(psutil.cpu_times_percent()), 0)

                # since we don't know the number of CPUs at import time,
                # we awkwardly say there are none until the second call
                per_cpu_percent = psutil.cpu_percent(percpu=True)
                self.assertEqual(sum(per_cpu_percent), 0)

                # ditto awkward length
                per_cpu_times_percent = psutil.cpu_times_percent(percpu=True)
                self.assertEqual(sum(map(sum, per_cpu_times_percent)), 0)

                # much user, very busy
                with open(os.path.join(my_procfs, 'stat'), 'w') as f:
                    f.write('cpu   1 0 0 0 0 0 0 0 0 0\n')
                    f.write('cpu0  1 0 0 0 0 0 0 0 0 0\n')
                    f.write('cpu1  1 0 0 0 0 0 0 0 0 0\n')

                self.assertNotEqual(psutil.cpu_percent(), 0)
                self.assertNotEqual(
                    sum(psutil.cpu_percent(percpu=True)), 0)
                self.assertNotEqual(sum(psutil.cpu_times_percent()), 0)
                self.assertNotEqual(
                    sum(map(sum, psutil.cpu_times_percent(percpu=True))), 0)
        finally:
            shutil.rmtree(my_procfs)
            importlib.reload(psutil)

        self.assertEqual(psutil.PROCFS_PATH, '/proc')

    @unittest.skipUnless(
        get_kernel_version() >= (2, 6, 36),
        "prlimit() not available on this Linux kernel version")
    def test_prlimit_availability(self):
        # prlimit() should be available starting from kernel 2.6.36
        p = psutil.Process(os.getpid())
        p.rlimit(psutil.RLIMIT_NOFILE)
        # if prlimit() is supported *at least* these constants should
        # be available
        self.assertTrue(hasattr(psutil, "RLIM_INFINITY"))
        self.assertTrue(hasattr(psutil, "RLIMIT_AS"))
        self.assertTrue(hasattr(psutil, "RLIMIT_CORE"))
        self.assertTrue(hasattr(psutil, "RLIMIT_CPU"))
        self.assertTrue(hasattr(psutil, "RLIMIT_DATA"))
        self.assertTrue(hasattr(psutil, "RLIMIT_FSIZE"))
        self.assertTrue(hasattr(psutil, "RLIMIT_LOCKS"))
        self.assertTrue(hasattr(psutil, "RLIMIT_MEMLOCK"))
        self.assertTrue(hasattr(psutil, "RLIMIT_NOFILE"))
        self.assertTrue(hasattr(psutil, "RLIMIT_NPROC"))
        self.assertTrue(hasattr(psutil, "RLIMIT_RSS"))
        self.assertTrue(hasattr(psutil, "RLIMIT_STACK"))

    @unittest.skipUnless(
        get_kernel_version() >= (3, 0),
        "prlimit constants not available on this Linux kernel version")
    def test_resource_consts_kernel_v(self):
        # more recent constants
        self.assertTrue(hasattr(psutil, "RLIMIT_MSGQUEUE"))
        self.assertTrue(hasattr(psutil, "RLIMIT_NICE"))
        self.assertTrue(hasattr(psutil, "RLIMIT_RTPRIO"))
        self.assertTrue(hasattr(psutil, "RLIMIT_RTTIME"))
        self.assertTrue(hasattr(psutil, "RLIMIT_SIGPENDING"))

    def test_boot_time_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                RuntimeError,
                psutil._pslinux.boot_time)
            assert m.called

    def test_users_mocked(self):
        # Make sure ':0' and ':0.0' (returned by C ext) are converted
        # to 'localhost'.
        with mock.patch('psutil._pslinux.cext.users',
                        return_value=[('giampaolo', 'pts/2', ':0',
                                      1436573184.0, True)]) as m:
            self.assertEqual(psutil.users()[0].host, 'localhost')
            assert m.called
        with mock.patch('psutil._pslinux.cext.users',
                        return_value=[('giampaolo', 'pts/2', ':0.0',
                                      1436573184.0, True)]) as m:
            self.assertEqual(psutil.users()[0].host, 'localhost')
            assert m.called
        # ...otherwise it should be returned as-is
        with mock.patch('psutil._pslinux.cext.users',
                        return_value=[('giampaolo', 'pts/2', 'foo',
                                      1436573184.0, True)]) as m:
            self.assertEqual(psutil.users()[0].host, 'foo')
            assert m.called

    def test_procfs_path(self):
        tdir = tempfile.mkdtemp()
        try:
            psutil.PROCFS_PATH = tdir
            self.assertRaises(IOError, psutil.virtual_memory)
            self.assertRaises(IOError, psutil.cpu_times)
            self.assertRaises(IOError, psutil.cpu_times, percpu=True)
            self.assertRaises(IOError, psutil.boot_time)
            # self.assertRaises(IOError, psutil.pids)
            self.assertRaises(IOError, psutil.net_connections)
            self.assertRaises(IOError, psutil.net_io_counters)
            self.assertRaises(IOError, psutil.net_if_stats)
            self.assertRaises(IOError, psutil.disk_io_counters)
            self.assertRaises(IOError, psutil.disk_partitions)
            self.assertRaises(psutil.NoSuchProcess, psutil.Process)
        finally:
            psutil.PROCFS_PATH = "/proc"
            os.rmdir(tdir)

    def test_sector_size_mock(self):
        # Test SECTOR_SIZE fallback in case 'hw_sector_size' file
        # does not exist.
        def open_mock(name, *args, **kwargs):
            if PY3 and isinstance(name, bytes):
                name = name.decode()
            if name.startswith("/sys/block/sda/queue/hw_sector_size"):
                flag.append(None)
                raise IOError(errno.ENOENT, '')
            else:
                return orig_open(name, *args, **kwargs)

        flag = []
        orig_open = open
        patch_point = 'builtins.open' if PY3 else '__builtin__.open'
        try:
            with mock.patch(patch_point, side_effect=open_mock):
                importlib.reload(psutil._pslinux)
                importlib.reload(psutil)
                self.assertEqual(flag, [None])
                self.assertEqual(psutil._pslinux.SECTOR_SIZE, 512)
        finally:
            importlib.reload(psutil._pslinux)
            importlib.reload(psutil)


# =====================================================================
# test process
# =====================================================================

@unittest.skipUnless(LINUX, "not a Linux system")
class TestProcess(unittest.TestCase):

    def setUp(self):
        safe_remove(TESTFN)

    tearDown = setUp

    def test_memory_maps(self):
        src = textwrap.dedent("""
            import time
            with open("%s", "w") as f:
                time.sleep(10)
            """ % TESTFN)
        sproc = pyrun(src)
        self.addCleanup(reap_children)
        call_until(lambda: os.listdir('.'), "'%s' not in ret" % TESTFN)
        p = psutil.Process(sproc.pid)
        time.sleep(.1)
        maps = p.memory_maps(grouped=False)
        pmap = sh('pmap -x %s' % p.pid).split('\n')
        # get rid of header
        del pmap[0]
        del pmap[0]
        while maps and pmap:
            this = maps.pop(0)
            other = pmap.pop(0)
            addr, _, rss, dirty, mode, path = other.split(None, 5)
            if not path.startswith('[') and not path.endswith(']'):
                self.assertEqual(path, os.path.basename(this.path))
            self.assertEqual(int(rss) * 1024, this.rss)
            # test only rwx chars, ignore 's' and 'p'
            self.assertEqual(mode[:3], this.perms[:3])

    def test_memory_full_info(self):
        src = textwrap.dedent("""
            import time
            with open("%s", "w") as f:
                time.sleep(10)
            """ % TESTFN)
        sproc = pyrun(src)
        self.addCleanup(reap_children)
        call_until(lambda: os.listdir('.'), "'%s' not in ret" % TESTFN)
        p = psutil.Process(sproc.pid)
        time.sleep(.1)
        mem = p.memory_full_info()
        maps = p.memory_maps(grouped=False)
        self.assertAlmostEqual(
            mem.uss, sum([x.private_dirty + x.private_clean for x in maps]),
            delta=4096)
        self.assertAlmostEqual(
            mem.pss, sum([x.pss for x in maps]), delta=4096)
        self.assertAlmostEqual(
            mem.swap, sum([x.swap for x in maps]), delta=4096)

    # On PYPY file descriptors are not closed fast enough.
    @unittest.skipIf(PYPY, "skipped on PYPY")
    def test_open_files_mode(self):
        def get_test_file():
            p = psutil.Process()
            giveup_at = time.time() + 2
            while True:
                for file in p.open_files():
                    if file.path == os.path.abspath(TESTFN):
                        return file
                    elif time.time() > giveup_at:
                        break
            raise RuntimeError("timeout looking for test file")

        #
        with open(TESTFN, "w"):
            self.assertEqual(get_test_file().mode, "w")
        with open(TESTFN, "r"):
            self.assertEqual(get_test_file().mode, "r")
        with open(TESTFN, "a"):
            self.assertEqual(get_test_file().mode, "a")
        #
        with open(TESTFN, "r+"):
            self.assertEqual(get_test_file().mode, "r+")
        with open(TESTFN, "w+"):
            self.assertEqual(get_test_file().mode, "r+")
        with open(TESTFN, "a+"):
            self.assertEqual(get_test_file().mode, "a+")
        # note: "x" bit is not supported
        if PY3:
            safe_remove(TESTFN)
            with open(TESTFN, "x"):
                self.assertEqual(get_test_file().mode, "w")
            safe_remove(TESTFN)
            with open(TESTFN, "x+"):
                self.assertEqual(get_test_file().mode, "r+")

    def test_open_files_file_gone(self):
        # simulates a file which gets deleted during open_files()
        # execution
        p = psutil.Process()
        files = p.open_files()
        with tempfile.NamedTemporaryFile():
            # give the kernel some time to see the new file
            call_until(p.open_files, "len(ret) != %i" % len(files))
            with mock.patch('psutil._pslinux.os.readlink',
                            side_effect=OSError(errno.ENOENT, "")) as m:
                files = p.open_files()
                assert not files
                assert m.called
            # also simulate the case where os.readlink() returns EINVAL
            # in which case psutil is supposed to 'continue'
            with mock.patch('psutil._pslinux.os.readlink',
                            side_effect=OSError(errno.EINVAL, "")) as m:
                self.assertEqual(p.open_files(), [])
                assert m.called

    # --- mocked tests

    def test_terminal_mocked(self):
        with mock.patch('psutil._pslinux._psposix._get_terminal_map',
                        return_value={}) as m:
            self.assertIsNone(psutil._pslinux.Process(os.getpid()).terminal())
            assert m.called

    def test_num_ctx_switches_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).num_ctx_switches)
            assert m.called

    def test_num_threads_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).num_threads)
            assert m.called

    def test_ppid_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).ppid)
            assert m.called

    def test_uids_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).uids)
            assert m.called

    def test_gids_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).gids)
            assert m.called

    def test_cmdline_mocked(self):
        # see: https://github.com/giampaolo/psutil/issues/639
        p = psutil.Process()
        fake_file = io.StringIO(u('foo\x00bar\x00'))
        with mock.patch('psutil._pslinux.open',
                        return_value=fake_file, create=True) as m:
            p.cmdline() == ['foo', 'bar']
            assert m.called
        fake_file = io.StringIO(u('foo\x00bar\x00\x00'))
        with mock.patch('psutil._pslinux.open',
                        return_value=fake_file, create=True) as m:
            p.cmdline() == ['foo', 'bar', '']
            assert m.called

    def test_io_counters_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).io_counters)
            assert m.called

    def test_readlink_path_deleted_mocked(self):
        with mock.patch('psutil._pslinux.os.readlink',
                        return_value='/home/foo (deleted)'):
            self.assertEqual(psutil.Process().exe(), "/home/foo")
            self.assertEqual(psutil.Process().cwd(), "/home/foo")

    def test_threads_mocked(self):
        # Test the case where os.listdir() returns a file (thread)
        # which no longer exists by the time we open() it (race
        # condition). threads() is supposed to ignore that instead
        # of raising NSP.
        def open_mock(name, *args, **kwargs):
            if name.startswith('/proc/%s/task' % os.getpid()):
                raise IOError(errno.ENOENT, "")
            else:
                return orig_open(name, *args, **kwargs)

        orig_open = open
        patch_point = 'builtins.open' if PY3 else '__builtin__.open'
        with mock.patch(patch_point, side_effect=open_mock) as m:
            ret = psutil.Process().threads()
            assert m.called
            self.assertEqual(ret, [])

        # ...but if it bumps into something != ENOENT we want an
        # exception.
        def open_mock(name, *args, **kwargs):
            if name.startswith('/proc/%s/task' % os.getpid()):
                raise IOError(errno.EPERM, "")
            else:
                return orig_open(name, *args, **kwargs)

        with mock.patch(patch_point, side_effect=open_mock):
            self.assertRaises(psutil.AccessDenied, psutil.Process().threads)

    # not sure why (doesn't fail locally)
    # https://travis-ci.org/giampaolo/psutil/jobs/108629915
    @unittest.skipIf(TRAVIS, "fails on travis")
    def test_exe_mocked(self):
        with mock.patch('psutil._pslinux.os.readlink',
                        side_effect=OSError(errno.ENOENT, "")) as m:
            # No such file error; might be raised also if /proc/pid/exe
            # path actually exists for system processes with low pids
            # (about 0-20). In this case psutil is supposed to return
            # an empty string.
            ret = psutil.Process().exe()
            assert m.called
            self.assertEqual(ret, "")

            # ...but if /proc/pid no longer exist we're supposed to treat
            # it as an alias for zombie process
            with mock.patch('psutil._pslinux.os.path.lexists',
                            return_value=False):
                self.assertRaises(psutil.ZombieProcess, psutil.Process().exe)


if __name__ == '__main__':
    run_test_module_by_name(__file__)
