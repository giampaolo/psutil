/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Global names shared by all platforms.

#include <Python.h>

// We do this so that all .c files have to include only one header
// (ourselves, init.h).

#if defined(PSUTIL_POSIX)
    #include "../../arch/posix/init.h"
#endif
#if defined(PSUTIL_BSD)
    #include "../../arch/bsd/init.h"
#endif

#if defined(PSUTIL_LINUX)
    #include "../../arch/linux/init.h"
#elif defined(PSUTIL_WINDOWS)
    #include "../../arch/windows/init.h"
#elif defined(PSUTIL_OSX)
    #include "../../arch/osx/init.h"
#elif defined(PSUTIL_FREEBSD)
    #include "../../arch/freebsd/init.h"
#elif defined(PSUTIL_OPENBSD)
    #include "../../arch/openbsd/init.h"
#elif defined(PSUTIL_NETBSD)
    #include "../../arch/netbsd/init.h"
#elif defined(PSUTIL_SUNOS)
    #include "../../arch/sunos/init.h"
#endif

// print debug messages when set to 1
extern int PSUTIL_DEBUG;
// a signaler for connections without an actual status
extern int PSUTIL_CONN_NONE;

#ifdef Py_GIL_DISABLED
    extern PyMutex utxent_lock;
    #define UTXENT_MUTEX_LOCK() PyMutex_Lock(&utxent_lock)
    #define UTXENT_MUTEX_UNLOCK() PyMutex_Unlock(&utxent_lock)
#else
    #define UTXENT_MUTEX_LOCK()
    #define UTXENT_MUTEX_UNLOCK()
#endif

// Print a debug message on stderr.
#define psutil_debug(...) do { \
    if (! PSUTIL_DEBUG) \
        break; \
    fprintf(stderr, "psutil-debug [%s:%d]> ", __FILE__, __LINE__); \
    fprintf(stderr, __VA_ARGS__); \
    fprintf(stderr, "\n");} while(0)


// strncpy() variant which appends a null terminator.
#define PSUTIL_STRNCPY(dst, src, n) \
    strncpy(dst, src, n - 1); \
    dst[n - 1] = '\0'

// ====================================================================
// --- Custom exceptions
// ====================================================================

PyObject* AccessDenied(const char *msg);
PyObject* NoSuchProcess(const char *msg);
PyObject* psutil_PyErr_SetFromOSErrnoWithSyscall(const char *syscall);

// ====================================================================
// --- Backward compatibility with missing Python.h APIs
// ====================================================================

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

#if defined(PSUTIL_WINDOWS) || defined(PSUTIL_BSD) || defined(PSUTIL_MACOS)
PyObject* psutil_pids(PyObject *self, PyObject *args);
#endif

PyObject* psutil_set_debug(PyObject *self, PyObject *args);
PyObject* psutil_check_pid_range(PyObject *self, PyObject *args);
int psutil_setup(void);
