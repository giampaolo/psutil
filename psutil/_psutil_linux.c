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
#include <linux/ethtool.h>  // DUPLEX_*

#include "arch/all/init.h"

// May happen on old RedHat versions, see:
// https://github.com/giampaolo/psutil/issues/607
#ifndef DUPLEX_UNKNOWN
    #define DUPLEX_UNKNOWN 0xff
#endif

static PyMethodDef mod_methods[] = {
    // --- per-process functions
#ifdef PSUTIL_HAS_IOPRIO
    {"proc_ioprio_get", psutil_proc_ioprio_get, METH_VARARGS},
    {"proc_ioprio_set", psutil_proc_ioprio_set, METH_VARARGS},
#endif
#ifdef PSUTIL_HAS_CPU_AFFINITY
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS},
#endif
    // --- system related functions
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
    // --- linux specific
    {"linux_sysinfo", psutil_linux_sysinfo, METH_VARARGS},
    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},
    {NULL, NULL, 0, NULL}
};


static int module_loaded = 0;

static int
_psutil_linux_exec(PyObject *mod) {
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
    if (PyModule_AddIntConstant(mod, "DUPLEX_HALF", DUPLEX_HALF))
        return -1;
    if (PyModule_AddIntConstant(mod, "DUPLEX_FULL", DUPLEX_FULL))
        return -1;
    if (PyModule_AddIntConstant(mod, "DUPLEX_UNKNOWN", DUPLEX_UNKNOWN))
        return -1;

    return 0;
}

static struct PyModuleDef_Slot _psutil_linux_slots[] = {
    {Py_mod_exec, _psutil_linux_exec},
    {0, NULL},
};

static struct PyModuleDef module_def = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "_psutil_linux",
    .m_size = 0,
    .m_methods = mod_methods,
    .m_slots = _psutil_linux_slots,
};

PyMODINIT_FUNC
PyInit__psutil_linux(void) {
    return PyModuleDef_Init(&module_def);
}
