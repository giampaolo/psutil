/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "../../arch/all/init.h"

#ifdef PSUTIL_HAS_POSIX_USERS
#include <Python.h>
#include <string.h>

#include <utmpx.h>


static void
setup() {
    UTXENT_MUTEX_LOCK();
    setutxent();
}


static void
teardown() {
    endutxent();
    UTXENT_MUTEX_UNLOCK();
}


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmpx *ut;
    size_t host_len;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    setup();

    while ((ut = getutxent()) != NULL) {
        if (ut->ut_type != USER_PROCESS)
            continue;
        py_tuple = NULL;

        py_username = PyUnicode_DecodeFSDefault(ut->ut_user);
        if (!py_username)
            goto error;

        py_tty = PyUnicode_DecodeFSDefault(ut->ut_line);
        if (!py_tty)
            goto error;

        host_len = strnlen(ut->ut_host, sizeof(ut->ut_host));
        if (host_len == 0 || (strcmp(ut->ut_host, ":0") == 0)
            || (strcmp(ut->ut_host, ":0.0") == 0))
        {
            py_hostname = PyUnicode_DecodeFSDefault("localhost");
        }
        else {
            // ut_host might not be null-terminated if the hostname is
            // very long, so we do it.
            char hostbuf[sizeof(ut->ut_host)];
            memcpy(hostbuf, ut->ut_host, host_len);
            hostbuf[host_len] = '\0';
            py_hostname = PyUnicode_DecodeFSDefault(hostbuf);
        }
        if (!py_hostname)
            goto error;

        py_tuple = Py_BuildValue(
            "OOOd" _Py_PARSE_PID,
            py_username,  // username
            py_tty,  // tty
            py_hostname,  // hostname
            (double)ut->ut_tv.tv_sec,  // tstamp
            ut->ut_pid  // process id
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

    teardown();
    return py_retlist;

error:
    teardown();
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}
#endif  // PSUTIL_HAS_POSIX_USERS
