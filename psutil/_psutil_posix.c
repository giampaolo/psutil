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
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    priority = getpriority(PRIO_PROCESS, pid);
    if (errno != 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
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
    if (! PyArg_ParseTuple(args, "li", &pid, &priority)) {
        return NULL;
    }
    retval = setpriority(PRIO_PROCESS, pid, priority);
    if (retval == -1) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    Py_INCREF(Py_None);
    return Py_None;
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
        // XXX socket module does not expose AF_LINK
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

    if (getifaddrs(&ifaddr) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (ifa = ifaddr; ifa != NULL; ifa = ifa->ifa_next) {
        family = ifa->ifa_addr->sa_family;

        py_address = Py_BuildValue("s", "0.0.0.0"); // psutil_convert_ipaddr(ifa->ifa_addr, family);
        if (py_address == NULL)
            goto error;
        py_netmask = Py_BuildValue("s", "0.0.0.0"); // psutil_convert_ipaddr(ifa->ifa_netmask, family);
        if (py_netmask == NULL)
            goto error;
/*
XXX - temporary
#ifdef __linux
        py_broadcast = psutil_convert_ipaddr(ifa->ifa_ifu.ifu_broadaddr, family);
#else
        py_broadcast = psutil_convert_ipaddr(ifa->ifa_broadaddr, family);
#endif
*/
        py_broadcast = Py_BuildValue("s", "0.0.0.0");

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

    if (module == NULL) {
        INITERROR;
    }
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
