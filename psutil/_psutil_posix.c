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
#include <signal.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <net/if.h>
#include <unistd.h>

#ifdef PSUTIL_SUNOS10
    #include "arch/solaris/v10/ifaddrs.h"
#elif PSUTIL_AIX
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
#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
    #include <sys/resource.h>
#endif

#include "_psutil_common.h"


// ====================================================================
// --- Utils
// ====================================================================


/*
 * From "man getpagesize" on Linux, https://linux.die.net/man/2/getpagesize:
 *
 * > In SUSv2 the getpagesize() call is labeled LEGACY, and in POSIX.1-2001
 * > it has been dropped.
 * > Portable applications should employ sysconf(_SC_PAGESIZE) instead
 * > of getpagesize().
 * > Most systems allow the synonym _SC_PAGE_SIZE for _SC_PAGESIZE.
 * > Whether getpagesize() is present as a Linux system call depends on the
 * > architecture.
 */
long
psutil_getpagesize(void) {
#ifdef _SC_PAGESIZE
    // recommended POSIX
    return sysconf(_SC_PAGESIZE);
#elif _SC_PAGE_SIZE
    // alias
    return sysconf(_SC_PAGE_SIZE);
#else
    // legacy
    return (long) getpagesize();
#endif
}


/*
 * Check if PID exists. Return values:
 * 1: exists
 * 0: does not exist
 * -1: error (Python exception is set)
 */
int
psutil_pid_exists(pid_t pid) {
    int ret;

    // No negative PID exists, plus -1 is an alias for sending signal
    // too all processes except system ones. Not what we want.
    if (pid < 0)
        return 0;

    // As per "man 2 kill" PID 0 is an alias for sending the signal to
    // every process in the process group of the calling process.
    // Not what we want. Some platforms have PID 0, some do not.
    // We decide that at runtime.
    if (pid == 0) {
#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
        return 0;
#else
        return 1;
#endif
    }

    ret = kill(pid , 0);
    if (ret == 0)
        return 1;
    else {
        if (errno == ESRCH) {
            // ESRCH == No such process
            return 0;
        }
        else if (errno == EPERM) {
            // EPERM clearly indicates there's a process to deny
            // access to.
            return 1;
        }
        else {
            // According to "man 2 kill" possible error values are
            // (EINVAL, EPERM, ESRCH) therefore we should never get
            // here. If we do let's be explicit in considering this
            // an error.
            PyErr_SetFromErrno(PyExc_OSError);
            return -1;
        }
    }
}


/*
 * Utility used for those syscalls which do not return a meaningful
 * error that we can translate into an exception which makes sense.
 * As such, we'll have to guess.
 * On UNIX, if errno is set, we return that one (OSError).
 * Else, if PID does not exist we assume the syscall failed because
 * of that so we raise NoSuchProcess.
 * If none of this is true we giveup and raise RuntimeError(msg).
 * This will always set a Python exception and return NULL.
 */
void
psutil_raise_for_pid(long pid, char *syscall) {
    if (errno != 0)
        psutil_PyErr_SetFromOSErrnoWithSyscall(syscall);
    else if (psutil_pid_exists(pid) == 0)
        NoSuchProcess(syscall);
    else
        PyErr_Format(PyExc_RuntimeError, "%s syscall failed", syscall);
}


// ====================================================================
// --- Python wrappers
// ====================================================================


// Exposed so we can test it against Python's stdlib.
static PyObject *
psutil_getpagesize_pywrapper(PyObject *self, PyObject *args) {
    return Py_BuildValue("l", psutil_getpagesize());
}


/*
 * Given a PID return process priority as a Python integer.
 */
static PyObject *
psutil_posix_getpriority(PyObject *self, PyObject *args) {
    pid_t pid;
    int priority;
    errno = 0;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

#ifdef PSUTIL_OSX
    priority = getpriority(PRIO_PROCESS, (id_t)pid);
#else
    priority = getpriority(PRIO_PROCESS, pid);
#endif
    if (errno != 0)
        return PyErr_SetFromErrno(PyExc_OSError);
    return Py_BuildValue("i", priority);
}


/*
 * Given a PID and a value change process priority.
 */
static PyObject *
psutil_posix_setpriority(PyObject *self, PyObject *args) {
    pid_t pid;
    int priority;
    int retval;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &priority))
        return NULL;

#ifdef PSUTIL_OSX
    retval = setpriority(PRIO_PROCESS, (id_t)pid, priority);
#else
    retval = setpriority(PRIO_PROCESS, pid, priority);
#endif
    if (retval == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    Py_RETURN_NONE;
}


/*
 * Translate a sockaddr struct into a Python string.
 * Return None if address family is not AF_INET* or AF_PACKET.
 */
static PyObject *
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
        err = getnameinfo(addr, addrlen, buf, sizeof(buf), NULL, 0,
                          NI_NUMERICHOST);
        if (err != 0) {
            // XXX we get here on FreeBSD when processing 'lo' / AF_INET6
            // broadcast. Not sure what to do other than returning None.
            // ifconfig does not show anything BTW.
            // PyErr_Format(PyExc_RuntimeError, gai_strerror(err));
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
psutil_net_if_addrs(PyObject* self, PyObject* args) {
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

        if (! py_tuple)
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
static PyObject *
psutil_net_if_mtu(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
#ifdef PSUTIL_SUNOS10
    struct lifreq lifr;
#else
    struct ifreq ifr;
#endif

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;

#ifdef PSUTIL_SUNOS10
    PSUTIL_STRNCPY(lifr.lifr_name, nic_name, sizeof(lifr.lifr_name));
    ret = ioctl(sock, SIOCGIFMTU, &lifr);
#else
    PSUTIL_STRNCPY(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));
    ret = ioctl(sock, SIOCGIFMTU, &ifr);
#endif
    if (ret == -1)
        goto error;
    close(sock);

#ifdef PSUTIL_SUNOS10
    return Py_BuildValue("i", lifr.lifr_mtu);
#else
    return Py_BuildValue("i", ifr.ifr_mtu);
#endif

error:
    if (sock != -1)
        close(sock);
    return PyErr_SetFromErrno(PyExc_OSError);
}

static int
append_flag(PyObject *py_retlist, const char * flag_name)
{
    PyObject *py_str = NULL;

#if PY_MAJOR_VERSION >= 3
    py_str = PyUnicode_FromString(flag_name);
#else
    py_str = PyString_FromString(flag_name);
#endif
    if (! py_str)
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
static PyObject *
psutil_net_if_flags(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    struct ifreq ifr;
    PyObject *py_retlist = PyList_New(0);
    short int flags;

    if (py_retlist == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        goto error;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("socket(SOCK_DGRAM)");
        goto error;
    }

    PSUTIL_STRNCPY(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));
    ret = ioctl(sock, SIOCGIFFLAGS, &ifr);
    if (ret == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("ioctl(SIOCGIFFLAGS)");
        goto error;
    }

    close(sock);
    sock = -1;

    flags = ifr.ifr_flags & 0xFFFF;

    // Linux/glibc IFF flags: https://sourceware.org/git/?p=glibc.git;a=blob;f=sysdeps/gnu/net/if.h;h=251418f82331c0426e58707fe4473d454893b132;hb=HEAD
    // macOS IFF flags: https://opensource.apple.com/source/xnu/xnu-792/bsd/net/if.h.auto.html
    // AIX IFF flags: https://www.ibm.com/support/pages/how-hexadecimal-flags-displayed-ifconfig-are-calculated
    // FreeBSD IFF flags: https://www.freebsd.org/cgi/man.cgi?query=if_allmulti&apropos=0&sektion=0&manpath=FreeBSD+10-current&format=html

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
static PyObject *
psutil_net_if_is_running(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    struct ifreq ifr;

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;

    PSUTIL_STRNCPY(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));
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
    return PyErr_SetFromErrno(PyExc_OSError);
}


/*
 * net_if_stats() macOS/BSD implementation.
 */
#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)

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
#if defined(IFM_1000_TX) && !defined(PSUTIL_OPENBSD)
                #define HAS_CASE_IFM_1000_TX 1
                // FreeBSD 4 and others (but NOT OpenBSD) -> #define IFM_1000_T in net/if_media.h
                case(IFM_1000_TX):
#endif
#ifdef IFM_1000_FX
                case(IFM_1000_FX):
#endif
#if defined(IFM_1000_T) && (!HAS_CASE_IFM_1000_TX || IFM_1000_T != IFM_1000_TX)
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
psutil_net_if_duplex_speed(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = -1;
    int ret;
    int duplex;
    int speed;
    struct ifreq ifr;
    struct ifmediareq ifmed;

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    PSUTIL_STRNCPY(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));

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
    return Py_BuildValue("[ii]", duplex, speed);
}
#endif  // net_if_stats() macOS/BSD implementation


#ifdef __cplusplus
extern "C" {
#endif


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef mod_methods[] = {
    {"getpagesize", psutil_getpagesize_pywrapper, METH_VARARGS},
    {"getpriority", psutil_posix_getpriority, METH_VARARGS},
    {"net_if_addrs", psutil_net_if_addrs, METH_VARARGS},
    {"net_if_flags", psutil_net_if_flags, METH_VARARGS},
    {"net_if_is_running", psutil_net_if_is_running, METH_VARARGS},
    {"net_if_mtu", psutil_net_if_mtu, METH_VARARGS},
    {"setpriority", psutil_posix_setpriority, METH_VARARGS},
#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
#endif
    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3
    #define INITERR return NULL

    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_psutil_posix",
        NULL,
        -1,
        mod_methods,
        NULL,
        NULL,
        NULL,
        NULL
    };

    PyObject *PyInit__psutil_posix(void)
#else  /* PY_MAJOR_VERSION */
    #define INITERR return

    void init_psutil_posix(void)
#endif  /* PY_MAJOR_VERSION */
{
#if PY_MAJOR_VERSION >= 3
    PyObject *mod = PyModule_Create(&moduledef);
#else
    PyObject *mod = Py_InitModule("_psutil_posix", mod_methods);
#endif
    if (mod == NULL)
        INITERR;

#ifdef Py_GIL_DISABLED
    PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED);
#endif

#if defined(PSUTIL_BSD) || \
        defined(PSUTIL_OSX) || \
        defined(PSUTIL_SUNOS) || \
        defined(PSUTIL_AIX)
    if (PyModule_AddIntConstant(mod, "AF_LINK", AF_LINK)) INITERR;
#endif

#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
    PyObject *v;

#ifdef RLIMIT_AS
    if (PyModule_AddIntConstant(mod, "RLIMIT_AS", RLIMIT_AS)) INITERR;
#endif

#ifdef RLIMIT_CORE
    if (PyModule_AddIntConstant(mod, "RLIMIT_CORE", RLIMIT_CORE)) INITERR;
#endif

#ifdef RLIMIT_CPU
    if (PyModule_AddIntConstant(mod, "RLIMIT_CPU", RLIMIT_CPU)) INITERR;
#endif

#ifdef RLIMIT_DATA
    if (PyModule_AddIntConstant(mod, "RLIMIT_DATA", RLIMIT_DATA)) INITERR;
#endif

#ifdef RLIMIT_FSIZE
    if (PyModule_AddIntConstant(mod, "RLIMIT_FSIZE", RLIMIT_FSIZE)) INITERR;
#endif

#ifdef RLIMIT_MEMLOCK
    if (PyModule_AddIntConstant(mod, "RLIMIT_MEMLOCK", RLIMIT_MEMLOCK)) INITERR;
#endif

#ifdef RLIMIT_NOFILE
    if (PyModule_AddIntConstant(mod, "RLIMIT_NOFILE", RLIMIT_NOFILE)) INITERR;
#endif

#ifdef RLIMIT_NPROC
    if (PyModule_AddIntConstant(mod, "RLIMIT_NPROC", RLIMIT_NPROC)) INITERR;
#endif

#ifdef RLIMIT_RSS
    if (PyModule_AddIntConstant(mod, "RLIMIT_RSS", RLIMIT_RSS)) INITERR;
#endif

#ifdef RLIMIT_STACK
    if (PyModule_AddIntConstant(mod, "RLIMIT_STACK", RLIMIT_STACK)) INITERR;
#endif

// Linux specific

#ifdef RLIMIT_LOCKS
    if (PyModule_AddIntConstant(mod, "RLIMIT_LOCKS", RLIMIT_LOCKS)) INITERR;
#endif

#ifdef RLIMIT_MSGQUEUE
    if (PyModule_AddIntConstant(mod, "RLIMIT_MSGQUEUE", RLIMIT_MSGQUEUE)) INITERR;
#endif

#ifdef RLIMIT_NICE
    if (PyModule_AddIntConstant(mod, "RLIMIT_NICE", RLIMIT_NICE)) INITERR;
#endif

#ifdef RLIMIT_RTPRIO
    if (PyModule_AddIntConstant(mod, "RLIMIT_RTPRIO", RLIMIT_RTPRIO)) INITERR;
#endif

#ifdef RLIMIT_RTTIME
    if (PyModule_AddIntConstant(mod, "RLIMIT_RTTIME", RLIMIT_RTTIME)) INITERR;
#endif

#ifdef RLIMIT_SIGPENDING
    if (PyModule_AddIntConstant(mod, "RLIMIT_SIGPENDING", RLIMIT_SIGPENDING)) INITERR;
#endif

// Free specific

#ifdef RLIMIT_SWAP
    if (PyModule_AddIntConstant(mod, "RLIMIT_SWAP", RLIMIT_SWAP)) INITERR;
#endif

#ifdef RLIMIT_SBSIZE
    if (PyModule_AddIntConstant(mod, "RLIMIT_SBSIZE", RLIMIT_SBSIZE)) INITERR;
#endif

#ifdef RLIMIT_NPTS
    if (PyModule_AddIntConstant(mod, "RLIMIT_NPTS", RLIMIT_NPTS)) INITERR;
#endif

#if defined(HAVE_LONG_LONG)
    if (sizeof(RLIM_INFINITY) > sizeof(long)) {
        v = PyLong_FromLongLong((PY_LONG_LONG) RLIM_INFINITY);
    } else
#endif
    {
        v = PyLong_FromLong((long) RLIM_INFINITY);
    }
    if (v) {
        PyModule_AddObject(mod, "RLIM_INFINITY", v);
    }
#endif  // defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)

    if (mod == NULL)
        INITERR;
#if PY_MAJOR_VERSION >= 3
    return mod;
#endif
}

#ifdef __cplusplus
}
#endif
