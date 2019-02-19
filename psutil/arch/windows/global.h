/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "ntextapi.h"


typedef PSTR (NTAPI * _RtlIpv4AddressToStringA)(struct in_addr *, PSTR);
typedef PSTR (NTAPI * _RtlIpv6AddressToStringA)(struct in6_addr *, PSTR);
typedef DWORD (_stdcall * NTQSI_PROC) (int, PVOID, ULONG, PULONG);
typedef DWORD (CALLBACK *_GetActiveProcessorCount)(WORD);


_RtlIpv4AddressToStringA \
    psutil_rtlIpv4AddressToStringA;

_NtQueryInformationProcess \
    psutil_NtQueryInformationProcess;

_RtlIpv6AddressToStringA \
    psutil_rtlIpv6AddressToStringA;

_NtSetInformationProcess
    psutil_NtSetInformationProcess;

NTQSI_PROC \
    psutil_NtQuerySystemInformation;

_GetActiveProcessorCount \
    psutil_GetActiveProcessorCount;

PWINSTATIONQUERYINFORMATIONW \
    psutil_WinStationQueryInformationW;

int psutil_load_globals();
