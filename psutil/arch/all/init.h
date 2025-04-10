/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// ====================================================================
// --- Global constants
// ====================================================================

// print debug messages when set to 1
extern int PSUTIL_DEBUG;
// a signaler for connections without an actual status
extern int PSUTIL_CONN_NONE;

// strncpy() variant which appends a null terminator.
#define PSUTIL_STRNCPY(dst, src, n) \
    strncpy(dst, src, n - 1); \
    dst[n - 1] = '\0'

// ====================================================================
// --- Backward compatibility with missing Python.h APIs
// ====================================================================

#if defined(PSUTIL_WINDOWS) && defined(PYPY_VERSION)
    #if !defined(PyErr_SetFromWindowsErrWithFilename)
        PyObject *PyErr_SetFromWindowsErrWithFilename(
            int ierr, const char *filename
        );
    #endif
    #if !defined(PyErr_SetExcFromWindowsErrWithFilenameObject)
        PyObject *PyErr_SetExcFromWindowsErrWithFilenameObject(
            PyObject *type, int ierr, PyObject *filename
        );
    #endif
#endif

// --- _Py_PARSE_PID

// SIZEOF_INT|LONG is missing on Linux + PyPy (only?).
// In this case we guess it from setup.py. It's not 100% bullet proof,
// If wrong we'll probably get compiler warnings.
// FWIW on all UNIX platforms I've seen pid_t is defined as an int.
// _getpid() on Windows also returns an int.
#if !defined(SIZEOF_INT)
    #define SIZEOF_INT 4
#endif
#if !defined(SIZEOF_LONG)
    #define SIZEOF_LONG 8
#endif
#if !defined(SIZEOF_PID_T)
    #define SIZEOF_PID_T PSUTIL_SIZEOF_PID_T  // set as a macro in setup.py
#endif

// _Py_PARSE_PID was added in Python 3, but since it's private we make
// sure it's always present.
#ifndef _Py_PARSE_PID
    #if SIZEOF_PID_T == SIZEOF_INT
        #define _Py_PARSE_PID "i"
    #elif SIZEOF_PID_T == SIZEOF_LONG
        #define _Py_PARSE_PID "l"
    #elif defined(SIZEOF_LONG_LONG) && SIZEOF_PID_T == SIZEOF_LONG_LONG
        #define _Py_PARSE_PID "L"
    #else
        #error "_Py_PARSE_PID: sizeof(pid_t) is neither sizeof(int), "
               "sizeof(long) or sizeof(long long)"
    #endif
#endif

// PyPy on Windows
#ifndef PyLong_FromPid
    #if ((SIZEOF_PID_T == SIZEOF_INT) || (SIZEOF_PID_T == SIZEOF_LONG))
        #define PyLong_FromPid PyLong_FromLong
    #elif defined(SIZEOF_LONG_LONG) && SIZEOF_PID_T == SIZEOF_LONG_LONG
        #define PyLong_FromPid PyLong_FromLongLong
    #else
        #error "PyLong_FromPid: sizeof(pid_t) is neither sizeof(int), "
               "sizeof(long) or sizeof(long long)"
    #endif
#endif

// ====================================================================
// --- Global utils
// ====================================================================

// Print a debug message on stderr.
#define psutil_debug(...) do { \
    if (! PSUTIL_DEBUG) \
        break; \
    fprintf(stderr, "psutil-debug [%s:%d]> ", __FILE__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); \
    fprintf(stderr, "\n");} while(0)

PyObject* psutil_set_debug(PyObject *self, PyObject *args);
PyObject* psutil_check_pid_range(PyObject *self, PyObject *args);
