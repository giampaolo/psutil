/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.

 * List of constants and objects that are globally available.
 */

#include <windows.h>
#include "ntextapi.h"  // make it available to any file including us

extern int PSUTIL_WINVER;
extern SYSTEM_INFO PSUTIL_SYSTEM_INFO;

#define PSUTIL_WINDOWS_VISTA 60
#define PSUTIL_WINDOWS_7 61
#define PSUTIL_WINDOWS_8 62
#define PSUTIL_WINDOWS_8_1 63
#define PSUTIL_WINDOWS_10 100
#define PSUTIL_WINDOWS_NEW MAXLONG

#define MALLOC(x) HeapAlloc(GetProcessHeap(), 0, (x))
#define FREE(x) HeapFree(GetProcessHeap(), 0, (x))
#define LO_T 1e-7
#define HI_T 429.4967296

#ifndef AF_INET6
#define AF_INET6 23
#endif

int psutil_load_globals();
PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
PVOID psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall);
