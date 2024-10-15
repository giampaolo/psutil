/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <utmp.h>
#include <string.h>

#include "../../_psutil_common.h"


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmp *ut;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;

    if (py_retlist == NULL)
        return NULL;
    setutent();
    while (NULL != (ut = getutent())) {
        if (ut->ut_type != USER_PROCESS)
            continue;
        py_tuple = NULL;
        py_username = PyUnicode_DecodeFSDefault(ut->ut_user);
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(ut->ut_line);
        if (! py_tty)
            goto error;
        if (strcmp(ut->ut_host, ":0") || strcmp(ut->ut_host, ":0.0"))
            py_hostname = PyUnicode_DecodeFSDefault("localhost");
        else
            py_hostname = PyUnicode_DecodeFSDefault(ut->ut_host);
        if (! py_hostname)
            goto error;

        py_tuple = Py_BuildValue(
            "OOOd" _Py_PARSE_PID,
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            (double)ut->ut_tv.tv_sec,  // tstamp
            ut->ut_pid                // process id
        );
        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }
    endutent();
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    endutent();
    return NULL;
}
