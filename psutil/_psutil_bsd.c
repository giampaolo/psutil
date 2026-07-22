/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola', Landry Breuil
 * (OpenBSD implementation), Ryo Onodera (NetBSD implementation).
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/proc.h>
#include <sys/param.h>  // BSD version
#include <netinet/tcp_fsm.h>  // for TCP connection states

#include "arch/all/init.h"
#include "arch/bsd/init.h"

#ifdef PSUTIL_FREEBSD
#include "arch/freebsd/init.h"
#elif PSUTIL_OPENBSD
#include "arch/openbsd/init.h"
#elif PSUTIL_NETBSD
#include "arch/netbsd/init.h"
#endif


static PyMethodDef mod_methods[] = {
    // --- per-process functions

    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_name", psutil_proc_name, METH_VARARGS},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS},
    {"proc_oneshot_kinfo", psutil_proc_oneshot_kinfo, METH_VARARGS},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS},
    {"proc_threads", psutil_proc_threads, METH_VARARGS},
#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_NETBSD)
    {"proc_num_threads", psutil_proc_num_threads, METH_VARARGS},
#endif
#if defined(PSUTIL_FREEBSD)
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS},
    {"proc_exe", psutil_proc_exe, METH_VARARGS},
    {"proc_getrlimit", psutil_proc_getrlimit, METH_VARARGS},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS},
    {"proc_net_connections", psutil_proc_net_connections, METH_VARARGS},
    {"proc_setrlimit", psutil_proc_setrlimit, METH_VARARGS},
#endif

    // --- system-related functions
    {"boot_time", psutil_boot_time, METH_VARARGS},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"cpu_times", psutil_cpu_times, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"net_connections", psutil_net_connections, METH_VARARGS},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"pids", psutil_pids, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},
#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_NETBSD)
    {"heap_info", psutil_heap_info, METH_VARARGS},
    {"heap_trim", psutil_heap_trim, METH_VARARGS},
#endif
#if defined(PSUTIL_OPENBSD)
    {"users", psutil_users, METH_VARARGS},
#endif
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS},
#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_OPENBSD)
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS},
#endif
#if defined(PSUTIL_FREEBSD)
    {"cpu_count_cores", psutil_cpu_count_cores, METH_VARARGS},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS},
    {"sensors_cpu_temperature", psutil_sensors_cpu_temperature, METH_VARARGS},
#endif
    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


static int
psutil_add_constants(PyObject *mod) {
    PSUTIL_ADD_INT(mod, "version", PSUTIL_VERSION);

    // process status constants
#ifdef PSUTIL_FREEBSD
    PSUTIL_ADD_INT(mod, "SIDL", SIDL);
    PSUTIL_ADD_INT(mod, "SRUN", SRUN);
    PSUTIL_ADD_INT(mod, "SSLEEP", SSLEEP);
    PSUTIL_ADD_INT(mod, "SSTOP", SSTOP);
    PSUTIL_ADD_INT(mod, "SZOMB", SZOMB);
    PSUTIL_ADD_INT(mod, "SWAIT", SWAIT);
    PSUTIL_ADD_INT(mod, "SLOCK", SLOCK);
#elif PSUTIL_OPENBSD
    PSUTIL_ADD_INT(mod, "SIDL", SIDL);
    PSUTIL_ADD_INT(mod, "SRUN", SRUN);
    PSUTIL_ADD_INT(mod, "SSLEEP", SSLEEP);
    PSUTIL_ADD_INT(mod, "SSTOP", SSTOP);
    PSUTIL_ADD_INT(mod, "SZOMB", SZOMB);  // unused
    PSUTIL_ADD_INT(mod, "SDEAD", SDEAD);
    PSUTIL_ADD_INT(mod, "SONPROC", SONPROC);
#elif defined(PSUTIL_NETBSD)
    PSUTIL_ADD_INT(mod, "SIDL", LSIDL);
    PSUTIL_ADD_INT(mod, "SRUN", LSRUN);
    PSUTIL_ADD_INT(mod, "SSLEEP", LSSLEEP);
    PSUTIL_ADD_INT(mod, "SSTOP", LSSTOP);
    PSUTIL_ADD_INT(mod, "SZOMB", LSZOMB);
#if __NetBSD_Version__ < 500000000
    PSUTIL_ADD_INT(mod, "SDEAD", LSDEAD);
#endif
    PSUTIL_ADD_INT(mod, "SONPROC", LSONPROC);
    // unique to NetBSD
    PSUTIL_ADD_INT(mod, "SSUSPENDED", LSSUSPENDED);
#endif

    // connection status constants
    PSUTIL_ADD_INT(mod, "TCPS_CLOSED", TCPS_CLOSED);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSING", TCPS_CLOSING);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT);
    PSUTIL_ADD_INT(mod, "TCPS_LISTEN", TCPS_LISTEN);
    PSUTIL_ADD_INT(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED);
    PSUTIL_ADD_INT(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT);
    PSUTIL_ADD_INT(mod, "TCPS_SYN_RECEIVED", TCPS_SYN_RECEIVED);
    PSUTIL_ADD_INT(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1);
    PSUTIL_ADD_INT(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2);
    PSUTIL_ADD_INT(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK);
    PSUTIL_ADD_INT(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT);
    PSUTIL_ADD_INT(mod, "PSUTIL_CONN_NONE", 128);

    return 0;
}


static int
psutil_exec(PyObject *mod) {
    if (psutil_setup() != 0)
        return -1;
    if (psutil_posix_add_constants(mod) != 0)
        return -1;
    if (psutil_posix_add_methods(mod) != 0)
        return -1;
    if (psutil_add_exceptions(mod) != 0)
        return -1;
    if (psutil_add_constants(mod) != 0)
        return -1;
    return 0;
}

PyMODINIT_FUNC
PyInit__psutil(void) {
    return psutil_mod_init("_psutil", mod_methods, psutil_exec);
}
