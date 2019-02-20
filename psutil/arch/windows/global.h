/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "ntextapi.h"
#include <iphlpapi.h>

typedef DWORD (_stdcall * NTQSI_PROC) (int, PVOID, ULONG, PULONG);
typedef PSTR (NTAPI * _RtlIpv4AddressToStringA)(struct in_addr *, PSTR);
typedef PSTR (NTAPI * _RtlIpv6AddressToStringA)(struct in6_addr *, PSTR);
typedef DWORD (WINAPI * _GetExtendedTcpTable)(PVOID, PDWORD, BOOL, ULONG,
                                              TCP_TABLE_CLASS, ULONG);
typedef DWORD (WINAPI * _GetExtendedUdpTable)(PVOID, PDWORD, BOOL, ULONG,
                                              UDP_TABLE_CLASS, ULONG);
typedef DWORD (CALLBACK *_GetActiveProcessorCount)(WORD);

// probably unnecessary?
/*
#ifndef NT_SUCCESS
#define NT_SUCCESS(Status) ((NTSTATUS)(Status) >= 0)
#endif

typedef ULONGLONG (CALLBACK *_GetTickCount64)(void);

_GetTickCount64 \
    psutil_GetTickCount64;

*/

NTQSI_PROC \
    psutil_NtQuerySystemInformation;

_NtQueryInformationProcess \
    psutil_NtQueryInformationProcess;

_NtSetInformationProcess
    psutil_NtSetInformationProcess;

PWINSTATIONQUERYINFORMATIONW \
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


int psutil_load_globals();
