/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to all POSIX compliant platforms.
 */

#include <Python.h>
#include <errno.h>
#include <stdlib.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <ifaddrs.h>

#ifdef __linux
#include <netdb.h>
#include <linux/if_packet.h>
#endif  // end linux

#if defined(__FreeBSD__) || defined(__APPLE__)
#include <netdb.h>
#include <netinet/in.h>
#include <net/if_dl.h>
#endif

#if defined(__sun)
#include <netdb.h>
#endif

#include "_psutil_posix.h"


/*
 * Given a PID return process priority as a Python integer.
 */
static PyObject *
psutil_posix_getpriority(PyObject *self, PyObject *args)
{
    long pid;
    int priority;
    errno = 0;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    priority = getpriority(PRIO_PROCESS, pid);
    if (errno != 0)
        return PyErr_SetFromErrno(PyExc_OSError);
    return Py_BuildValue("i", priority);
}


/*
 * Given a PID and a value change process priority.
 */
static PyObject *
psutil_posix_setpriority(PyObject *self, PyObject *args)
{
    long pid;
    int priority;
    int retval;

    if (! PyArg_ParseTuple(args, "li", &pid, &priority))
        return NULL;
    retval = setpriority(PRIO_PROCESS, pid, priority);
    if (retval == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    Py_RETURN_NONE;
}


/*
 * Translate a sockaddr struct into a Python string.
 * Return None if address family is not AF_INET* or AF_PACKET.
 */
static PyObject *
psutil_convert_ipaddr(struct sockaddr *addr, int family)
{
    char buf[NI_MAXHOST];
    int err;
    int addrlen;
    int n;
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
        err = getnameinfo(addr, addrlen, buf, sizeof(buf), NULL, 0,
                          NI_NUMERICHOST);
        if (err != 0) {
            // XXX we get here on FreeBSD when processing 'lo' / AF_INET6
            // broadcast. Not sure what to do other than returning None.
            // ifconfig does not show anything BTW.
            //PyErr_Format(PyExc_RuntimeError, gai_strerror(err));
            //return NULL;
            Py_INCREF(Py_None);
            return Py_None;
        }
        else {
            return Py_BuildValue("s", buf);
        }
    }
#ifdef __linux
    else if (family == AF_PACKET) {
        struct sockaddr_ll *lladdr = (struct sockaddr_ll *)addr;
        len = lladdr->sll_halen;
        data = (const char *)lladdr->sll_addr;
    }
#endif
#if defined(__FreeBSD__) || defined(__APPLE__)
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
            sprintf(ptr, "%02x:", data[n] & 0xff);
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
static PyObject*
psutil_net_if_addrs(PyObject* self, PyObject* args)
{
    struct ifaddrs *ifaddr, *ifa;
    int family;

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_address = NULL;
    PyObject *py_netmask = NULL;
    PyObject *py_broadcast = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (getifaddrs(&ifaddr) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
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
#ifdef __linux
        py_broadcast = psutil_convert_ipaddr(ifa->ifa_ifu.ifu_broadaddr, family);
#else
        py_broadcast = psutil_convert_ipaddr(ifa->ifa_broadaddr, family);
#endif
        if (py_broadcast == NULL)
            goto error;
        py_tuple = Py_BuildValue(
            "(siOOO)",
            ifa->ifa_name,
            family,
            py_address,
            py_netmask,
            py_broadcast
        );

        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
        Py_DECREF(py_address);
        Py_DECREF(py_netmask);
        Py_DECREF(py_broadcast);
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
    return NULL;
}


/*
 * net_if_stats() implementation. This is here because it is common
 * to both OSX and FreeBSD and I didn't know where else to put it.
 */
#if defined(__FreeBSD__) || defined(__APPLE__)

#include <sys/sockio.h>
#include <net/if_media.h>
#include <net/if.h>

int psutil_get_nic_speed(int ifm_active) {
    // Determine NIC speed. Taken from:
    // http://www.i-scream.org/libstatgrab/
    // Assuming only ETHER devices
    switch(IFM_TYPE(ifm_active)) {
        case IFM_ETHER:
            switch(IFM_SUBTYPE(ifm_active)) {
#if defined(IFM_HPNA_1) && ((!defined(IFM_10G_LR)) \
    || (IFM_10G_LR != IFM_HPNA_1))
                // HomePNA 1.0 (1Mb/s)
                case(IFM_HPNA_1):
                    return 1;
#endif
                // 10 Mbit
                case(IFM_10_T):  // 10BaseT - RJ45
                case(IFM_10_2):  // 10Base2 - Thinnet
                case(IFM_10_5):  // 10Base5 - AUI
                case(IFM_10_STP):  // 10BaseT over shielded TP
                case(IFM_10_FL):  // 10baseFL - Fiber
                    return 10;
                // 100 Mbit
                case(IFM_100_TX):  // 100BaseTX - RJ45
                case(IFM_100_FX):  // 100BaseFX - Fiber
                case(IFM_100_T4):  // 100BaseT4 - 4 pair cat 3
                case(IFM_100_VG):  // 100VG-AnyLAN
                case(IFM_100_T2):  // 100BaseT2
                    return 100;
                // 1000 Mbit
                case(IFM_1000_SX):  // 1000BaseSX - multi-mode fiber
                case(IFM_1000_LX):  // 1000baseLX - single-mode fiber
                case(IFM_1000_CX):  // 1000baseCX - 150ohm STP
#if defined(IFM_1000_TX) && !defined(OPENBSD)
                // FreeBSD 4 and others (but NOT OpenBSD)?
                case(IFM_1000_TX):
#endif
#ifdef IFM_1000_FX
                case(IFM_1000_FX):
#endif
#ifdef IFM_1000_T
                case(IFM_1000_T):
#endif
                    return 1000;
#if defined(IFM_10G_SR) || defined(IFM_10G_LR) || defined(IFM_10G_CX4) \
         || defined(IFM_10G_T)
#ifdef IFM_10G_SR
                case(IFM_10G_SR):
#endif
#ifdef IFM_10G_LR
                case(IFM_10G_LR):
#endif
#ifdef IFM_10G_CX4
                case(IFM_10G_CX4):
#endif
#ifdef IFM_10G_TWINAX
                case(IFM_10G_TWINAX):
#endif
#ifdef IFM_10G_TWINAX_LONG
                case(IFM_10G_TWINAX_LONG):
#endif
#ifdef IFM_10G_T
                case(IFM_10G_T):
#endif
                    return 10000;
#endif
#if defined(IFM_2500_SX)
#ifdef IFM_2500_SX
                case(IFM_2500_SX):
#endif
                    return 2500;
#endif // any 2.5GBit stuff...
                // We don't know what it is
                default:
                    return 0;
            }
            break;

#ifdef IFM_TOKEN
        case IFM_TOKEN:
            switch(IFM_SUBTYPE(ifm_active)) {
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
            switch(IFM_SUBTYPE(ifm_active)) {
                // We don't know what it is
                default:
                    return 0;
            }
            break;
#endif
        case IFM_IEEE80211:
            switch(IFM_SUBTYPE(ifm_active)) {
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
static PyObject *
psutil_net_if_stats(PyObject *self, PyObject *args)
{
    char *nic_name;
    int sock = 0;
    int ret;
    int duplex;
    int speed;
    int mtu;
    struct ifreq ifr;
    struct ifmediareq ifmed;

    PyObject *py_is_up = NULL;

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;
    strncpy(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));

    // is up?
    ret = ioctl(sock, SIOCGIFFLAGS, &ifr);
    if (ret == -1)
        goto error;
    if ((ifr.ifr_flags & IFF_UP) != 0)
        py_is_up = Py_True;
    else
        py_is_up = Py_False;
    Py_INCREF(py_is_up);

    // MTU
    ret = ioctl(sock, SIOCGIFMTU, &ifr);
    if (ret == -1)
        goto error;
    mtu = ifr.ifr_mtu;

    // speed / duplex
    memset(&ifmed, 0, sizeof(struct ifmediareq));
    strlcpy(ifmed.ifm_name, nic_name, sizeof(ifmed.ifm_name));
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
    Py_DECREF(py_is_up);

    return Py_BuildValue("[Oiii]", py_is_up, duplex, speed, mtu);

error:
    Py_XDECREF(py_is_up);
    if (sock != 0)
        close(sock);
    PyErr_SetFromErrno(PyExc_OSError);
    return NULL;
}
#endif  // net_if_stats() implementation


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] =
{
    {"getpriority", psutil_posix_getpriority, METH_VARARGS,
     "Return process priority"},
    {"setpriority", psutil_posix_setpriority, METH_VARARGS,
     "Set process priority"},
    {"net_if_addrs", psutil_net_if_addrs, METH_VARARGS,
     "Retrieve NICs information"},
#if defined(__FreeBSD__) || defined(__APPLE__)
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS,
     "Return NIC stats."},
#endif
    {NULL, NULL, 0, NULL}
};

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
#endif

#if PY_MAJOR_VERSION >= 3

static int
psutil_posix_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_posix_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_posix",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_posix_traverse,
    psutil_posix_clear,
    NULL
};

#define INITERROR return NULL

PyMODINIT_FUNC PyInit__psutil_posix(void)

#else
#define INITERROR return

void init_psutil_posix(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_posix", PsutilMethods);
#endif

#if defined(__FreeBSD__) || defined(__APPLE__) || defined(__sun)
    PyModule_AddIntConstant(module, "AF_LINK", AF_LINK);
#endif

    if (module == NULL)
        INITERROR;
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
