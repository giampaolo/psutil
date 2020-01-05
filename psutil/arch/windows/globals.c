/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * This code is executed on import. It loads private/undocumented
 * Windows APIs and sets Windows version constants so that they are
 * available globally.
 */

#include <windows.h>
#include <Python.h>
#include "globals.h"


// Needed to make these globally visible.
int PSUTIL_WINVER;
SYSTEM_INFO PSUTIL_SYSTEM_INFO;

#define NT_FACILITY_MASK 0xfff
#define NT_FACILITY_SHIFT 16
#define NT_FACILITY(Status) \
    ((((ULONG)(Status)) >> NT_FACILITY_SHIFT) & NT_FACILITY_MASK)
#define NT_NTWIN32(status) (NT_FACILITY(Status) == FACILITY_WIN32)
#define WIN32_FROM_NTSTATUS(Status) (((ULONG)(Status)) & 0xffff)


// A wrapper around GetModuleHandle and GetProcAddress.
PVOID
psutil_GetProcAddress(LPCSTR libname, LPCSTR procname) {
    HMODULE mod;
    FARPROC addr;

    if ((mod = GetModuleHandleA(libname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, procname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, procname);
        return NULL;
    }
    return addr;
}


// A wrapper around LoadLibrary and GetProcAddress.
PVOID
psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname) {
    HMODULE mod;
    FARPROC addr;

    Py_BEGIN_ALLOW_THREADS
    mod = LoadLibraryA(libname);
    Py_END_ALLOW_THREADS
    if (mod  == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, procname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, procname);
        FreeLibrary(mod);
        return NULL;
    }
    // Causes crash.
    // FreeLibrary(mod);
    return addr;
}


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
    /*
     * Mandatory.
     */
    NtQuerySystemInformation = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQuerySystemInformation");
    if (NtQuerySystemInformation == NULL)
        return 1;

    NtQueryInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! NtQueryInformationProcess)
        return 1;

    NtSetInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess");
    if (! NtSetInformationProcess)
        return 1;

    WinStationQueryInformationW = psutil_GetProcAddressFromLib(
        "winsta.dll", "WinStationQueryInformationW");
    if (! WinStationQueryInformationW)
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

    /*
     * Optional.
     */
    // not available on Wine
    RtlIpv6AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");

    // minimum requirement: Win Vista
    GetTickCount64 = psutil_GetProcAddress(
        "kernel32", "GetTickCount64");

    // minimum requirement: Win 7
    GetActiveProcessorCount = psutil_GetProcAddress(
        "kernel32", "GetActiveProcessorCount");

    // minumum requirement: Win 7
    GetLogicalProcessorInformationEx = psutil_GetProcAddressFromLib(
        "kernel32", "GetLogicalProcessorInformationEx");

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


static int
psutil_load_sysinfo() {
    GetSystemInfo(&PSUTIL_SYSTEM_INFO);
    return 0;
}


int
psutil_load_globals() {
    if (psutil_loadlibs() != 0)
        return 1;
    if (psutil_set_winver() != 0)
        return 1;
    if (psutil_load_sysinfo() != 0)
        return 1;
    return 0;
}
