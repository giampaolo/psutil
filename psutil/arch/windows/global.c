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
    FreeLibrary(mod);
    return addr;
}


int
psutil_load_globals() {
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
        return NULL;

    psutil_rtlIpv4AddressToStringA = ps_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv4AddressToStringA");
    if (! psutil_rtlIpv4AddressToStringA)
        return 1;

    psutil_rtlIpv6AddressToStringA = ps_GetProcAddressFromLib(
        "ntdll.dll", "RtlIpv6AddressToStringA");
    if (! psutil_rtlIpv6AddressToStringA)
        return 1;

    return 0;
}
