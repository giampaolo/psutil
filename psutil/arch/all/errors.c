/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#if defined(PSUTIL_WINDOWS)
#include <windows.h>
#endif


// Set OSError() exception based on errno (UNIX) or GetLastError (Windows).
PyObject *
psutil_oserror(void) {
#ifdef PSUTIL_WINDOWS
    PyErr_SetFromWindowsErr(0);
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


// Set OSError(errno=ESRCH, strerror="No such process (originated from")
// exception.
PyObject *
psutil_oserror_nsp(const char *syscall) {
    PyObject *exc;
    char msg[1024];

    sprintf(msg, "assume no such process (originated from %s)", syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", ESRCH, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// Set OSError(errno=EACCES, strerror="Permission denied" (originated from ...)
// exception.
PyObject *
psutil_oserror_ad(const char *syscall) {
    PyObject *exc;
    char msg[1024];

    sprintf(msg, "assume access denied (originated from %s)", syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", EACCES, msg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


// Set RuntimeError exception with a formatted `msg`. Optionally, it
// also accepts a variable number of args to populate `msg`.
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
