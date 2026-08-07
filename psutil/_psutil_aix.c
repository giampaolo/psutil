/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// AIX support is experimental at this time.
// The following functions and methods are unsupported on the AIX platform:
// - psutil.Process.memory_maps
//
// Known limitations:
// - psutil.Process.io_counters read count is always 0
// - psutil.Process.io_counters may not be available on older AIX versions
// - psutil.Process.threads may not be available on older AIX versions
// - psutil.net_io_counters may not be available on older AIX versions
// - reading basic process info may fail or return incorrect values when
//   process is starting (see IBM APAR IV58499 - fixed in newer AIX versions)
// - sockets and pipes may not be counted in num_fds (fixed in newer AIX
//   versions)
//
// Useful resources:
// - proc filesystem:
// http://www-01.ibm.com/support/knowledgecenter/ssw_aix_72/com.ibm.aix.files/proc.htm
// - libperfstat:
// http://www-01.ibm.com/support/knowledgecenter/ssw_aix_72/com.ibm.aix.files/libperfstat.h.htm

#include <Python.h>
#include <sys/proc.h>
#include <netinet/tcp_fsm.h>
#include <libperfstat.h>  // CURR_VERSION_* guards below

#include "arch/all/init.h"
#include "arch/aix/init.h"


// define the psutil C module methods and initialize the module.
static PyMethodDef mod_methods[] = {
    // --- process-related functions
    {"proc_args", psutil_proc_args, METH_VARARGS},
    {"proc_cpu_times", psutil_proc_cpu_times, METH_VARARGS},
    {"proc_cred", psutil_proc_cred, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_name", psutil_proc_name, METH_VARARGS},
    {"proc_oneshot", psutil_proc_oneshot, METH_VARARGS},
#ifdef CURR_VERSION_THREAD
    {"proc_threads", psutil_proc_threads, METH_VARARGS},
#endif
#ifdef CURR_VERSION_PROCESS
    {"proc_io_counters", psutil_proc_io_counters, METH_VARARGS},
#endif
    {"proc_num_ctx_switches", psutil_proc_num_ctx_switches, METH_VARARGS},

    // --- system-related functions
    {"boot_time", psutil_boot_time, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS},
#if defined(CURR_VERSION_NETINTERFACE) && CURR_VERSION_NETINTERFACE >= 3
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
#endif
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"net_connections", psutil_net_connections, METH_VARARGS},
    {"net_if_stats", psutil_net_if_stats, METH_VARARGS},

    // --- others
    {"check_pid_range", psutil_check_pid_range, METH_VARARGS},
    {"set_debug", psutil_set_debug, METH_VARARGS},

    {NULL, NULL, 0, NULL}
};


#ifdef __cplusplus
extern "C" {
#endif

static int
psutil_add_constants(PyObject *mod) {
    PSUTIL_ADD_INT(mod, "version", PSUTIL_VERSION);
    PSUTIL_ADD_INT(mod, "SIDL", SIDL);
    PSUTIL_ADD_INT(mod, "SZOMB", SZOMB);
    PSUTIL_ADD_INT(mod, "SACTIVE", SACTIVE);
    PSUTIL_ADD_INT(mod, "SSWAP", SSWAP);
    PSUTIL_ADD_INT(mod, "SSTOP", SSTOP);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSED", TCPS_CLOSED);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSING", TCPS_CLOSING);
    PSUTIL_ADD_INT(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT);
    PSUTIL_ADD_INT(mod, "TCPS_LISTEN", TCPS_LISTEN);
    PSUTIL_ADD_INT(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED);
    PSUTIL_ADD_INT(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT);
    PSUTIL_ADD_INT(mod, "TCPS_SYN_RCVD", TCPS_SYN_RECEIVED);
    PSUTIL_ADD_INT(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1);
    PSUTIL_ADD_INT(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2);
    PSUTIL_ADD_INT(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK);
    PSUTIL_ADD_INT(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT);
    PSUTIL_ADD_INT(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE);
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

#ifdef __cplusplus
}
#endif
