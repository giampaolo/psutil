#/usr/bin/env python
#
#$Id$
#

"""Common objects shared by all _ps* modules."""

from psutil._compat import namedtuple

# system
ntuple_sys_cputimes = namedtuple('cputimes', 'user nice system idle iowait irq softirq')

# processes
ntuple_meminfo = namedtuple('meminfo', 'rss vms')
ntuple_cputimes = namedtuple('cputimes', 'user system')
ntuple_openfile = namedtuple('openfile', 'path fd')
ntuple_connection = namedtuple('connection', 'fd family type local_address remote_address status')
ntuple_thread = namedtuple('thread', 'id user_time system_time')
ntuple_uids = namedtuple('user', 'real effective saved')
ntuple_gids = namedtuple('group', 'real effective saved')
ntuple_io = namedtuple('io', 'read_count write_count read_bytes write_bytes')
ntuple_ionice = namedtuple('ionice', 'ioclass iodata')

# the __all__ namespace common to all _ps*.py platform modules
base_module_namespace = [
    # constants
    "NUM_CPUS", "TOTAL_PHYMEM", "BOOT_TIME",
    # classes
    "PlatformProcess",
    # functions
    "avail_phymem", "used_phymem", "total_virtmem", "avail_virtmem",
    "used_virtmem", "get_system_cpu_times", "pid_exists", "get_pid_list",
    ]

