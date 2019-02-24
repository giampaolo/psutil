/*
 * Copyright (c) 2009, Giampaolo Rodola', Jeff Tang. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// because of WSAAddressToStringA
#define _WINSOCK_DEPRECATED_NO_WARNINGS
#include <ws2tcpip.h>

PCSTR WSAAPI
inet_ntop(
    __in                                INT             Family,
    __in                                const VOID *    pAddr,
    __out_ecount(StringBufSize)         PSTR            pStringBuf,
    __in                                size_t          StringBufSize
);
