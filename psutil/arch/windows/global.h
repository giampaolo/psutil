/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.

 * List of constants and objects that are globally available.
 */

#include <windows.h>
#include "ntextapi.h"

extern int PSUTIL_WINVER;
extern SYSTEM_INFO PSUTIL_SYSTEM_INFO;
#define PSUTIL_WINDOWS_XP 51
#define PSUTIL_WINDOWS_SERVER_2003 52
#define PSUTIL_WINDOWS_VISTA 60
#define PSUTIL_WINDOWS_7 61
#define PSUTIL_WINDOWS_8 62
#define PSUTIL_WINDOWS_8_1 63
#define PSUTIL_WINDOWS_10 100
#define PSUTIL_WINDOWS_NEW MAXLONG

int psutil_load_globals();
PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
PVOID psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall);

_NtQuerySystemInformation \
    psutil_NtQuerySystemInformation;

_NtQueryInformationProcess \
    psutil_NtQueryInformationProcess;

_NtSetInformationProcess
    psutil_NtSetInformationProcess;

_WinStationQueryInformationW \
    psutil_WinStationQueryInformationW;

_RtlIpv4AddressToStringA \
    psutil_rtlIpv4AddressToStringA;

_RtlIpv6AddressToStringA \
    psutil_rtlIpv6AddressToStringA;

_GetExtendedTcpTable \
    psutil_GetExtendedTcpTable;

_GetExtendedUdpTable \
    psutil_GetExtendedUdpTable;

_GetActiveProcessorCount \
    psutil_GetActiveProcessorCount;

_GetTickCount64 \
    psutil_GetTickCount64;

_NtQueryObject \
    psutil_NtQueryObject;

_GetLogicalProcessorInformationEx \
    psutil_GetLogicalProcessorInformationEx;

_RtlGetVersion \
    psutil_RtlGetVersion;

_NtSuspendProcess \
    psutil_NtSuspendProcess;

_NtResumeProcess \
    psutil_NtResumeProcess;

_NtQueryVirtualMemory \
    psutil_NtQueryVirtualMemory;

_RtlNtStatusToDosErrorNoTeb \
    psutil_RtlNtStatusToDosErrorNoTeb;
