/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include "arch/all/init.h"

// ====================================================================
// --- Custom exceptions
// ====================================================================

PyObject* AccessDenied(const char *msg);
PyObject* NoSuchProcess(const char *msg);
PyObject* psutil_PyErr_SetFromOSErrnoWithSyscall(const char *syscall);

// ====================================================================
// --- Global utils
// ====================================================================

int psutil_setup(void);

// ====================================================================
// --- BSD
// ====================================================================

void convert_kvm_err(const char *syscall, char *errbuf);

// ====================================================================
// --- macOS
// ====================================================================

#ifdef PSUTIL_OSX
    #include <mach/mach_time.h>

    extern struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;
#endif

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

    PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
    PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
    PVOID psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall);
    double psutil_FiletimeToUnixTime(FILETIME ft);
    double psutil_LargeIntegerToUnixTime(LARGE_INTEGER li);
#endif
