/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <utmp.h>

#include "../../arch/all/init.h"


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;

    struct utmp ut;
    FILE *fp;

    Py_BEGIN_ALLOW_THREADS
    fp = fopen(_PATH_UTMP, "r");
    Py_END_ALLOW_THREADS
    if (fp == NULL) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, _PATH_UTMP);
        goto error;
    }

    while (fread(&ut, sizeof(ut), 1, fp) == 1) {
        if (*ut.ut_name == '\0')
            continue;
        py_username = PyUnicode_DecodeFSDefault(ut.ut_name);
        if (!py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(ut.ut_line);
        if (!py_tty)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(ut.ut_host);
        if (!py_hostname)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOOdO)",
            py_username,  // username
            py_tty,  // tty
            py_hostname,  // hostname
            (double)ut.ut_time,  // start time
            Py_None  // pid
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }

    fclose(fp);
    return py_retlist;

error:
    fclose(fp);
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}
