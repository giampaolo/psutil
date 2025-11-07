# Copyright (c) 2009, Giampaolo Rodola". All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import namedtuple

from ._common import AIX
from ._common import BSD
from ._common import FREEBSD
from ._common import LINUX
from ._common import MACOS
from ._common import SUNOS
from ._common import WINDOWS

# ===================================================================
# --- system functions
# ===================================================================

# psutil.swap_memory()
sswap = namedtuple(
    "sswap", ("total", "used", "free", "percent", "sin", "sout")
)

# psutil.disk_usage()
sdiskusage = namedtuple("sdiskusage", ("total", "used", "free", "percent"))

# psutil.disk_io_counters()
sdiskio = namedtuple(
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
sdiskpart = namedtuple("sdiskpart", ("device", "mountpoint", "fstype", "opts"))

# psutil.net_io_counters()
snetio = namedtuple(
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
suser = namedtuple("suser", ("name", "terminal", "host", "started", "pid"))

# psutil.net_connections()
sconn = namedtuple(
    "sconn", ("fd", "family", "type", "laddr", "raddr", "status", "pid")
)

# psutil.net_if_addrs()
snicaddr = namedtuple(
    "snicaddr", ("family", "address", "netmask", "broadcast", "ptp")
)

# psutil.net_if_stats()
snicstats = namedtuple(
    "snicstats", ("isup", "duplex", "speed", "mtu", "flags")
)

# psutil.cpu_stats()
scpustats = namedtuple(
    "scpustats", ("ctx_switches", "interrupts", "soft_interrupts", "syscalls")
)

# psutil.cpu_freq()
scpufreq = namedtuple("scpufreq", ("current", "min", "max"))

# psutil.sensors_temperatures()
shwtemp = namedtuple("shwtemp", ("label", "current", "high", "critical"))

# psutil.sensors_battery()
sbattery = namedtuple("sbattery", ("percent", "secsleft", "power_plugged"))

# psutil.sensors_fans()
sfan = namedtuple("sfan", ("label", "current"))

# ===================================================================
# --- Process class
# ===================================================================

# psutil.Process.cpu_times()
pcputimes = namedtuple(
    "pcputimes", ("user", "system", "children_user", "children_system")
)

# psutil.Process.open_files()
popenfile = namedtuple("popenfile", ("path", "fd"))

# psutil.Process.threads()
pthread = namedtuple("pthread", ("id", "user_time", "system_time"))

# psutil.Process.uids()
puids = namedtuple("puids", ("real", "effective", "saved"))

# psutil.Process.gids()
pgids = namedtuple("pgids", ("real", "effective", "saved"))

# psutil.Process.io_counters()
pio = namedtuple(
    "pio", ("read_count", "write_count", "read_bytes", "write_bytes")
)

# psutil.Process.ionice()
pionice = namedtuple("pionice", ("ioclass", "value"))

# psutil.Process.ctx_switches()
pctxsw = namedtuple("pctxsw", ("voluntary", "involuntary"))

# psutil.Process.net_connections()
pconn = namedtuple(
    "pconn", ("fd", "family", "type", "laddr", "raddr", "status")
)

# psutil.net_connections() and psutil.Process.net_connections()
addr = namedtuple("addr", ("ip", "port"))

# ===================================================================
# --- Linux
# ===================================================================

if LINUX:
    # This gets set from _pslinux.py
    scputimes = None

    # psutil.virtual_memory()
    svmem = namedtuple(
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
    sdiskio = namedtuple(
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
    popenfile = namedtuple(
        "popenfile", ("path", "fd", "position", "mode", "flags")
    )

    # psutil.Process().memory_info()
    pmem = namedtuple(
        "pmem", ("rss", "vms", "shared", "text", "lib", "data", "dirty")
    )

    # psutil.Process().memory_full_info()
    pfullmem = namedtuple("pfullmem", pmem._fields + ("uss", "pss", "swap"))

    # psutil.Process().memory_maps(grouped=True)
    pmmap_grouped = namedtuple(
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
    pmmap_ext = namedtuple(
        "pmmap_ext", "addr perms " + " ".join(pmmap_grouped._fields)
    )

    # psutil.Process.io_counters()
    pio = namedtuple(
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
    pcputimes = namedtuple(
        "pcputimes",
        ("user", "system", "children_user", "children_system", "iowait"),
    )

# ===================================================================
# --- Windows
# ===================================================================

elif WINDOWS:

    # psutil.cpu_times()
    scputimes = namedtuple(
        "scputimes", ("user", "system", "idle", "interrupt", "dpc")
    )
    # psutil.virtual_memory()
    svmem = namedtuple(
        "svmem", ("total", "available", "percent", "used", "free")
    )
    # psutil.Process.memory_info()
    pmem = namedtuple(
        "pmem",
        (
            "rss",
            "vms",
            "num_page_faults",
            "peak_wset",
            "wset",
            "peak_paged_pool",
            "paged_pool",
            "peak_nonpaged_pool",
            "nonpaged_pool",
            "pagefile",
            "peak_pagefile",
            "private",
        ),
    )
    # psutil.Process.memory_full_info()
    pfullmem = namedtuple("pfullmem", pmem._fields + ("uss",))
    # psutil.Process.memory_maps(grouped=True)
    pmmap_grouped = namedtuple("pmmap_grouped", ("path", "rss"))
    # psutil.Process.memory_maps(grouped=False)
    pmmap_ext = namedtuple(
        "pmmap_ext", "addr perms " + " ".join(pmmap_grouped._fields)
    )
    # psutil.Process.io_counters()
    pio = namedtuple(
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
    scputimes = namedtuple("scputimes", ("user", "nice", "system", "idle"))
    # psutil.virtual_memory()
    svmem = namedtuple(
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
    pmem = namedtuple("pmem", ("rss", "vms", "pfaults", "pageins"))

    # psutil.Process.memory_full_info()
    pfullmem = namedtuple("pfullmem", pmem._fields + ("uss",))

# ===================================================================
# --- BSD
# ===================================================================

elif BSD:

    # psutil.virtual_memory()
    svmem = namedtuple(
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
    scputimes = namedtuple(
        "scputimes", ("user", "nice", "system", "idle", "irq")
    )

    # psutil.Process.memory_info()
    pmem = namedtuple("pmem", ("rss", "vms", "text", "data", "stack"))

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.cpu_times()
    pcputimes = namedtuple(
        "pcputimes", ("user", "system", "children_user", "children_system")
    )

    # psutil.Process.memory_maps(grouped=True)
    pmmap_grouped = namedtuple(
        "pmmap_grouped", "path rss, private, ref_count, shadow_count"
    )

    # psutil.Process.memory_maps(grouped=False)
    pmmap_ext = namedtuple(
        "pmmap_ext", "addr, perms path rss, private, ref_count, shadow_count"
    )

    # psutil.disk_io_counters()
    if FREEBSD:
        sdiskio = namedtuple(
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
        sdiskio = namedtuple(
            "sdiskio",
            ("read_count", "write_count", "read_bytes", "write_bytes"),
        )

# ===================================================================
# --- SunOS
# ===================================================================

elif SUNOS:

    # psutil.cpu_times()
    scputimes = namedtuple("scputimes", ("user", "system", "idle", "iowait"))

    # psutil.cpu_times(percpu=True)
    pcputimes = namedtuple(
        "pcputimes", ("user", "system", "children_user", "children_system")
    )

    # psutil.virtual_memory()
    svmem = namedtuple(
        "svmem", ("total", "available", "percent", "used", "free")
    )

    # psutil.Process.memory_info()
    pmem = namedtuple("pmem", ("rss", "vms"))

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.memory_maps(grouped=True)
    pmmap_grouped = namedtuple(
        "pmmap_grouped", ("path", "rss", "anonymous", "locked")
    )

    # psutil.Process.memory_maps(grouped=False)
    pmmap_ext = namedtuple(
        "pmmap_ext", "addr perms " + " ".join(pmmap_grouped._fields)
    )

# ===================================================================
# --- AIX
# ===================================================================

elif AIX:

    # psutil.Process.memory_info()
    pmem = namedtuple("pmem", ("rss", "vms"))

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.cpu_times()
    scputimes = namedtuple("scputimes", ("user", "system", "idle", "iowait"))

    # psutil.virtual_memory()
    svmem = namedtuple(
        "svmem", ("total", "available", "percent", "used", "free")
    )
