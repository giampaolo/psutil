/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Functions specific to all POSIX compliant platforms.
 */

#include <Python.h>
#include <sys/resource.h>
#include <sys/socket.h>

#include "arch/all/init.h"
#include "arch/posix/proc.h"
#include "arch/posix/net.h"


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


// Exposed so we can test it against Python's stdlib.
static PyObject *
psutil_getpagesize_pywrapper(PyObject *self, PyObject *args) {
    return Py_BuildValue("l", psutil_getpagesize());
}


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

PyObject *
PyInit__psutil_posix(void) {
    PyObject *mod = PyModule_Create(&moduledef);
    if (mod == NULL)
        return NULL;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

#if defined(PSUTIL_BSD) || \
        defined(PSUTIL_OSX) || \
        defined(PSUTIL_SUNOS) || \
        defined(PSUTIL_AIX)
    if (PyModule_AddIntConstant(mod, "AF_LINK", AF_LINK))
        return NULL;
#endif

#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
    PyObject *v;

#ifdef RLIMIT_AS
    if (PyModule_AddIntConstant(mod, "RLIMIT_AS", RLIMIT_AS))
        return NULL;
#endif

#ifdef RLIMIT_CORE
    if (PyModule_AddIntConstant(mod, "RLIMIT_CORE", RLIMIT_CORE))
        return NULL;
#endif

#ifdef RLIMIT_CPU
    if (PyModule_AddIntConstant(mod, "RLIMIT_CPU", RLIMIT_CPU))
        return NULL;
#endif

#ifdef RLIMIT_DATA
    if (PyModule_AddIntConstant(mod, "RLIMIT_DATA", RLIMIT_DATA))
        return NULL;
#endif

#ifdef RLIMIT_FSIZE
    if (PyModule_AddIntConstant(mod, "RLIMIT_FSIZE", RLIMIT_FSIZE))
        return NULL;
#endif

#ifdef RLIMIT_MEMLOCK
    if (PyModule_AddIntConstant(mod, "RLIMIT_MEMLOCK", RLIMIT_MEMLOCK))
        return NULL;
#endif

#ifdef RLIMIT_NOFILE
    if (PyModule_AddIntConstant(mod, "RLIMIT_NOFILE", RLIMIT_NOFILE))
        return NULL;
#endif

#ifdef RLIMIT_NPROC
    if (PyModule_AddIntConstant(mod, "RLIMIT_NPROC", RLIMIT_NPROC))
        return NULL;
#endif

#ifdef RLIMIT_RSS
    if (PyModule_AddIntConstant(mod, "RLIMIT_RSS", RLIMIT_RSS))
        return NULL;
#endif

#ifdef RLIMIT_STACK
    if (PyModule_AddIntConstant(mod, "RLIMIT_STACK", RLIMIT_STACK))
        return NULL;
#endif

// Linux specific

#ifdef RLIMIT_LOCKS
    if (PyModule_AddIntConstant(mod, "RLIMIT_LOCKS", RLIMIT_LOCKS))
        return NULL;
#endif

#ifdef RLIMIT_MSGQUEUE
    if (PyModule_AddIntConstant(mod, "RLIMIT_MSGQUEUE", RLIMIT_MSGQUEUE))
        return NULL;
#endif

#ifdef RLIMIT_NICE
    if (PyModule_AddIntConstant(mod, "RLIMIT_NICE", RLIMIT_NICE))
        return NULL;
#endif

#ifdef RLIMIT_RTPRIO
    if (PyModule_AddIntConstant(mod, "RLIMIT_RTPRIO", RLIMIT_RTPRIO))
        return NULL;
#endif

#ifdef RLIMIT_RTTIME
    if (PyModule_AddIntConstant(mod, "RLIMIT_RTTIME", RLIMIT_RTTIME))
        return NULL;
#endif

#ifdef RLIMIT_SIGPENDING
    if (PyModule_AddIntConstant(mod, "RLIMIT_SIGPENDING", RLIMIT_SIGPENDING))
        return NULL;
#endif

// Free specific

#ifdef RLIMIT_SWAP
    if (PyModule_AddIntConstant(mod, "RLIMIT_SWAP", RLIMIT_SWAP))
        return NULL;
#endif

#ifdef RLIMIT_SBSIZE
    if (PyModule_AddIntConstant(mod, "RLIMIT_SBSIZE", RLIMIT_SBSIZE))
        return NULL;
#endif

#ifdef RLIMIT_NPTS
    if (PyModule_AddIntConstant(mod, "RLIMIT_NPTS", RLIMIT_NPTS))
        return NULL;
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
        if (PyModule_AddObject(mod, "RLIM_INFINITY", v))
            return NULL;
    }
#endif  // defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)

    return mod;
}
