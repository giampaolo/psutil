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
    int saved_errno = errno;
    str_format(
        msg,
        sizeof(msg),
        "%s (originated from %s)",
        strerror(saved_errno),
        syscall
    );
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", saved_errno, msg);
    if (exc != NULL) {
        PyErr_SetObject(PyExc_OSError, exc);
        Py_DECREF(exc);
    }
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
    if (exc != NULL) {
        PyErr_SetObject(PyExc_OSError, exc);
        Py_DECREF(exc);
    }
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
    if (exc != NULL) {
        PyErr_SetObject(PyExc_OSError, exc);
        Py_DECREF(exc);
    }
    return NULL;
}


// Print a debug message to stderr. Don't call this directly, use the
// psutil_debug() macro, which fills in `file` and `line` with the
// caller's location.
void
_psutil_debug_impl(const char *file, int lineno, const char *fmt, ...) {
    va_list args;

    if (!PSUTIL_DEBUG)
        return;
    fprintf(stderr, "psutil-debug [%s:%d]> ", file, lineno);
    va_start(args, fmt);
    vfprintf(stderr, fmt, args);
    va_end(args);
    fprintf(stderr, "\n");
}


// Emit a RuntimeWarning, also printed as a debug message. It never
// raises: with -W error the exception is discarded. Don't call this
// directly, use the psutil_warn() macro, which fills in `file` and
// `lineno` with the caller's location.
void
_psutil_warn_impl(const char *file, int lineno, const char *fmt, ...) {
    char msg[MSG_SIZE];
    char full[MSG_SIZE + 512];
    va_list args;
    int ret;
    PyGILState_STATE gstate;

    va_start(args, fmt);
    ret = vsnprintf(msg, sizeof(msg), fmt, args);
    va_end(args);
    // If vsnprintf() failed msg is garbage.
    if (ret < 0)
        str_copy(msg, sizeof(msg), "psutil_warn: bad format");

    _psutil_debug_impl(file, lineno, "%s", msg);

    str_format(
        full, sizeof(full), "%s (originated from %s:%d)", msg, file, lineno
    );
    // Grab the GIL: unlike psutil_debug() this is safe to call also
    // inside Py_BEGIN/END_ALLOW_THREADS blocks.
    gstate = PyGILState_Ensure();
    if (PyErr_WarnEx(PyExc_RuntimeWarning, full, 1) != 0)
        PyErr_Clear();
    PyGILState_Release(gstate);
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
