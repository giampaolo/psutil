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
