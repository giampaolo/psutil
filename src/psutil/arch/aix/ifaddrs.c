/*
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*! Based on code from
    https://lists.samba.org/archive/samba-technical/2009-February/063079.html
!*/

#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <net/if.h>
#include <netinet/in.h>
#include <sys/ioctl.h>
#include <sys/types.h>
#include <sys/socket.h>

#include "ifaddrs.h"

#define MAX(x,y) ((x)>(y)?(x):(y))
#define SIZE(p) MAX((p).sa_len,sizeof(p))


static struct sockaddr *
sa_dup(struct sockaddr *sa1)
{
    struct sockaddr *sa2;
    size_t sz = sa1->sa_len;
    sa2 = (struct sockaddr *) calloc(1, sz);
    if (sa2 == NULL)
        return NULL;
    memcpy(sa2, sa1, sz);
    return sa2;
}


void freeifaddrs(struct ifaddrs *ifp)
{
    if (NULL == ifp) return;
    free(ifp->ifa_name);
    free(ifp->ifa_addr);
    free(ifp->ifa_netmask);
    free(ifp->ifa_dstaddr);
    freeifaddrs(ifp->ifa_next);
    free(ifp);
}


int getifaddrs(struct ifaddrs **ifap)
{
    int sd, ifsize;
    char *ccp, *ecp;
    struct ifconf ifc;
    struct ifreq *ifr;
    struct ifaddrs *cifa = NULL; /* current */
    struct ifaddrs *pifa = NULL; /* previous */
    const size_t IFREQSZ = sizeof(struct ifreq);
    int fam;

    *ifap = NULL;

    sd = socket(AF_INET, SOCK_DGRAM, 0);
    if (sd == -1)
        goto error;

    /* find how much memory to allocate for the SIOCGIFCONF call */
    if (ioctl(sd, SIOCGSIZIFCONF, (caddr_t)&ifsize) < 0)
        goto error;

    ifc.ifc_req = (struct ifreq *) calloc(1, ifsize);
    if (ifc.ifc_req == NULL)
        goto error;
    ifc.ifc_len = ifsize;

    if (ioctl(sd, SIOCGIFCONF, &ifc) < 0)
        goto error;

    ccp = (char *)ifc.ifc_req;
    ecp = ccp + ifsize;

    while (ccp < ecp) {

        ifr = (struct ifreq *) ccp;
        ifsize = sizeof(ifr->ifr_name) + SIZE(ifr->ifr_addr);
        fam = ifr->ifr_addr.sa_family;

        if (fam == AF_INET || fam == AF_INET6) {
            cifa = (struct ifaddrs *) calloc(1, sizeof(struct ifaddrs));
            if (cifa == NULL)
                goto error;
            cifa->ifa_next = NULL;

            if (pifa == NULL) *ifap = cifa; /* first one */
            else pifa->ifa_next = cifa;

            cifa->ifa_name = strdup(ifr->ifr_name);
            if (cifa->ifa_name == NULL)
                goto error;
            cifa->ifa_flags = 0;
            cifa->ifa_dstaddr = NULL;

            cifa->ifa_addr = sa_dup(&ifr->ifr_addr);
            if (cifa->ifa_addr == NULL)
                goto error;

            if (fam == AF_INET) {
                if (ioctl(sd, SIOCGIFNETMASK, ifr, IFREQSZ) < 0)
                    goto error;
                cifa->ifa_netmask = sa_dup(&ifr->ifr_addr);
                if (cifa->ifa_netmask == NULL)
                    goto error;
            }

            if (0 == ioctl(sd, SIOCGIFFLAGS, ifr)) /* optional */
                cifa->ifa_flags = ifr->ifr_flags;

            if (fam == AF_INET) {
                if (ioctl(sd, SIOCGIFDSTADDR, ifr, IFREQSZ) < 0) {
                    if (0 == ioctl(sd, SIOCGIFBRDADDR, ifr, IFREQSZ)) {
                        cifa->ifa_dstaddr = sa_dup(&ifr->ifr_addr);
                        if (cifa->ifa_dstaddr == NULL)
                            goto error;
                    }
                }
                else {
                    cifa->ifa_dstaddr = sa_dup(&ifr->ifr_addr);
                    if (cifa->ifa_dstaddr == NULL)
                        goto error;
                }
            }
            pifa = cifa;
        }

        ccp += ifsize;
    }
    free(ifc.ifc_req);
    close(sd);
    return 0;
error:
    if (ifc.ifc_req != NULL)
        free(ifc.ifc_req);
    if (sd != -1)
        close(sd);
    freeifaddrs(*ifap);
    return (-1);
}
