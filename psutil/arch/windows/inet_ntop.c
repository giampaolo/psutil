/*
 * Copyright (c) 2009, Giampaolo Rodola', Jeff Tang. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include "inet_ntop.h"

// From: https://memset.wordpress.com/2010/10/09/inet_ntop-for-win32/
PCSTR WSAAPI
inet_ntop(INT family, PVOID pAddr, PSTR stringBuf, size_t strBufSize) {
    DWORD dwAddressLength = 0;
    struct sockaddr_storage srcaddr;
    struct sockaddr_in *srcaddr4 = (struct sockaddr_in*) &srcaddr;
    struct sockaddr_in6 *srcaddr6 = (struct sockaddr_in6*) &srcaddr;

    memset(&srcaddr, 0, sizeof(struct sockaddr_storage));
    srcaddr.ss_family = family;

    if (family == AF_INET) {
        dwAddressLength = sizeof(struct sockaddr_in);
        memcpy(&(srcaddr4->sin_addr), pAddr, sizeof(struct in_addr));
    }
    else if (family == AF_INET6) {
        dwAddressLength = sizeof(struct sockaddr_in6);
        memcpy(&(srcaddr6->sin6_addr), pAddr, sizeof(struct in6_addr));
    }
    else {
        PyErr_SetString(PyExc_ValueError, "invalid family");
        return NULL;
    }

    if (WSAAddressToStringA(
            (LPSOCKADDR) &srcaddr,
            dwAddressLength,
            0,
            stringBuf,
            (LPDWORD) &strBufSize) != 0)
    {
        PyErr_SetExcFromWindowsErr(PyExc_OSError, WSAGetLastError());
        return NULL;
    }
    return stringBuf;
}
