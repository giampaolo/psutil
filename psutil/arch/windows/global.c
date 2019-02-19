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



int
psutil_load_globals() {
    psutil_NtQueryInformationProcess = ps_GetProcAddress(
        "ntdll.dll", "NtQueryInformationProcess");
    if (! psutil_NtQueryInformationProcess)
        return 1;
    return 0;
}
