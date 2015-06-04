#include "inet_ntop.h"

// From: https://memset.wordpress.com/2010/10/09/inet_ntop-for-win32/
PCSTR
WSAAPI
inet_ntop(
    __in                                INT             Family,
    __in                                PVOID           pAddr,
    __out_ecount(StringBufSize)         PSTR            pStringBuf,
    __in                                size_t          StringBufSize
    )
{
    struct sockaddr_in srcaddr;

    memset(&srcaddr, 0, sizeof(struct sockaddr_in));
    memcpy(&(srcaddr.sin_addr), pAddr, sizeof(srcaddr.sin_addr));

    srcaddr.sin_family = Family;
    if (WSAAddressToString((struct sockaddr*) &srcaddr, sizeof(struct sockaddr_in), 0, pStringBuf, (LPDWORD) &StringBufSize) != 0) {
        DWORD rv = WSAGetLastError();
        return NULL;
    }
    return pStringBuf;
}