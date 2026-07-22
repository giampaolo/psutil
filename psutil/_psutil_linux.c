/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Linux-specific functions.

#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include <Python.h>
#include <linux/ethtool.h>  // DUPLEX_*

#include "arch/all/init.h"

// May happen on old RedHat versions, see:
// https://github.com/giampaolo/psutil/issues/607
#ifndef DUPLEX_UNKNOWN
#define DUPLEX_UNKNOWN 0xff
#endif

static PyMethodDef mod_methods[] = {
    // --- per-process functions
    {"proc_ioprio_get", psutil_proc_ioprio_get, METH_VARARGS},
    {"proc_ioprio_set", psutil_proc_ioprio_set, METH_VARARGS},
#ifdef PSUTIL_HAS_CPU_AFFINITY
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS},
#endif
    // --- system related functions
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
#ifdef PSUTIL_HAS_HEAP_INFO
    {"heap_info", psutil_heap_info, METH_VARARGS},
#endif
#ifdef PSUTIL_HAS_HEAP_TRIM
    {"heap_trim", psutil_heap_trim, METH_VARARGS},
#endif

    // --- linux specific
    {"linux_sysinfo", psutil_linux_sysinfo, METH_VARARGS},
    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},
    {NULL, NULL, 0, NULL}
};


static int
psutil_linux_exec(PyObject *mod) {
    if (psutil_setup() != 0)
        return -1;
    if (psutil_posix_add_constants(mod) != 0)
        return -1;
    if (psutil_posix_add_methods(mod) != 0)
        return -1;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        return -1;
    if (PyModule_AddIntConstant(mod, "DUPLEX_HALF", DUPLEX_HALF))
        return -1;
    if (PyModule_AddIntConstant(mod, "DUPLEX_FULL", DUPLEX_FULL))
        return -1;
    if (PyModule_AddIntConstant(mod, "DUPLEX_UNKNOWN", DUPLEX_UNKNOWN))
        return -1;

    return 0;
}

PyMODINIT_FUNC
PyInit__psutil_linux(void) {
    return psutil_mod_init("_psutil_linux", mod_methods, psutil_linux_exec);
}
