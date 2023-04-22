/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <stdio.h>
#include <sys/param.h>  // OS version
#ifdef PSUTIL_FREEBSD
    #if __FreeBSD_version < 900000
        #include <utmp.h>
    #else
        #include <utmpx.h>
    #endif
#elif PSUTIL_NETBSD
    #include <utmpx.h>
#elif PSUTIL_OPENBSD
    #include <utmp.h>
#endif


// Return a Python float indicating the system boot time expressed in
// seconds since the epoch.
PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    // fetch sysctl "kern.boottime"
    static int request[2] = { CTL_KERN, KERN_BOOTTIME };
    struct timeval boottime;
    size_t len = sizeof(boottime);

    if (sysctl(request, 2, &boottime, &len, NULL, 0) == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    return Py_BuildValue("d", (double)boottime.tv_sec);
}


PyObject *
psutil_users(PyObject *self, PyObject *args) {
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_pid = NULL;

    if (py_retlist == NULL)
        return NULL;

#if (defined(__FreeBSD_version) && (__FreeBSD_version < 900000)) || PSUTIL_OPENBSD
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
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(ut.ut_line);
        if (! py_tty)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(ut.ut_host);
        if (! py_hostname)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOOdi)",
            py_username,        // username
            py_tty,             // tty
            py_hostname,        // hostname
            (double)ut.ut_time,  // start time
#if defined(PSUTIL_OPENBSD) || (defined(__FreeBSD_version) && __FreeBSD_version < 900000)
            -1                  // process id (set to None later)
#else
            ut.ut_pid           // TODO: use PyLong_FromPid
#endif
        );
        if (!py_tuple) {
            fclose(fp);
            goto error;
        }
        if (PyList_Append(py_retlist, py_tuple)) {
            fclose(fp);
            goto error;
        }
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }

    fclose(fp);
#else
    struct utmpx *utx;
    setutxent();
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
#ifdef PSUTIL_OPENBSD
        py_pid = Py_BuildValue("i", -1);  // set to None later
#else
        py_pid = PyLong_FromPid(utx->ut_pid);
#endif
        if (! py_pid)
            goto error;

        py_tuple = Py_BuildValue(
            "(OOOdO)",
            py_username,   // username
            py_tty,        // tty
            py_hostname,   // hostname
            (double)utx->ut_tv.tv_sec,  // start time
            py_pid         // process id
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
        Py_CLEAR(py_pid);
    }

    endutxent();
#endif
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_pid);
    Py_DECREF(py_retlist);
    return NULL;
}
