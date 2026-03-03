# Copyright (c) 2009, Giampaolo Rodola". All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import warnings
from collections import namedtuple as nt

from ._common import AIX
from ._common import BSD
from ._common import FREEBSD
from ._common import LINUX
from ._common import MACOS
from ._common import SUNOS
from ._common import WINDOWS
from ._common import deprecated_property

# ===================================================================
# --- system functions
# ===================================================================

# psutil.swap_memory()
sswap = nt("sswap", ("total", "used", "free", "percent", "sin", "sout"))

# psutil.disk_usage()
sdiskusage = nt("sdiskusage", ("total", "used", "free", "percent"))

# psutil.disk_io_counters()
sdiskio = nt(
    "sdiskio",
    (
        "read_count",
        "write_count",
        "read_bytes",
        "write_bytes",
        "read_time",
        "write_time",
    ),
)

# psutil.disk_partitions()
sdiskpart = nt("sdiskpart", ("device", "mountpoint", "fstype", "opts"))

# psutil.net_io_counters()
snetio = nt(
    "snetio",
    (
        "bytes_sent",
        "bytes_recv",
        "packets_sent",
        "packets_recv",
        "errin",
        "errout",
        "dropin",
        "dropout",
    ),
)

# psutil.users()
suser = nt("suser", ("name", "terminal", "host", "started", "pid"))

# psutil.net_connections()
sconn = nt(
    "sconn", ("fd", "family", "type", "laddr", "raddr", "status", "pid")
)

# psutil.net_if_addrs()
snicaddr = nt("snicaddr", ("family", "address", "netmask", "broadcast", "ptp"))

# psutil.net_if_stats()
snicstats = nt("snicstats", ("isup", "duplex", "speed", "mtu", "flags"))

# psutil.cpu_stats()
scpustats = nt(
    "scpustats", ("ctx_switches", "interrupts", "soft_interrupts", "syscalls")
)

# psutil.cpu_freq()
scpufreq = nt("scpufreq", ("current", "min", "max"))

# psutil.sensors_temperatures()
shwtemp = nt("shwtemp", ("label", "current", "high", "critical"))

# psutil.sensors_battery()
sbattery = nt("sbattery", ("percent", "secsleft", "power_plugged"))

# psutil.sensors_fans()
sfan = nt("sfan", ("label", "current"))

# psutil.heap_info() (mallinfo2 Linux struct)
if LINUX or WINDOWS or MACOS or BSD:
    pheap = nt(
        "pheap",
        [
            "heap_used",  # uordblks, memory allocated via malloc()
            "mmap_used",  # hblkhd, memory allocated via mmap() (large blocks)
        ],
    )
    if WINDOWS:
        pheap = nt("pheap", pheap._fields + ("heap_count",))

# ===================================================================
# --- Process class
# ===================================================================

# psutil.Process.cpu_times()
pcputimes = nt(
    "pcputimes", ("user", "system", "children_user", "children_system")
)

# psutil.Process.open_files()
popenfile = nt("popenfile", ("path", "fd"))

# psutil.Process.threads()
pthread = nt("pthread", ("id", "user_time", "system_time"))

# psutil.Process.uids()
puids = nt("puids", ("real", "effective", "saved"))

# psutil.Process.gids()
pgids = nt("pgids", ("real", "effective", "saved"))

# psutil.Process.io_counters()
pio = nt("pio", ("read_count", "write_count", "read_bytes", "write_bytes"))

# psutil.Process.ionice()
pionice = nt("pionice", ("ioclass", "value"))

# psutil.Process.ctx_switches()
pctxsw = nt("pctxsw", ("voluntary", "involuntary"))

# psutil.Process.page_faults()
ppagefaults = nt("ppagefaults", ("minor", "major"))

# psutil.Process.net_connections()
pconn = nt("pconn", ("fd", "family", "type", "laddr", "raddr", "status"))

# psutil.net_connections() and psutil.Process.net_connections()
addr = nt("addr", ("ip", "port"))

# ===================================================================
# --- Linux
# ===================================================================

if LINUX:

    # This gets set from _pslinux.py
    scputimes = None

    # psutil.virtual_memory()
    svmem = nt(
        "svmem",
        (
            "total",
            "available",
            "percent",
            "used",
            "free",
            "active",
            "inactive",
            "buffers",
            "cached",
            "shared",
            "slab",
        ),
    )

    # psutil.disk_io_counters()
    sdiskio = nt(
        "sdiskio",
        (
            "read_count",
            "write_count",
            "read_bytes",
            "write_bytes",
            "read_time",
            "write_time",
            "read_merged_count",
            "write_merged_count",
            "busy_time",
        ),
    )

    # psutil.Process().open_files()
    popenfile = nt("popenfile", ("path", "fd", "position", "mode", "flags"))

    # psutil.Process().memory_info()
    _pmem = nt("pmem", ("rss", "vms", "shared", "text", "data"))

    class pmem(_pmem):
        __slots__ = ()

        @property
        def lib(self):
            # It has always been 0 since Linux 2.6.
            msg = "'lib' field is deprecated and will be removed"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return 0

        @property
        def dirty(self):
            # It has always been 0 since Linux 2.6.
            msg = "'dirty' field is deprecated and will be removed"
            warnings.warn(msg, DeprecationWarning, stacklevel=2)
            return 0

    # psutil.Process().memory_info_ex()
    pmem_ex = nt(
        "pmem_ex",
        pmem._fields
        + (
            "peak_rss",
            "peak_vms",
            "rss_anon",
            "rss_file",
            "rss_shmem",
            "swap",
            "hugetlb",
        ),
    )

    # psutil.Process().memory_footprint()
    pfootprint = nt("pfootprint", ("uss", "pss", "swap"))

    # psutil.Process().memory_full_info()
    pfullmem = nt("pfullmem", pmem._fields + ("uss", "pss", "swap"))

    # psutil.Process().memory_maps(grouped=True)
    pmmap_grouped = nt(
        "pmmap_grouped",
        (
            "path",
            "rss",
            "size",
            "pss",
            "shared_clean",
            "shared_dirty",
            "private_clean",
            "private_dirty",
            "referenced",
            "anonymous",
            "swap",
        ),
    )

    # psutil.Process().memory_maps(grouped=False)
    pmmap_ext = nt(
        "pmmap_ext", "addr perms " + " ".join(pmmap_grouped._fields)
    )

    # psutil.Process.io_counters()
    pio = nt(
        "pio",
        (
            "read_count",
            "write_count",
            "read_bytes",
            "write_bytes",
            "read_chars",
            "write_chars",
        ),
    )

    # psutil.Process.cpu_times()
    pcputimes = nt(
        "pcputimes",
        ("user", "system", "children_user", "children_system", "iowait"),
    )

# ===================================================================
# --- Windows
# ===================================================================

elif WINDOWS:

    # psutil.cpu_times()
    scputimes = nt("scputimes", ("user", "system", "idle", "interrupt", "dpc"))

    # psutil.virtual_memory()
    svmem = nt("svmem", ("total", "available", "percent", "used", "free"))

    # psutil.Process.memory_info()
    _pmem = nt(
        "pmem",
        (
            "rss",
            "vms",
            "num_page_faults",
            "paged_pool",
            "nonpaged_pool",
            "peak_rss",
            "peak_vms",
            "peak_paged_pool",
            "peak_nonpaged_pool",
        ),
    )

    class pmem(_pmem):
        __slots__ = ()

        wset = deprecated_property(replacement="rss")
        peak_wset = deprecated_property(replacement="peak_rss")
        pagefile = deprecated_property(replacement="vms")
        peak_pagefile = deprecated_property(replacement="peak_vms")
        private = deprecated_property(replacement="vms")

    # psutil.Process.memory_info_ex()
    _pmem_ex = nt(
        "pmem_ex",
        pmem._fields + ("virtual", "peak_virtual"),
    )

    class pmem_ex(pmem, _pmem_ex):
        __slots__ = ()
        _fields = _pmem_ex._fields
        __repr__ = _pmem_ex.__repr__

        def __new__(cls, *args, **kwargs):
            return _pmem_ex.__new__(cls, *args, **kwargs)

        @classmethod
        def _make(cls, iterable):
            result = tuple.__new__(cls, iterable)
            n = len(cls._fields)
            if len(result) != n:
                msg = f"Expected {n} arguments, got {len(result)}"
                raise TypeError(msg)
            return result

    # psutil.Process.memory_footprint()
    pfootprint = nt("pfootprint", ("uss",))

    # psutil.Process.memory_full_info()
    pfullmem = nt("pfullmem", pmem._fields + ("uss",))

    # psutil.Process.memory_maps(grouped=True)
    pmmap_grouped = nt("pmmap_grouped", ("path", "rss"))

    # psutil.Process.memory_maps(grouped=False)
    pmmap_ext = nt(
        "pmmap_ext", "addr perms " + " ".join(pmmap_grouped._fields)
    )

    # psutil.Process.io_counters()
    pio = nt(
        "pio",
        (
            "read_count",
            "write_count",
            "read_bytes",
            "write_bytes",
            "other_count",
            "other_bytes",
        ),
    )

# ===================================================================
# --- macOS
# ===================================================================

elif MACOS:

    # psutil.cpu_times()
    scputimes = nt("scputimes", ("user", "nice", "system", "idle"))

    # psutil.virtual_memory()
    svmem = nt(
        "svmem",
        (
            "total",
            "available",
            "percent",
            "used",
            "free",
            "active",
            "inactive",
            "wired",
        ),
    )

    # psutil.Process.memory_info()
    pmem = nt("pmem", ("rss", "vms"))

    # psutil.Process.memory_info_ex()
    pmem_ex = nt(
        "pmem_ex",
        pmem._fields
        + (
            "peak_rss",
            "rss_anon",
            "rss_file",
            "wired",
            "compressed",
            "phys_footprint",
        ),
    )

    # psutil.Process.memory_footprint()
    pfootprint = nt("pfootprint", ("uss",))

    # psutil.Process.memory_full_info()
    pfullmem = nt("pfullmem", pmem._fields + ("uss",))

# ===================================================================
# --- BSD
# ===================================================================

elif BSD:

    # psutil.virtual_memory()
    svmem = nt(
        "svmem",
        (
            "total",
            "available",
            "percent",
            "used",
            "free",
            "active",
            "inactive",
            "buffers",
            "cached",
            "shared",
            "wired",
        ),
    )

    # psutil.cpu_times()
    scputimes = nt("scputimes", ("user", "nice", "system", "idle", "irq"))

    # psutil.Process.memory_info()
    pmem = nt("pmem", ("rss", "vms", "text", "data", "stack", "peak_rss"))

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.cpu_times()
    pcputimes = nt(
        "pcputimes", ("user", "system", "children_user", "children_system")
    )

    # psutil.Process.memory_maps(grouped=True)
    pmmap_grouped = nt(
        "pmmap_grouped", "path rss, private, ref_count, shadow_count"
    )

    # psutil.Process.memory_maps(grouped=False)
    pmmap_ext = nt(
        "pmmap_ext", "addr, perms path rss, private, ref_count, shadow_count"
    )

    # psutil.disk_io_counters()
    if FREEBSD:
        sdiskio = nt(
            "sdiskio",
            (
                "read_count",
                "write_count",
                "read_bytes",
                "write_bytes",
                "read_time",
                "write_time",
                "busy_time",
            ),
        )
    else:
        sdiskio = nt(
            "sdiskio",
            ("read_count", "write_count", "read_bytes", "write_bytes"),
        )

# ===================================================================
# --- SunOS
# ===================================================================

elif SUNOS:

    # psutil.cpu_times()
    scputimes = nt("scputimes", ("user", "system", "idle", "iowait"))

    # psutil.cpu_times(percpu=True)
    pcputimes = nt(
        "pcputimes", ("user", "system", "children_user", "children_system")
    )

    # psutil.virtual_memory()
    svmem = nt("svmem", ("total", "available", "percent", "used", "free"))

    # psutil.Process.memory_info()
    pmem = nt("pmem", ("rss", "vms"))

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.memory_maps(grouped=True)
    pmmap_grouped = nt("pmmap_grouped", ("path", "rss", "anonymous", "locked"))

    # psutil.Process.memory_maps(grouped=False)
    pmmap_ext = nt(
        "pmmap_ext", "addr perms " + " ".join(pmmap_grouped._fields)
    )

# ===================================================================
# --- AIX
# ===================================================================

elif AIX:

    # psutil.Process.memory_info()
    pmem = nt("pmem", ("rss", "vms"))

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.cpu_times()
    scputimes = nt("scputimes", ("user", "system", "idle", "iowait"))

    # psutil.virtual_memory()
    svmem = nt("svmem", ("total", "available", "percent", "used", "free"))
