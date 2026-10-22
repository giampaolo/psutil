/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Linux-specific functions.

#ifndef _GNU_SOURCE
#define _GNU_SOURCE 1
#endif
#include <Python.h>
#include <linux/cn_proc.h>  // PROC_EVENT_*
#include <linux/connector.h>  // CN_IDX_PROC
#include <linux/ethtool.h>  // DUPLEX_*
#include <linux/netlink.h>  // NETLINK_CONNECTOR

#include "arch/all/init.h"

// May happen on old RedHat versions, see:
// https://github.com/giampaolo/psutil/issues/607
#ifndef DUPLEX_UNKNOWN
#define DUPLEX_UNKNOWN 0xff
#endif

static PyMethodDef mod_methods[] = {
    // --- per-process functions
    {"proc_ioprio_get", psutil_proc_ioprio_get, METH_VARARGS},
    {"proc_ioprio_set", psutil_proc_ioprio_set, METH_VARARGS},
#ifdef PSUTIL_HAS_CPU_AFFINITY
    {"proc_cpu_affinity_get", psutil_proc_cpu_affinity_get, METH_VARARGS},
    {"proc_cpu_affinity_set", psutil_proc_cpu_affinity_set, METH_VARARGS},
#endif
    // --- system related functions
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"net_if_duplex_speed", psutil_net_if_duplex_speed, METH_VARARGS},
    {"netlink_proc_register", psutil_netlink_proc_register, METH_VARARGS},
    {"netlink_proc_read", psutil_netlink_proc_read, METH_VARARGS},
#ifdef PSUTIL_HAS_HEAP_INFO
    {"heap_info", psutil_heap_info, METH_VARARGS},
#endif
#ifdef PSUTIL_HAS_HEAP_TRIM
    {"heap_trim", psutil_heap_trim, METH_VARARGS},
#endif

    // --- linux specific
    {"linux_sysinfo", psutil_linux_sysinfo, METH_VARARGS},
    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},
    {NULL, NULL, 0, NULL}
};


static int
psutil_add_constants(PyObject *mod) {
    PSUTIL_ADD_INT(mod, "version", PSUTIL_VERSION);
    PSUTIL_ADD_INT(mod, "DUPLEX_HALF", DUPLEX_HALF);
    PSUTIL_ADD_INT(mod, "DUPLEX_FULL", DUPLEX_FULL);
    PSUTIL_ADD_INT(mod, "DUPLEX_UNKNOWN", DUPLEX_UNKNOWN);

    // netlink sockets
    PSUTIL_ADD_INT(mod, "NETLINK_CONNECTOR", NETLINK_CONNECTOR);
    PSUTIL_ADD_INT(mod, "CN_IDX_PROC", CN_IDX_PROC);

    // process events
    PSUTIL_ADD_INT(mod, "PROC_EVENT_COMM", PROC_EVENT_COMM);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_COREDUMP", PROC_EVENT_COREDUMP);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_EXEC", PROC_EVENT_EXEC);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_EXIT", PROC_EVENT_EXIT);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_FORK", PROC_EVENT_FORK);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_GID", PROC_EVENT_GID);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_PTRACE", PROC_EVENT_PTRACE);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_SID", PROC_EVENT_SID);
    PSUTIL_ADD_INT(mod, "PROC_EVENT_UID", PROC_EVENT_UID);
    return 0;
}


static int
psutil_exec(PyObject *mod) {
    if (psutil_setup() != 0)
        return -1;
    if (psutil_posix_add_constants(mod) != 0)
        return -1;
    if (psutil_posix_add_methods(mod) != 0)
        return -1;
    if (psutil_add_exceptions(mod) != 0)
        return -1;
    if (psutil_add_constants(mod) != 0)
        return -1;
    return 0;
}

PyMODINIT_FUNC
PyInit__psutil(void) {
    return psutil_mod_init("_psutil", mod_methods, psutil_exec);
}
