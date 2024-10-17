/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Linux-specific functions.
 */

#ifndef _GNU_SOURCE
    #define _GNU_SOURCE 1
#endif
#include <Python.h>

#include "_psutil_common.h"
#include "arch/gnu/disk.h"
#include "arch/gnu/mem.h"
#include "arch/gnu/net.h"
#include "arch/gnu/proc.h"
#include "arch/gnu/users.h"


static PyMethodDef mod_methods[] = {
    // --- per-process functions
    {"proc_ioprio_get", psutil_proc_ioprio_get, METH_VARARGS},
    {"proc_ioprio_set", psutil_proc_ioprio_set, METH_VARARGS},
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS},
    // --- system related functions
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"users", psutil_users, METH_VARARGS},
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
    // --- gnu specific
    {"gnu_meminfo", psutil_gnu_meminfo, METH_VARARGS},
    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},
    {NULL, NULL, 0, NULL}
};

#define DUPLEX_UNKNOWN 0xff

#if PY_MAJOR_VERSION >= 3
    #define INITERR return NULL

    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_psutil_gnu",
        NULL,
        -1,
        mod_methods,
        NULL,
        NULL,
        NULL,
        NULL
    };

    PyObject *PyInit__psutil_gnu(void)
#else  /* PY_MAJOR_VERSION */
    #define INITERR return

    void init_psutil_gnu(void)
#endif  /* PY_MAJOR_VERSION */
{
#if PY_MAJOR_VERSION >= 3
    PyObject *mod = PyModule_Create(&moduledef);
#else
    PyObject *mod = Py_InitModule("_psutil_gnu", mod_methods);
#endif
    if (mod == NULL)
        INITERR;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION)) INITERR;
    if (PyModule_AddIntConstant(mod, "DUPLEX_UNKNOWN", DUPLEX_UNKNOWN)) INITERR;

    psutil_setup();

    if (mod == NULL)
        INITERR;
#if PY_MAJOR_VERSION >= 3
    return mod;
#endif
}
