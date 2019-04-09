/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Routines common to all platforms.
 */

#include <Python.h>
#ifdef _WIN32
#include <windows.h>
#endif

#include "_psutil_common.h"

// Global vars.
int PSUTIL_DEBUG = 0;
int PSUTIL_TESTING = 0;


/*
 * Backport of unicode FS APIs from Python 3.
 * On Python 2 we just return a plain byte string
 * which is never supposed to raise decoding errors.
 * See: https://github.com/giampaolo/psutil/issues/1040
 */
#if PY_MAJOR_VERSION < 3
PyObject *
PyUnicode_DecodeFSDefault(char *s) {
    return PyString_FromString(s);
}


PyObject *
PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size) {
    return PyString_FromStringAndSize(s, size);
}
#endif


/*
 * Set OSError(errno=ESRCH, strerror="No such process") Python exception.
 * If msg != "" the exception message will change in accordance.
 */
PyObject *
NoSuchProcess(const char *msg) {
    PyObject *exc;
    exc = PyObject_CallFunction(
        PyExc_OSError, "(is)", ESRCH, strlen(msg) ? msg : strerror(ESRCH));
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


/*
 * Same as PyErr_SetFromErrno(0) but adds the syscall to the exception
 * message.
 */
PyObject *
PyErr_SetFromOSErrnoWithSyscall(const char *syscall) {
    char fullmsg[1024];

#ifdef _WIN32
    sprintf(fullmsg, "(originated from %s)", syscall);
    PyErr_SetFromWindowsErrWithFilename(GetLastError(), fullmsg);
#else
    PyObject *exc;
    sprintf(fullmsg, "%s (originated from %s)", strerror(errno), syscall);
    exc = PyObject_CallFunction(PyExc_OSError, "(is)", errno, fullmsg);
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
#endif
    return NULL;
}


/*
 * Set OSError(errno=EACCES, strerror="Permission denied") Python exception.
 * If msg != "" the exception message will change in accordance.
 */
PyObject *
AccessDenied(const char *msg) {
    PyObject *exc;
    exc = PyObject_CallFunction(
        PyExc_OSError, "(is)", EACCES, strlen(msg) ? msg : strerror(EACCES));
    PyErr_SetObject(PyExc_OSError, exc);
    Py_XDECREF(exc);
    return NULL;
}


/*
 * Enable testing mode. This has the same effect as setting PSUTIL_TESTING
 * env var. This dual method exists because updating os.environ on
 * Windows has no effect. Called on unit tests setup.
 */
PyObject *
psutil_set_testing(PyObject *self, PyObject *args) {
    PSUTIL_TESTING = 1;
    Py_INCREF(Py_None);
    return Py_None;
}


/*
 * Print a debug message on stderr. No-op if PSUTIL_DEBUG env var is not set.
 */
void
psutil_debug(const char* format, ...) {
    va_list argptr;
    if (PSUTIL_DEBUG) {
        va_start(argptr, format);
        fprintf(stderr, "psutil-debug> ");
        vfprintf(stderr, format, argptr);
        fprintf(stderr, "\n");
        va_end(argptr);
    }
}


/*
 * Called on module import on all platforms.
 */
int
psutil_setup(void) {
    if (getenv("PSUTIL_DEBUG") != NULL)
        PSUTIL_DEBUG = 1;
    if (getenv("PSUTIL_TESTING") != NULL)
        PSUTIL_TESTING = 1;
    return 0;
}
