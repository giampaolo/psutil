/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <utmp.h>

#include "../../_psutil_common.h"


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmp *ut;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_user_proc = NULL;

    if (py_retlist == NULL)
        return NULL;
    setutent();
    while (NULL != (ut = getutent())) {
        py_tuple = NULL;
        py_user_proc = NULL;
        if (ut->ut_type == USER_PROCESS)
            py_user_proc = Py_True;
        else
            py_user_proc = Py_False;
        py_username = PyUnicode_DecodeFSDefault(ut->ut_user);
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(ut->ut_line);
        if (! py_tty)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(ut->ut_host);
        if (! py_hostname)
            goto error;

        py_tuple = Py_BuildValue(
            "OOOdO" _Py_PARSE_PID,
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            (double)ut->ut_tv.tv_sec,  // tstamp
            py_user_proc,             // (bool) user process
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
