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
