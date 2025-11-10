/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
 * Functions specific to Sun OS Solaris platforms.
 *
 * Thanks to Justin Venus who originally wrote a consistent part of
 * this in Cython which I later on translated in C.
 *
 * Fix compilation issue on SunOS 5.10, see:
 * https://github.com/giampaolo/psutil/issues/421
 * https://github.com/giampaolo/psutil/issues/1077
 */

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
    {"proc_basic_info", psutil_proc_basic_info, METH_VARARGS},
    {"proc_cpu_num", psutil_proc_cpu_num, METH_VARARGS},
    {"proc_cpu_times", psutil_proc_cpu_times, METH_VARARGS},
    {"proc_cred", psutil_proc_cred, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_memory_maps", psutil_proc_memory_maps, METH_VARARGS},
    {"proc_name_and_args", psutil_proc_name_and_args, METH_VARARGS},
    {"proc_num_ctx_switches", psutil_proc_num_ctx_switches, METH_VARARGS},
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


struct module_state {
    PyObject *error;
};


static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_sunos",
    NULL,
    -1,
    mod_methods,
    NULL,
    NULL,
    NULL,
    NULL
};


PyObject *
PyInit__psutil_sunos(void) {
    PyObject *mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

    if (psutil_setup() != 0)
        return NULL;
    if (psutil_posix_add_constants(mod) != 0)
        return NULL;
    if (psutil_posix_add_methods(mod) != 0)
        return NULL;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SONPROC", SONPROC))
        return NULL;
#ifdef SWAIT
    if (PyModule_AddIntConstant(mod, "SWAIT", SWAIT))
        return NULL;
#else
    /* sys/proc.h started defining SWAIT somewhere
     * after Update 3 and prior to Update 5 included.
     */
    if (PyModule_AddIntConstant(mod, "SWAIT", 0))
        return NULL;
#endif
    // for process tty
    if (PyModule_AddIntConstant(mod, "PRNODEV", PRNODEV))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSED", TCPS_CLOSED))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSING", TCPS_CLOSING))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_LISTEN", TCPS_LISTEN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RCVD", TCPS_SYN_RCVD))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        return NULL;
    // sunos specific
    if (PyModule_AddIntConstant(mod, "TCPS_IDLE", TCPS_IDLE))
        return NULL;
    // sunos specific
    if (PyModule_AddIntConstant(mod, "TCPS_BOUND", TCPS_BOUND))
        return NULL;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        return NULL;

    return mod;
}
