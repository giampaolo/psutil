/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Global names shared by all platforms.

#include <Python.h>
#ifdef PSUTIL_WINDOWS
#include <windows.h>
#endif

#include "init.h"

int PSUTIL_DEBUG = 0;
int PSUTIL_CONN_NONE = 128;

#ifdef Py_GIL_DISABLED
PyMutex utxent_lock = {0};
#endif


// Set OSError(errno=ESRCH, strerror="No such process (originated from")
// Python exception.
PyObject *
NoSuchProcess(const char *syscall) {
    PyObject *exc;
    char msg[1024];

    sprintf(msg, "assume no such process (originated from %s)", syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// Set OSError(errno=EACCES, strerror="Permission denied" (originated from ...)
// Python exception.
PyObject *
AccessDenied(const char *syscall) {
    PyObject *exc;
    char msg[1024];

    sprintf(msg, "assume access denied (originated from %s)", syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", EACCES, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// Same as PyErr_SetFromErrno(0) but adds the syscall to the exception
// message.
PyObject *
psutil_PyErr_SetFromOSErrnoWithSyscall(const char *syscall) {
    char fullmsg[1024];

#ifdef PSUTIL_WINDOWS
    DWORD dwLastError = GetLastError();
    sprintf(fullmsg, "(originated from %s)", syscall);
    PyErr_SetFromWindowsErrWithFilename(dwLastError, fullmsg);
#else
    PyObject *exc;
    sprintf(fullmsg, "%s (originated from %s)", strerror(errno), syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", errno, fullmsg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
#endif
    return NULL;
}


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


// Raise OverflowError if Python int value overflowed when converting
// to pid_t. Raise ValueError if Python int value is negative.
// Otherwise, return None.
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


// Use it when invalid args are passed to a C function.
int
psutil_badargs(const char *funcname) {
    PyErr_Format(
        PyExc_RuntimeError, "%s() invalid args passed to function", funcname
    );
    return -1;
}


// Called on module import on all platforms.
int
psutil_setup(void) {
    if (getenv("PSUTIL_DEBUG") != NULL)
        PSUTIL_DEBUG = 1;
    return 0;
}
