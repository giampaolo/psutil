#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Linux specific tests."""

import collections
import contextlib
import ctypes
import errno
import fnmatch
import glob
import importlib
import io
import mmap
import os
import platform
import re
import shutil
import socket
import struct
import sys
import textwrap
import time
import warnings
from unittest import mock

import psutil
from psutil import LINUX
from psutil import _psutil

from . import AARCH64
from . import GLOBAL_TIMEOUT
from . import HAS_BATTERY
from . import HAS_CPU_FREQ
from . import PYTHON_EXE
from . import PYTHON_EXE_ENV
from . import PYTHON_SLEEP_CODE
from . import TOLERANCE_DISK_USAGE
from . import TOLERANCE_SYS_MEM
from . import PsutilTestCase
from . import ThreadTask
from . import call_until
from . import df
from . import is_busybox
from . import isolated
from . import pytest
from . import requires_cli
from . import retry_on_failure
from . import safe_rmpath
from . import serial
from . import sh
from . import skip_on_not_implemented
from . import skipif

if LINUX:
    from psutil._pslinux import CLOCK_TICKS
    from psutil._pslinux import RootFsDeviceFinder
    from psutil._pslinux import _cpu_get_cpuinfo_freq
    from psutil._pslinux import _parse_cpulist
    from psutil._pslinux import calculate_avail_vmem
    from psutil._pslinux import open_binary


SIOCGIFADDR = 0x8915
SIOCGIFHWADDR = 0x8927
SIOCGIFNETMASK = 0x891B
SIOCGIFBRDADDR = 0x8919
if LINUX:
    SECTOR_SIZE = 512
# Overlayfs and btrfs give / an anonymous device (major 0), which has
# no /proc/partitions or /sys/dev/block entry to look up.
ROOTFS_ON_BLOCK_DEV = LINUX and os.major(os.stat("/").st_dev) != 0
CPUINFO_HAS_MHZ = LINUX and bool(_cpu_get_cpuinfo_freq())


@skipif(not LINUX, reason="LINUX only")
class LinuxTestCase(PsutilTestCase):
    pass


# =====================================================================
# --- utils
# =====================================================================


def get_ipv4_address(ifname):
    import fcntl

    ifname = bytes(ifname[:15], "ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        return socket.inet_ntoa(
            fcntl.ioctl(s.fileno(), SIOCGIFADDR, struct.pack('256s', ifname))[
                20:24
            ]
        )


def get_ipv4_netmask(ifname):
    import fcntl

    ifname = bytes(ifname[:15], "ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(), SIOCGIFNETMASK, struct.pack('256s', ifname)
            )[20:24]
        )


def get_ipv4_broadcast(ifname):
    import fcntl

    ifname = bytes(ifname[:15], "ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        return socket.inet_ntoa(
            fcntl.ioctl(
                s.fileno(), SIOCGIFBRDADDR, struct.pack('256s', ifname)
            )[20:24]
        )


def get_ipv6_addresses(ifname):
    with open("/proc/net/if_inet6") as f:
        all_fields = []
        for line in f:
            fields = line.split()
            if fields[-1] == ifname:
                all_fields.append(fields)

        if len(all_fields) == 0:
            raise ValueError(f"could not find interface {ifname!r}")

    for i in range(len(all_fields)):
        unformatted = all_fields[i][0]
        groups = [
            unformatted[j : j + 4] for j in range(0, len(unformatted), 4)
        ]
        formatted = ":".join(groups)
        packed = socket.inet_pton(socket.AF_INET6, formatted)
        all_fields[i] = socket.inet_ntop(socket.AF_INET6, packed)
    return all_fields


def get_mac_address(ifname):
    import fcntl

    ifname = bytes(ifname[:15], "ascii")
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        info = fcntl.ioctl(
            s.fileno(), SIOCGIFHWADDR, struct.pack('256s', ifname)
        )
        return "".join([f"{char:02x}:" for char in info[18:24]])[:-1]


def free_swap():
    """Parse 'free' cmd and return swap memory's s total, used and free
    values.
    """
    out = sh(["free", "-b"], env={"LANG": "C.UTF-8"})
    lines = out.split('\n')
    for line in lines:
        if line.startswith('Swap'):
            _, total, used, free = line.split()
            nt = collections.namedtuple('free', 'total used free')
            return nt(int(total), int(used), int(free))
    raise ValueError(f"can't find 'Swap' in 'free' output:\n{out}")


def free_physmem():
    """Parse 'free' cmd and return physical memory's total, used
    and free values.
    """
    # Note: free can have 2 different formats, invalidating 'shared'
    # and 'cached' memory which may have different positions so we
    # do not return them.
    # https://github.com/giampaolo/psutil/issues/538#issuecomment-57059946
    out = sh(["free", "-b"], env={"LANG": "C.UTF-8"})
    lines = out.split('\n')
    for line in lines:
        if line.startswith('Mem'):
            total, used, free, shared = (int(x) for x in line.split()[1:5])
            nt = collections.namedtuple(
                'free', 'total used free shared output'
            )
            return nt(total, used, free, shared, out)
    raise ValueError(f"can't find 'Mem' in 'free' output:\n{out}")


@requires_cli("vmstat")
def vmstat(stat):
    out = sh(["vmstat", "-s"], env={"LANG": "C.UTF-8"})
    for line in out.split("\n"):
        line = line.strip()
        if stat in line:
            return int(line.split(' ')[0])
    raise ValueError(f"can't find {stat!r} in 'vmstat' output")


def get_free_version_info():
    if is_busybox("free"):
        return pytest.skip("busybox free has no -V option")
    out = sh(["free", "-V"]).strip()
    if 'UNKNOWN' in out:
        return pytest.skip("can't determine free version")
    return tuple(map(int, re.findall(r'\d+', out.split()[-1])))


@contextlib.contextmanager
def mock_open_content(pairs):
    """Mock open() builtin and forces it to return a certain content
    for a given path. `pairs` is a {"pattern": content, ...} dict.
    Patterns are fnmatch()ed in order, the first match wins. Content
    can be str, bytes or an exception to raise.
    """

    def open_mock(name, *args, **kwargs):
        for pattern, content in pairs.items():
            if fnmatch.fnmatchcase(name, pattern):
                if isinstance(content, str):
                    return io.StringIO(content)
                elif isinstance(content, bytes):
                    return io.BytesIO(content)
                else:
                    raise content
        return orig_open(name, *args, **kwargs)

    orig_open = open
    with mock.patch("builtins.open", create=True, side_effect=open_mock) as m:
        yield m


def mock_open_exception(for_path, exc):
    return mock_open_content({for_path: exc})


@contextlib.contextmanager
def mock_cpufreq_sysfs(files, num_policies):
    def exists_mock(path):
        if path.startswith("/sys/devices/system/cpu/"):
            return True
        return orig_exists(path)

    def glob_mock(pattern):
        if pattern == "/sys/devices/system/cpu/cpufreq/policy[0-9]*":
            return [
                f"/sys/devices/system/cpu/cpufreq/policy{n}"
                for n in range(num_policies)
            ]
        return orig_glob(pattern)

    orig_exists = os.path.exists
    orig_glob = glob.glob
    try:
        with mock.patch("os.path.exists", side_effect=exists_mock):
            importlib.reload(psutil._pslinux)
            with mock.patch("glob.glob", side_effect=glob_mock):
                with mock_open_content(files):
                    yield
    finally:
        importlib.reload(psutil._pslinux)
        importlib.reload(psutil)


# =====================================================================
# --- system virtual memory
# =====================================================================


class TestVirtualMemoryAgainstFree(LinuxTestCase):
    def test_total(self):
        cli_value = free_physmem().total
        psutil_value = psutil.virtual_memory().total
        assert cli_value == psutil_value

    @retry_on_failure
    def test_used(self):
        # Older versions of procps used slab memory to calculate used memory.
        # This got changed in:
        # https://gitlab.com/procps-ng/procps/-/commit/05d751c4f07
        # Newer versions of procps (>=4.0.1) are using yet another way to
        # compute used memory.
        # https://gitlab.com/procps-ng/procps/-/commit/2184e90d2e7
        if get_free_version_info() < (4, 0, 1):
            return pytest.skip("free version too old")
        cli_value = free_physmem().used
        psutil_value = psutil.virtual_memory().used
        assert abs(cli_value - psutil_value) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_free(self):
        cli_value = free_physmem().free
        psutil_value = psutil.virtual_memory().free
        assert abs(cli_value - psutil_value) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_shared(self):
        free = free_physmem()
        free_value = free.shared
        if free_value == 0:
            return pytest.skip("free does not support 'shared' column")
        psutil_value = psutil.virtual_memory().shared
        assert (
            abs(free_value - psutil_value) < TOLERANCE_SYS_MEM
        ), f"{free_value} {psutil_value} \n{free.output}"

    @retry_on_failure
    def test_available(self):
        # "free" output format has changed at some point:
        # https://github.com/giampaolo/psutil/issues/538#issuecomment-147192098
        out = sh(["free", "-b"])
        lines = out.split('\n')
        if 'available' not in lines[0]:
            return pytest.skip("free does not support 'available' column")
        free_value = int(lines[1].split()[-1])
        psutil_value = psutil.virtual_memory().available
        assert abs(free_value - psutil_value) < TOLERANCE_SYS_MEM


class TestVirtualMemoryAgainstVmstat(LinuxTestCase):
    def check_vmstat(self, stat, field):
        vmstat_value = vmstat(stat) * 1024
        psutil_value = getattr(psutil.virtual_memory(), field)
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_total(self):
        self.check_vmstat("total memory", "total")

    @retry_on_failure
    def test_used(self):
        # Older versions of procps used slab memory to calculate used memory.
        # This got changed in:
        # https://gitlab.com/procps-ng/procps/-/commit/05d751c4f07
        # Newer versions of procps (>=4.0.1) are using yet another way to
        # compute used memory.
        # https://gitlab.com/procps-ng/procps/-/commit/2184e90d2e7
        if get_free_version_info() < (4, 0, 1):
            return pytest.skip("free version too old")
        self.check_vmstat("used memory", "used")

    @retry_on_failure
    def test_free(self):
        self.check_vmstat("free memory", "free")

    @retry_on_failure
    def test_buffers(self):
        self.check_vmstat("buffer memory", "buffers")

    @retry_on_failure
    def test_active(self):
        self.check_vmstat("active memory", "active")

    @retry_on_failure
    def test_inactive(self):
        self.check_vmstat("inactive memory", "inactive")


class TestVirtualMemoryAgainstMeminfo(LinuxTestCase):
    @staticmethod
    def read_meminfo():
        mems = {}
        with open("/proc/meminfo") as f:
            for line in f:
                fields = line.split()
                if len(fields) >= 2:
                    mems[fields[0]] = int(fields[1]) * 1024
        return mems

    @retry_on_failure
    def test_buffers(self):
        proc_value = self.read_meminfo()["Buffers:"]
        psutil_value = psutil.virtual_memory().buffers
        assert abs(psutil_value - proc_value) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_cached(self):
        # psutil cached = Cached + SReclaimable
        mems = self.read_meminfo()
        proc_value = mems["Cached:"] + mems.get("SReclaimable:", 0)
        psutil_value = psutil.virtual_memory().cached
        assert abs(psutil_value - proc_value) < TOLERANCE_SYS_MEM


class TestVirtualMemoryMocks(LinuxTestCase):
    MEMINFO_NO_AVAIL = textwrap.dedent("""\
        Active:          9444728 kB
        Active(anon):    6145416 kB
        Active(file):    2950064 kB
        Buffers:          287952 kB
        Cached:          4818144 kB
        Inactive(anon):   574764 kB
        Inactive(file):  1567648 kB
        MemFree:         2057400 kB
        MemTotal:       16325648 kB
        Shmem:            577588 kB
        SReclaimable:     346648 kB
        """)

    def mocked_virtual_memory(self, files):
        with mock_open_content(files) as m:
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ret = psutil.virtual_memory()
        assert m.called
        return ret, [str(w.message) for w in ws]

    def test_warnings_on_misses(self):
        # Emulate a case where /proc/meminfo provides few info.
        # psutil is supposed to set the missing fields to 0 and
        # raise a warning.
        content = textwrap.dedent("""\
            Active(anon):    6145416 kB
            Active(file):    2950064 kB
            Inactive(anon):   574764 kB
            Inactive(file):  1567648 kB
            MemAvailable:         -1 kB
            MemFree:         2057400 kB
            MemTotal:       16325648 kB
            SReclaimable:     346648 kB
            """).encode()
        ret, ws = self.mocked_virtual_memory({"/proc/meminfo": content})
        assert len(ws) == 1
        msg = ws[0]
        assert "memory stats couldn't be determined" in msg
        assert "cached" in msg
        assert "shared" in msg
        assert "active" in msg
        assert "inactive" in msg
        assert "buffers" in msg
        assert "available" in msg
        assert ret.cached == 0
        assert ret.active == 0
        assert ret.inactive == 0
        assert ret.shared == 0
        assert ret.buffers == 0
        assert ret.available == 0
        assert ret.slab == 0

    @retry_on_failure
    def test_avail_old_percent(self):
        # Make sure that our calculation of avail mem for old kernels
        # is off by max 15%.
        mems = {}
        with open_binary('/proc/meminfo') as f:
            for line in f:
                fields = line.split()
                mems[fields[0]] = int(fields[1]) * 1024

        a = calculate_avail_vmem(mems)
        if b'MemAvailable:' in mems:
            b = mems[b'MemAvailable:']
            diff_percent = abs(a - b) / a * 100
            assert diff_percent < 15

    def test_avail_old_comes_from_kernel(self):
        # Make sure "MemAvailable:" coluimn is used instead of relying
        # on our internal algorithm to calculate avail mem.
        content = self.MEMINFO_NO_AVAIL + "MemAvailable:    6574984 kB\n"
        ret, ws = self.mocked_virtual_memory(
            {"/proc/meminfo": content.encode()}
        )
        assert ret.available == 6574984 * 1024
        assert "inactive memory stats couldn't be determined" in ws[0]

    def test_avail_old_missing_fields(self):
        # Remove Active(file), Inactive(file) and SReclaimable
        # from /proc/meminfo and make sure the fallback is used
        # (free + cached),
        removed = ("Active(file):", "Inactive(file):", "SReclaimable:")
        content = "".join(
            line
            for line in self.MEMINFO_NO_AVAIL.splitlines(keepends=True)
            if not line.startswith(removed)
        )
        ret, ws = self.mocked_virtual_memory(
            {"/proc/meminfo": content.encode()}
        )
        assert ret.available == 2057400 * 1024 + 4818144 * 1024
        assert "inactive memory stats couldn't be determined" in ws[0]

    def test_avail_old_missing_zoneinfo(self):
        # Remove /proc/zoneinfo file. Make sure fallback is used
        # (free + cached).
        ret, ws = self.mocked_virtual_memory({
            "/proc/meminfo": self.MEMINFO_NO_AVAIL.encode(),
            "/proc/zoneinfo": FileNotFoundError,
        })
        assert ret.available == 2057400 * 1024 + 4818144 * 1024
        assert "inactive memory stats couldn't be determined" in ws[0]

    def test_virtual_memory_mocked(self):
        # Emulate /proc/meminfo because neither vmstat nor free return slab.
        content = textwrap.dedent("""\
            MemTotal:              100 kB
            MemFree:               2 kB
            MemAvailable:          3 kB
            Buffers:               4 kB
            Cached:                5 kB
            SwapCached:            6 kB
            Active:                7 kB
            Inactive:              8 kB
            Active(anon):          9 kB
            Inactive(anon):        10 kB
            Active(file):          11 kB
            Inactive(file):        12 kB
            Unevictable:           13 kB
            Mlocked:               14 kB
            SwapTotal:             15 kB
            SwapFree:              16 kB
            Dirty:                 17 kB
            Writeback:             18 kB
            AnonPages:             19 kB
            Mapped:                20 kB
            Shmem:                 21 kB
            Slab:                  22 kB
            SReclaimable:          23 kB
            SUnreclaim:            24 kB
            KernelStack:           25 kB
            PageTables:            26 kB
            NFS_Unstable:          27 kB
            Bounce:                28 kB
            WritebackTmp:          29 kB
            CommitLimit:           30 kB
            Committed_AS:          31 kB
            VmallocTotal:          32 kB
            VmallocUsed:           33 kB
            VmallocChunk:          34 kB
            HardwareCorrupted:     35 kB
            AnonHugePages:         36 kB
            ShmemHugePages:        37 kB
            ShmemPmdMapped:        38 kB
            CmaTotal:              39 kB
            CmaFree:               40 kB
            HugePages_Total:       41 kB
            HugePages_Free:        42 kB
            HugePages_Rsvd:        43 kB
            HugePages_Surp:        44 kB
            Hugepagesize:          45 kB
            DirectMap46k:          46 kB
            DirectMap47M:          47 kB
            DirectMap48G:          48 kB
            """).encode()
        with mock_open_content({"/proc/meminfo": content}) as m:
            mem = psutil.virtual_memory()
            assert m.called
            assert mem.total == 100 * 1024
            assert mem.free == 2 * 1024
            assert mem.buffers == 4 * 1024
            # cached mem also includes reclaimable memory
            assert mem.cached == (5 + 23) * 1024
            assert mem.shared == 21 * 1024
            assert mem.active == 7 * 1024
            assert mem.inactive == 8 * 1024
            assert mem.slab == 22 * 1024
            assert mem.available == 3 * 1024

    def test_virtual_memory_no_space_after_colon(self):
        """Some Linux meminfo fields may not have a space after the colon:
        https://github.com/torvalds/linux/blob/8356a5a3b078ca89c526dd6d71e9a76fec571c37/fs/proc/meminfo.c#L113-L116
        """
        content = textwrap.dedent("""\
            MemTotal:              100 kB
            MemFree:               2 kB
            MemAvailable:          3 kB
            Buffers:               4 kB
            Cached:                5 kB
            Active:                6 kB
            Inactive:              7 kB
            Shmem:                 8 kB
            Slab:                  9 kB
            ShadowCallStack:10373888 kB
            """).encode()
        with mock_open_content({"/proc/meminfo": content}) as m:
            mem = psutil.virtual_memory()
            assert m.called
            assert mem.total == 100 * 1024


# =====================================================================
# --- system swap memory
# =====================================================================


class TestSwapMemory(LinuxTestCase):
    @staticmethod
    def meminfo_has_swap_info():
        """Return True if /proc/meminfo provides swap metrics."""
        with open("/proc/meminfo") as f:
            data = f.read()
        return 'SwapTotal:' in data and 'SwapFree:' in data

    def test_total(self):
        free_value = free_swap().total
        psutil_value = psutil.swap_memory().total
        assert abs(free_value - psutil_value) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_used(self):
        free_value = free_swap().used
        psutil_value = psutil.swap_memory().used
        assert abs(free_value - psutil_value) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_free(self):
        free_value = free_swap().free
        psutil_value = psutil.swap_memory().free
        assert abs(free_value - psutil_value) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_sin_sout(self):
        # Cross-check sin/sout against /proc/vmstat pswpin/pswpout fields.
        # psutil converts pages to bytes using a 4096-byte page size.
        PAGE_SIZE = 4 * 1024
        with open("/proc/vmstat") as f:
            vmstat = dict(line.split() for line in f if line.split())
        sin = int(vmstat["pswpin"]) * PAGE_SIZE
        sout = int(vmstat["pswpout"]) * PAGE_SIZE
        swap = psutil.swap_memory()
        assert swap.sin == sin
        assert swap.sout == sout

    def test_missing_sin_sout(self):
        with mock.patch('psutil._common.open', create=True) as m:
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ret = psutil.swap_memory()
                assert m.called
                assert len(ws) == 1
                w = ws[0]
                assert (
                    "'sin' and 'sout' swap memory stats couldn't be determined"
                    in str(w.message)
                )
                assert ret.sin == 0
                assert ret.sout == 0

    def test_no_vmstat_mocked(self):
        # see https://github.com/giampaolo/psutil/issues/722
        with mock_open_exception("/proc/vmstat", FileNotFoundError) as m:
            with warnings.catch_warnings(record=True) as ws:
                warnings.simplefilter("always")
                ret = psutil.swap_memory()
                assert m.called
                assert len(ws) == 1
                w = ws[0]
                assert (
                    "'sin' and 'sout' swap memory stats couldn't "
                    "be determined and were set to 0"
                    in str(w.message)
                )
                assert ret.sin == 0
                assert ret.sout == 0

    def test_meminfo_against_sysinfo(self):
        # Make sure the content of /proc/meminfo about swap memory
        # matches sysinfo() syscall, see:
        # https://github.com/giampaolo/psutil/issues/1015
        if not self.meminfo_has_swap_info():
            return pytest.skip("/proc/meminfo has no swap metrics")
        with mock.patch.object(_psutil, 'linux_sysinfo') as m:
            swap = psutil.swap_memory()
        assert not m.called

        _, _, _, _, total, free, unit_multiplier = _psutil.linux_sysinfo()
        total *= unit_multiplier
        free *= unit_multiplier
        assert swap.total == total
        assert abs(swap.free - free) < TOLERANCE_SYS_MEM

    def test_emulate_meminfo_has_no_metrics(self):
        # Emulate a case where /proc/meminfo provides no swap metrics
        # in which case sysinfo() syscall is supposed to be used
        # as a fallback.
        with mock_open_content({"/proc/meminfo": b""}) as m:
            psutil.swap_memory()
            assert m.called

    def test_no_space_after_colon(self):
        # Some Linux meminfo fields may not have a space after the
        # colon, see:
        # https://github.com/giampaolo/psutil/issues/2809
        content = textwrap.dedent("""\
            MemTotal:              100 kB
            MemFree:               2 kB
            SwapTotal:             15 kB
            SwapFree:              14 kB
            ShadowCallStack:10373888 kB
            """).encode()
        with mock_open_content({"/proc/meminfo": content}) as m:
            swap = psutil.swap_memory()
            assert m.called
            assert swap.total == 15 * 1024
            assert swap.free == 14 * 1024


# =====================================================================
# --- system CPU
# =====================================================================


class TestCpuCountLogical(LinuxTestCase):
    @skipif(
        not os.path.exists("/sys/devices/system/cpu/online"),
        reason="/sys/devices/system/cpu/online does not exist",
    )
    def test_against_sysdev_cpu_online(self):
        with open("/sys/devices/system/cpu/online") as f:
            value = f.read().strip()
        if "-" in str(value):
            value = int(value.split('-')[1]) + 1
            assert psutil.cpu_count() == value

    @skipif(
        not os.path.exists("/sys/devices/system/cpu"),
        reason="/sys/devices/system/cpu does not exist",
    )
    def test_against_sysdev_cpu_num(self):
        # The kernel creates a directory for every *possible* CPU, so
        # this is an upper bound: cpu_count() counts the online ones.
        ls = os.listdir("/sys/devices/system/cpu")
        count = len([x for x in ls if re.search(r"cpu\d+$", x) is not None])
        assert psutil.cpu_count() <= count

    @requires_cli("nproc")
    def test_against_nproc(self):
        num = int(sh("nproc"))
        assert psutil.cpu_count(logical=True) == num

    @requires_cli("lscpu")
    def test_against_lscpu(self):
        out = sh("lscpu -p")
        num = len([x for x in out.split('\n') if not x.startswith('#')])
        assert psutil.cpu_count(logical=True) == num

    def test_emulate_fallbacks(self):
        import psutil._pslinux

        original = psutil._pslinux.cpu_count_logical()
        # Here we want to mock os.sysconf("SC_NPROCESSORS_ONLN") in
        # order to cause the parsing of /proc/cpuinfo and /proc/stat.
        with mock.patch(
            'psutil._pslinux.os.sysconf', side_effect=ValueError
        ) as m:
            assert psutil._pslinux.cpu_count_logical() == original
            assert m.called

            # Let's have open() return empty data and make sure None is
            # returned ('cause we mimic os.cpu_count()).
            with mock.patch('psutil._common.open', create=True) as m:
                assert psutil._pslinux.cpu_count_logical() is None
                assert m.call_count == 2
                # /proc/stat should be the last one
                assert m.call_args[0][0] == '/proc/stat'

            # Let's push this a bit further and make sure /proc/cpuinfo
            # parsing works as expected.
            with open('/proc/cpuinfo', 'rb') as f:
                cpuinfo_data = f.read()
            with mock_open_content({"/proc/cpuinfo": cpuinfo_data}) as m:
                assert psutil._pslinux.cpu_count_logical() == original
                assert m.called

            # Finally, let's make /proc/cpuinfo return meaningless data;
            # this way we'll fall back on relying on /proc/stat
            with mock_open_content({"/proc/cpuinfo": b""}) as m:
                assert psutil._pslinux.cpu_count_logical() == original
                assert m.called


class TestCpuCountCores(LinuxTestCase):
    @requires_cli("lscpu")
    def test_against_lscpu(self):
        pairs = []
        per_socket = ""
        for line in sh("lscpu").splitlines():
            key, _, value = line.partition(":")
            key, value = key.strip(), value.strip()
            if key == "Core(s) per socket":
                per_socket = value
            elif key == "Socket(s)":
                pairs.append((per_socket, value))
        # In a VM lscpu may print "-" instead of a number.
        if not pairs or not all(x.isdigit() and y.isdigit() for x, y in pairs):
            return pytest.skip("lscpu doesn't report the number of cores")
        cores = sum(int(x) * int(y) for x, y in pairs)
        assert psutil.cpu_count(logical=False) == cores

    @skipif(
        platform.machine() not in {"x86_64", "i686"}, reason="x86_64/i686 only"
    )
    def test_method_2(self):
        meth_1 = psutil._pslinux.cpu_count_cores()
        with mock.patch('glob.glob', return_value=[]) as m:
            meth_2 = psutil._pslinux.cpu_count_cores()
            assert m.called
        if meth_1 is not None:
            assert meth_1 == meth_2

    def test_emulate_none(self):
        with mock.patch('glob.glob', return_value=[]) as m1:
            with mock.patch('psutil._common.open', create=True) as m2:
                assert psutil._pslinux.cpu_count_cores() is None
        assert m1.called
        assert m2.called


class TestCpuFreq(LinuxTestCase):
    def test_cpuinfo_freq_ppc(self):
        content = b"clock\t\t: 2750.000000MHz\nclock\t\t: 2500.000000MHz\n"
        with mock_open_content({"/proc/cpuinfo": content}):
            assert _cpu_get_cpuinfo_freq() == [2750.0, 2500.0]

    def test_cpuinfo_freq_s390x(self):
        content = (
            b"cpu MHz dynamic : 5200\ncpu MHz static  : 5000\n"
            b"cpu MHz dynamic : 5100\ncpu MHz static  : 5000\n"
        )
        with mock_open_content({"/proc/cpuinfo": content}):
            assert _cpu_get_cpuinfo_freq() == [5200.0, 5100.0]

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    @skipif(AARCH64, reason="aarch64 does not always expose frequency")
    @skipif(
        not os.path.exists("/sys/devices/system/cpu/cpu0/cpufreq"),
        reason="no cpu0/cpufreq in sysfs",
    )
    def test_emulate_use_second_file(self):
        # https://github.com/giampaolo/psutil/issues/981
        def glob_mock(pattern):
            if pattern.startswith("/sys/devices/system/cpu/cpufreq/policy"):
                return []
            else:
                return orig_glob(pattern)

        orig_glob = glob.glob
        with mock.patch("glob.glob", side_effect=glob_mock) as m:
            assert psutil.cpu_freq(percpu=True)
        m.assert_any_call("/sys/devices/system/cpu/cpu[0-9]*/cpufreq")

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    @skipif(not CPUINFO_HAS_MHZ, reason="no 'cpu MHz' in /proc/cpuinfo")
    def test_emulate_use_cpuinfo(self):
        # Emulate a case where /sys/devices/system/cpu/cpufreq* does not
        # exist and /proc/cpuinfo is used instead.
        def path_exists_mock(path):
            if path.startswith('/sys/devices/system/cpu/'):
                return False
            else:
                return os_path_exists(path)

        os_path_exists = os.path.exists
        try:
            with mock.patch("os.path.exists", side_effect=path_exists_mock):
                importlib.reload(psutil._pslinux)
                ret = psutil.cpu_freq()
                assert ret, ret
                assert ret.max == 0.0
                assert ret.min == 0.0
                for freq in psutil.cpu_freq(percpu=True):
                    assert freq.max == 0.0
                    assert freq.min == 0.0
        finally:
            importlib.reload(psutil._pslinux)
            importlib.reload(psutil)

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_emulate_data(self):
        files = {
            "*/affected_cpus": b"0",
            "*/scaling_cur_freq": b"500000",
            "*/scaling_min_freq": b"600000",
            "*/scaling_max_freq": b"700000",
            "/proc/cpuinfo": b"cpu MHz     : 500",
        }
        with mock_cpufreq_sysfs(files, 1):
            freq = psutil.cpu_freq()
        assert freq == (500.0, 600.0, 700.0)

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_emulate_multi_cpu(self):
        files = {
            "*/policy0/affected_cpus": b"0",
            "*/policy0/scaling_cur_freq": b"100000",
            "*/policy0/scaling_min_freq": b"200000",
            "*/policy0/scaling_max_freq": b"300000",
            "*/policy1/affected_cpus": b"1",
            "*/policy1/scaling_cur_freq": b"400000",
            "*/policy1/scaling_min_freq": b"500000",
            "*/policy1/scaling_max_freq": b"600000",
            "/proc/cpuinfo": b"cpu MHz     : 100\ncpu MHz     : 400",
        }
        with mock_cpufreq_sysfs(files, 2):
            freq = psutil.cpu_freq(percpu=True)
        assert freq == [(100.0, 200.0, 300.0), (400.0, 500.0, 600.0)]

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_emulate_shared_policy(self):
        # A single policy governing 4 CPUs must yield 4 entries, see:
        # https://github.com/giampaolo/psutil/issues/2512
        files = {
            "*/affected_cpus": b"0 1 2 3",
            "*/scaling_cur_freq": b"100000",
            "*/scaling_min_freq": b"200000",
            "*/scaling_max_freq": b"300000",
            "/proc/cpuinfo": b"",
        }
        with mock_cpufreq_sysfs(files, 1):
            freq = psutil.cpu_freq(percpu=True)
        assert len(freq) == 4
        for nt in freq:
            assert nt == (100.0, 200.0, 300.0)

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_emulate_no_scaling_cur_freq_file(self):
        # See: https://github.com/giampaolo/psutil/issues/1071
        files = {
            "*/affected_cpus": b"0",
            "*/scaling_cur_freq": FileNotFoundError,
            "*/cpuinfo_cur_freq": b"200000",
            "*/scaling_min_freq": b"100000",
            "*/scaling_max_freq": b"300000",
            "/proc/cpuinfo": b"",
        }
        with mock_cpufreq_sysfs(files, 1):
            freq = psutil.cpu_freq()
        assert freq.current == 200

    @skipif(not HAS_CPU_FREQ, reason="not supported")
    def test_emulate_offline_cpus(self):
        # Offline CPU cores must not be taken into account, else they
        # drag down the average frequency. See:
        # https://github.com/giampaolo/psutil/issues/2628
        # Only CPUs 0 and 1 are online; 2 and 3 are offline.
        files = {
            "/proc/cpuinfo": b"cpu MHz\t: 200\ncpu MHz\t: 400",
            "*/policy0/affected_cpus": b"0",
            "*/policy1/affected_cpus": b"1",
            "*/policy2/affected_cpus": b"2",
            "*/policy3/affected_cpus": b"3",
            "*/policy0/scaling_cur_freq": b"200000",
            "*/policy1/scaling_cur_freq": b"400000",
            "*/policy[01]/scaling_min_freq": b"100000",
            "*/policy[01]/scaling_max_freq": b"300000",
            "*/policy[23]/scaling_cur_freq": FileNotFoundError,
            "*/policy[23]/cpuinfo_cur_freq": FileNotFoundError,
            "*/online": "0\n",
        }

        with mock_cpufreq_sysfs(files, 4):
            percpu = psutil.cpu_freq(percpu=True)
            freq = psutil.cpu_freq()
        assert len(percpu) == 2
        assert [f.current for f in percpu] == [200.0, 400.0]
        assert freq.current == 300.0
        assert freq.min == 100.0
        assert freq.max == 300.0


class TestCpuTimes(LinuxTestCase):

    @retry_on_failure
    def test_against_proc_stat(self):
        with open("/proc/stat") as f:
            line = f.readline()
        ticks = [float(x) for x in line.split()[1:]]
        fields = [t / CLOCK_TICKS for t in ticks]
        ct = psutil.cpu_times()
        TOLERANCE = 1  # 1 second
        assert abs(ct.user - fields[0]) < TOLERANCE
        assert abs(ct.nice - fields[1]) < TOLERANCE
        assert abs(ct.system - fields[2]) < TOLERANCE
        assert abs(ct.idle - fields[3]) < TOLERANCE
        assert abs(ct.iowait - fields[4]) < TOLERANCE
        assert abs(ct.irq - fields[5]) < TOLERANCE
        assert abs(ct.softirq - fields[6]) < TOLERANCE
        assert abs(ct.steal - fields[7]) < TOLERANCE

    def test_cpu_steal_decrease(self):
        # Test cumulative cpu stats decrease. We should ignore this.
        # See issue #1210.
        content = textwrap.dedent("""\
            cpu   0 0 0 0 0 0 0 1 0 0
            cpu0  0 0 0 0 0 0 0 1 0 0
            cpu1  0 0 0 0 0 0 0 1 0 0
            """).encode()
        with mock_open_content({"/proc/stat": content}) as m:
            # first call to "percent" functions should read the new stat file
            # and compare to the "real" file read at import time - so the
            # values are meaningless
            psutil.cpu_percent()
            assert m.called
            psutil.cpu_percent(percpu=True)
            psutil.cpu_times_percent()
            psutil.cpu_times_percent(percpu=True)

        content = textwrap.dedent("""\
            cpu   1 0 0 0 0 0 0 0 0 0
            cpu0  1 0 0 0 0 0 0 0 0 0
            cpu1  1 0 0 0 0 0 0 0 0 0
            """).encode()
        with mock_open_content({"/proc/stat": content}) as m:
            # Increase "user" while steal goes "backwards" to zero.
            cpu_percent = psutil.cpu_percent()
            assert m.called
            cpu_percent_percpu = psutil.cpu_percent(percpu=True)
            cpu_times_percent = psutil.cpu_times_percent()
            cpu_times_percent_percpu = psutil.cpu_times_percent(percpu=True)
            assert cpu_percent != 0
            assert sum(cpu_percent_percpu) != 0
            assert sum(cpu_times_percent) != 0
            assert sum(cpu_times_percent) != 100.0
            assert sum(map(sum, cpu_times_percent_percpu)) != 0
            assert sum(map(sum, cpu_times_percent_percpu)) != 100.0
            assert cpu_times_percent.steal == 0
            assert cpu_times_percent.user != 0


class TestCpuStats(LinuxTestCase):

    @staticmethod
    def assert_close_to_vmstat(vmstat_value, psutil_value):
        # Old procps keeps these counters in 32 bits, so it wraps once
        # the kernel goes past 2**32 and psutil doesn't.
        if psutil_value >= 2**32 and vmstat_value < 2**32:
            return pytest.skip("vmstat truncated the counter to 32 bits")
        assert abs(vmstat_value - psutil_value) < 500

    @isolated
    def test_ctx_switches(self):
        vmstat_value = vmstat("context switches")
        psutil_value = psutil.cpu_stats().ctx_switches
        self.assert_close_to_vmstat(vmstat_value, psutil_value)

    @isolated
    def test_interrupts(self):
        vmstat_value = vmstat("interrupts")
        psutil_value = psutil.cpu_stats().interrupts
        self.assert_close_to_vmstat(vmstat_value, psutil_value)


# =====================================================================
# --- system network
# =====================================================================


class TestNetIfAddrs(LinuxTestCase):
    def test_ips(self):
        for name, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == psutil.AF_LINK:
                    assert addr.address == get_mac_address(name)
                elif addr.family == socket.AF_INET:
                    assert addr.address == get_ipv4_address(name)
                    assert addr.netmask == get_ipv4_netmask(name)
                    if addr.broadcast is not None:
                        assert addr.broadcast == get_ipv4_broadcast(name)
                    else:
                        # SIOCGIFBRDADDR shares a union with the peer
                        # address, so on a /32 it echoes the address
                        # back and on a ptp link it gives the peer.
                        assert get_ipv4_broadcast(name) in {
                            '0.0.0.0',
                            addr.address,
                            addr.ptp,
                        }
                elif addr.family == socket.AF_INET6:
                    # IPv6 addresses can have a percent symbol at the end.
                    # E.g. these 2 are equivalent:
                    # "fe80::1ff:fe23:4567:890a"
                    # "fe80::1ff:fe23:4567:890a%eth0"
                    # That is the "zone id" portion, which usually is the name
                    # of the network interface.
                    address = addr.address.split('%')[0]
                    assert address in get_ipv6_addresses(name)

    @requires_cli("ip")
    @retry_on_failure
    def test_against_ip_addr_v4(self):
        # Parse IPv4 addresses per interface from `ip addr` output and
        # compare against psutil. Use the label at the end of each inet
        # line as the interface name, since it reflects aliases like
        # "vboxnet0:avahi" that psutil also uses as keys.
        out = sh("ip addr")
        ip_addrs = {}  # {ifname: [addr, ...]}
        for line in out.splitlines():
            # "    inet 1.2.3.4/24 brd ... scope global eth0"
            m = re.match(r'^\s+inet\s+(\S+).*\s+(\S+)$', line)
            if m:
                addr = m.group(1).split('/')[0]
                ifname = m.group(2)
                ip_addrs.setdefault(ifname, []).append(addr)
        psutil_addrs = psutil.net_if_addrs()
        for ifname, addrs in ip_addrs.items():
            if ifname not in psutil_addrs:
                continue
            psutil_ipv4 = {
                a.address
                for a in psutil_addrs[ifname]
                if a.family == socket.AF_INET
            }
            for addr in addrs:
                assert addr in psutil_ipv4

    @requires_cli("ip")
    @retry_on_failure
    def test_against_ip_addr_v6(self):
        # Parse IPv6 addresses per interface from `ip addr` output and
        # compare against psutil. Unlike inet, inet6 lines have no label,
        # so the interface name comes from the header line.
        out = sh("ip addr")
        ip_addrs = {}  # {ifname: [addr, ...]}
        current_if = None
        for line in out.splitlines():
            m = re.match(r'^\d+:\s+(\S+):', line)
            if m:
                current_if = m.group(1).rstrip(':')
            m = re.match(r'^\s+inet6\s+(\S+)', line)
            if m and current_if:
                addr = m.group(1).split('/')[0]
                ip_addrs.setdefault(current_if, []).append(addr)
        psutil_addrs = psutil.net_if_addrs()
        for ifname, addrs in ip_addrs.items():
            if ifname not in psutil_addrs:
                continue
            # psutil may append %ifname zone ID to link-local addresses.
            psutil_ipv6 = {
                a.address.split('%')[0]
                for a in psutil_addrs[ifname]
                if a.family == socket.AF_INET6
            }
            for addr in addrs:
                assert addr in psutil_ipv6

    @requires_cli("ip")
    def test_net_if_names(self):
        out = sh("ip addr").strip()
        nics = [x for x in psutil.net_if_addrs() if ':' not in x]
        found = 0
        for line in out.split('\n'):
            line = line.strip()
            if re.search(r"^\d+:", line):
                found += 1
                name = line.split(':')[1].strip().split('@')[0]
                assert name in nics
        assert len(nics) == found


class TestNetIfStats(LinuxTestCase):
    @requires_cli("ifconfig")
    def test_against_ifconfig(self):
        for name, stats in psutil.net_if_stats().items():
            try:
                out = sh(f"ifconfig {name}")
            except RuntimeError:
                pass
            else:
                assert stats.isup == ('RUNNING' in out), out
                assert stats.mtu == int(
                    re.findall(r'(?i)MTU[: ](\d+)', out)[0]
                )

    def test_mtu(self):
        for name, stats in psutil.net_if_stats().items():
            with open(f"/sys/class/net/{name}/mtu") as f:
                assert stats.mtu == int(f.read().strip())

    @requires_cli("ifconfig")
    def test_flags(self):
        # first line looks like this:
        # "eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500"
        matches_found = 0
        for name, stats in psutil.net_if_stats().items():
            try:
                out = sh(f"ifconfig {name}")
            except RuntimeError:
                pass
            else:
                match = re.search(r"flags=(\d+)?<(.*?)>", out)
                if match and len(match.groups()) >= 2:
                    matches_found += 1
                    ifconfig_flags = set(match.group(2).lower().split(","))
                    psutil_flags = set(stats.flags.split(","))
                    assert ifconfig_flags == psutil_flags
                else:
                    # ifconfig has a different output on CentOS 6
                    # let's try that
                    match = re.search(r"(.*)  MTU:(\d+)  Metric:(\d+)", out)
                    if match and len(match.groups()) >= 3:
                        matches_found += 1
                        ifconfig_flags = set(match.group(1).lower().split())
                        psutil_flags = set(stats.flags.split(","))
                        assert ifconfig_flags == psutil_flags

        if not matches_found:
            return pytest.fail("no matches were found")


class TestNetIoCounters(LinuxTestCase):
    @requires_cli("ifconfig")
    @retry_on_failure
    def test_against_ifconfig(self):
        def ifconfig(nic):
            ret = {}
            out = sh(f"ifconfig {nic}")
            ret['packets_recv'] = int(
                re.findall(r'RX packets[: ](\d+)', out)[0]
            )
            ret['packets_sent'] = int(
                re.findall(r'TX packets[: ](\d+)', out)[0]
            )
            ret['errin'] = int(re.findall(r'errors[: ](\d+)', out)[0])
            ret['errout'] = int(re.findall(r'errors[: ](\d+)', out)[1])
            ret['dropin'] = int(re.findall(r'dropped[: ](\d+)', out)[0])
            ret['dropout'] = int(re.findall(r'dropped[: ](\d+)', out)[1])
            ret['bytes_recv'] = int(
                re.findall(r'RX (?:packets \d+ +)?bytes[: ](\d+)', out)[0]
            )
            ret['bytes_sent'] = int(
                re.findall(r'TX (?:packets \d+ +)?bytes[: ](\d+)', out)[0]
            )
            return ret

        nio = psutil.net_io_counters(pernic=True, nowrap=False)
        for name, stats in nio.items():
            try:
                ifconfig_ret = ifconfig(name)
            except RuntimeError:
                continue
            if not any(ifconfig_ret.values()):
                # net-tools can't parse /proc/net/dev lines whose NIC
                # name fills the whole 15 chars (e.g. enxbaa44ee7dd5e),
                # and prints zeros for the whole interface.
                continue

            assert (
                abs(stats.bytes_recv - ifconfig_ret['bytes_recv']) < 1024 * 10
            )
            assert (
                abs(stats.bytes_sent - ifconfig_ret['bytes_sent']) < 1024 * 10
            )
            assert (
                abs(stats.packets_recv - ifconfig_ret['packets_recv']) < 1024
            )
            assert (
                abs(stats.packets_sent - ifconfig_ret['packets_sent']) < 1024
            )
            assert abs(stats.errin - ifconfig_ret['errin']) < 10
            assert abs(stats.errout - ifconfig_ret['errout']) < 10
            assert abs(stats.dropin - ifconfig_ret['dropin']) < 10
            assert abs(stats.dropout - ifconfig_ret['dropout']) < 10


class TestNetConnections(LinuxTestCase):
    @mock.patch('psutil._pslinux.socket.inet_ntop', side_effect=ValueError)
    @mock.patch('psutil._pslinux.supports_ipv6', return_value=False)
    @skipif(not os.path.exists("/proc/net/tcp6"), reason="no IPv6")
    def test_emulate_ipv6_unsupported(self, supports_ipv6, inet_ntop):
        # see: https://github.com/giampaolo/psutil/issues/623
        header = "  sl  local_address remote_address st\n"
        content = (
            header
            + "   0: 00000000000000000000000001000000:0016"
            " 00000000000000000000000000000000:0000 0A 00000000:00000000"
            " 00:00000000 00000000     0        0 12345 1\n"
        )
        files = {"/proc/net/tcp6": content, "/proc/net/udp6": header}
        with mock_open_content(files):
            assert psutil.net_connections(kind='inet6') == []
        assert inet_ntop.called

    @skipif(sys.byteorder != "little", reason="big endian")
    def test_decode_address(self):
        decode = psutil._pslinux.NetConnections.decode_address
        assert decode("0500000A:0016", socket.AF_INET) == ("10.0.0.5", 22)
        assert decode(
            "0000000000000000FFFF00000100007F:9E49", socket.AF_INET6
        ) == ("::ffff:127.0.0.1", 40521)
        assert decode("0500000A:0000", socket.AF_INET) == ()

    def test_emulate_unix(self):
        content = textwrap.dedent("""\
            0: 00000003 000 000 0001 03 462170 @/tmp/dbus-Qw2hMPIU3n
            0: 00000003 000 000 0001 03 35010 @/tmp/dbus-tB2X8h69BQ
            0: 00000003 000 000 0001 03 34424 @/tmp/dbus-cHy80Y8O
            000000000000000000000000000000000000000000000000000000
            """)
        with mock_open_content({"/proc/net/unix": content}) as m:
            psutil.net_connections(kind='unix')
            assert m.called

    @serial
    @requires_cli("ss")
    @retry_on_failure
    def test_against_ss(self):
        # Listening ports are more stable, so an exact set comparison is
        # more reliable.
        out = sh(["ss", "-tuanp"])
        ss_ports = set()
        for line in out.splitlines():
            fields = line.split()
            if (
                len(fields) >= 5
                and fields[0] == "tcp"
                and fields[1] == "LISTEN"
            ):
                port = int(fields[4].rsplit(":", 1)[-1])
                ss_ports.add(port)
        psutil_ports = {
            c.laddr.port
            for c in psutil.net_connections(kind="tcp")
            if c.status == psutil.CONN_LISTEN
        }
        assert ss_ports == psutil_ports


# =====================================================================
# --- system disks
# =====================================================================


class TestDiskPartitions(LinuxTestCase):
    @skip_on_not_implemented
    def test_against_df(self):
        # test psutil.disk_usage() and psutil.disk_partitions()
        # against "df -a"
        for part in psutil.disk_partitions(all=False):
            usage = psutil.disk_usage(part.mountpoint)
            _, total, used, free, _ = df(part.mountpoint)
            assert usage.total == total
            assert abs(usage.free - free) < TOLERANCE_DISK_USAGE
            assert abs(usage.used - used) < TOLERANCE_DISK_USAGE

    def test_zfs_fs(self):
        # Test that ZFS partitions are returned.
        with open("/proc/filesystems") as f:
            data = f.read()
        if 'zfs' in data:
            for part in psutil.disk_partitions():
                if part.fstype == 'zfs':
                    return

        # No ZFS partitions on this system. Let's fake one.
        fake_file = io.StringIO("nodev\tzfs\n")
        with mock.patch(
            'psutil._common.open', return_value=fake_file, create=True
        ) as m1:
            with mock.patch.object(
                _psutil,
                'disk_partitions',
                return_value=[('/dev/sdb3', '/', 'zfs', 'rw')],
            ) as m2:
                ret = psutil.disk_partitions()
                assert m1.called
                assert m2.called
                assert ret
                assert ret[0].fstype == 'zfs'

    def test_emulate_realpath_fail(self):
        # See: https://github.com/giampaolo/psutil/issues/1307
        with mock.patch('os.path.realpath', return_value='/non/existent') as m:
            with pytest.raises(FileNotFoundError):
                psutil.disk_partitions()
            assert m.called

    def test_emulate_filesystems_permission_error(self):
        real_open = psutil._pslinux.open_text

        def fake_open(path, *args, **kwargs):
            if path.endswith("/filesystems"):
                raise PermissionError(path)
            return real_open(path, *args, **kwargs)

        expected = psutil.disk_partitions()
        with mock.patch.object(psutil._pslinux, "open_text", fake_open):
            ret = psutil.disk_partitions()
        assert set(expected) <= set(ret)
        for part in ret:
            assert part.device.startswith("/dev/") or part.fstype == "zfs"


class TestDiskIoCounters(LinuxTestCase):
    def emulate_diskstats(self, content, storage_devices, perdisk=False):
        with mock_open_content({"/proc/diskstats": content}):
            with mock.patch(
                "psutil._pslinux.is_storage_device",
                side_effect=lambda name: name in storage_devices,
            ):
                return psutil.disk_io_counters(perdisk=perdisk, nowrap=False)

    def check_full_counters(self, ret):
        assert ret.read_count == 1
        assert ret.read_merged_count == 2
        assert ret.read_bytes == 3 * SECTOR_SIZE
        assert ret.read_time == 4
        assert ret.write_count == 5
        assert ret.write_merged_count == 6
        assert ret.write_bytes == 7 * SECTOR_SIZE
        assert ret.write_time == 8
        assert ret.busy_time == 10

    def test_emulate_kernel_2_4(self):
        # Tests /proc/diskstats parsing format for 2.4 kernels, see:
        # https://github.com/giampaolo/psutil/issues/767
        content = "   3     0   1 hda 2 3 4 5 6 7 8 9 10 11 12"
        self.check_full_counters(self.emulate_diskstats(content, {"hda"}))

    def test_emulate_kernel_2_6_full(self):
        # Tests /proc/diskstats parsing format for 2.6 kernels,
        # lines reporting all metrics:
        # https://github.com/giampaolo/psutil/issues/767
        content = "   3    0   hda 1 2 3 4 5 6 7 8 9 10 11"
        self.check_full_counters(self.emulate_diskstats(content, {"hda"}))

    def test_emulate_kernel_2_6_limited(self):
        # Tests /proc/diskstats parsing format for 2.6 kernels,
        # where one line of /proc/partitions return a limited
        # amount of metrics when it bumps into a partition
        # (instead of a disk). See:
        # https://github.com/giampaolo/psutil/issues/767
        ret = self.emulate_diskstats("   3    1   hda 1 2 3 4", {"hda"})
        assert ret.read_count == 1
        assert ret.read_bytes == 2 * SECTOR_SIZE
        assert ret.write_count == 3
        assert ret.write_bytes == 4 * SECTOR_SIZE

        assert ret.read_merged_count == 0
        assert ret.read_time == 0
        assert ret.write_merged_count == 0
        assert ret.write_time == 0
        assert ret.busy_time == 0

    def test_emulate_include_partitions(self):
        # Make sure that when perdisk=True disk partitions are returned,
        # see:
        # https://github.com/giampaolo/psutil/pull/1313#issuecomment-408626842
        content = textwrap.dedent("""\
            3    0   nvme0n1 1 2 3 4 5 6 7 8 9 10 11
            3    0   nvme0n1p1 1 2 3 4 5 6 7 8 9 10 11
            """)
        ret = self.emulate_diskstats(content, set(), perdisk=True)
        assert len(ret) == 2
        assert ret['nvme0n1'].read_count == 1
        assert ret['nvme0n1p1'].read_count == 1
        assert ret['nvme0n1'].write_count == 5
        assert ret['nvme0n1p1'].write_count == 5

    def test_emulate_exclude_partitions(self):
        # Make sure that when perdisk=False partitions (e.g. 'sda1',
        # 'nvme0n1p1') are skipped and not included in the total count.
        # https://github.com/giampaolo/psutil/pull/1313#issuecomment-408626842
        content = textwrap.dedent("""\
            3    0   nvme0n1 1 2 3 4 5 6 7 8 9 10 11
            3    0   nvme0n1p1 1 2 3 4 5 6 7 8 9 10 11
            """)
        assert self.emulate_diskstats(content, set()) is None

        ret = self.emulate_diskstats(content, {"nvme0n1"})
        assert ret.read_count == 1
        assert ret.write_count == 5

    def test_emulate_use_sysfs(self):
        def exists(path):
            return path == '/sys/block'

        wprocfs = psutil.disk_io_counters(perdisk=True)
        with mock.patch(
            'psutil._pslinux.os.path.exists', create=True, side_effect=exists
        ) as m:
            wsysfs = psutil.disk_io_counters(perdisk=True)
        m.assert_any_call('/sys/block')
        assert sorted(wprocfs) == sorted(wsysfs)

    def test_emulate_not_impl(self):
        def exists(path):
            return False

        with mock.patch(
            'psutil._pslinux.os.path.exists', create=True, side_effect=exists
        ):
            with pytest.raises(NotImplementedError):
                psutil.disk_io_counters()

    @requires_cli("iostat")
    @retry_on_failure
    def test_against_iostat(self):
        # Cross-check read_bytes/write_bytes against 'iostat -d -k'
        # cumulative totals (kB_read, kB_wrtn columns).
        out = sh(["iostat", "-d", "-k"])
        iostat_disks = {}
        for line in out.splitlines():
            fields = line.split()
            if len(fields) < 7 or fields[0] in {"Linux", "Device"}:
                continue
            name = fields[0]
            try:
                kb_read = int(fields[5])
                kb_wrtn = int(fields[6])
            except ValueError:
                continue
            iostat_disks[name] = (kb_read * 1024, kb_wrtn * 1024)

        psutil_disks = psutil.disk_io_counters(perdisk=True, nowrap=False)
        for name, (bytes_read, bytes_wrtn) in iostat_disks.items():
            if name not in psutil_disks:
                continue
            stats = psutil_disks[name]
            assert abs(stats.read_bytes - bytes_read) < 1024 * 1024
            assert abs(stats.write_bytes - bytes_wrtn) < 1024 * 1024


class TestRootFsDeviceFinder(LinuxTestCase):
    def setUp(self):
        dev = os.stat("/").st_dev
        self.major = os.major(dev)
        self.minor = os.minor(dev)

    def test_call_methods(self):
        finder = RootFsDeviceFinder()
        if os.path.exists("/proc/partitions"):
            finder.ask_proc_partitions()
        else:
            with pytest.raises(FileNotFoundError):
                finder.ask_proc_partitions()
        if os.path.exists(f"/sys/dev/block/{self.major}:{self.minor}/uevent"):
            finder.ask_sys_dev_block()
        else:
            with pytest.raises(FileNotFoundError):
                finder.ask_sys_dev_block()
        finder.ask_sys_class_block()

    @skipif(not ROOTFS_ON_BLOCK_DEV, reason="/ is not on a block device")
    def test_comparisons(self):
        finder = RootFsDeviceFinder()
        assert finder.find() is not None

        a = b = c = None
        if os.path.exists("/proc/partitions"):
            a = finder.ask_proc_partitions()
        if os.path.exists(f"/sys/dev/block/{self.major}:{self.minor}/uevent"):
            b = finder.ask_sys_dev_block()
        c = finder.ask_sys_class_block()

        assert {x for x in (a, b, c) if x} == {finder.find()}

    def test_find_fallbacks(self):
        finder = RootFsDeviceFinder()
        finder.major = 8
        finder.minor = 1
        files = {
            "/proc/partitions": FileNotFoundError,
            "/sys/dev/block/8:1/uevent": "MAJOR=8\nDEVNAME=sdb1\n",
            "/sys/class/block/sda/dev": "8:0\n",
            "/sys/class/block/sda1/dev": "8:1\n",
        }
        dev_files = ["/sys/class/block/sda/dev", "/sys/class/block/sda1/dev"]
        with mock.patch("os.path.exists", return_value=True):
            with mock.patch("glob.iglob", return_value=dev_files):
                with mock_open_content(files):
                    assert finder.find() == "/dev/sdb1"
                files["/sys/dev/block/8:1/uevent"] = FileNotFoundError
                with mock_open_content(files):
                    assert finder.find() == "/dev/sda1"

    @requires_cli("findmnt")
    @skipif(not ROOTFS_ON_BLOCK_DEV, reason="/ is not on a block device")
    def test_against_findmnt(self):
        psutil_value = RootFsDeviceFinder().find()
        findmnt_value = sh("findmnt -o SOURCE -rn /")
        # findmnt prints the friendly alias (e.g. /dev/mapper/vg-root),
        # psutil the kernel name it points to (e.g. /dev/dm-0).
        assert os.path.realpath(psutil_value) == os.path.realpath(
            findmnt_value
        )

    def test_disk_partitions_mocked(self):
        with mock.patch.object(
            _psutil,
            'disk_partitions',
            return_value=[('/dev/root', '/', 'ext4', 'rw')],
        ) as m:
            part = psutil.disk_partitions(all=True)[0]
            assert m.called
            assert part.device != "/dev/root"
            assert part.device == RootFsDeviceFinder().find()


# =====================================================================
# --- misc
# =====================================================================


class TestMisc(LinuxTestCase):
    def test_no_procfs_on_import(self):
        my_procfs = self.get_testfn()
        os.mkdir(my_procfs)

        with open(os.path.join(my_procfs, 'stat'), 'w') as f:
            f.write('cpu   0 0 0 0 0 0 0 0 0 0\n')
            f.write('cpu0  0 0 0 0 0 0 0 0 0 0\n')
            f.write('cpu1  0 0 0 0 0 0 0 0 0 0\n')

        try:
            with mock_open_content({"/proc*": FileNotFoundError}):
                importlib.reload(psutil)

                with pytest.raises(OSError):
                    psutil.cpu_times()
                with pytest.raises(OSError):
                    psutil.cpu_times(percpu=True)
                with pytest.raises(OSError):
                    psutil.cpu_percent()
                with pytest.raises(OSError):
                    psutil.cpu_percent(percpu=True)
                with pytest.raises(OSError):
                    psutil.cpu_times_percent()
                with pytest.raises(OSError):
                    psutil.cpu_times_percent(percpu=True)

                psutil.PROCFS_PATH = my_procfs

                assert psutil.cpu_percent() == 0
                assert sum(psutil.cpu_times_percent()) == 0

                # since we don't know the number of CPUs at import time,
                # we awkwardly say there are none until the second call
                per_cpu_percent = psutil.cpu_percent(percpu=True)
                assert sum(per_cpu_percent) == 0

                # ditto awkward length
                per_cpu_times_percent = psutil.cpu_times_percent(percpu=True)
                assert sum(map(sum, per_cpu_times_percent)) == 0

                # much user, very busy
                with open(os.path.join(my_procfs, 'stat'), 'w') as f:
                    f.write('cpu   1 0 0 0 0 0 0 0 0 0\n')
                    f.write('cpu0  1 0 0 0 0 0 0 0 0 0\n')
                    f.write('cpu1  1 0 0 0 0 0 0 0 0 0\n')

                assert psutil.cpu_percent() != 0
                assert sum(psutil.cpu_percent(percpu=True)) != 0
                assert sum(psutil.cpu_times_percent()) != 0
                assert (
                    sum(map(sum, psutil.cpu_times_percent(percpu=True))) != 0
                )
        finally:
            shutil.rmtree(my_procfs)
            importlib.reload(psutil)

        assert psutil.PROCFS_PATH == '/proc'

    def test_procfs_path(self):
        tdir = self.get_testfn()
        os.mkdir(tdir)
        try:
            psutil.PROCFS_PATH = tdir
            with pytest.raises(OSError):
                psutil.virtual_memory()
            with pytest.raises(OSError):
                psutil.cpu_times()
            with pytest.raises(OSError):
                psutil.cpu_times(percpu=True)
            with pytest.raises(OSError):
                psutil.boot_time()
            with pytest.raises(OSError):
                psutil.net_connections()
            with pytest.raises(OSError):
                psutil.net_io_counters()
            with pytest.raises(OSError):
                psutil.net_if_stats()
            with pytest.raises(OSError):
                psutil.disk_partitions()
            with pytest.raises(psutil.NoSuchProcess):
                psutil.Process()
        finally:
            psutil.PROCFS_PATH = "/proc"

    def test_pid_exists_no_proc_status(self):
        # Internally pid_exists relies on /proc/{pid}/status.
        # Emulate a case where this file is empty in which case
        # psutil is supposed to fall back on using pids().
        with mock_open_content({f"/proc/{os.getpid()}/status": ""}) as m:
            assert psutil.pid_exists(os.getpid())
            assert m.called


# =====================================================================
# --- sensors
# =====================================================================


@contextlib.contextmanager
def mock_battery(files):
    pairs = dict(files)
    pairs.setdefault("*/BAT0/energy_now", b"50000000")
    pairs.setdefault("*/BAT0/power_now", b"10000000")
    pairs.setdefault("*/BAT0/energy_full", b"60000000")
    pairs.setdefault("/sys/class/power_supply/*", FileNotFoundError)
    with mock.patch("psutil._pslinux.os.listdir", return_value=["BAT0"]):
        with mock_open_content(pairs) as m:
            yield m


class TestSensorsBattery(LinuxTestCase):
    @skipif(not HAS_BATTERY, reason="no battery")
    @requires_cli("acpi")
    @retry_on_failure
    def test_percent(self):
        out = sh("acpi -b")
        first_battery = out.split("\n")[0]
        acpi_value = int(first_battery.split(",")[1].strip().replace('%', ''))
        psutil_value = psutil.sensors_battery().percent
        assert abs(acpi_value - psutil_value) < 2

    def test_emulate_power_plugged(self):
        # Pretend the AC power cable is connected.
        with mock_battery({"*/AC0/online": b"1", "*/AC/online": b"1"}) as m:
            assert psutil.sensors_battery().power_plugged is True
            assert (
                psutil.sensors_battery().secsleft
                == psutil.POWER_TIME_UNLIMITED
            )
            assert m.called

    def test_emulate_power_plugged_2(self):
        # Same as above but pretend /AC0/online does not exist in which
        # case code relies on /status file.
        with mock_battery({
            "*/AC0/online": FileNotFoundError,
            "*/AC/online": FileNotFoundError,
            "*/status": "charging",
        }) as m:
            assert psutil.sensors_battery().power_plugged is True
            assert m.called

    def test_emulate_power_not_plugged(self):
        # Pretend the AC power cable is not connected.
        with mock_battery({"*/AC0/online": b"0", "*/AC/online": b"0"}) as m:
            assert psutil.sensors_battery().power_plugged is False
            assert m.called

    def test_emulate_power_not_plugged_2(self):
        # Same as above but pretend /AC0/online does not exist in which
        # case code relies on /status file.
        with mock_battery({
            "*/AC0/online": FileNotFoundError,
            "*/AC/online": FileNotFoundError,
            "*/status": "discharging",
        }) as m:
            assert psutil.sensors_battery().power_plugged is False
            assert m.called

    def test_emulate_power_undetermined(self):
        # Pretend we can't know whether the AC power cable not
        # connected (assert fallback to False).
        with mock_battery({
            "/sys/class/power_supply/AC0/online": FileNotFoundError,
            "/sys/class/power_supply/AC/online": FileNotFoundError,
            "/sys/class/power_supply/BAT0/status": b"???",
        }) as m:
            assert psutil.sensors_battery().power_plugged is None
            assert m.called

    def test_emulate_energy_full_0(self):
        # Emulate a case where energy_full files returns 0.
        with mock_battery(
            {"/sys/class/power_supply/BAT0/energy_full": b"0"}
        ) as m:
            assert psutil.sensors_battery().percent == 0
            assert m.called

    def test_emulate_energy_full_not_avail(self):
        # Emulate a case where energy_full file does not exist.
        # Expected fallback on /capacity.
        with mock_battery({
            "/sys/class/power_supply/BAT0/energy_full": FileNotFoundError,
            "/sys/class/power_supply/BAT0/charge_full": FileNotFoundError,
            "/sys/class/power_supply/BAT0/capacity": b"88",
        }):
            assert psutil.sensors_battery().percent == 88

    @skipif(not HAS_BATTERY, reason="no battery")
    @skipif(
        not os.path.isfile("/sys/class/power_supply/BAT0/capacity"),
        reason="BAT /capacity file don't exist",
    )
    def test_percent_against_capacity(self):
        # Internally, if we have /energy_full, the percentage will be
        # calculated by NOT reading the /capacity file, to get more
        # accuracy. Check against /capacity to make sure our percentage
        # is calculated correctly.
        with open("/sys/class/power_supply/BAT0/capacity") as f:
            capacity = float(f.read())
        assert psutil.sensors_battery().percent == pytest.approx(
            capacity, abs=1
        )

    def test_emulate_no_power(self):
        # Emulate a case where /AC0/online file nor /BAT0/status exist.
        with mock_battery({
            "/sys/class/power_supply/AC/online": FileNotFoundError,
            "/sys/class/power_supply/AC0/online": FileNotFoundError,
            "/sys/class/power_supply/BAT0/status": FileNotFoundError,
        }):
            assert psutil.sensors_battery().power_plugged is None

    def test_fully_emulated(self):
        files = {
            "*/energy_now": "60000000",
            "*/power_now": "0",
            "*/energy_full": "60000001",
        }
        with mock.patch('os.listdir', return_value=["BAT0"]) as mlistdir:
            with mock_open_content(files) as mopen:
                assert psutil.sensors_battery() is not None
        assert mlistdir.called
        assert mopen.called


class TestSensorsTemperatures(LinuxTestCase):
    def test_emulate_class_hwmon(self):
        with mock_open_content({
            "*/name": "name",
            "*/temp1_label": "label",
            "*/temp1_input": b"30000",
            "*/temp1_max": b"40000",
            "*/temp1_crit": b"50000",
        }):
            # Test case with /sys/class/hwmon
            with mock.patch(
                'glob.glob', return_value=['/sys/class/hwmon/hwmon0/temp1']
            ):
                temp = psutil.sensors_temperatures()['name'][0]
                assert temp.label == 'label'
                assert temp.current == 30.0
                assert temp.high == 40.0
                assert temp.critical == 50.0

    def test_emulate_class_thermal(self):
        files = {
            "*0_temp": b"50000",
            "*temp": b"30000",
            "*0_type": "critical",
            "*type": "name",
        }

        def glob_mock(path):
            if path in {
                '/sys/class/hwmon/hwmon*/temp*_*',
                '/sys/class/hwmon/hwmon*/device/temp*_*',
            }:
                return []
            elif path == '/sys/class/thermal/thermal_zone*':
                return ['/sys/class/thermal/thermal_zone0']
            elif path == '/sys/class/thermal/thermal_zone0/trip_point*':
                return [
                    '/sys/class/thermal/thermal_zone1/trip_point_0_type',
                    '/sys/class/thermal/thermal_zone1/trip_point_0_temp',
                ]
            return []

        with mock_open_content(files):
            with mock.patch('glob.glob', create=True, side_effect=glob_mock):
                temp = psutil.sensors_temperatures()['name'][0]
                assert temp.label == ''
                assert temp.current == 30.0
                assert temp.high == 50.0
                assert temp.critical == 50.0


class TestSensorsFans(LinuxTestCase):
    def test_emulate_data(self):
        with mock_open_content({
            "*/name": "name",
            "*/fan1_label": "label",
            "*/fan1_input": "2000",
        }):
            with mock.patch(
                'glob.glob', return_value=['/sys/class/hwmon/hwmon2/fan1']
            ):
                fan = psutil.sensors_fans()['name'][0]
                assert fan.label == 'label'
                assert fan.current == 2000


# =====================================================================
# --- other system APIs
# =====================================================================


class TestOtherSystemAPIs(LinuxTestCase):
    def test_boot_time(self):
        vmstat_value = vmstat('boot time')
        psutil_value = psutil.boot_time()
        assert int(vmstat_value) == int(psutil_value)

    def test_boot_time_mocked(self):
        with mock.patch('psutil._common.open', create=True) as m:
            with pytest.raises(RuntimeError):
                psutil._pslinux.boot_time()
            assert m.called

    def test_users(self):
        # Make sure the C extension converts ':0' and ':0.0' to
        # 'localhost'.
        for user in psutil.users():
            assert user.host not in {":0", ":0.0"}


# =====================================================================
# --- test process
# =====================================================================


class TestProcessIdentity(LinuxTestCase):
    def test_terminal_mocked(self):
        with mock.patch(
            'psutil._pslinux._psposix._get_terminal_map', return_value={}
        ):
            assert psutil._pslinux.Process(os.getpid()).terminal() is None

    def check_cmdline(self, content, expected):
        path = f"/proc/{os.getpid()}/cmdline"
        with mock_open_content({path: content.encode()}):
            assert psutil.Process().cmdline() == expected

    def test_cmdline_mocked(self):
        # see: https://github.com/giampaolo/psutil/issues/639
        self.check_cmdline('foo\x00bar\x00', ['foo', 'bar'])
        self.check_cmdline('foo\x00bar\x00\x00', ['foo', 'bar', ''])

    def test_cmdline_spaces_mocked(self):
        # see: https://github.com/giampaolo/psutil/issues/1179
        self.check_cmdline('foo bar ', ['foo', 'bar'])
        self.check_cmdline('foo bar  ', ['foo', 'bar', ''])

    def test_cmdline_mixed_separators(self):
        # https://github.com/giampaolo/psutil/issues/1179#issuecomment-552984549
        self.check_cmdline('foo\x20bar\x00', ['foo', 'bar'])

    def test_cmdline_environ_carriage_return(self):
        cmd = [PYTHON_EXE, "-c", PYTHON_SLEEP_CODE, "a\rb", "c\r\nd"]
        env = PYTHON_EXE_ENV.copy()
        env["PSUTIL_TEST_ENVIRON"] = "e\rf"
        p = self.spawn_psproc(cmd, env=env)
        assert p.cmdline() == cmd
        assert p.environ()["PSUTIL_TEST_ENVIRON"] == "e\rf"

    def test_readlink_path_deleted_mocked(self):
        with mock.patch(
            'psutil._pslinux.os.readlink', return_value='/home/foo (deleted)'
        ):
            assert psutil.Process().exe() == "/home/foo"
            assert psutil.Process().cwd() == "/home/foo"

    def test_exe_mocked(self):
        with mock.patch(
            'psutil._pslinux.readlink', side_effect=FileNotFoundError
        ) as m:
            with mock.patch(
                'psutil._pslinux.Process.cmdline', return_value=[]
            ):
                ret = psutil.Process().exe()
                assert m.called
                assert ret == ""

    def test_cwd_mocked(self):
        # https://github.com/giampaolo/psutil/issues/2514
        with mock.patch(
            'psutil._pslinux.readlink', side_effect=FileNotFoundError
        ) as m:
            ret = psutil.Process().cwd()
            assert m.called
            assert ret == ""

    def test_create_time_monotonic(self):
        p = psutil.Process()
        assert p._proc.create_time() != p._proc.create_time(monotonic=True)
        assert p._get_ident()[1] == p._proc.create_time(monotonic=True)


class TestProcessCpu(LinuxTestCase):
    def test_ioprio_pid_0(self):
        ioclass, value = _psutil.proc_ioprio_get(os.getpid())
        with pytest.raises(PermissionError):
            _psutil.proc_ioprio_get(0)
        with pytest.raises(PermissionError):
            _psutil.proc_ioprio_set(0, ioclass, value)
        assert _psutil.proc_ioprio_get(os.getpid()) == (ioclass, value)

    def test_rlimit_zombie(self):
        # Emulate a case where rlimit() raises ENOSYS, which may
        # happen in case of zombie process:
        # https://travis-ci.org/giampaolo/psutil/jobs/51368273
        with mock.patch(
            "resource.prlimit", side_effect=OSError(errno.ENOSYS, "")
        ) as m1:
            with mock.patch(
                "psutil._pslinux.Process._is_zombie", return_value=True
            ) as m2:
                p = psutil.Process()
                p.name()
                with pytest.raises(psutil.ZombieProcess) as cm:
                    p.rlimit(psutil.RLIMIT_NOFILE)
        assert m1.called
        assert m2.called
        assert cm.value.pid == p.pid
        assert cm.value.name == p.name()

    def test_rlimit_infinity_normalized(self):
        # Python 3.15 changed resource.prlimit() to return RLIM_INFINITY
        # as the unsigned 2**64-1 instead of -1; psutil maps it back.
        unsigned = 2**64 - 1
        p = psutil.Process()
        with mock.patch(
            "psutil._pslinux.resource.prlimit",
            return_value=(unsigned, unsigned),
        ) as m:
            soft, hard = p.rlimit(psutil.RLIMIT_FSIZE)
            assert m.called
        assert soft == psutil.RLIM_INFINITY
        assert hard == psutil.RLIM_INFINITY


class TestProcessMemory(LinuxTestCase):
    @retry_on_failure
    def test_parse_smaps_vs_memory_maps(self):
        sproc = self.spawn_subproc()
        uss, pss, swap, shared = psutil._pslinux.Process(
            sproc.pid
        )._parse_smaps()
        maps = psutil.Process(sproc.pid).memory_maps(grouped=False)
        assert (
            abs(uss - sum(x.private_dirty + x.private_clean for x in maps))
            < 4096
        )
        assert abs(pss - sum(x.pss for x in maps)) < 4096
        assert abs(swap - sum(x.swap for x in maps)) < 4096
        assert (
            abs(shared - sum(x.shared_dirty + x.shared_clean for x in maps))
            < 4096
        )

    def test_parse_smaps_mocked(self):
        # See: https://github.com/giampaolo/psutil/issues/1222
        content = textwrap.dedent("""\
            fffff0 r-xp 00000000 00:00 0                  [vsyscall]
            Size:                  1 kB
            Rss:                   2 kB
            Pss:                   3 kB
            Shared_Clean:          4 kB
            Shared_Dirty:          5 kB
            Private_Clean:         6 kB
            Private_Dirty:         7 kB
            Referenced:            8 kB
            Anonymous:             9 kB
            LazyFree:              10 kB
            AnonHugePages:         11 kB
            ShmemPmdMapped:        12 kB
            Shared_Hugetlb:        13 kB
            Private_Hugetlb:       14 kB
            Swap:                  15 kB
            SwapPss:               16 kB
            KernelPageSize:        17 kB
            MMUPageSize:           18 kB
            Locked:                19 kB
            VmFlags: rd ex
            """).encode()
        with mock_open_content({f"/proc/{os.getpid()}/smaps": content}) as m:
            p = psutil._pslinux.Process(os.getpid())
            uss, pss, swap, shared = p._parse_smaps()
            assert m.called
            assert uss == (6 + 7 + 14) * 1024
            assert pss == 3 * 1024
            assert swap == 15 * 1024
            assert shared == (4 + 5 + 13) * 1024

    def test_issue_1014(self):
        # Emulates a case where smaps file does not exist. In this case
        # wrap_exception decorator should not raise NoSuchProcess.
        with mock_open_exception(
            f"/proc/{os.getpid()}/smaps", FileNotFoundError
        ) as m:
            p = psutil.Process()
            with pytest.raises(FileNotFoundError):
                p.memory_maps()
            assert m.called

    def test_issue_2418(self):
        p = psutil.Process()
        with mock_open_exception(
            f"/proc/{os.getpid()}/statm", FileNotFoundError
        ):
            with mock.patch("os.path.exists", return_value=False):
                with pytest.raises(psutil.NoSuchProcess):
                    p.memory_info()

    def test_memory_extras(self):
        p = psutil.Process()
        with open(f"/proc/{p.pid}/status", "rb") as f:
            data = f.read()
        with mock.patch.object(
            psutil._pslinux.Process, "_read_status_file", return_value=data
        ):
            mem = p.memory_extras()
        vmrss = int(re.search(br"VmRSS:\s+(\d+)", data).group(1)) * 1024
        assert mem.rss_anon + mem.rss_file + mem.rss_shmem == vmrss

    def test_memory_extras_locked(self):
        libc = ctypes.CDLL(None, use_errno=True)
        size = mmap.PAGESIZE * 4
        buf = mmap.mmap(-1, size)
        self.addCleanup(buf.close)
        view = ctypes.c_char.from_buffer(buf)
        addr = ctypes.addressof(view)
        del view
        base = psutil.Process().memory_extras().locked
        if libc.mlock(ctypes.c_void_p(addr), ctypes.c_size_t(size)) != 0:
            err = ctypes.get_errno()
            return pytest.skip(f"mlock() failed: {os.strerror(err)}")
        self.addCleanup(
            libc.munlock, ctypes.c_void_p(addr), ctypes.c_size_t(size)
        )
        after = psutil.Process().memory_extras().locked
        assert after - base == size

    def test_memory_footprint_shared_self_mappings(self):
        # A page mapped twice by the same process counts as shared,
        # even with no other process involved.
        size = 4 * 1024 * 1024
        path = self.get_testfn()
        with open(path, "wb") as f:
            f.write(b"\x00" * size)
        with open(path, "r+b") as f:
            m1 = mmap.mmap(f.fileno(), size)
            self.addCleanup(m1.close)
            m2 = mmap.mmap(f.fileno(), size)
            self.addCleanup(m2.close)
            base = psutil.Process().memory_footprint().shared
            for i in range(0, size, 4096):
                m1[i]
                m2[i]
            after = psutil.Process().memory_footprint().shared
        assert after - base >= size // 2

    def test_parse_smaps_rollup_mocked(self):
        data = (
            b"Rss:                 100 kB\n"
            b"Pss:                  50 kB\n"
            b"Shared_Clean:         30 kB\n"
            b"Shared_Dirty:         40 kB\n"
            b"Private_Clean:        20 kB\n"
            b"Private_Dirty:        10 kB\n"
            b"Swap:                  5 kB\n"
            b"SwapPss:               3 kB\n"
            b"Shared_Hugetlb:        2 kB\n"
            b"Private_Hugetlb:       1 kB\n"
        )
        p = psutil.Process()
        with mock.patch(
            "psutil._pslinux.open_binary", return_value=io.BytesIO(data)
        ):
            assert p._proc._parse_smaps_rollup() == (
                31 * 1024,
                50 * 1024,
                5 * 1024,
                72 * 1024,
            )


class TestProcessThreads(LinuxTestCase):
    def test_threads_mocked(self):
        # Test the case where os.listdir() returns a file (thread)
        # which no longer exists by the time we open() it (race
        # condition). threads() is supposed to ignore that instead
        # of raising NSP.
        task = f"/proc/{os.getpid()}/task*"
        with mock_open_content({task: FileNotFoundError}) as m:
            ret = psutil.Process().threads()
            assert m.called
            assert ret == []

        # ...but if it bumps into something != ENOENT we want an
        # exception.
        with mock_open_content({task: PermissionError}):
            with pytest.raises(psutil.AccessDenied):
                psutil.Process().threads()

    @retry_on_failure
    @isolated
    def test_issue_687(self):
        # In case of thread ID:
        # - pid_exists() is supposed to return False
        # - Process(tid) is supposed to work
        # - pids() should not return the TID
        # See: https://github.com/giampaolo/psutil/issues/687
        p = psutil.Process()
        nthreads = len(p.threads())
        with ThreadTask():
            threads = p.threads()
            assert len(threads) == nthreads + 1
            tid = sorted(threads, key=lambda x: x.id)[1].id
            assert p.pid != tid
            pt = psutil.Process(tid)
            pt.as_dict()
            assert not psutil.pid_exists(tid)
            assert tid not in psutil.pids()


class TestProcessFiles(LinuxTestCase):
    def test_open_files_mode(self):
        def get_test_file(fname):
            p = psutil.Process()
            giveup_at = time.monotonic() + GLOBAL_TIMEOUT
            while True:
                for file in p.open_files():
                    if file.path == os.path.abspath(fname):
                        return file
                if time.monotonic() > giveup_at:
                    raise RuntimeError("timeout looking for test file")

        testfn = self.get_testfn()
        with open(testfn, "w"):
            assert get_test_file(testfn).mode == "w"
        with open(testfn):
            assert get_test_file(testfn).mode == "r"
        with open(testfn, "a"):
            assert get_test_file(testfn).mode == "a"
        with open(testfn, "r+"):
            assert get_test_file(testfn).mode == "r+"
        with open(testfn, "w+"):
            assert get_test_file(testfn).mode == "r+"
        with open(testfn, "a+"):
            assert get_test_file(testfn).mode == "a+"

        safe_rmpath(testfn)
        with open(testfn, "x"):
            assert get_test_file(testfn).mode == "w"
        safe_rmpath(testfn)
        with open(testfn, "x+"):
            assert get_test_file(testfn).mode == "r+"

    def test_open_files_file_gone(self):
        # simulates a file which gets deleted during open_files()
        # execution
        p = psutil.Process()
        files = p.open_files()
        with open(self.get_testfn(), 'w'):
            # give the kernel some time to see the new file
            call_until(lambda: len(p.open_files()) != len(files))
            with mock.patch(
                'psutil._pslinux.os.readlink',
                side_effect=FileNotFoundError,
            ) as m:
                assert p.open_files() == []
                assert m.called
            # also simulate the case where os.readlink() returns EINVAL
            # in which case psutil is supposed to 'continue'
            with mock.patch(
                'psutil._pslinux.os.readlink',
                side_effect=OSError(errno.EINVAL, ""),
            ) as m:
                assert p.open_files() == []
                assert m.called

    def test_open_files_fd_gone(self):
        # Simulate a case where /proc/{pid}/fdinfo/{fd} disappears
        # while iterating through fds.
        # https://travis-ci.org/giampaolo/psutil/jobs/225694530
        p = psutil.Process()
        files = p.open_files()
        with open(self.get_testfn(), 'w'):
            # give the kernel some time to see the new file
            call_until(lambda: len(p.open_files()) != len(files))
            with mock.patch(
                "builtins.open", side_effect=FileNotFoundError
            ) as m:
                assert p.open_files() == []
                assert m.called

    def test_open_files_enametoolong(self):
        # Simulate a case where /proc/{pid}/fd/{fd} symlink
        # points to a file with full path longer than PATH_MAX, see:
        # https://github.com/giampaolo/psutil/issues/1940
        p = psutil.Process()
        files = p.open_files()
        with open(self.get_testfn(), 'w'):
            # give the kernel some time to see the new file
            call_until(lambda: len(p.open_files()) != len(files))
            patch_point = 'psutil._pslinux.os.readlink'
            with mock.patch(
                patch_point, side_effect=OSError(errno.ENAMETOOLONG, "")
            ) as m:
                with mock.patch("psutil._pslinux.debug"):
                    assert p.open_files() == []
                    assert m.called

    def test_net_connections_enametoolong(self):
        # Simulate a case where /proc/{pid}/fd/{fd} symlink points to
        # a file with full path longer than PATH_MAX, see:
        # https://github.com/giampaolo/psutil/issues/1940
        with mock.patch(
            'psutil._pslinux.os.readlink',
            side_effect=OSError(errno.ENAMETOOLONG, ""),
        ) as m:
            p = psutil.Process()
            with mock.patch("psutil._pslinux.debug"):
                assert p.net_connections() == []
                assert m.called


class TestProcessProcfsParsing(LinuxTestCase):
    def test_stat_file_parsing(self):
        args = [
            "0",  # pid
            "(cat)",  # name
            "Z",  # status
            "1",  # ppid
            "0",  # pgrp
            "0",  # session
            "0",  # tty
            "0",  # tpgid
            "0",  # flags
            "0",  # minflt
            "0",  # cminflt
            "0",  # majflt
            "0",  # cmajflt
            "2",  # utime
            "3",  # stime
            "4",  # cutime
            "5",  # cstime
            "0",  # priority
            "0",  # nice
            "0",  # num_threads
            "0",  # itrealvalue
            "6",  # starttime
            "0",  # vsize
            "0",  # rss
            "0",  # rsslim
            "0",  # startcode
            "0",  # endcode
            "0",  # startstack
            "0",  # kstkesp
            "0",  # kstkeip
            "0",  # signal
            "0",  # blocked
            "0",  # sigignore
            "0",  # sigcatch
            "0",  # wchan
            "0",  # nswap
            "0",  # cnswap
            "0",  # exit_signal
            "6",  # processor
            "0",  # rt priority
            "0",  # policy
            "7",  # delayacct_blkio_ticks
        ]
        content = " ".join(args).encode()
        with mock_open_content({f"/proc/{os.getpid()}/stat": content}):
            p = psutil.Process()
            assert p.name() == 'cat'
            assert p.status() == psutil.STATUS_ZOMBIE
            assert p.ppid() == 1
            assert p.create_time() == 6 / CLOCK_TICKS + psutil.boot_time()
            cpu = p.cpu_times()
            assert cpu.user == 2 / CLOCK_TICKS
            assert cpu.system == 3 / CLOCK_TICKS
            assert cpu.children_user == 4 / CLOCK_TICKS
            assert cpu.children_system == 5 / CLOCK_TICKS
            assert cpu.iowait == 7 / CLOCK_TICKS
            assert p.cpu_num() == 6

        content = " ".join(args[:-1]).encode()
        with mock_open_content({f"/proc/{os.getpid()}/stat": content}):
            cpu = psutil.Process().cpu_times()
            assert cpu.user == 2 / CLOCK_TICKS
            assert cpu.iowait == 0

    def test_status_file_parsing(self):
        content = textwrap.dedent("""\
            Uid:\t1000\t1001\t1002\t1003
            Gid:\t1004\t1005\t1006\t1007
            Threads:\t66
            Cpus_allowed:\tf
            Cpus_allowed_list:\t0-7
            voluntary_ctxt_switches:\t12
            nonvoluntary_ctxt_switches:\t13""").encode()
        with mock_open_content({f"/proc/{os.getpid()}/status": content}):
            p = psutil.Process()
            assert p.num_ctx_switches().voluntary == 12
            assert p.num_ctx_switches().involuntary == 13
            assert p.num_threads() == 66
            uids = p.uids()
            assert uids.real == 1000
            assert uids.effective == 1001
            assert uids.saved == 1002
            gids = p.gids()
            assert gids.real == 1004
            assert gids.effective == 1005
            assert gids.saved == 1006
            assert p._proc._get_eligible_cpus() == list(range(8))

    def test_status_file_cpus_allowed_list(self):
        content = b"Cpus_allowed_list:\t0-3,8\n"
        with mock_open_content({f"/proc/{os.getpid()}/status": content}):
            p = psutil.Process()
            assert p._proc._get_eligible_cpus() == [0, 1, 2, 3, 8]


class TestProcessAgainstStatus(LinuxTestCase):
    """/proc/pid/stat and /proc/pid/status have many values in common.
    Whenever possible, psutil uses /proc/pid/stat (it's faster).
    For all those cases we check that the value found in
    /proc/pid/stat (by psutil) matches the one found in
    /proc/pid/status.
    """

    @classmethod
    def setUpClass(cls):
        cls.proc = psutil.Process()

    def read_status_file(self, linestart):
        with psutil._psplatform.open_text(
            f"/proc/{self.proc.pid}/status"
        ) as f:
            for line in f:
                line = line.strip()
                if line.startswith(linestart):
                    value = line.partition('\t')[2]
                    try:
                        return int(value)
                    except ValueError:
                        return value
            raise ValueError(f"can't find {linestart!r}")

    def test_name(self):
        value = self.read_status_file("Name:")
        assert self.proc.name() == value

    def test_status(self):
        value = self.read_status_file("State:")
        value = value[value.find('(') + 1 : value.rfind(')')]
        value = value.replace(' ', '-')
        assert self.proc.status() == value

    def test_ppid(self):
        value = self.read_status_file("PPid:")
        assert self.proc.ppid() == value

    def test_num_threads(self):
        value = self.read_status_file("Threads:")
        assert self.proc.num_threads() == value

    def test_uids(self):
        value = self.read_status_file("Uid:")
        value = tuple(map(int, value.split()[1:4]))
        assert self.proc.uids() == value

    def test_gids(self):
        value = self.read_status_file("Gid:")
        value = tuple(map(int, value.split()[1:4]))
        assert self.proc.gids() == value

    @retry_on_failure
    def test_num_ctx_switches(self):
        value = self.read_status_file("voluntary_ctxt_switches:")
        assert self.proc.num_ctx_switches().voluntary == value
        value = self.read_status_file("nonvoluntary_ctxt_switches:")
        assert self.proc.num_ctx_switches().involuntary == value

    def test_cpu_affinity(self):
        value = self.read_status_file("Cpus_allowed_list:")
        # The mask covers the possible CPUs, while sched_getaffinity
        # only reports the online ones.
        with open("/sys/devices/system/cpu/online") as f:
            online = _parse_cpulist(f.read())
        expected = [x for x in _parse_cpulist(str(value)) if x in online]
        assert self.proc.cpu_affinity() == expected

    def test_cpu_affinity_eligible_cpus(self):
        value = self.read_status_file("Cpus_allowed_list:")
        with mock.patch("psutil._pslinux.per_cpu_times") as m:
            cpus = self.proc._proc._get_eligible_cpus()
        assert cpus == _parse_cpulist(str(value))
        assert not m.called


# =====================================================================
# --- test utils
# =====================================================================


class TestUtils(LinuxTestCase):
    def test_readlink(self):
        with mock.patch("os.readlink", return_value="foo (deleted)") as m:
            assert psutil._psplatform.readlink("bar") == "foo"
            assert m.called
