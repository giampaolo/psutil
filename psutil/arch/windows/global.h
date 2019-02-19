/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "ntextapi.h"


typedef PSTR (NTAPI * _RtlIpv4AddressToStringA)(struct in_addr *, PSTR);

_RtlIpv4AddressToStringA \
    psutil_rtlIpv4AddressToStringA;
_NtQueryInformationProcess \
    psutil_NtQueryInformationProcess;

int psutil_load_globals();
