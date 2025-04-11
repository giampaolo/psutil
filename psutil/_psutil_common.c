/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Routines common to all platforms.
 */

#include <Python.h>

#include "arch/all/init.h"
#include "_psutil_common.h"


// ============================================================================
// Utility functions (BSD)
// ============================================================================

#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
void
convert_kvm_err(const char *syscall, char *errbuf) {
    char fullmsg[8192];

    sprintf(fullmsg, "(originated from %s: %s)", syscall, errbuf);
    if (strstr(errbuf, "Permission denied") != NULL)
        AccessDenied(fullmsg);
    else if (strstr(errbuf, "Operation not permitted") != NULL)
        AccessDenied(fullmsg);
    else
        PyErr_Format(PyExc_RuntimeError, fullmsg);
}
#endif

// ====================================================================
// --- macOS
// ====================================================================

#ifdef PSUTIL_OSX
#include <mach/mach_time.h>

struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;
#endif

// ====================================================================
// --- Windows
// ====================================================================

#ifdef PSUTIL_WINDOWS
#include <windows.h>


/*
 * Convert a NTSTATUS value to a Win32 error code and set the proper
 * Python exception.
 */
PVOID
psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall) {
    ULONG err;
    char fullmsg[1024];

    if (NT_NTWIN32(Status))
        err = WIN32_FROM_NTSTATUS(Status);
    else
        err = RtlNtStatusToDosErrorNoTeb(Status);
    // if (GetLastError() != 0)
    //     err = GetLastError();
    sprintf(fullmsg, "(originated from %s)", syscall);
    return PyErr_SetFromWindowsErrWithFilename(err, fullmsg);
}


static int
psutil_loadlibs() {
    // --- Mandatory
    NtQuerySystemInformation = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQuerySystemInformation");
    if (! NtQuerySystemInformation)
        return 1;
    NtQueryInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! NtQueryInformationProcess)
        return 1;
    NtSetInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess");
    if (! NtSetInformationProcess)
        return 1;
    NtQueryObject = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQueryObject");
    if (! NtQueryObject)
        return 1;
    RtlIpv4AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv4AddressToStringA");
    if (! RtlIpv4AddressToStringA)
        return 1;
    GetExtendedTcpTable = psutil_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedTcpTable");
    if (! GetExtendedTcpTable)
        return 1;
    GetExtendedUdpTable = psutil_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedUdpTable");
    if (! GetExtendedUdpTable)
        return 1;
    RtlGetVersion = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlGetVersion");
    if (! RtlGetVersion)
        return 1;
    NtSuspendProcess = psutil_GetProcAddressFromLib(
        "ntdll", "NtSuspendProcess");
    if (! NtSuspendProcess)
        return 1;
    NtResumeProcess = psutil_GetProcAddressFromLib(
        "ntdll", "NtResumeProcess");
    if (! NtResumeProcess)
        return 1;
    NtQueryVirtualMemory = psutil_GetProcAddressFromLib(
        "ntdll", "NtQueryVirtualMemory");
    if (! NtQueryVirtualMemory)
        return 1;
    RtlNtStatusToDosErrorNoTeb = psutil_GetProcAddressFromLib(
        "ntdll", "RtlNtStatusToDosErrorNoTeb");
    if (! RtlNtStatusToDosErrorNoTeb)
        return 1;
    GetTickCount64 = psutil_GetProcAddress(
        "kernel32", "GetTickCount64");
    if (! GetTickCount64)
        return 1;
    RtlIpv6AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");
    if (! RtlIpv6AddressToStringA)
        return 1;

    // --- Optional

    // minimum requirement: Win 7
    QueryInterruptTime = psutil_GetProcAddressFromLib(
        "kernelbase.dll", "QueryInterruptTime");
    // minimum requirement: Win 7
    GetActiveProcessorCount = psutil_GetProcAddress(
        "kernel32", "GetActiveProcessorCount");
    // minimum requirement: Win 7
    GetLogicalProcessorInformationEx = psutil_GetProcAddressFromLib(
        "kernel32", "GetLogicalProcessorInformationEx");
    // minimum requirements: Windows Server Core
    WTSEnumerateSessionsW = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSEnumerateSessionsW");
    WTSQuerySessionInformationW = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSQuerySessionInformationW");
    WTSFreeMemory = psutil_GetProcAddressFromLib(
        "wtsapi32.dll", "WTSFreeMemory");

    PyErr_Clear();
    return 0;
}


static int
psutil_set_winver() {
    RTL_OSVERSIONINFOEXW versionInfo;
    ULONG maj;
    ULONG min;

    versionInfo.dwOSVersionInfoSize = sizeof(RTL_OSVERSIONINFOEXW);
    memset(&versionInfo, 0, sizeof(RTL_OSVERSIONINFOEXW));
    RtlGetVersion((PRTL_OSVERSIONINFOW)&versionInfo);
    maj = versionInfo.dwMajorVersion;
    min = versionInfo.dwMinorVersion;
    if (maj == 6 && min == 0)
        PSUTIL_WINVER = PSUTIL_WINDOWS_VISTA;  // or Server 2008
    else if (maj == 6 && min == 1)
        PSUTIL_WINVER = PSUTIL_WINDOWS_7;
    else if (maj == 6 && min == 2)
        PSUTIL_WINVER = PSUTIL_WINDOWS_8;
    else if (maj == 6 && min == 3)
        PSUTIL_WINVER = PSUTIL_WINDOWS_8_1;
    else if (maj == 10 && min == 0)
        PSUTIL_WINVER = PSUTIL_WINDOWS_10;
    else
        PSUTIL_WINVER = PSUTIL_WINDOWS_NEW;
    return 0;
}
#endif  // PSUTIL_WINDOWS


// Called on module import on all platforms.
int
psutil_setup(void) {
    if (getenv("PSUTIL_DEBUG") != NULL)
        PSUTIL_DEBUG = 1;

#ifdef PSUTIL_WINDOWS
    if (psutil_loadlibs() != 0)
        return 1;
    if (psutil_set_winver() != 0)
        return 1;
#endif
#ifdef PSUTIL_OSX
    mach_timebase_info(&PSUTIL_MACH_TIMEBASE_INFO);
#endif
    return 0;
}
