/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// macOS platform-specific module methods.

#include <Python.h>
#include <sys/time.h>  // needed for old macOS versions
#include <sys/proc.h>
#include <netinet/tcp_fsm.h>

#include "arch/all/init.h"
#include "arch/osx/init.h"


static PyMethodDef mod_methods[] = {
    // --- per-process functions
    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_exe", psutil_proc_exe, METH_VARARGS},
    {"proc_is_zombie", psutil_proc_is_zombie, METH_VARARGS},
    {"proc_kinfo_oneshot", psutil_proc_kinfo_oneshot, METH_VARARGS},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS},
    {"proc_name", psutil_proc_name, METH_VARARGS},
    {"proc_net_connections", psutil_proc_net_connections, METH_VARARGS},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS},
    {"proc_pidtaskinfo_oneshot", psutil_proc_pidtaskinfo_oneshot, METH_VARARGS
    },
    {"proc_threads", psutil_proc_threads, METH_VARARGS},

    // --- system-related functions
    {"boot_time", psutil_boot_time, METH_VARARGS},
    {"cpu_count_cores", psutil_cpu_count_cores, METH_VARARGS},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS},
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"cpu_times", psutil_cpu_times, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"disk_usage_used", psutil_disk_usage_used, METH_VARARGS},
    {"has_cpu_freq", psutil_has_cpu_freq, METH_VARARGS},
    {"heap_info", psutil_heap_info, METH_VARARGS},
    {"heap_trim", psutil_heap_trim, METH_VARARGS},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"pids", psutil_pids, METH_VARARGS},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_psutil_osx",
    NULL,
    -1,
    mod_methods,
    NULL,
    NULL,
    NULL,
    NULL
};


PyObject *
PyInit__psutil_osx(void) {
    PyObject *mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

    if (psutil_setup() != 0)
        return NULL;
    if (psutil_setup_osx() != 0)
        return NULL;
    if (psutil_posix_add_constants(mod) != 0)
        return NULL;
    if (psutil_posix_add_methods(mod) != 0)
        return NULL;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        return NULL;
    // process status constants, defined in:
    // http://fxr.watson.org/fxr/source/bsd/sys/proc.h?v=xnu-792.6.70#L149
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        return NULL;
    // connection status constants
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
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RECEIVED", TCPS_SYN_RECEIVED))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        return NULL;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        return NULL;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        return NULL;

    return mod;
}
