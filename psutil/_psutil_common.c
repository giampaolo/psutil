/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Routines common to all platforms.
 */

#ifdef PSUTIL_POSIX
#include <sys/types.h>
#include <signal.h>
#endif

#include <Python.h>


/*
 * Set OSError(errno=ESRCH, strerror="No such process") Python exception.
 */
PyObject *
NoSuchProcess(void) {
    PyObject *exc;
    char *msg = strerror(ESRCH);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


/*
 * Set OSError(errno=EACCES, strerror="Permission denied") Python exception.
 */
PyObject *
AccessDenied(void) {
    PyObject *exc;
    char *msg = strerror(EACCES);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", EACCES, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


#ifdef PSUTIL_POSIX
/*
 * Check if PID exists. Return values:
 * 1: exists
 * 0: does not exist
 * -1: error (Python exception is set)
 */
int
psutil_pid_exists(long pid) {
    int ret;

    // No negative PID exists, plus -1 is an alias for sending signal
    // too all processes except system ones. Not what we want.
    if (pid < 0)
        return 0;

    // As per "man 2 kill" PID 0 is an alias for sending the seignal to
    // every  process in the process group of the calling process.
    // Not what we want.
    if (pid == 0) {
#if defined(PSUTIL_LINUX) || defined(BSD)
        // PID 0 does not exist at leas on Linux and all BSDs.
        return 0;
#else
        // On OSX it does.
        // TODO: check Solaris.
        return 1;
#endif
    }

    ret = kill(pid , 0);
    if (ret == 0)
        return 1;
    else {
        if (errno == ESRCH)
            return 0;
        else if (errno == EPERM)
            return 1;
        else {
            PyErr_SetFromErrno(PyExc_OSError);
            return -1;
        }
    }
}


int
psutil_raise_ad_or_nsp(long pid) {
    // Set exception to AccessDenied if pid exists else NoSuchProcess.
    int ret;
    ret = psutil_pid_exists(pid);
    if (ret == 0)
        NoSuchProcess();
    else if (ret == 1)
        AccessDenied();
    return ret;
}
#endif
