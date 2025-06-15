/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to Sun OS Solaris platforms.
 *
 * Thanks to Justin Venus who originally wrote a consistent part of
 * this in Cython which I later on translated in C.
 */

/* fix compilation issue on SunOS 5.10, see:
 * https://github.com/giampaolo/psutil/issues/421
 * https://github.com/giampaolo/psutil/issues/1077
*/

#define _STRUCTURED_PROC 1

#include <Python.h>

#if !defined(_LP64) && _FILE_OFFSET_BITS == 64
#  undef _FILE_OFFSET_BITS
#  undef _LARGEFILE64_SOURCE
#endif

#include <inet/tcp.h>

#include "arch/all/init.h"
#include "arch/sunos/cpu.h"
#include "arch/sunos/disk.h"
#include "arch/sunos/environ.h"
#include "arch/sunos/mem.h"
#include "arch/sunos/net.h"
#include "arch/sunos/proc.h"
#include "arch/sunos/sys.h"


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
    {"users", psutil_users, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


struct module_state {
    PyObject *error;
};


static int module_loaded = 0;

static int
_psutil_sunos_exec(PyObject *mod) {
    // https://docs.python.org/3/howto/isolating-extensions.html#opt-out-limiting-to-one-module-object-per-process
    if (module_loaded) {
        PyErr_SetString(PyExc_ImportError,
                        "cannot load module more than once per process");
        return -1;
    }
    module_loaded = 1;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

    if (psutil_setup() != 0)
        return -1;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        return -1;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        return -1;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        return -1;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        return -1;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        return -1;
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        return -1;
    if (PyModule_AddIntConstant(mod, "SONPROC", SONPROC))
        return -1;
#ifdef SWAIT
    if (PyModule_AddIntConstant(mod, "SWAIT", SWAIT))
        return -1;
#else
    /* sys/proc.h started defining SWAIT somewhere
     * after Update 3 and prior to Update 5 included.
     */
    if (PyModule_AddIntConstant(mod, "SWAIT", 0))
        return -1;
#endif
    // for process tty
    if (PyModule_AddIntConstant(mod, "PRNODEV", PRNODEV))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSED", TCPS_CLOSED))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSING", TCPS_CLOSING))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_LISTEN", TCPS_LISTEN))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RCVD", TCPS_SYN_RCVD))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        return -1;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        return -1;
    // sunos specific
    if (PyModule_AddIntConstant(mod, "TCPS_IDLE", TCPS_IDLE))
        return -1;
    // sunos specific
    if (PyModule_AddIntConstant(mod, "TCPS_BOUND", TCPS_BOUND))
        return -1;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        return -1;

    return 0;
}

static struct PyModuleDef_Slot _psutil_sunos_slots[] = {
    {Py_mod_exec, _psutil_sunos_exec},
    {0, NULL},
};

static struct PyModuleDef module_def = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "_psutil_sunos",
    .m_size = 0,
    .m_methods = mod_methods,
    .m_slots = _psutil_sunos_slots,
};

PyMODINIT_FUNC
PyInit__psutil_sunos(void) {
    return PyModuleDef_Init(&module_def);
}
