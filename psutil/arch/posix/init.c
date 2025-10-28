/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/resource.h>
#include <sys/socket.h>

#include "init.h"

PyObject *ZombieProcessError = NULL;

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
    return (long)getpagesize();
#endif
}


// Exposed so we can test it against Python's stdlib.
PyObject *
psutil_getpagesize_pywrapper(PyObject *self, PyObject *args) {
    return Py_BuildValue("l", psutil_getpagesize());
}


// POSIX-only methods.
static PyMethodDef posix_methods[] = {
    {"getpagesize", psutil_getpagesize_pywrapper, METH_VARARGS},
    {"net_if_addrs", psutil_net_if_addrs, METH_VARARGS},
    {"net_if_flags", psutil_net_if_flags, METH_VARARGS},
    {"net_if_is_running", psutil_net_if_is_running, METH_VARARGS},
    {"net_if_mtu", psutil_net_if_mtu, METH_VARARGS},
    {"proc_priority_get", psutil_proc_priority_get, METH_VARARGS},
    {"proc_priority_set", psutil_proc_priority_set, METH_VARARGS},
#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
#endif
#if !defined(PSUTIL_OPENBSD) && !defined(PSUTIL_AIX)
    {"users", psutil_users, METH_VARARGS},
#endif
#if defined(PSUTIL_OSX) || defined(PSUTIL_BSD)
    {"proc_is_zombie", psutil_proc_is_zombie, METH_VARARGS},
#endif
    {NULL, NULL, 0, NULL}
};


// Add POSIX methods to main OS module.
int
psutil_posix_add_methods(PyObject *mod) {
    for (int i = 0; posix_methods[i].ml_name != NULL; i++) {
        PyObject *f = PyCFunction_NewEx(&posix_methods[i], NULL, mod);
        if (!f) {
            return -1;
        }
        if (PyModule_AddObject(mod, posix_methods[i].ml_name, f)) {
            Py_DECREF(f);
            return -1;
        }
    }

    // custom exception
    ZombieProcessError = PyErr_NewException(
        "_psutil_posix.ZombieProcessError", NULL, NULL
    );
    if (ZombieProcessError == NULL)
        return -1;
    if (PyModule_AddObject(mod, "ZombieProcessError", ZombieProcessError))
        return -1;

    return 0;
}


// Add POSIX constants to main OS module.
int
psutil_posix_add_constants(PyObject *mod) {
    if (!mod)
        return -1;

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX) || defined(PSUTIL_SUNOS) \
    || defined(PSUTIL_AIX)
    if (PyModule_AddIntConstant(mod, "AF_LINK", AF_LINK))
        return -1;
#endif

#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
    PyObject *v;

#ifdef RLIMIT_AS
    if (PyModule_AddIntConstant(mod, "RLIMIT_AS", RLIMIT_AS))
        return -1;
#endif

#ifdef RLIMIT_CORE
    if (PyModule_AddIntConstant(mod, "RLIMIT_CORE", RLIMIT_CORE))
        return -1;
#endif

#ifdef RLIMIT_CPU
    if (PyModule_AddIntConstant(mod, "RLIMIT_CPU", RLIMIT_CPU))
        return -1;
#endif

#ifdef RLIMIT_DATA
    if (PyModule_AddIntConstant(mod, "RLIMIT_DATA", RLIMIT_DATA))
        return -1;
#endif

#ifdef RLIMIT_FSIZE
    if (PyModule_AddIntConstant(mod, "RLIMIT_FSIZE", RLIMIT_FSIZE))
        return -1;
#endif

#ifdef RLIMIT_MEMLOCK
    if (PyModule_AddIntConstant(mod, "RLIMIT_MEMLOCK", RLIMIT_MEMLOCK))
        return -1;
#endif

#ifdef RLIMIT_NOFILE
    if (PyModule_AddIntConstant(mod, "RLIMIT_NOFILE", RLIMIT_NOFILE))
        return -1;
#endif

#ifdef RLIMIT_NPROC
    if (PyModule_AddIntConstant(mod, "RLIMIT_NPROC", RLIMIT_NPROC))
        return -1;
#endif

#ifdef RLIMIT_RSS
    if (PyModule_AddIntConstant(mod, "RLIMIT_RSS", RLIMIT_RSS))
        return -1;
#endif

#ifdef RLIMIT_STACK
    if (PyModule_AddIntConstant(mod, "RLIMIT_STACK", RLIMIT_STACK))
        return -1;
#endif

        // Linux specific

#ifdef RLIMIT_LOCKS
    if (PyModule_AddIntConstant(mod, "RLIMIT_LOCKS", RLIMIT_LOCKS))
        return -1;
#endif

#ifdef RLIMIT_MSGQUEUE
    if (PyModule_AddIntConstant(mod, "RLIMIT_MSGQUEUE", RLIMIT_MSGQUEUE))
        return -1;
#endif

#ifdef RLIMIT_NICE
    if (PyModule_AddIntConstant(mod, "RLIMIT_NICE", RLIMIT_NICE))
        return -1;
#endif

#ifdef RLIMIT_RTPRIO
    if (PyModule_AddIntConstant(mod, "RLIMIT_RTPRIO", RLIMIT_RTPRIO))
        return -1;
#endif

#ifdef RLIMIT_RTTIME
    if (PyModule_AddIntConstant(mod, "RLIMIT_RTTIME", RLIMIT_RTTIME))
        return -1;
#endif

#ifdef RLIMIT_SIGPENDING
    if (PyModule_AddIntConstant(mod, "RLIMIT_SIGPENDING", RLIMIT_SIGPENDING))
        return -1;
#endif

        // Free specific

#ifdef RLIMIT_SWAP
    if (PyModule_AddIntConstant(mod, "RLIMIT_SWAP", RLIMIT_SWAP))
        return -1;
#endif

#ifdef RLIMIT_SBSIZE
    if (PyModule_AddIntConstant(mod, "RLIMIT_SBSIZE", RLIMIT_SBSIZE))
        return -1;
#endif

#ifdef RLIMIT_NPTS
    if (PyModule_AddIntConstant(mod, "RLIMIT_NPTS", RLIMIT_NPTS))
        return -1;
#endif

#if defined(HAVE_LONG_LONG)
    if (sizeof(RLIM_INFINITY) > sizeof(long)) {
        v = PyLong_FromLongLong((PY_LONG_LONG)RLIM_INFINITY);
    }
    else
#endif
    {
        v = PyLong_FromLong((long)RLIM_INFINITY);
    }
    if (v) {
        if (PyModule_AddObject(mod, "RLIM_INFINITY", v))
            return -1;
    }
#endif  // defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)

    return 0;
}
