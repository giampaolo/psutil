/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * macOS platform-specific module methods.
 */

#include <Python.h>
#include <sys/proc.h>
#include <netinet/tcp_fsm.h>

#include "_psutil_common.h"
#include "arch/osx/cpu.h"
#include "arch/osx/disk.h"
#include "arch/osx/mem.h"
#include "arch/osx/net.h"
#include "arch/osx/proc.h"
#include "arch/osx/sensors.h"
#include "arch/osx/sys.h"


static PyMethodDef mod_methods[] = {
    // --- per-process functions
    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS},
    {"proc_connections", psutil_proc_connections, METH_VARARGS},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_exe", psutil_proc_exe, METH_VARARGS},
    {"proc_kinfo_oneshot", psutil_proc_kinfo_oneshot, METH_VARARGS},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS},
    {"proc_name", psutil_proc_name, METH_VARARGS},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS},
    {"proc_pidtaskinfo_oneshot", psutil_proc_pidtaskinfo_oneshot, METH_VARARGS},
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
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"pids", psutil_pids, METH_VARARGS},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},
    {"users", psutil_users, METH_VARARGS},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3
    #define INITERR return NULL

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

    PyObject *PyInit__psutil_osx(void)
#else  /* PY_MAJOR_VERSION */
    #define INITERR return

    void init_psutil_osx(void)
#endif  /* PY_MAJOR_VERSION */
{
#if PY_MAJOR_VERSION >= 3
    PyObject *mod = PyModule_Create(&moduledef);
#else
    PyObject *mod = Py_InitModule("_psutil_osx", mod_methods);
#endif
    if (mod == NULL)
        INITERR;

    if (psutil_setup() != 0)
        INITERR;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        INITERR;
    // process status constants, defined in:
    // http://fxr.watson.org/fxr/source/bsd/sys/proc.h?v=xnu-792.6.70#L149
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        INITERR;
    // connection status constants
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSED", TCPS_CLOSED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSING", TCPS_CLOSING))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_LISTEN", TCPS_LISTEN))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RECEIVED", TCPS_SYN_RECEIVED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        INITERR;

    if (mod == NULL)
        INITERR;
#if PY_MAJOR_VERSION >= 3
    return mod;
#endif
}
