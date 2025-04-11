/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

extern int PSUTIL_WINVER;

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

PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
double psutil_FiletimeToUnixTime(FILETIME ft);
double psutil_LargeIntegerToUnixTime(LARGE_INTEGER li);
int psutil_setup_windows(void);
