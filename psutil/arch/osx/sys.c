/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// System related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c

#include <Python.h>
#include <sys/sysctl.h>
#include <utmpx.h>

#include "../../_psutil_common.h"


PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    // fetch sysctl "kern.boottime"
    static int request[2] = { CTL_KERN, KERN_BOOTTIME };
    struct timeval result;
    size_t result_len = sizeof result;
    time_t boot_time = 0;

    if (sysctl(request, 2, &result, &result_len, NULL, 0) == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    boot_time = result.tv_sec;
    return Py_BuildValue("f", (float)boot_time);
}


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmpx *utx;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    while ((utx = getutxent()) != NULL) {
        if (utx->ut_type != USER_PROCESS)
            continue;
        py_username = PyUnicode_DecodeFSDefault(utx->ut_user);
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(utx->ut_line);
        if (! py_tty)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(utx->ut_host);
        if (! py_hostname)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOOdi)",
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            (double)utx->ut_tv.tv_sec, // start time
            utx->ut_pid               // process id
        );
        if (!py_tuple) {
            endutxent();
            goto error;
        }
        if (PyList_Append(py_retlist, py_tuple)) {
            endutxent();
            goto error;
        }
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }

    endutxent();
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}
