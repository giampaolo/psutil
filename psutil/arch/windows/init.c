/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

#include "../../arch/all/init.h"


// Needed to make these globally visible.
SYSTEM_INFO PSUTIL_SYSTEM_INFO;
CRITICAL_SECTION PSUTIL_CRITICAL_SECTION;

// Declared extern in ntextapi.h, assigned by psutil_loadlibs() below.
_NtQueryInformationProcess NtQueryInformationProcess = NULL;
_NtQueryObject NtQueryObject = NULL;
_NtQuerySystemInformation NtQuerySystemInformation = NULL;
_NtQueryVirtualMemory NtQueryVirtualMemory = NULL;
_NtResumeProcess NtResumeProcess = NULL;
_NtSetInformationProcess NtSetInformationProcess = NULL;
_NtSuspendProcess NtSuspendProcess = NULL;
_RtlGetVersion RtlGetVersion = NULL;
_RtlNtStatusToDosErrorNoTeb RtlNtStatusToDosErrorNoTeb = NULL;
_WTSEnumerateSessionsW WTSEnumerateSessionsW = NULL;
_WTSFreeMemory WTSFreeMemory = NULL;
_WTSQuerySessionInformationW WTSQuerySessionInformationW = NULL;


// ====================================================================
// --- Utils
// ====================================================================

// Convert a NTSTATUS value to a Win32 error code and set the proper
// Python exception.
PVOID
psutil_SetFromNTStatusErr(NTSTATUS status, const char *syscall) {
    ULONG err;
    char fullmsg[1024];

    if (NT_NTWIN32(status))
        err = WIN32_FROM_NTSTATUS(status);
    else
        err = RtlNtStatusToDosErrorNoTeb(status);
    str_format(fullmsg, sizeof(fullmsg), "(originated from %s)", syscall);
    return PyErr_SetFromWindowsErrWithFilename(err, fullmsg);
}


// A wrapper around GetModuleHandle and GetProcAddress.
PVOID
psutil_GetProcAddress(LPCSTR libname, LPCSTR apiname) {
    HMODULE mod;
    FARPROC addr;

    if ((mod = GetModuleHandleA(libname)) == NULL) {
        psutil_debug(
            "%s module not supported (needed for %s)", libname, apiname
        );
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, apiname)) == NULL) {
        psutil_debug("%s -> %s API not supported", libname, apiname);
        PyErr_SetFromWindowsErrWithFilename(0, apiname);
        return NULL;
    }
    return addr;
}


// A wrapper around LoadLibrary and GetProcAddress.
PVOID
psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR apiname) {
    HMODULE mod;
    FARPROC addr;

    Py_BEGIN_ALLOW_THREADS
    mod = LoadLibraryA(libname);
    Py_END_ALLOW_THREADS
    if (mod == NULL) {
        psutil_debug("%s lib not supported (needed for %s)", libname, apiname);
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, apiname)) == NULL) {
        psutil_debug("%s -> %s not supported", libname, apiname);
        PyErr_SetFromWindowsErrWithFilename(0, apiname);
        FreeLibrary(mod);
        return NULL;
    }
    // Causes crash.
    // FreeLibrary(mod);
    return addr;
}


// Convert the hi and lo parts of a FILETIME structure or a
// LARGE_INTEGER to a UNIX time. A FILETIME contains a 64-bit value
// representing the number of 100-nanosecond intervals since January 1,
// 1601 (UTC). A UNIX time is the number of seconds that have elapsed
// since the UNIX epoch, that is the time 00:00:00 UTC on 1 January
// 1970.
static double
_to_unix_time(ULONGLONG hiPart, ULONGLONG loPart) {
    ULONGLONG ret;

    // 100 nanosecond intervals since January 1, 1601.
    ret = hiPart << 32;
    ret += loPart;
    // Change starting time to the Epoch (00:00:00 UTC, January 1, 1970).
    ret -= 116444736000000000ull;
    // Convert nano secs to secs.
    return (double)ret / 10000000ull;
}


double
psutil_FiletimeToUnixTime(FILETIME ft) {
    return _to_unix_time(
        (ULONGLONG)ft.dwHighDateTime, (ULONGLONG)ft.dwLowDateTime
    );
}


double
psutil_LargeIntegerToUnixTime(LARGE_INTEGER li) {
    return _to_unix_time((ULONGLONG)li.HighPart, (ULONGLONG)li.LowPart);
}


// ====================================================================
// --- Init / load libs
// ====================================================================


static int
psutil_loadlibs() {
    // --- Mandatory. ntdll is loaded in every process, so
    // GetModuleHandle is enough.
    NtQuerySystemInformation = psutil_GetProcAddress(
        "ntdll.dll", "NtQuerySystemInformation"
    );
    if (!NtQuerySystemInformation)
        return -1;
    NtQueryInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess"
    );
    if (!NtQueryInformationProcess)
        return -1;
    NtSetInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess"
    );
    if (!NtSetInformationProcess)
        return -1;
    NtQueryObject = psutil_GetProcAddress("ntdll.dll", "NtQueryObject");
    if (!NtQueryObject)
        return -1;
    RtlGetVersion = psutil_GetProcAddress("ntdll.dll", "RtlGetVersion");
    if (!RtlGetVersion)
        return -1;
    NtSuspendProcess = psutil_GetProcAddress("ntdll.dll", "NtSuspendProcess");
    if (!NtSuspendProcess)
        return -1;
    NtResumeProcess = psutil_GetProcAddress("ntdll.dll", "NtResumeProcess");
    if (!NtResumeProcess)
        return -1;
    NtQueryVirtualMemory = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryVirtualMemory"
    );
    if (!NtQueryVirtualMemory)
        return -1;
    RtlNtStatusToDosErrorNoTeb = psutil_GetProcAddress(
        "ntdll.dll", "RtlNtStatusToDosErrorNoTeb"
    );
    if (!RtlNtStatusToDosErrorNoTeb)
        return -1;

    // --- Optional

    // minimum requirements: Windows Server Core
    WTSEnumerateSessionsW = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSEnumerateSessionsW"
    );
    WTSQuerySessionInformationW = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSQuerySessionInformationW"
    );
    WTSFreeMemory = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSFreeMemory"
    );

    PyErr_Clear();
    return 0;
}


static int
psutil_check_winver() {
    RTL_OSVERSIONINFOEXW versionInfo;
    NTSTATUS status;
    ULONG maj;
    ULONG min;

    memset(&versionInfo, 0, sizeof(RTL_OSVERSIONINFOEXW));
    versionInfo.dwOSVersionInfoSize = sizeof(RTL_OSVERSIONINFOEXW);
    status = RtlGetVersion((PRTL_OSVERSIONINFOW)&versionInfo);
    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "RtlGetVersion");
        return -1;
    }
    maj = versionInfo.dwMajorVersion;
    min = versionInfo.dwMinorVersion;
    if (maj < 10) {
        psutil_runtime_error(
            "this Windows version is too old (%lu.%lu); psutil 7.2.x is "
            "the latest version supporting Windows Vista, 7, 8, 8.1 and "
            "their server counterparts",
            maj,
            min
        );
        return -1;
    }
    return 0;
}


// Called on module import.
int
psutil_setup_windows(void) {
    if (psutil_loadlibs() != 0)
        return -1;
    if (psutil_check_winver() != 0)
        return -1;
    GetSystemInfo(&PSUTIL_SYSTEM_INFO);
    InitializeCriticalSection(&PSUTIL_CRITICAL_SECTION);
    return 0;
}
