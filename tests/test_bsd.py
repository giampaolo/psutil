#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# TODO: (FreeBSD) add test for comparing connections with 'sockstat' cmd.


"""Tests specific to all BSD platforms."""

import datetime
import os
import re
import time
from unittest import mock

import psutil
from psutil import BSD
from psutil import FREEBSD
from psutil import NETBSD
from psutil import OPENBSD
from psutil import _psutil

from . import HAS_BATTERY
from . import TOLERANCE_SYS_MEM
from . import PsutilTestCase
from . import isolated
from . import pytest
from . import requires_cli
from . import retry_on_failure
from . import sh
from . import skipif
from . import spawn_subproc
from . import terminate

PAGESIZE = _psutil.getpagesize() if BSD else None


def sysctl(cmdline):
    """Expects a sysctl command with an argument and parse the result
    returning only the value of interest.
    """
    result = sh("sysctl " + cmdline)
    if FREEBSD:
        result = result[result.find(": ") + 2 :]
    elif OPENBSD or NETBSD:
        result = result[result.find("=") + 1 :]
    try:
        return int(result)
    except ValueError:
        return result


# =====================================================================
# --- All BSD*
# =====================================================================


@skipif(not BSD, reason="BSD only")
class TestSystemAPIs(PsutilTestCase):
    """System tests common to all BSD variants."""

    def test_disks(self):
        # test psutil.disk_usage() and psutil.disk_partitions()
        # against "df -a"
        def df(path):
            out = sh(f'df -k "{path}"').strip()
            lines = out.split('\n')
            lines.pop(0)
            line = lines.pop(0)
            dev, total, used, free = line.split()[:4]
            if dev == 'none':
                dev = ''
            total = int(total) * 1024
            used = int(used) * 1024
            free = int(free) * 1024
            return dev, total, used, free

        for part in psutil.disk_partitions(all=False):
            usage = psutil.disk_usage(part.mountpoint)
            dev, total, used, free = df(part.mountpoint)
            assert part.device == dev
            assert usage.total == total
            # 10 MB tolerance
            if abs(usage.free - free) > 10 * 1024 * 1024:
                return pytest.fail(f"psutil={usage.free}, df={free}")
            if abs(usage.used - used) > 10 * 1024 * 1024:
                return pytest.fail(f"psutil={usage.used}, df={used}")

    @requires_cli("sysctl")
    def test_cpu_count_logical(self):
        syst = sysctl("hw.ncpu")
        assert psutil.cpu_count(logical=True) == syst

    # On NetBSD total is UVM's managed pages, which is less than
    # physical RAM. NetBSDTestCase.test_vmem_total covers it instead.
    @requires_cli("sysctl")
    @skipif(NETBSD, reason="hw.physmem is not what psutil reports")
    def test_virtual_memory_total(self):
        num = sysctl('hw.physmem')
        assert num == psutil.virtual_memory().total

    @requires_cli("ifconfig")
    def test_net_if_stats(self):
        for name, stats in psutil.net_if_stats().items():
            try:
                out = sh(f"ifconfig {name}")
            except RuntimeError:
                pass
            else:
                assert stats.isup == ('RUNNING' in out)
                if "mtu" in out:
                    assert stats.mtu == int(re.findall(r'mtu (\d+)', out)[0])


@skipif(not BSD, reason="BSD only")
class TestProcessAPIs(PsutilTestCase):

    @classmethod
    def setUpClass(cls):
        cls.pid = spawn_subproc().pid

    @classmethod
    def tearDownClass(cls):
        terminate(cls.pid)

    @skipif(NETBSD, reason="-o lstart doesn't work on NETBSD")
    def test_create_time(self):
        output = sh(f"ps -o lstart -p {self.pid}")
        start_ps = output.replace('STARTED', '').strip()
        start_psutil = psutil.Process(self.pid).create_time()
        start_psutil = time.strftime(
            "%a %b %e %H:%M:%S %Y", time.localtime(start_psutil)
        )
        assert start_ps == start_psutil

    def test_environ_zombie(self):
        _parent, zombie = self.spawn_zombie()
        with pytest.raises(psutil.ZombieProcess):
            zombie.environ()


@skipif(not BSD, reason="BSD only")
class TestVmstat(PsutilTestCase):

    @staticmethod
    def vmstat(labels):
        out = sh(["vmstat", "-s"], env={"LANG": "C.UTF-8"})
        for line in out.split("\n"):
            line = line.strip()
            num, _, what = line.partition(" ")
            for label in labels:
                if label == what:
                    return int(num)
        return pytest.skip(f"can't find {labels} in vmstat output")

    # --- virtual_memory()

    def test_vmem_free(self):
        vmstat_value = self.vmstat(['pages free']) * PAGESIZE
        psutil_value = psutil.virtual_memory().free
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_vmem_active(self):
        vmstat_value = self.vmstat(['pages active']) * PAGESIZE
        psutil_value = psutil.virtual_memory().active
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_vmem_inactive(self):
        vmstat_value = self.vmstat(['pages inactive']) * PAGESIZE
        psutil_value = psutil.virtual_memory().inactive
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_vmem_cached(self):
        # NetBSD / OpenBSD
        vmstat_value = (
            self.vmstat(['cached file pages'])
            + self.vmstat(['cached executable pages'])
        ) * PAGESIZE
        psutil_value = psutil.virtual_memory().cached
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_vmem_wired(self):
        vmstat_value = (
            self.vmstat(['pages wired', 'pages wired down']) * PAGESIZE
        )
        psutil_value = psutil.virtual_memory().wired
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    @skipif(not (OPENBSD or NETBSD), reason="NETBSD / OPENBSD only")
    def test_vmem_shared(self):
        out = sh("vmstat -t")
        if "vm-sh" not in out:
            return pytest.skip("can't find 'vm-sh' in vmstat output")
        lines = out.splitlines()
        headers = lines[1].split()
        values = lines[2].split()
        row = dict(zip(headers, values))
        expected = int(row["vm-sh"]) * PAGESIZE
        assert (
            abs(psutil.virtual_memory().shared - expected) < TOLERANCE_SYS_MEM
        )

    # --- swap_memory()

    def test_swap_total(self):
        vmstat_value = self.vmstat(['swap pages']) * PAGESIZE
        psutil_value = psutil.swap_memory().total
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_swap_used(self):
        vmstat_value = self.vmstat(['swap pages in use']) * PAGESIZE
        psutil_value = psutil.swap_memory().used
        assert abs(vmstat_value - psutil_value) < TOLERANCE_SYS_MEM

    def test_swap_sin(self):
        vmstat_value = self.vmstat(['pages swapped in']) * PAGESIZE
        psutil_value = psutil.swap_memory().sin
        assert abs(vmstat_value - psutil_value) < 1024

    def test_swap_sout(self):
        vmstat_value = self.vmstat(['pages swapped oud']) * PAGESIZE
        psutil_value = psutil.swap_memory().sout
        assert abs(vmstat_value - psutil_value) < 1024

    # --- cpu_stats()

    @isolated
    @retry_on_failure
    def test_cpu_stats_interrupts(self):
        vmstat_value = self.vmstat(['device interrupts', 'interrupts'])
        psutil_value = psutil.cpu_stats().interrupts
        assert abs(vmstat_value - psutil_value) <= 100

    @isolated
    @retry_on_failure
    def test_cpu_stats_soft_interrupts(self):
        vmstat_value = self.vmstat(['software interrupts'])
        psutil_value = psutil.cpu_stats().soft_interrupts
        assert abs(vmstat_value - psutil_value) <= 100

    @isolated
    @retry_on_failure
    def test_cpu_stats_syscalls(self):
        vmstat_value = self.vmstat(['system calls', 'syscalls'])
        psutil_value = psutil.cpu_stats().syscalls
        assert abs(vmstat_value - psutil_value) <= 100

    @isolated
    @retry_on_failure
    def test_cpu_stats_ctx_switches(self):
        vmstat_value = self.vmstat(['cpu context switches'])
        psutil_value = psutil.cpu_stats().ctx_switches
        assert abs(vmstat_value - psutil_value) <= 100


# =====================================================================
# --- FreeBSD
# =====================================================================


@skipif(not FREEBSD, reason="FREEBSD only")
class FreeBSDProcessTestCase(PsutilTestCase):
    @classmethod
    def setUpClass(cls):
        cls.pid = spawn_subproc().pid

    @classmethod
    def tearDownClass(cls):
        terminate(cls.pid)

    @retry_on_failure
    def test_memory_maps(self):
        out = sh(f"procstat -v {self.pid}")
        maps = psutil.Process(self.pid).memory_maps(grouped=False)
        lines = out.split('\n')[1:]
        while lines:
            line = lines.pop()
            fields = line.split()
            _, start, stop, _perms, res = fields[:5]
            map = maps.pop()
            assert f"{start}-{stop}" == map.addr
            assert int(res) * PAGESIZE == map.rss
            if not map.path.startswith('['):
                assert fields[10] == map.path

    def test_exe(self):
        out = sh(f"procstat -b {self.pid}")
        assert psutil.Process(self.pid).exe() == out.split('\n')[1].split()[-1]

    def test_cmdline(self):
        out = sh(f"procstat -c {self.pid}")
        assert ' '.join(psutil.Process(self.pid).cmdline()) == ' '.join(
            out.split('\n')[1].split()[2:]
        )

    def test_uids_gids(self):
        out = sh(f"procstat -s {self.pid}")
        euid, ruid, suid, egid, rgid, sgid = out.split('\n')[1].split()[2:8]
        p = psutil.Process(self.pid)
        uids = p.uids()
        gids = p.gids()
        assert uids.real == int(ruid)
        assert uids.effective == int(euid)
        assert uids.saved == int(suid)
        assert gids.real == int(rgid)
        assert gids.effective == int(egid)
        assert gids.saved == int(sgid)

    @retry_on_failure
    def test_ctx_switches(self):
        tested = []
        out = sh(f"procstat -r {self.pid}")
        p = psutil.Process(self.pid)
        for line in out.split('\n'):
            line = line.lower().strip()
            if ' voluntary context' in line:
                pstat_value = int(line.split()[-1])
                psutil_value = p.num_ctx_switches().voluntary
                assert pstat_value == psutil_value
                tested.append(None)
            elif ' involuntary context' in line:
                pstat_value = int(line.split()[-1])
                psutil_value = p.num_ctx_switches().involuntary
                assert pstat_value == psutil_value
                tested.append(None)
        if len(tested) != 2:
            raise RuntimeError("couldn't find lines match in procstat out")

    @retry_on_failure
    def test_cpu_times(self):
        tested = []
        out = sh(f"procstat -r {self.pid}")
        p = psutil.Process(self.pid)
        for line in out.split('\n'):
            line = line.lower().strip()
            if 'user time' in line:
                pstat_value = float('0.' + line.split()[-1].split('.')[-1])
                psutil_value = p.cpu_times().user
                assert pstat_value == psutil_value
                tested.append(None)
            elif 'system time' in line:
                pstat_value = float('0.' + line.split()[-1].split('.')[-1])
                psutil_value = p.cpu_times().system
                assert pstat_value == psutil_value
                tested.append(None)
        if len(tested) != 2:
            raise RuntimeError("couldn't find lines match in procstat out")


@skipif(not FREEBSD, reason="FREEBSD only")
class FreeBSDSystemTestCase(PsutilTestCase):
    @staticmethod
    def parse_swapinfo():
        # the last line is always the total
        output = sh("swapinfo -k").splitlines()[-1]
        parts = re.split(r'\s+', output)

        if not parts:
            raise ValueError(f"Can't parse swapinfo: {output}")

        # the size is in 1k units, so multiply by 1024
        total, used, free = (int(p) * 1024 for p in parts[1:4])
        return total, used, free

    # --- virtual_memory(); tests against sysctl

    @retry_on_failure
    def test_vmem_active(self):
        syst = sysctl("vm.stats.vm.v_active_count") * PAGESIZE
        assert abs(psutil.virtual_memory().active - syst) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_vmem_inactive(self):
        syst = sysctl("vm.stats.vm.v_inactive_count") * PAGESIZE
        assert abs(psutil.virtual_memory().inactive - syst) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_vmem_wired(self):
        syst = sysctl("vm.stats.vm.v_wire_count") * PAGESIZE
        assert abs(psutil.virtual_memory().wired - syst) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_vmem_cached(self):
        syst = sysctl("vm.stats.vm.v_cache_count") * PAGESIZE
        assert abs(psutil.virtual_memory().cached - syst) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_vmem_free(self):
        syst = sysctl("vm.stats.vm.v_free_count") * PAGESIZE
        assert abs(psutil.virtual_memory().free - syst) < TOLERANCE_SYS_MEM

    @retry_on_failure
    def test_vmem_buffers(self):
        syst = sysctl("vfs.bufspace")
        assert abs(psutil.virtual_memory().buffers - syst) < TOLERANCE_SYS_MEM

    # --- swap memory

    # --- net

    # --- others

    def test_boot_time(self):
        s = sysctl('sysctl kern.boottime')
        s = s[s.find(" sec = ") + 7 :]
        s = s[: s.find(',')]
        btime = int(s)
        assert btime == psutil.boot_time()

    # --- sensors_battery

    # --- sensors_temperatures


# =====================================================================
# --- OpenBSD
# =====================================================================


@skipif(not OPENBSD, reason="OPENBSD only")
class OpenBSDSystemTestCase(PsutilTestCase):
    def test_boot_time(self):
        s = sysctl('kern.boottime')
        sys_bt = datetime.datetime.strptime(s, "%a %b %d %H:%M:%S %Y")
        psutil_bt = datetime.datetime.fromtimestamp(psutil.boot_time())
        assert sys_bt == psutil_bt


# =====================================================================
# --- NetBSD
# =====================================================================


@skipif(not NETBSD, reason="NETBSD only")
class NetBSDTestCase(PsutilTestCase):
    def test_pid_0(self):
        p = psutil.Process(0)
        assert p.num_fds() == 0
        assert p.open_files() == []

    @staticmethod
    def parse_vmstat(look_for):
        """Parse a cumulative field from 'vmstat -s' output.
        Lines are formatted as: '<value> <description>'
        Mirrors the same uvmexp_sysctl fields that psutil reads via
        sysctl(CTL_VM, VM_UVMEXP2) in C, without requiring procfs.
        """
        out = sh("vmstat -s")
        for line in out.splitlines():
            line = line.strip()
            if look_for in line:
                return int(line.split()[0])
        raise ValueError(f"can't find {look_for!r} in vmstat -s output")

    # --- virtual mem

    def test_vmem_total(self):
        num = self.parse_vmstat("pages managed")
        assert num * PAGESIZE == psutil.virtual_memory().total

    @retry_on_failure
    def test_vmem_buffers(self):
        # uv.filepages: file-backed pages excluding executable mappings
        assert (
            abs(
                psutil.virtual_memory().buffers
                - self.parse_vmstat("cached file pages") * PAGESIZE
            )
            < TOLERANCE_SYS_MEM
        )

    # --- swap mem

    @retry_on_failure
    def test_swapmem_total(self):
        assert (
            abs(
                psutil.swap_memory().total
                - self.parse_vmstat("swap pages") * PAGESIZE
            )
            < TOLERANCE_SYS_MEM
        )
