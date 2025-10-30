/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <unistd.h>

#ifdef PSUTIL_AIX
#include "arch/aix/ifaddrs.h"
#else
#include <ifaddrs.h>
#endif

#if defined(PSUTIL_LINUX)
#include <netdb.h>
#include <linux/types.h>
#include <linux/if_packet.h>
#endif

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
#include <netdb.h>
#include <netinet/in.h>
#include <net/if_dl.h>
#include <sys/sockio.h>
#include <net/if_media.h>
#include <net/if.h>
#endif

#if defined(PSUTIL_SUNOS)
#include <netdb.h>
#include <sys/sockio.h>
#endif

#if defined(PSUTIL_AIX)
#include <netdb.h>
#endif

#include "../../arch/all/init.h"


/*
 * Translate a sockaddr struct into a Python string.
 * Return None if address family is not AF_INET* or AF_PACKET.
 */
PyObject *
psutil_convert_ipaddr(struct sockaddr *addr, int family) {
    char buf[NI_MAXHOST];
    int err;
    int addrlen;
    size_t n;
    size_t len;
    const char *data;
    char *ptr;

    if (addr == NULL) {
        Py_INCREF(Py_None);
        return Py_None;
    }
    else if (family == AF_INET || family == AF_INET6) {
        if (family == AF_INET)
            addrlen = sizeof(struct sockaddr_in);
        else
            addrlen = sizeof(struct sockaddr_in6);
        err = getnameinfo(
            addr, addrlen, buf, sizeof(buf), NULL, 0, NI_NUMERICHOST
        );
        if (err != 0) {
            // XXX we get here on FreeBSD when processing 'lo' / AF_INET6
            // broadcast. Not sure what to do other than returning None.
            // ifconfig does not show anything BTW.
            // psutil_runtime_error(gai_strerror(err));
            // return NULL;
            Py_INCREF(Py_None);
            return Py_None;
        }
        else {
            return Py_BuildValue("s", buf);
        }
    }
#ifdef PSUTIL_LINUX
    else if (family == AF_PACKET) {
        struct sockaddr_ll *lladdr = (struct sockaddr_ll *)addr;
        len = lladdr->sll_halen;
        data = (const char *)lladdr->sll_addr;
    }
#elif defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    else if (addr->sa_family == AF_LINK) {
        // Note: prior to Python 3.4 socket module does not expose
        // AF_LINK so we'll do.
        struct sockaddr_dl *dladdr = (struct sockaddr_dl *)addr;
        len = dladdr->sdl_alen;
        data = LLADDR(dladdr);
    }
#endif
    else {
        // unknown family
        Py_INCREF(Py_None);
        return Py_None;
    }

    // AF_PACKET or AF_LINK
    if (len > 0) {
        ptr = buf;
        for (n = 0; n < len; ++n) {
            str_format(ptr, sizeof(ptr), "%02x:", data[n] & 0xff);
            ptr += 3;
        }
        *--ptr = '\0';
        return Py_BuildValue("s", buf);
    }
    else {
        Py_INCREF(Py_None);
        return Py_None;
    }
}


/*
 * Return NICs information a-la ifconfig as a list of tuples.
 * TODO: on Solaris we won't get any MAC address.
 */
PyObject *
psutil_net_if_addrs(PyObject *self, PyObject *args) {
    struct ifaddrs *ifaddr, *ifa;
    int family;

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_address = NULL;
    PyObject *py_netmask = NULL;
    PyObject *py_broadcast = NULL;
    PyObject *py_ptp = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (getifaddrs(&ifaddr) == -1) {
        psutil_oserror();
        goto error;
    }

    for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
        if (!ifa->ifa_addr)
            continue;
        family = ifa->ifa_addr->sa_family;
        py_address = psutil_convert_ipaddr(ifa->ifa_addr, family);
        // If the primary address can't be determined just skip it.
        // I've never seen this happen on Linux but I did on FreeBSD.
        if (py_address == Py_None)
            continue;
        if (py_address == NULL)
            goto error;
        py_netmask = psutil_convert_ipaddr(ifa->ifa_netmask, family);
        if (py_netmask == NULL)
            goto error;

        if (ifa->ifa_flags & IFF_BROADCAST) {
            py_broadcast = psutil_convert_ipaddr(ifa->ifa_broadaddr, family);
            Py_INCREF(Py_None);
            py_ptp = Py_None;
        }
        else if (ifa->ifa_flags & IFF_POINTOPOINT) {
            py_ptp = psutil_convert_ipaddr(ifa->ifa_dstaddr, family);
            Py_INCREF(Py_None);
            py_broadcast = Py_None;
        }
        else {
            Py_INCREF(Py_None);
            Py_INCREF(Py_None);
            py_broadcast = Py_None;
            py_ptp = Py_None;
        }

        if ((py_broadcast == NULL) || (py_ptp == NULL))
            goto error;
        py_tuple = Py_BuildValue(
            "(siOOOO)",
            ifa->ifa_name,
            family,
            py_address,
            py_netmask,
            py_broadcast,
            py_ptp
        );

        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
        Py_CLEAR(py_address);
        Py_CLEAR(py_netmask);
        Py_CLEAR(py_broadcast);
        Py_CLEAR(py_ptp);
    }

    freeifaddrs(ifaddr);
    return py_retlist;

error:
    if (ifaddr != NULL)
        freeifaddrs(ifaddr);
    Py_DECREF(py_retlist);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_address);
    Py_XDECREF(py_netmask);
    Py_XDECREF(py_broadcast);
    Py_XDECREF(py_ptp);
    return NULL;
}


/*
 * Return NIC MTU. References:
 * http://www.i-scream.org/libstatgrab/
 */
PyObject *
psutil_net_if_mtu(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    struct ifreq ifr;

    if (!PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;

    str_copy(ifr.ifr_name, sizeof(ifr.ifr_name), nic_name);
    ret = ioctl(sock, SIOCGIFMTU, &ifr);
    if (ret == -1)
        goto error;
    close(sock);

    return Py_BuildValue("i", ifr.ifr_mtu);

error:
    if (sock != -1)
        close(sock);
    return psutil_oserror();
}

static int
append_flag(PyObject *py_retlist, const char *flag_name) {
    PyObject *py_str = NULL;

    py_str = PyUnicode_FromString(flag_name);
    if (!py_str)
        return 0;
    if (PyList_Append(py_retlist, py_str)) {
        Py_DECREF(py_str);
        return 0;
    }
    Py_CLEAR(py_str);

    return 1;
}

/*
 * Get all of the NIC flags and return them.
 */
PyObject *
psutil_net_if_flags(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    struct ifreq ifr;
    PyObject *py_retlist = PyList_New(0);
    short int flags;

    if (py_retlist == NULL)
        return NULL;

    if (!PyArg_ParseTuple(args, "s", &nic_name))
        goto error;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1) {
        psutil_oserror_wsyscall("socket(SOCK_DGRAM)");
        goto error;
    }

    str_copy(ifr.ifr_name, sizeof(ifr.ifr_name), nic_name);
    ret = ioctl(sock, SIOCGIFFLAGS, &ifr);
    if (ret == -1) {
        psutil_oserror_wsyscall("ioctl(SIOCGIFFLAGS)");
        goto error;
    }

    close(sock);
    sock = -1;

    flags = ifr.ifr_flags & 0xFFFF;

    // Linux/glibc IFF flags:
    // https://sourceware.org/git/?p=glibc.git;a=blob;f=sysdeps/gnu/net/if.h;h=251418f82331c0426e58707fe4473d454893b132;hb=HEAD
    // macOS IFF flags:
    // https://opensource.apple.com/source/xnu/xnu-792/bsd/net/if.h.auto.html
    // AIX IFF flags:
    // https://www.ibm.com/support/pages/how-hexadecimal-flags-displayed-ifconfig-are-calculated
    // FreeBSD IFF flags:
    // https://www.freebsd.org/cgi/man.cgi?query=if_allmulti&apropos=0&sektion=0&manpath=FreeBSD+10-current&format=html

#ifdef IFF_UP
    // Available in (at least) Linux, macOS, AIX, BSD
    if (flags & IFF_UP)
        if (!append_flag(py_retlist, "up"))
            goto error;
#endif
#ifdef IFF_BROADCAST
    // Available in (at least) Linux, macOS, AIX, BSD
    if (flags & IFF_BROADCAST)
        if (!append_flag(py_retlist, "broadcast"))
            goto error;
#endif
#ifdef IFF_DEBUG
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_DEBUG)
        if (!append_flag(py_retlist, "debug"))
            goto error;
#endif
#ifdef IFF_LOOPBACK
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_LOOPBACK)
        if (!append_flag(py_retlist, "loopback"))
            goto error;
#endif
#ifdef IFF_POINTOPOINT
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_POINTOPOINT)
        if (!append_flag(py_retlist, "pointopoint"))
            goto error;
#endif
#ifdef IFF_NOTRAILERS
    // Available in (at least) Linux, macOS, AIX
    if (flags & IFF_NOTRAILERS)
        if (!append_flag(py_retlist, "notrailers"))
            goto error;
#endif
#ifdef IFF_RUNNING
    // Available in (at least) Linux, macOS, AIX, BSD
    if (flags & IFF_RUNNING)
        if (!append_flag(py_retlist, "running"))
            goto error;
#endif
#ifdef IFF_NOARP
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_NOARP)
        if (!append_flag(py_retlist, "noarp"))
            goto error;
#endif
#ifdef IFF_PROMISC
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_PROMISC)
        if (!append_flag(py_retlist, "promisc"))
            goto error;
#endif
#ifdef IFF_ALLMULTI
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_ALLMULTI)
        if (!append_flag(py_retlist, "allmulti"))
            goto error;
#endif
#ifdef IFF_MASTER
    // Available in (at least) Linux
    if (flags & IFF_MASTER)
        if (!append_flag(py_retlist, "master"))
            goto error;
#endif
#ifdef IFF_SLAVE
    // Available in (at least) Linux
    if (flags & IFF_SLAVE)
        if (!append_flag(py_retlist, "slave"))
            goto error;
#endif
#ifdef IFF_MULTICAST
    // Available in (at least) Linux, macOS, BSD
    if (flags & IFF_MULTICAST)
        if (!append_flag(py_retlist, "multicast"))
            goto error;
#endif
#ifdef IFF_PORTSEL
    // Available in (at least) Linux
    if (flags & IFF_PORTSEL)
        if (!append_flag(py_retlist, "portsel"))
            goto error;
#endif
#ifdef IFF_AUTOMEDIA
    // Available in (at least) Linux
    if (flags & IFF_AUTOMEDIA)
        if (!append_flag(py_retlist, "automedia"))
            goto error;
#endif
#ifdef IFF_DYNAMIC
    // Available in (at least) Linux
    if (flags & IFF_DYNAMIC)
        if (!append_flag(py_retlist, "dynamic"))
            goto error;
#endif
#ifdef IFF_OACTIVE
    // Available in (at least) macOS, BSD
    if (flags & IFF_OACTIVE)
        if (!append_flag(py_retlist, "oactive"))
            goto error;
#endif
#ifdef IFF_SIMPLEX
    // Available in (at least) macOS, AIX, BSD
    if (flags & IFF_SIMPLEX)
        if (!append_flag(py_retlist, "simplex"))
            goto error;
#endif
#ifdef IFF_LINK0
    // Available in (at least) macOS, BSD
    if (flags & IFF_LINK0)
        if (!append_flag(py_retlist, "link0"))
            goto error;
#endif
#ifdef IFF_LINK1
    // Available in (at least) macOS, BSD
    if (flags & IFF_LINK1)
        if (!append_flag(py_retlist, "link1"))
            goto error;
#endif
#ifdef IFF_LINK2
    // Available in (at least) macOS, BSD
    if (flags & IFF_LINK2)
        if (!append_flag(py_retlist, "link2"))
            goto error;
#endif
#ifdef IFF_D2
    // Available in (at least) AIX
    if (flags & IFF_D2)
        if (!append_flag(py_retlist, "d2"))
            goto error;
#endif

    return py_retlist;

error:
    Py_DECREF(py_retlist);
    if (sock != -1)
        close(sock);
    return NULL;
}


/*
 * Inspect NIC flags, returns a bool indicating whether the NIC is
 * running. References:
 * http://www.i-scream.org/libstatgrab/
 */
PyObject *
psutil_net_if_is_running(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    struct ifreq ifr;

    if (!PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;

    str_copy(ifr.ifr_name, sizeof(ifr.ifr_name), nic_name);
    ret = ioctl(sock, SIOCGIFFLAGS, &ifr);
    if (ret == -1)
        goto error;

    close(sock);
    if ((ifr.ifr_flags & IFF_RUNNING) != 0)
        return Py_BuildValue("O", Py_True);
    else
        return Py_BuildValue("O", Py_False);

error:
    if (sock != -1)
        close(sock);
    return psutil_oserror();
}


// net_if_stats() macOS/BSD implementation.
#ifdef PSUTIL_HAS_NET_IF_DUPLEX_SPEED

int
psutil_get_nic_speed(int ifm_active) {
    // Determine NIC speed. Taken from:
    // http://www.i-scream.org/libstatgrab/
    // Assuming only ETHER devices
    switch (IFM_TYPE(ifm_active)) {
        case IFM_ETHER:
            switch (IFM_SUBTYPE(ifm_active)) {
#if defined(IFM_HPNA_1) \
    && ((!defined(IFM_10G_LR)) || (IFM_10G_LR != IFM_HPNA_1))
                // HomePNA 1.0 (1Mb/s)
                case (IFM_HPNA_1):
                    return 1;
#endif
                // 10 Mbit
                case (IFM_10_T):  // 10BaseT - RJ45
                case (IFM_10_2):  // 10Base2 - Thinnet
                case (IFM_10_5):  // 10Base5 - AUI
                case (IFM_10_STP):  // 10BaseT over shielded TP
                case (IFM_10_FL):  // 10baseFL - Fiber
                    return 10;
                // 100 Mbit
                case (IFM_100_TX):  // 100BaseTX - RJ45
                case (IFM_100_FX):  // 100BaseFX - Fiber
                case (IFM_100_T4):  // 100BaseT4 - 4 pair cat 3
                case (IFM_100_VG):  // 100VG-AnyLAN
                case (IFM_100_T2):  // 100BaseT2
                    return 100;
                // 1000 Mbit
                case (IFM_1000_SX):  // 1000BaseSX - multi-mode fiber
                case (IFM_1000_LX):  // 1000baseLX - single-mode fiber
                case (IFM_1000_CX):  // 1000baseCX - 150ohm STP
#if defined(IFM_1000_TX) && !defined(PSUTIL_OPENBSD)
#define HAS_CASE_IFM_1000_TX 1
                // FreeBSD 4 and others (but NOT OpenBSD) -> #define IFM_1000_T
                // in net/if_media.h
                case (IFM_1000_TX):
#endif
#ifdef IFM_1000_FX
                case (IFM_1000_FX):
#endif
#if defined(IFM_1000_T) && (!HAS_CASE_IFM_1000_TX || IFM_1000_T != IFM_1000_TX)
                case (IFM_1000_T):
#endif
                    return 1000;
#if defined(IFM_10G_SR) || defined(IFM_10G_LR) || defined(IFM_10G_CX4) \
    || defined(IFM_10G_T)
#ifdef IFM_10G_SR
                case (IFM_10G_SR):
#endif
#ifdef IFM_10G_LR
                case (IFM_10G_LR):
#endif
#ifdef IFM_10G_CX4
                case (IFM_10G_CX4):
#endif
#ifdef IFM_10G_TWINAX
                case (IFM_10G_TWINAX):
#endif
#ifdef IFM_10G_TWINAX_LONG
                case (IFM_10G_TWINAX_LONG):
#endif
#ifdef IFM_10G_T
                case (IFM_10G_T):
#endif
                    return 10000;
#endif
#if defined(IFM_2500_SX)
#ifdef IFM_2500_SX
                case (IFM_2500_SX):
#endif
                    return 2500;
#endif  // any 2.5GBit stuff...
        // We don't know what it is
                default:
                    return 0;
            }
            break;

#ifdef IFM_TOKEN
        case IFM_TOKEN:
            switch (IFM_SUBTYPE(ifm_active)) {
                case IFM_TOK_STP4:  // Shielded twisted pair 4m - DB9
                case IFM_TOK_UTP4:  // Unshielded twisted pair 4m - RJ45
                    return 4;
                case IFM_TOK_STP16:  // Shielded twisted pair 16m - DB9
                case IFM_TOK_UTP16:  // Unshielded twisted pair 16m - RJ45
                    return 16;
#if defined(IFM_TOK_STP100) || defined(IFM_TOK_UTP100)
#ifdef IFM_TOK_STP100
                case IFM_TOK_STP100:  // Shielded twisted pair 100m - DB9
#endif
#ifdef IFM_TOK_UTP100
                case IFM_TOK_UTP100:  // Unshielded twisted pair 100m - RJ45
#endif
                    return 100;
#endif
                // We don't know what it is
                default:
                    return 0;
            }
            break;
#endif

#ifdef IFM_FDDI
        case IFM_FDDI:
            switch (IFM_SUBTYPE(ifm_active)) {
                // We don't know what it is
                default:
                    return 0;
            }
            break;
#endif
        case IFM_IEEE80211:
            switch (IFM_SUBTYPE(ifm_active)) {
                case IFM_IEEE80211_FH1:  // Frequency Hopping 1Mbps
                case IFM_IEEE80211_DS1:  // Direct Sequence 1Mbps
                    return 1;
                case IFM_IEEE80211_FH2:  // Frequency Hopping 2Mbps
                case IFM_IEEE80211_DS2:  // Direct Sequence 2Mbps
                    return 2;
                case IFM_IEEE80211_DS5:  // Direct Sequence 5Mbps
                    return 5;
                case IFM_IEEE80211_DS11:  // Direct Sequence 11Mbps
                    return 11;
                case IFM_IEEE80211_DS22:  // Direct Sequence 22Mbps
                    return 22;
                // We don't know what it is
                default:
                    return 0;
            }
            break;

        default:
            return 0;
    }
}


/*
 * Return stats about a particular network interface.
 * References:
 * http://www.i-scream.org/libstatgrab/
 */
PyObject *
psutil_net_if_duplex_speed(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    int duplex;
    int speed;
    struct ifreq ifr;
    struct ifmediareq ifmed;

    if (!PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        return psutil_oserror();
    str_copy(ifr.ifr_name, sizeof(ifr.ifr_name), nic_name);

    // speed / duplex
    memset(&ifmed, 0, sizeof(struct ifmediareq));
    str_copy(ifmed.ifm_name, sizeof(ifmed.ifm_name), nic_name);
    ret = ioctl(sock, SIOCGIFMEDIA, (caddr_t)&ifmed);
    if (ret == -1) {
        speed = 0;
        duplex = 0;
    }
    else {
        speed = psutil_get_nic_speed(ifmed.ifm_active);
        if ((ifmed.ifm_active | IFM_FDX) == ifmed.ifm_active)
            duplex = 2;
        else if ((ifmed.ifm_active | IFM_HDX) == ifmed.ifm_active)
            duplex = 1;
        else
            duplex = 0;
    }

    close(sock);
    return Py_BuildValue("[ii]", duplex, speed);
}
#endif  // PSUTIL_HAS_NET_IF_DUPLEX_SPEED
