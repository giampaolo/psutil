/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to all POSIX compliant platforms.
 */

#include <Python.h>
#include <sys/resource.h>
#include <sys/socket.h>

#include "arch/all/init.h"


static PyMethodDef mod_methods[] = {
    {"net_if_addrs", psutil_net_if_addrs, METH_VARARGS},
    {"net_if_flags", psutil_net_if_flags, METH_VARARGS},
    {"net_if_is_running", psutil_net_if_is_running, METH_VARARGS},
    {"net_if_mtu", psutil_net_if_mtu, METH_VARARGS},
#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
#endif
#if !defined(PSUTIL_OPENBSD) && !defined(PSUTIL_AIX)
    {"users", psutil_users, METH_VARARGS},
#endif
    {NULL, NULL, 0, NULL}
};


static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "_psutil_posix",
    NULL,
    -1,
    mod_methods,
    NULL,
    NULL,
    NULL,
    NULL
};

PyObject *
PyInit__psutil_posix(void) {
    PyObject *mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

    return mod;
}
