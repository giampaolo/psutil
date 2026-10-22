/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <errno.h>
#include <stdlib.h>
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


// Set OSError(errnum, msg). msg is locale text (strerror() output),
// so decode it the way Python does instead of assuming UTF-8, or a
// non-UTF-8 locale turns the OSError into a UnicodeDecodeError.
static PyObject *
psutil_oserror_msg(int errnum, const char *msg) {
    PyObject *text;
    PyObject *exc;

    text = PyUnicode_DecodeLocale(msg, "surrogateescape");
    if (text == NULL)
        return NULL;
    exc = PyObject_CallFunction(PyExc_OSError, "(iO)", errnum, text);
    Py_DECREF(text);
    if (exc != NULL) {
        PyErr_SetObject(PyExc_OSError, exc);
        Py_DECREF(exc);
    }
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
    int saved_errno = errno;
    str_format(
        msg,
        sizeof(msg),
        "%s (originated from %s)",
        strerror(saved_errno),
        syscall
    );
    psutil_oserror_msg(saved_errno, msg);
#endif
    return NULL;
}


// Set OSError(errno=ESRCH) ("No such process").
PyObject *
psutil_oserror_nsp(const char *syscall) {
    char msg[MSG_SIZE];

    str_format(
        msg, sizeof(msg), "force no such process (originated from %s)", syscall
    );
    return psutil_oserror_msg(ESRCH, msg);
}


// Set OSError(errno=EACCES) ("Permission denied").
PyObject *
psutil_oserror_ad(const char *syscall) {
    char msg[MSG_SIZE];

    str_format(
        msg,
        sizeof(msg),
        "force permission denied (originated from %s)",
        syscall
    );
    return psutil_oserror_msg(EACCES, msg);
}


// Print a debug message to stderr if PSUTIL_DEBUG mode is enabled.
// Don't call this directly, use the psutil_debug() macro.
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
// raises: with -W error the exception is discarded. Use it for events
// which are never supposed to happen, and imply a psutil bug. Don't
// call this directly, use the psutil_warn() macro.
// Plain [v]snprintf() and no str_*() helpers in here: their failure
// path calls psutil_warn(), which would recurse back into us.
void
_psutil_warn_impl(const char *file, int lineno, const char *fmt, ...) {
    char msg[MSG_SIZE];
    char full[MSG_SIZE + 512];
    const char *warning;
    va_list args;
    int ret;
    PyGILState_STATE gstate;
    PyObject *text;

    va_start(args, fmt);
    ret = vsnprintf(msg, sizeof(msg), fmt, args);
    va_end(args);
    msg[sizeof(msg) - 1] = '\0';
    // If vsnprintf() failed msg is garbage.
    warning = (ret < 0) ? "psutil_warn: bad format" : msg;

    _psutil_debug_impl(file, lineno, "%s", warning);

    ret = snprintf(
        full, sizeof(full), "%s (originated from %s:%d)", warning, file, lineno
    );
    full[sizeof(full) - 1] = '\0';
    if (ret >= 0)
        warning = full;

    if (PSUTIL_TESTING) {
        fprintf(stderr, "CRITICAL: %s\n", warning);
        fflush(stderr);
        exit(EXIT_FAILURE);  // terminate execution
    }

    // Grab the GIL: unlike psutil_debug() this is safe to call also
    // inside Py_BEGIN/END_ALLOW_THREADS blocks. Caveat: the
    // PyGILState_* API doesn't support sub-interpreters.
    gstate = PyGILState_Ensure();
    text = PyUnicode_DecodeLocale(warning, "surrogateescape");
    if (text == NULL) {
        PyErr_Clear();
    }
    else {
        if (PyErr_WarnFormat(PyExc_RuntimeWarning, 1, "%U", text) != 0)
            PyErr_Clear();
        Py_DECREF(text);
    }
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
