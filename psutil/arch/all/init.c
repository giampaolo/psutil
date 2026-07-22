/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Global names shared by all platforms.

#include <Python.h>

#include "init.h"

int PSUTIL_DEBUG = 0;
int PSUTIL_TESTING = 0;
int PSUTIL_CONN_NONE = 128;

#ifdef Py_GIL_DISABLED
PyMutex utxent_lock = {0};
#endif


// Enable or disable PSUTIL_DEBUG messages.
PyObject *
psutil_set_debug(PyObject *self, PyObject *args) {
    PyObject *value;
    int x;

    if (!PyArg_ParseTuple(args, "O", &value))
        return NULL;
    x = PyObject_IsTrue(value);
    if (x < 0) {
        return NULL;
    }
    else if (x == 0) {
        PSUTIL_DEBUG = 0;
    }
    else {
        PSUTIL_DEBUG = 1;
    }
    Py_RETURN_NONE;
}


// Called on module import on all platforms.
int
psutil_setup(void) {
    if (getenv("PSUTIL_DEBUG") != NULL)
        PSUTIL_DEBUG = 1;
    if (getenv("PSUTIL_TESTING") != NULL)
        PSUTIL_TESTING = 1;
    return 0;
}


// Create a custom exception once (cached in *dst) and add it to the
// module. PyModule_AddObject() steals a ref on success only, so INCREF
// first and drop it again on failure.
static int
_psutil_add_exception(
    PyObject *mod, const char *name, const char *qualname, PyObject **dst
) {
    if (*dst == NULL) {
        *dst = PyErr_NewException(qualname, NULL, NULL);
        if (*dst == NULL)
            return -1;
    }
    Py_INCREF(*dst);
    if (PyModule_AddObject(mod, name, *dst)) {
        Py_DECREF(*dst);
        return -1;
    }
    return 0;
}


// Add exceptions to the C extension module.
int
psutil_add_exceptions(PyObject *mod) {
#ifdef PSUTIL_WINDOWS
    if (_psutil_add_exception(
            mod,
            "TimeoutExpired",
            "_psutil_windows.TimeoutExpired",
            &TimeoutExpired
        ))
        return -1;
    if (_psutil_add_exception(
            mod,
            "TimeoutAbandoned",
            "_psutil_windows.TimeoutAbandoned",
            &TimeoutAbandoned
        ))
        return -1;
#elif defined(PSUTIL_POSIX)
    if (_psutil_add_exception(
            mod,
            "ZombieProcessError",
            "_psutil_posix.ZombieProcessError",
            &ZombieProcessError
        ))
        return -1;
#endif
    return 0;
}


// Initialize the Python C extension module.
PyObject *
psutil_mod_init(
    const char *name, PyMethodDef *methods, int (*exec)(PyObject *)
) {
    static PyModuleDef_Slot slots[] = {
        {Py_mod_exec, NULL},  // platform exec, filled below
#ifdef Py_mod_gil
        {Py_mod_gil, Py_MOD_GIL_NOT_USED},
#endif
        {0, NULL}
    };
    static struct PyModuleDef def = {
        .m_base = PyModuleDef_HEAD_INIT,
        .m_size = 0,
        .m_slots = slots,
    };

    slots[0].value = (void *)exec;
    def.m_name = name;
    def.m_methods = methods;
    return PyModuleDef_Init(&def);
}
