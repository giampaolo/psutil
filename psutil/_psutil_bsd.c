/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola', Landry Breuil
 * (OpenBSD implementation), Ryo Onodera (NetBSD implementation).
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
 * Platform-specific module methods for FreeBSD and OpenBSD.

 * OpenBSD references:
 * - OpenBSD source code: https://github.com/openbsd/src
 *
 * OpenBSD / NetBSD: missing APIs compared to FreeBSD implementation:
 * - psutil.net_connections()
 * - psutil.Process.get/set_cpu_affinity()  (not supported natively)
 * - psutil.Process.memory_maps()
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


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef mod_methods[] = {
    // --- per-process functions

    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_name", psutil_proc_name, METH_VARARGS},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS},
    {"proc_oneshot_info", psutil_proc_oneshot_info, METH_VARARGS},
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
    {"cpu_topology", psutil_cpu_topology, METH_VARARGS},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS},
    {"sensors_cpu_temperature", psutil_sensors_cpu_temperature, METH_VARARGS},
#endif
    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_psutil_bsd",
    NULL,
    -1,
    mod_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyObject *
PyInit__psutil_bsd(void) {
    PyObject *v;
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

        // process status constants
#ifdef PSUTIL_FREEBSD
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
    if (PyModule_AddIntConstant(mod, "SWAIT", SWAIT))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SLOCK", SLOCK))
        return NULL;
#elif PSUTIL_OPENBSD
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        return NULL;  // unused
    if (PyModule_AddIntConstant(mod, "SDEAD", SDEAD))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SONPROC", SONPROC))
        return NULL;
#elif defined(PSUTIL_NETBSD)
    if (PyModule_AddIntConstant(mod, "SIDL", LSIDL))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SRUN", LSRUN))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSLEEP", LSSLEEP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SSTOP", LSSTOP))
        return NULL;
    if (PyModule_AddIntConstant(mod, "SZOMB", LSZOMB))
        return NULL;
#if __NetBSD_Version__ < 500000000
    if (PyModule_AddIntConstant(mod, "SDEAD", LSDEAD))
        return NULL;
#endif
    if (PyModule_AddIntConstant(mod, "SONPROC", LSONPROC))
        return NULL;
    // unique to NetBSD
    if (PyModule_AddIntConstant(mod, "SSUSPENDED", LSSUSPENDED))
        return NULL;
#endif

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
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", 128))
        return NULL;

    return mod;
}
