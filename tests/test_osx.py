#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""macOS specific tests."""

import re
import time

import psutil
from psutil import MACOS

from . import AARCH64
from . import CI_TESTING
from . import HAS_BATTERY
from . import HAS_CPU_FREQ
from . import TOLERANCE_DISK_USAGE
from . import TOLERANCE_SYS_MEM
from . import PsutilTestCase
from . import pytest
from . import retry_on_failure
from . import sh
from . import spawn_subproc
from . import terminate


def sysctl(cmdline):
    """Expects a sysctl command with an argument and parse the result
    returning only the value of interest.
    """
    out = sh(cmdline)
    result = out.split()[1]
    try:
        return int(result)
    except ValueError:
        return result


def vm_stat(field):
    """Wrapper around 'vm_stat' cmdline utility."""
    out = sh('vm_stat')
    for line in out.split('\n'):
        if field in line:
            break
    else:
        raise ValueError("line not found")
    return (
        int(re.search(r'\d+', line).group(0))
        * psutil._psplatform.cext.getpagesize()
    )


@pytest.mark.skipif(not MACOS, reason="MACOS only")
class MacosTestCase(PsutilTestCase):
    pass


# =====================================================================
# --- Process APIs (most are tested in test_posix.py)
# =====================================================================


class TestProcess(MacosTestCase):

    @classmethod
    def setUpClass(cls):
        cls.pid = spawn_subproc().pid

    @classmethod
    def tearDownClass(cls):
        terminate(cls.pid)

    def test_create_time(self):
        output = sh(f"ps -o lstart -p {self.pid}")
        start_ps = output.replace('STARTED', '').strip()
        hhmmss = start_ps.split(' ')[-2]
        year = start_ps.split(' ')[-1]
        start_psutil = psutil.Process(self.pid).create_time()
        assert hhmmss == time.strftime(
            "%H:%M:%S", time.localtime(start_psutil)
        )
        assert year == time.strftime("%Y", time.localtime(start_psutil))


# =====================================================================
# --- Test system APIs
# =====================================================================


class TestVirtualMemory(MacosTestCase):

    def test_total(self):
        sysctl_hwphymem = sysctl('sysctl hw.memsize')
        assert sysctl_hwphymem == psutil.virtual_memory().total

    @pytest.mark.skipif(
        CI_TESTING and MACOS and AARCH64,
        reason="skipped on MACOS + ARM64 + CI_TESTING",
    )
    @retry_on_failure()
    def test_free(self):
        vmstat_val = vm_stat("free")
        psutil_val = psutil.virtual_memory().free
        assert abs(psutil_val - vmstat_val) < TOLERANCE_SYS_MEM

    @pytest.mark.skipif(
        CI_TESTING and MACOS and AARCH64,
        reason="skipped on MACOS + ARM64 + CI_TESTING",
    )
    @retry_on_failure()
    def test_active(self):
        vmstat_val = vm_stat("active")
        psutil_val = psutil.virtual_memory().active
        assert abs(psutil_val - vmstat_val) < TOLERANCE_SYS_MEM

    # XXX: fails too often
    @pytest.mark.skipif(CI_TESTING, reason="skipped on CI_TESTING")
    @retry_on_failure()
    def test_inactive(self):
        vmstat_val = vm_stat("inactive")
        psutil_val = psutil.virtual_memory().inactive
        assert abs(psutil_val - vmstat_val) < TOLERANCE_SYS_MEM

    @retry_on_failure()
    def test_wired(self):
        vmstat_val = vm_stat("wired")
        psutil_val = psutil.virtual_memory().wired
        assert abs(psutil_val - vmstat_val) < TOLERANCE_SYS_MEM


class TestSwapMemory(MacosTestCase):

    @staticmethod
    def parse_swapusage(out):
        # Parse 'sysctl vm.swapusage' output into bytes.
        # E.g. 'total = 2.00G' -> 2147483648.
        units = {"K": 1024, "M": 1024**2, "G": 1024**3}
        ret = {}
        for key in ("total", "used", "free"):
            m = re.search(rf"{key}\s*=\s*([0-9.]+)([KMG])", out)
            ret[key] = int(float(m.group(1)) * units[m.group(2)])
        return ret

    def test_total(self):
        out = sh("sysctl vm.swapusage")
        sysctl_val = self.parse_swapusage(out)["total"]
        # 0.01M display precision = ~10KB rounding
        assert abs(psutil.swap_memory().total - sysctl_val) < 100 * 1024

    @retry_on_failure()
    def test_used(self):
        out = sh("sysctl vm.swapusage")
        sysctl_val = self.parse_swapusage(out)["used"]
        assert abs(psutil.swap_memory().used - sysctl_val) < TOLERANCE_SYS_MEM

    @retry_on_failure()
    def test_free(self):
        out = sh("sysctl vm.swapusage")
        sysctl_val = self.parse_swapusage(out)["free"]
        assert abs(psutil.swap_memory().free - sysctl_val) < TOLERANCE_SYS_MEM

    @retry_on_failure()
    def test_sin(self):
        vmstat_val = vm_stat("Pageins")
        psutil_val = psutil.swap_memory().sin
        assert abs(psutil_val - vmstat_val) < TOLERANCE_SYS_MEM

    @retry_on_failure()
    def test_sout(self):
        vmstat_val = vm_stat("Pageout")
        psutil_val = psutil.swap_memory().sout
        assert abs(psutil_val - vmstat_val) < TOLERANCE_SYS_MEM


class TestCpuAPIs(MacosTestCase):

    def test_cpu_count_logical(self):
        num = sysctl("sysctl hw.logicalcpu")
        assert num == psutil.cpu_count(logical=True)

    def test_cpu_count_cores(self):
        num = sysctl("sysctl hw.physicalcpu")
        assert num == psutil.cpu_count(logical=False)

    @pytest.mark.skipif(
        MACOS and AARCH64 and not HAS_CPU_FREQ,
        reason="not available on MACOS + AARCH64",
    )
    def test_cpu_freq(self):
        freq = psutil.cpu_freq()
        assert freq.current * 1000 * 1000 == sysctl("sysctl hw.cpufrequency")
        assert freq.min * 1000 * 1000 == sysctl("sysctl hw.cpufrequency_min")
        assert freq.max * 1000 * 1000 == sysctl("sysctl hw.cpufrequency_max")


class TestDiskAPIs(MacosTestCase):

    @retry_on_failure()
    def test_disk_partitions(self):
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
            assert abs(usage.free - free) < TOLERANCE_DISK_USAGE
            assert abs(usage.used - used) < TOLERANCE_DISK_USAGE


class TestNetAPIs(MacosTestCase):

    def test_net_if_stats(self):
        for name, stats in psutil.net_if_stats().items():
            try:
                out = sh(f"ifconfig {name}")
            except RuntimeError:
                pass
            else:
                assert stats.isup == ('RUNNING' in out), out
                assert stats.mtu == int(re.findall(r'mtu (\d+)', out)[0])

    @retry_on_failure()
    def test_net_io_counters(self):
        out = sh("netstat -ib")
        netstat = {}
        for line in out.splitlines():
            fields = line.split()
            if len(fields) < 10 or "<Link#" not in fields[2]:
                continue
            name = fields[0].rstrip("*")
            if len(fields) == 11:
                ibytes, obytes = int(fields[6]), int(fields[9])
            else:
                ibytes, obytes = int(fields[5]), int(fields[8])
            netstat[name] = (ibytes, obytes)
        ps = psutil.net_io_counters(pernic=True)
        tolerance = 1 * 1024 * 1024  # 1 MB
        for name, (ibytes, obytes) in netstat.items():
            if name not in ps:
                continue
            assert abs(ps[name].bytes_recv - ibytes) < tolerance
            assert abs(ps[name].bytes_sent - obytes) < tolerance


class TestSensorsAPIs(MacosTestCase):

    @pytest.mark.skipif(not HAS_BATTERY, reason="no battery")
    def test_sensors_battery(self):
        out = sh("pmset -g batt")
        percent = re.search(r"(\d+)%", out).group(1)
        drawing_from = re.search(r"Now drawing from '([^']+)'", out).group(1)
        power_plugged = drawing_from == "AC Power"
        psutil_result = psutil.sensors_battery()
        assert psutil_result.power_plugged == power_plugged
        assert psutil_result.percent == int(percent)


class TestOtherSystemAPIs(MacosTestCase):

    def test_boot_time(self):
        out = sh('sysctl kern.boottime')
        a = float(re.search(r"sec\s*=\s*(\d+)", out).groups(0)[0])
        b = psutil.boot_time()
        assert a == b
