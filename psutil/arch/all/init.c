/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// ====================================================================
// --- Global vars
// ====================================================================

int PSUTIL_DEBUG = 0;
int PSUTIL_CONN_NONE = 128;

// ====================================================================
// --- Global utils
// ====================================================================

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

/*
 * Raise OverflowError if Python int value overflowed when converting to pid_t.
 * Raise ValueError if Python int value is negative.
 * Otherwise, return None.
 */
PyObject *
psutil_check_pid_range(PyObject *self, PyObject *args) {
#ifdef PSUTIL_WINDOWS
    DWORD pid;
#else
    pid_t pid;
#endif

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (pid < 0) {
        PyErr_SetString(PyExc_ValueError, "pid must be a positive integer");
        return NULL;
    }
    Py_RETURN_NONE;
}
