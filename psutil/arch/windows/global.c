/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <windows.h>
#include <Python.h>
#include "ntextapi.h"
#include "global.h"


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
 * This is executed on import and loads Windows APIs so that they
 * are available globally.
 */
psutil_loadlibs() {
    /*
     * Mandatory.
     */

    psutil_NtQuerySystemInformation = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQuerySystemInformation");
    if (psutil_NtQuerySystemInformation == NULL)
        return 1;

    psutil_NtQueryInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! psutil_NtQueryInformationProcess)
        return 1;

    psutil_NtSetInformationProcess = psutil_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess");
    if (! psutil_NtSetInformationProcess)
        return 1;

    psutil_WinStationQueryInformationW = psutil_GetProcAddressFromLib(
        "winsta.dll", "WinStationQueryInformationW");
    if (! psutil_WinStationQueryInformationW)
        return 1;

    psutil_NtQueryObject = psutil_GetProcAddressFromLib(
        "ntdll.dll", "NtQueryObject");
    if (! psutil_NtQueryObject)
        return 1;

    psutil_rtlIpv4AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv4AddressToStringA");
    if (! psutil_rtlIpv4AddressToStringA)
        return 1;

    psutil_rtlIpv6AddressToStringA = psutil_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");
    if (! psutil_rtlIpv6AddressToStringA)
        return 1;

    // minimum requirement: Win XP SP3
    psutil_GetExtendedTcpTable = psutil_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedTcpTable");
    if (! psutil_GetExtendedTcpTable)
        return 1;

    // minimum requirement: Win XP SP3
    psutil_GetExtendedUdpTable = psutil_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedUdpTable");
    if (! psutil_GetExtendedUdpTable)
        return 1;

    /*
     * Optional.
     */

    // minimum requirement: Win Vista
    psutil_GetTickCount64 = psutil_GetProcAddress(
        "kernel32", "GetTickCount64");

    // minimum requirement: Win 7
    psutil_GetActiveProcessorCount = psutil_GetProcAddress(
        "kernel32", "GetActiveProcessorCount");

    // minumum requirement: Win 7
    psutil_GetLogicalProcessorInformationEx = psutil_GetProcAddressFromLib(
        "kernel32", "GetLogicalProcessorInformationEx");

    PyErr_Clear();
    return 0;
}
