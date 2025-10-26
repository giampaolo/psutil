/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#if defined(PSUTIL_WINDOWS) || defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
#include <Python.h>

#include "init.h"


PyObject *
psutil_pids(PyObject *self, PyObject *args) {
#ifdef PSUTIL_WINDOWS
    DWORD *pids_array = NULL;
#else
    pid_t *pids_array = NULL;
#endif
    int pids_count = 0;
    int i;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_pid = NULL;

    if (!py_retlist)
        return NULL;

    if (_psutil_pids(&pids_array, &pids_count) != 0)
        goto error;

    if (pids_count == 0) {
        PyErr_Format(PyExc_RuntimeError, "no PIDs found");
        goto error;
    }

    for (i = 0; i < pids_count; i++) {
        py_pid = PyLong_FromPid(pids_array[i]);
        if (!py_pid)
            goto error;
        if (PyList_Append(py_retlist, py_pid))
            goto error;
        Py_CLEAR(py_pid);
    }

    free(pids_array);
    return py_retlist;

error:
    Py_XDECREF(py_pid);
    Py_DECREF(py_retlist);
    free(pids_array);
    return NULL;
}
#endif
