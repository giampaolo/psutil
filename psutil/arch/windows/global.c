/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <stdio.h>
#include <windows.h>
#include <Python.h>
#include "ntextapi.h"
#include "global.h"


// A wrapper around GetModuleHandle and GetProcAddress.
static PVOID
ps_GetProcAddress(LPCSTR libname, LPCSTR procname) {
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
static PVOID
ps_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname) {
    HMODULE mod;
    FARPROC addr;

    if ((mod = LoadLibraryA(libname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, libname);
        return NULL;
    }
    if ((addr = GetProcAddress(mod, procname)) == NULL) {
        PyErr_SetFromWindowsErrWithFilename(0, procname);
        FreeLibrary(mod);
        return NULL;
    }
    // FreeLibrary(mod);
    return addr;
}


int
psutil_load_globals() {
    // Mandatory.

    psutil_NtQuerySystemInformation = ps_GetProcAddressFromLib(
        "ntdll.dll", "NtQuerySystemInformation");
    if (psutil_NtQuerySystemInformation == NULL)
        return 1;

    psutil_NtQueryInformationProcess = ps_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! psutil_NtQueryInformationProcess)
        return 1;

    psutil_NtSetInformationProcess = ps_GetProcAddress(
        "ntdll.dll", "NtSetInformationProcess");
    if (! psutil_NtSetInformationProcess)
        return 1;

    psutil_WinStationQueryInformationW = ps_GetProcAddressFromLib(
        "winsta.dll", "WinStationQueryInformationW");
    if (! psutil_WinStationQueryInformationW)
        return 1;

    psutil_rtlIpv4AddressToStringA = ps_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv4AddressToStringA");
    if (! psutil_rtlIpv4AddressToStringA)
        return 1;

    psutil_rtlIpv6AddressToStringA = ps_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");
    if (! psutil_rtlIpv6AddressToStringA)
        return 1;

    psutil_GetExtendedTcpTable = ps_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedTcpTable");
    if (! psutil_GetExtendedTcpTable)
        return 1;

    psutil_GetExtendedUdpTable = ps_GetProcAddressFromLib(
        "iphlpapi.dll", "GetExtendedUdpTable");
    if (! psutil_GetExtendedUdpTable)
        return 1;

    // Optionals.

    psutil_GetActiveProcessorCount = ps_GetProcAddress(
        "kernel32", "GetActiveProcessorCount");

    return 0;
}
