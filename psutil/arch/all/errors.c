/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <errno.h>
#include <string.h>
#if defined(PSUTIL_WINDOWS)
#include <windows.h>
#endif

#include "init.h"

#define MSG_SIZE 512


// Set OSError() based on errno (UNIX) or GetLastError() (Windows).
PyObject *
psutil_oserror(void) {
#ifdef PSUTIL_WINDOWS
    PyErr_SetFromWindowsErr(GetLastError());
#else
    PyErr_SetFromErrno(PyExc_OSError);
#endif
    return NULL;
}


// Same as above, but adds the syscall to the exception message. On
// Windows this is achieved by setting the `filename` attribute of the
// OSError object.
PyObject *
psutil_oserror_wsyscall(const char *syscall) {
    char msg[MSG_SIZE];

#ifdef PSUTIL_WINDOWS
    DWORD err = GetLastError();
    str_format(msg, sizeof(msg), "(originated from %s)", syscall);
    PyErr_SetFromWindowsErrWithFilename(err, msg);
#else
    PyObject *exc;
    str_format(
        msg, sizeof(msg), "%s (originated from %s)", strerror(errno), syscall
    );
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", errno, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
#endif
    return NULL;
}


// Set OSError(errno=ESRCH) ("No such process").
PyObject *
psutil_oserror_nsp(const char *syscall) {
    PyObject *exc;
    char msg[MSG_SIZE];

    str_format(
        msg, sizeof(msg), "force no such process (originated from %s)", syscall
    );
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// Set OSError(errno=EACCES) ("Permission denied").
PyObject *
psutil_oserror_ad(const char *syscall) {
    PyObject *exc;
    char msg[MSG_SIZE];

    str_format(
        msg,
        sizeof(msg),
        "force permission denied (originated from %s)",
        syscall
    );
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", EACCES, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// Set RuntimeError with formatted `msg` and optional arguments.
PyObject *
psutil_runtime_error(const char *msg, ...) {
    va_list args;

    va_start(args, msg);
    PyErr_FormatV(PyExc_RuntimeError, msg, args);
    va_end(args);
    return NULL;
}


// Use it when invalid args are passed to a C function.
int
psutil_badargs(const char *funcname) {
    PyErr_Format(
        PyExc_RuntimeError, "%s() invalid args passed to function", funcname
    );
    return -1;
}
