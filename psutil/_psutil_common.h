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

// strncpy() variant which appends a null terminator.
#define PSUTIL_STRNCPY(dst, src, n) \
    strncpy(dst, src, n - 1); \
    dst[n - 1] = '\0'

// ====================================================================
// --- Backward compatibility with missing Python.h APIs
// ====================================================================

#if PY_MAJOR_VERSION < 3
    // On Python 2 we just return a plain byte string, which is never
    // supposed to raise decoding errors, see:
    // https://github.com/giampaolo/psutil/issues/1040
    #define PyUnicode_DecodeFSDefault          PyString_FromString
    #define PyUnicode_DecodeFSDefaultAndSize   PyString_FromStringAndSize
#endif

#if defined(PSUTIL_WINDOWS) && \
        defined(PYPY_VERSION) && \
        !defined(PyErr_SetFromWindowsErrWithFilename)
    PyObject *PyErr_SetFromWindowsErrWithFilename(int ierr,
                                                  const char *filename);
#endif

// --- _Py_PARSE_PID

// SIZEOF_INT|LONG is missing on Linux + PyPy (only?).
// SIZEOF_PID_T is missing on Windows + Python2.
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

// _Py_PARSE_PID is Python 3 only, but since it's private make sure it's
// always present.
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

// Python 2 or PyPy on Windows
#ifndef PyLong_FromPid
    #if ((SIZEOF_PID_T == SIZEOF_INT) || (SIZEOF_PID_T == SIZEOF_LONG))
        #if PY_MAJOR_VERSION >= 3
            #define PyLong_FromPid PyLong_FromLong
        #else
            #define PyLong_FromPid PyInt_FromLong
        #endif
    #elif defined(SIZEOF_LONG_LONG) && SIZEOF_PID_T == SIZEOF_LONG_LONG
        #define PyLong_FromPid PyLong_FromLongLong
    #else
        #error "PyLong_FromPid: sizeof(pid_t) is neither sizeof(int), "
               "sizeof(long) or sizeof(long long)"
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
// --- BSD
// ====================================================================

void convert_kvm_err(const char *syscall, char *errbuf);

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

    #define _NT_FACILITY_MASK 0xfff
    #define _NT_FACILITY_SHIFT 16
    #define _NT_FACILITY(status) \
        ((((ULONG)(status)) >> _NT_FACILITY_SHIFT) & _NT_FACILITY_MASK)

    #define NT_NTWIN32(status) (_NT_FACILITY(status) == FACILITY_WIN32)
    #define WIN32_FROM_NTSTATUS(status) (((ULONG)(status)) & 0xffff)

    #define LO_T 1e-7
    #define HI_T 429.4967296

    #ifndef AF_INET6
        #define AF_INET6 23
    #endif

    int psutil_load_globals();
    PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
    PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
    PVOID psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall);
    double psutil_FiletimeToUnixTime(FILETIME ft);
    double psutil_LargeIntegerToUnixTime(LARGE_INTEGER li);
#endif
