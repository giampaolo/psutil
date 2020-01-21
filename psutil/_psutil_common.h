/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// ====================================================================
// --- Global vars / constants
// ====================================================================

extern int PSUTIL_TESTING;
extern int PSUTIL_DEBUG;
// a signaler for connections without an actual status
static const int PSUTIL_CONN_NONE = 128;

// ====================================================================
// --- Python functions and backward compatibility
// ====================================================================

#if PY_MAJOR_VERSION < 3
    PyObject* PyUnicode_DecodeFSDefault(char *s);
    PyObject* PyUnicode_DecodeFSDefaultAndSize(char *s, Py_ssize_t size);
#endif

// Python 2 compatibility for PyArg_ParseTuple pid arg type handling.
#if PY_MAJOR_VERSION == 2
    // XXX: not bullet proof (long long case is missing).
    #if PSUTIL_SIZEOF_PID_T == 4
        #define _Py_PARSE_PID "i"
    #else
        #define _Py_PARSE_PID "l"
    #endif
#endif

// ====================================================================
// --- Custom exceptions
// ====================================================================

PyObject* AccessDenied(const char *msg);
PyObject* NoSuchProcess(const char *msg);
PyObject* PyErr_SetFromOSErrnoWithSyscall(const char *syscall);

// ====================================================================
// --- Global utils
// ====================================================================

PyObject* psutil_set_testing(PyObject *self, PyObject *args);
void psutil_debug(const char* format, ...);
int psutil_setup(void);

// ====================================================================
// --- Windows
// ====================================================================

#ifdef PSUTIL_WINDOWS
    #include <windows.h>
    // make it available to any file which includes this module
    #include "arch/windows/ntextapi.h"

    extern int PSUTIL_WINVER;
    extern SYSTEM_INFO          PSUTIL_SYSTEM_INFO;
    extern CRITICAL_SECTION     PSUTIL_CRITICAL_SECTION;

    #define PSUTIL_WINDOWS_VISTA 60
    #define PSUTIL_WINDOWS_7 61
    #define PSUTIL_WINDOWS_8 62
    #define PSUTIL_WINDOWS_8_1 63
    #define PSUTIL_WINDOWS_10 100
    #define PSUTIL_WINDOWS_NEW MAXLONG

    #define MALLOC(x) HeapAlloc(GetProcessHeap(), 0, (x))
    #define MALLOC_ZERO(x) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (x))
    #define FREE(x) HeapFree(GetProcessHeap(), 0, (x))

    #define LO_T 1e-7
    #define HI_T 429.4967296

    #ifndef AF_INET6
        #define AF_INET6 23
    #endif

    int psutil_load_globals();
    PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
    PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
    PVOID psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall);
#endif
