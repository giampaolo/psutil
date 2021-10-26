/*
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*! Based on code from
    https://lists.samba.org/archive/samba-technical/2009-February/063079.html
!*/


#ifndef GENERIC_AIX_IFADDRS_H
#define GENERIC_AIX_IFADDRS_H

#include <sys/socket.h>
#include <net/if.h>

#undef  ifa_dstaddr
#undef  ifa_broadaddr
#define ifa_broadaddr ifa_dstaddr

struct ifaddrs {
    struct ifaddrs  *ifa_next;
    char            *ifa_name;
    unsigned int     ifa_flags;
    struct sockaddr *ifa_addr;
    struct sockaddr *ifa_netmask;
    struct sockaddr *ifa_dstaddr;
};

extern int getifaddrs(struct ifaddrs **);
extern void freeifaddrs(struct ifaddrs *);
#endif
