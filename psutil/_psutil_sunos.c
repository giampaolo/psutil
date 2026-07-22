/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Functions specific to Sun OS Solaris platforms.
//
// Thanks to Justin Venus who originally wrote a consistent part of
// this in Cython which I later on translated in C.
//
// Fix compilation issue on SunOS 5.10, see:
// https://github.com/giampaolo/psutil/issues/421
// https://github.com/giampaolo/psutil/issues/1077

#define _STRUCTURED_PROC 1
#define NEW_MIB_COMPLIANT 1

#include <Python.h>

#if !defined(_LP64) && _FILE_OFFSET_BITS == 64
#undef _FILE_OFFSET_BITS
#undef _LARGEFILE64_SOURCE
#endif

#include <inet/tcp.h>
#include <sys/proc.h>

#include "arch/all/init.h"


static PyMethodDef mod_methods[] = {
    // --- process-related functions
    {"proc_cpu_num", psutil_proc_cpu_num, METH_VARARGS},
    {"proc_cpu_times", psutil_proc_cpu_times, METH_VARARGS},
    {"proc_cred", psutil_proc_cred, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS},
    {"proc_name_and_args", psutil_proc_name_and_args, METH_VARARGS},
    {"proc_num_ctx_switches", psutil_proc_num_ctx_switches, METH_VARARGS},
    {"proc_oneshot", psutil_proc_oneshot, METH_VARARGS},
    {"proc_page_faults", psutil_proc_page_faults, METH_VARARGS},
    {"query_process_thread", psutil_proc_query_thread, METH_VARARGS},

    // --- system-related functions
    {"boot_time", psutil_boot_time, METH_VARARGS},
    {"cpu_count_cores", psutil_cpu_count_cores, METH_VARARGS},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"net_connections", psutil_net_connections, METH_VARARGS},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


static int
psutil_add_constants(PyObject *mod) {
    PSUTIL_ADD_INT(mod, "version", PSUTIL_VERSION);
    PSUTIL_ADD_INT(mod, "SSLEEP", SSLEEP);
    PSUTIL_ADD_INT(mod, "SRUN", SRUN);
    PSUTIL_ADD_INT(mod, "SZOMB", SZOMB);
    PSUTIL_ADD_INT(mod, "SSTOP", SSTOP);
    PSUTIL_ADD_INT(mod, "SIDL", SIDL);
    PSUTIL_ADD_INT(mod, "SONPROC", SONPROC);
#ifdef SWAIT
    PSUTIL_ADD_INT(mod, "SWAIT", SWAIT);
#else
    // sys/proc.h started defining SWAIT somewhere
    // after Update 3 and prior to Update 5 included.
    PSUTIL_ADD_INT(mod, "SWAIT", 0);
#endif
    // for process tty
    PSUTIL_ADD_INT(mod, "PRNODEV", PRNODEV);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSED", TCPS_CLOSED);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSING", TCPS_CLOSING);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT);
    PSUTIL_ADD_INT(mod, "TCPS_LISTEN", TCPS_LISTEN);
    PSUTIL_ADD_INT(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED);
    PSUTIL_ADD_INT(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT);
    PSUTIL_ADD_INT(mod, "TCPS_SYN_RCVD", TCPS_SYN_RCVD);
    PSUTIL_ADD_INT(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1);
    PSUTIL_ADD_INT(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2);
    PSUTIL_ADD_INT(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK);
    PSUTIL_ADD_INT(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT);
    // sunos specific
    PSUTIL_ADD_INT(mod, "TCPS_IDLE", TCPS_IDLE);
    // sunos specific
    PSUTIL_ADD_INT(mod, "TCPS_BOUND", TCPS_BOUND);
    PSUTIL_ADD_INT(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE);

    return 0;
}


static int
psutil_sunos_exec(PyObject *mod) {
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
PyInit__psutil_sunos(void) {
    return psutil_mod_init("_psutil_sunos", mod_methods, psutil_sunos_exec);
}
