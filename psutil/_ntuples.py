# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

from collections import namedtuple

# ===================================================================
# --- system functions
# ===================================================================

# psutil.swap_memory()
sswap = namedtuple(
    'sswap', ['total', 'used', 'free', 'percent', 'sin', 'sout']
)

# psutil.disk_usage()
sdiskusage = namedtuple('sdiskusage', ['total', 'used', 'free', 'percent'])

# psutil.disk_io_counters()
sdiskio = namedtuple(
    'sdiskio',
    [
        'read_count',
        'write_count',
        'read_bytes',
        'write_bytes',
        'read_time',
        'write_time',
    ],
)

# psutil.disk_partitions()
sdiskpart = namedtuple('sdiskpart', ['device', 'mountpoint', 'fstype', 'opts'])

# psutil.net_io_counters()
snetio = namedtuple(
    'snetio',
    [
        'bytes_sent',
        'bytes_recv',
        'packets_sent',
        'packets_recv',
        'errin',
        'errout',
        'dropin',
        'dropout',
    ],
)

# psutil.users()
suser = namedtuple('suser', ['name', 'terminal', 'host', 'started', 'pid'])

# psutil.net_connections()
sconn = namedtuple(
    'sconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status', 'pid']
)

# psutil.net_if_addrs()
snicaddr = namedtuple(
    'snicaddr', ['family', 'address', 'netmask', 'broadcast', 'ptp']
)

# psutil.net_if_stats()
snicstats = namedtuple(
    'snicstats', ['isup', 'duplex', 'speed', 'mtu', 'flags']
)

# psutil.cpu_stats()
scpustats = namedtuple(
    'scpustats', ['ctx_switches', 'interrupts', 'soft_interrupts', 'syscalls']
)

# psutil.cpu_freq()
scpufreq = namedtuple('scpufreq', ['current', 'min', 'max'])

# psutil.sensors_temperatures()
shwtemp = namedtuple('shwtemp', ['label', 'current', 'high', 'critical'])

# psutil.sensors_battery()
sbattery = namedtuple('sbattery', ['percent', 'secsleft', 'power_plugged'])

# psutil.sensors_fans()
sfan = namedtuple('sfan', ['label', 'current'])

# ===================================================================
# --- Process class
# ===================================================================

# psutil.Process.cpu_times()
pcputimes = namedtuple(
    'pcputimes', ['user', 'system', 'children_user', 'children_system']
)

# psutil.Process.open_files()
popenfile = namedtuple('popenfile', ['path', 'fd'])

# psutil.Process.threads()
pthread = namedtuple('pthread', ['id', 'user_time', 'system_time'])

# psutil.Process.uids()
puids = namedtuple('puids', ['real', 'effective', 'saved'])

# psutil.Process.gids()
pgids = namedtuple('pgids', ['real', 'effective', 'saved'])

# psutil.Process.io_counters()
pio = namedtuple(
    'pio', ['read_count', 'write_count', 'read_bytes', 'write_bytes']
)

# psutil.Process.ionice()
pionice = namedtuple('pionice', ['ioclass', 'value'])

# psutil.Process.ctx_switches()
pctxsw = namedtuple('pctxsw', ['voluntary', 'involuntary'])

# psutil.Process.net_connections()
pconn = namedtuple(
    'pconn', ['fd', 'family', 'type', 'laddr', 'raddr', 'status']
)

# psutil.net_connections() and psutil.Process.net_connections()
addr = namedtuple('addr', ['ip', 'port'])
