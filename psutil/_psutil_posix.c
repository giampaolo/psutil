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
#if !defined(PSUTIL_OPENBSD) && !defined(PSUTIL_AIX)
    {"users", psutil_users, METH_VARARGS},
#endif
    {NULL, NULL, 0, NULL}
};


static int module_loaded = 0;

static int
_psutil_posix_exec(PyObject *mod) {
    // https://docs.python.org/3/howto/isolating-extensions.html#opt-out-limiting-to-one-module-object-per-process
    if (module_loaded) {
        PyErr_SetString(PyExc_ImportError,
                        "cannot load module more than once per process");
        return -1;
    }
    module_loaded = 1;

#ifdef Py_GIL_DISABLED
    if (PyUnstable_Module_SetGIL(mod, Py_MOD_GIL_NOT_USED))
        return NULL;
#endif

#if defined(PSUTIL_BSD) || \
        defined(PSUTIL_OSX) || \
        defined(PSUTIL_SUNOS) || \
        defined(PSUTIL_AIX)
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
        v = PyLong_FromLongLong((PY_LONG_LONG) RLIM_INFINITY);
    } else
#endif
    {
        v = PyLong_FromLong((long) RLIM_INFINITY);
    }
    if (v) {
        if (PyModule_AddObject(mod, "RLIM_INFINITY", v))
            return -1;
    }
#endif  // defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)

    return 0;
}

static struct PyModuleDef_Slot _psutil_posix_slots[] = {
    {Py_mod_exec, _psutil_posix_exec},
    {0, NULL},
};

static struct PyModuleDef module_def = {
    .m_base = PyModuleDef_HEAD_INIT,
    .m_name = "_psutil_posix",
    .m_size = 0,
    .m_methods = mod_methods,
    .m_slots = _psutil_posix_slots,
};

PyMODINIT_FUNC
PyInit__psutil_posix(void) {
    return PyModuleDef_Init(&module_def);
}
