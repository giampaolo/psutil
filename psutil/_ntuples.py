# Copyright (c) 2009, Giampaolo Rodola". All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from __future__ import annotations

import warnings
from collections import namedtuple
from typing import TYPE_CHECKING
from typing import NamedTuple

if TYPE_CHECKING:
    import socket

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
class sswap(NamedTuple):
    total: int
    used: int
    free: int
    percent: float
    sin: int
    sout: int


# psutil.disk_usage()
class sdiskusage(NamedTuple):
    total: int
    used: int
    free: int
    percent: float


# psutil.disk_io_counters()
class sdiskio(NamedTuple):
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int
    if LINUX:
        read_time: int
        write_time: int
        read_merged_count: int
        write_merged_count: int
        busy_time: int
    elif FREEBSD:
        read_time: int
        write_time: int
        busy_time: int


# psutil.disk_partitions()
class sdiskpart(NamedTuple):
    device: str
    mountpoint: str
    fstype: str
    opts: str


# psutil.net_io_counters()
class snetio(NamedTuple):
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    errin: int
    errout: int
    dropin: int
    dropout: int


# psutil.users()
class suser(NamedTuple):
    name: str
    terminal: str | None
    host: str | None
    started: float
    pid: int | None


# psutil.net_connections() and psutil.Process.net_connections()
class addr(NamedTuple):
    ip: str
    port: int


# psutil.net_connections()
class sconn(NamedTuple):
    fd: int
    family: socket.AddressFamily
    type: socket.SocketKind
    laddr: addr | tuple | str
    raddr: addr | tuple | str
    status: str
    pid: int | None


# psutil.net_if_addrs()
class snicaddr(NamedTuple):
    family: socket.AddressFamily
    address: str
    netmask: str | None
    broadcast: str | None
    ptp: str | None


# psutil.net_if_stats()
class snicstats(NamedTuple):
    isup: bool
    duplex: int
    speed: int
    mtu: int
    flags: str


# psutil.cpu_stats()
class scpustats(NamedTuple):
    ctx_switches: int
    interrupts: int
    soft_interrupts: int
    syscalls: int


# psutil.cpu_freq()
class scpufreq(NamedTuple):
    current: float
    min: float | None
    max: float | None


# psutil.sensors_temperatures()
class shwtemp(NamedTuple):
    label: str
    current: float | None
    high: float | None
    critical: float | None


# psutil.sensors_battery()
class sbattery(NamedTuple):
    percent: float
    secsleft: int
    power_plugged: bool | None


# psutil.sensors_fans()
class sfan(NamedTuple):
    label: str
    current: int


# psutil.heap_info()
if WINDOWS:

    class pheap(NamedTuple):
        heap_used: int
        mmap_used: int
        heap_count: int

elif LINUX or MACOS or BSD:

    class pheap(NamedTuple):
        heap_used: int
        mmap_used: int


# psutil.cpu_times()
if LINUX:
    # This gets set dynamically from _pslinux.py
    scputimes = None
else:

    class scputimes(NamedTuple):
        user: float
        system: float
        idle: float
        if WINDOWS:
            interrupt: float
            dpc: float
        if MACOS or BSD:
            nice: float
        if BSD:
            irq: float
        if SUNOS or AIX:
            iowait: float


# psutil.virtual_memory()
class svmem(NamedTuple):
    total: int
    available: int
    percent: float
    used: int
    free: int
    if LINUX:
        active: int
        inactive: int
        buffers: int
        cached: int
        shared: int
        slab: int
    elif BSD:
        active: int
        inactive: int
        buffers: int
        cached: int
        shared: int
        wired: int
    elif MACOS:
        active: int
        inactive: int
        wired: int


# ===================================================================
# --- Process class
# ===================================================================


# psutil.Process.cpu_times()
class pcputimes(NamedTuple):
    user: float
    system: float
    children_user: float
    children_system: float
    if LINUX:
        iowait: float


# psutil.Process.open_files()
class popenfile(NamedTuple):
    path: str
    fd: int


# psutil.Process.threads()
class pthread(NamedTuple):
    id: int
    user_time: float
    system_time: float


# psutil.Process.uids()
class puids(NamedTuple):
    real: int
    effective: int
    saved: int


# psutil.Process.gids()
class pgids(NamedTuple):
    real: int
    effective: int
    saved: int


# psutil.Process.io_counters()
class pio(NamedTuple):
    read_count: int
    write_count: int
    read_bytes: int
    write_bytes: int
    if LINUX:
        read_chars: int
        write_chars: int
    elif WINDOWS:
        other_count: int
        other_bytes: int


# psutil.Process.ionice()
class pionice(NamedTuple):
    ioclass: int
    value: int


# psutil.Process.ctx_switches()
class pctxsw(NamedTuple):
    voluntary: int
    involuntary: int


# psutil.Process.page_faults()
class ppagefaults(NamedTuple):
    minor: int
    major: int


# psutil.Process().memory_footprint()
if LINUX or MACOS or WINDOWS:

    class pfootprint(NamedTuple):
        uss: int
        if LINUX:
            pss: int
            swap: int


# psutil.Process.net_connections()
class pconn(NamedTuple):
    fd: int
    family: socket.AddressFamily
    type: socket.SocketKind
    laddr: addr | tuple | str
    raddr: addr | tuple | str
    status: str


# ===================================================================
# --- Linux
# ===================================================================

if LINUX:

    # psutil.Process().open_files()
    class popenfile(NamedTuple):
        path: str
        fd: int
        position: int
        mode: str
        flags: int

    # psutil.Process().memory_info()
    class pmem(NamedTuple):
        rss: int
        vms: int
        shared: int
        text: int
        data: int

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
    class pmem_ex(NamedTuple):
        rss: int
        vms: int
        shared: int
        text: int
        data: int
        peak_rss: int
        peak_vms: int
        rss_anon: int
        rss_file: int
        rss_shmem: int
        swap: int
        hugetlb: int

    # psutil.Process().memory_full_info()
    class pfullmem(NamedTuple):
        rss: int
        vms: int
        shared: int
        text: int
        data: int
        uss: int
        pss: int
        swap: int

    # psutil.Process().memory_maps(grouped=True)
    class pmmap_grouped(NamedTuple):
        path: str
        rss: int
        size: int
        pss: int
        shared_clean: int
        shared_dirty: int
        private_clean: int
        private_dirty: int
        referenced: int
        anonymous: int
        swap: int

    # psutil.Process().memory_maps(grouped=False)
    class pmmap_ext(NamedTuple):
        addr: str
        perms: str
        path: str
        rss: int
        size: int
        pss: int
        shared_clean: int
        shared_dirty: int
        private_clean: int
        private_dirty: int
        referenced: int
        anonymous: int
        swap: int


# ===================================================================
# --- Windows
# ===================================================================

elif WINDOWS:
    # psutil.Process.memory_info()
    class pmem(  # noqa: SLOT002
        namedtuple("pmem", ("rss", "vms", "peak_rss", "peak_vms"))
    ):
        def __new__(cls, rss, vms, peak_rss, peak_vms, _deprecated=None):
            inst = super().__new__(cls, rss, vms, peak_rss, peak_vms)
            inst.__dict__["_deprecated"] = _deprecated or {}
            return inst

        def __getattr__(self, name):
            depr = self.__dict__["_deprecated"]
            if name in depr:
                msg = f"pmem.{name} is deprecated"
                if name in {
                    "paged_pool",
                    "nonpaged_pool",
                    "peak_paged_pool",
                    "peak_nonpaged_pool",
                }:
                    msg += "; use memory_info_ex() instead"
                elif name == "num_page_faults":
                    msg += "; use page_faults() instead"
                warnings.warn(msg, DeprecationWarning, stacklevel=2)
                return depr[name]

            msg = f"{self.__class__.__name__} object has no attribute {name!r}"
            raise AttributeError(msg)

    # psutil.Process.memory_info_ex()
    class pmem_ex(NamedTuple):
        rss: int
        vms: int
        peak_rss: int
        peak_vms: int
        virtual: int
        peak_virtual: int
        paged_pool: int
        nonpaged_pool: int
        peak_paged_pool: int
        peak_nonpaged_pool: int

    # psutil.Process.memory_full_info()
    class pfullmem(NamedTuple):
        rss: int
        vms: int
        peak_rss: int
        peak_vms: int
        uss: int

    # psutil.Process.memory_maps(grouped=True)
    class pmmap_grouped(NamedTuple):
        path: str
        rss: int

    # psutil.Process.memory_maps(grouped=False)
    class pmmap_ext(NamedTuple):
        addr: str
        perms: str
        path: str
        rss: int


# ===================================================================
# --- macOS
# ===================================================================

elif MACOS:

    # psutil.Process.memory_info()
    class pmem(NamedTuple):
        rss: int
        vms: int

    # psutil.Process.memory_info_ex()
    class pmem_ex(NamedTuple):
        rss: int
        vms: int
        peak_rss: int
        rss_anon: int
        rss_file: int
        wired: int
        compressed: int
        phys_footprint: int

    # psutil.Process.memory_full_info()
    class pfullmem(NamedTuple):
        rss: int
        vms: int
        uss: int


# ===================================================================
# --- BSD
# ===================================================================

elif BSD:

    # psutil.Process.memory_info()
    class pmem(NamedTuple):
        rss: int
        vms: int
        text: int
        data: int
        stack: int
        peak_rss: int

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.memory_maps(grouped=True)
    class pmmap_grouped(NamedTuple):
        path: str
        rss: int
        private: int
        ref_count: int
        shadow_count: int

    # psutil.Process.memory_maps(grouped=False)
    class pmmap_ext(NamedTuple):
        addr: str
        perms: str
        path: str
        rss: int
        private: int
        ref_count: int
        shadow_count: int


# ===================================================================
# --- SunOS
# ===================================================================

elif SUNOS:
    # psutil.Process.memory_info()
    class pmem(NamedTuple):
        rss: int
        vms: int

    # psutil.Process.memory_full_info()
    pfullmem = pmem

    # psutil.Process.memory_maps(grouped=True)
    class pmmap_grouped(NamedTuple):
        path: str
        rss: int
        anonymous: int
        locked: int

    # psutil.Process.memory_maps(grouped=False)
    class pmmap_ext(NamedTuple):
        addr: str
        perms: str
        path: str
        rss: int
        anonymous: int
        locked: int


# ===================================================================
# --- AIX
# ===================================================================

elif AIX:
    # psutil.Process.memory_info()
    class pmem(NamedTuple):
        rss: int
        vms: int

    # psutil.Process.memory_full_info()
    pfullmem = pmem
