#!/usr/bin/env python

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux specific tests.  These are implicitly run by test_psutil.py."""

from __future__ import division
import contextlib
import errno
import fcntl
import io
import os
import pprint
import re
import socket
import struct
import sys
import tempfile
import time
import warnings

try:
    from unittest import mock  # py3
except ImportError:
    import mock  # requires "pip install mock"

from test_psutil import POSIX, TOLERANCE, TRAVIS, LINUX
from test_psutil import (skip_on_not_implemented, sh, get_test_subprocess,
                         retry_before_failing, get_kernel_version, unittest,
                         which, call_until)

import psutil
import psutil._pslinux
from psutil._compat import PY3, u


SIOCGIFADDR = 0x8915
SIOCGIFCONF = 0x8912
SIOCGIFHWADDR = 0x8927


def get_ipv4_address(ifname):
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


@unittest.skipUnless(LINUX, "not a Linux system")
class LinuxSpecificTestCase(unittest.TestCase):

    @unittest.skipIf(
        POSIX and not hasattr(os, 'statvfs'),
        reason="os.statvfs() function not available on this platform")
    @skip_on_not_implemented()
    def test_disks(self):
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
            self.assertEqual(part.device, dev)
            self.assertEqual(usage.total, total)
            # 10 MB tollerance
            if abs(usage.free - free) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % (usage.free, free))
            if abs(usage.used - used) > 10 * 1024 * 1024:
                self.fail("psutil=%s, df=%s" % (usage.used, used))

    def test_memory_maps(self):
        sproc = get_test_subprocess()
        time.sleep(1)
        p = psutil.Process(sproc.pid)
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

    def test_vmem_total(self):
        lines = sh('free').split('\n')[1:]
        total = int(lines[0].split()[1]) * 1024
        self.assertEqual(total, psutil.virtual_memory().total)

    @retry_before_failing()
    def test_vmem_used(self):
        lines = sh('free').split('\n')[1:]
        used = int(lines[0].split()[2]) * 1024
        self.assertAlmostEqual(used, psutil.virtual_memory().used,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_free(self):
        lines = sh('free').split('\n')[1:]
        free = int(lines[0].split()[3]) * 1024
        self.assertAlmostEqual(free, psutil.virtual_memory().free,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_buffers(self):
        lines = sh('free').split('\n')[1:]
        buffers = int(lines[0].split()[5]) * 1024
        self.assertAlmostEqual(buffers, psutil.virtual_memory().buffers,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_vmem_cached(self):
        lines = sh('free').split('\n')[1:]
        cached = int(lines[0].split()[6]) * 1024
        self.assertAlmostEqual(cached, psutil.virtual_memory().cached,
                               delta=TOLERANCE)

    def test_swapmem_total(self):
        lines = sh('free').split('\n')[1:]
        total = int(lines[2].split()[1]) * 1024
        self.assertEqual(total, psutil.swap_memory().total)

    @retry_before_failing()
    def test_swapmem_used(self):
        lines = sh('free').split('\n')[1:]
        used = int(lines[2].split()[2]) * 1024
        self.assertAlmostEqual(used, psutil.swap_memory().used,
                               delta=TOLERANCE)

    @retry_before_failing()
    def test_swapmem_free(self):
        lines = sh('free').split('\n')[1:]
        free = int(lines[2].split()[3]) * 1024
        self.assertAlmostEqual(free, psutil.swap_memory().free,
                               delta=TOLERANCE)

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

    def test_net_if_addrs_ips(self):
        for name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    self.assertEqual(addr.address, get_mac_address(name))
                elif addr.family == socket.AF_INET:
                    self.assertEqual(addr.address, get_ipv4_address(name))
                # TODO: test for AF_INET6 family

    @unittest.skipUnless(which('ip'), "'ip' utility not available")
    @unittest.skipIf(TRAVIS, "skipped on Travis")
    def test_net_if_names(self):
        out = sh("ip addr").strip()
        nics = psutil.net_if_addrs()
        found = 0
        for line in out.split('\n'):
            line = line.strip()
            if re.search("^\d+:", line):
                found += 1
                name = line.split(':')[1].strip()
                self.assertIn(name, nics.keys())
        self.assertEqual(len(nics), found, msg="%s\n---\n%s" % (
            pprint.pformat(nics), out))

    @unittest.skipUnless(which("nproc"), "nproc utility not available")
    def test_cpu_count_logical_w_nproc(self):
        num = int(sh("nproc --all"))
        self.assertEqual(psutil.cpu_count(logical=True), num)

    @unittest.skipUnless(which("lscpu"), "lscpu utility not available")
    def test_cpu_count_logical_w_lscpu(self):
        out = sh("lscpu -p")
        num = len([x for x in out.split('\n') if not x.startswith('#')])
        self.assertEqual(psutil.cpu_count(logical=True), num)

    # --- mocked tests

    def test_virtual_memory_mocked_warnings(self):
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

    def test_swap_memory_mocked_warnings(self):
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

    def test_cpu_count_physical_mocked(self):
        # Have open() return emtpy data and make sure None is returned
        # ('cause we want to mimick os.cpu_count())
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertIsNone(psutil._pslinux.cpu_count_physical())
            assert m.called

    def test_proc_open_files_file_gone(self):
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

    def test_proc_terminal_mocked(self):
        with mock.patch('psutil._pslinux._psposix._get_terminal_map',
                        return_value={}) as m:
            self.assertIsNone(psutil._pslinux.Process(os.getpid()).terminal())
            assert m.called

    def test_proc_num_ctx_switches_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).num_ctx_switches)
            assert m.called

    def test_proc_num_threads_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).num_threads)
            assert m.called

    def test_proc_ppid_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).ppid)
            assert m.called

    def test_proc_uids_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).uids)
            assert m.called

    def test_proc_gids_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).gids)
            assert m.called

    def test_proc_cmdline_mocked(self):
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

    def test_proc_io_counters_mocked(self):
        with mock.patch('psutil._pslinux.open', create=True) as m:
            self.assertRaises(
                NotImplementedError,
                psutil._pslinux.Process(os.getpid()).io_counters)
            assert m.called

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

    # --- tests for specific kernel versions

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


def main():
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(LinuxSpecificTestCase))
    result = unittest.TextTestRunner(verbosity=2).run(test_suite)
    return result.wasSuccessful()

if __name__ == '__main__':
    if not main():
        sys.exit(1)
