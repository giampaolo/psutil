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
#include <sys/limits.h>
#include <sys/proc.h>
#include <sys/procfs.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysinfo.h>
#include <sys/thread.h>
#include <sys/types.h>
#include <fcntl.h>
#include <utmp.h>
#include <utmpx.h>
#include <mntent.h>
#include <sys/ioctl.h>
#include <sys/tihdr.h>
#include <stropts.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <libperfstat.h>
#include <unistd.h>

#include "../../arch/all/init.h"
#include "ifaddrs.h"
#include "net_connections.h"
#include "common.h"


#define TV2DOUBLE(t) (((t).tv_nsec * 0.000000001) + (t).tv_sec)


static PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int ncpu, rc, i;
    long ticks;
    perfstat_cpu_t *cpu = NULL;
    perfstat_id_t id;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    // get the number of ticks per second
    ticks = sysconf(_SC_CLK_TCK);
    if (ticks < 0) {
        psutil_oserror();
        goto error;
    }

    // get the number of cpus in ncpu
    ncpu = perfstat_cpu(NULL, NULL, sizeof(perfstat_cpu_t), 0);
    if (ncpu <= 0) {
        psutil_oserror();
        goto error;
    }

    // allocate enough memory to hold the ncpu structures
    cpu = (perfstat_cpu_t *)malloc(ncpu * sizeof(perfstat_cpu_t));
    if (cpu == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, "");
    rc = perfstat_cpu(&id, cpu, sizeof(perfstat_cpu_t), ncpu);

    if (rc <= 0) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < ncpu; i++) {
        if (!pylist_append_fmt(
                py_retlist,
                "(dddd)",
                (double)cpu[i].user / ticks,
                (double)cpu[i].sys / ticks,
                (double)cpu[i].idle / ticks,
                (double)cpu[i].wait / ticks
            ))
        {
            goto error;
        }
    }
    free(cpu);
    return py_retlist;

error:
    Py_DECREF(py_retlist);
    if (cpu != NULL)
        free(cpu);
    return NULL;
}


static PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    int ncpu, rc, i;
    // perfstat_cpu_total_t doesn't have invol/vol cswitch, only pswitch
    // which is apparently something else. We have to sum over all cpus
    perfstat_cpu_t *cpu = NULL;
    perfstat_id_t id;
    u_longlong_t cswitches = 0;
    u_longlong_t devintrs = 0;
    u_longlong_t softintrs = 0;
    u_longlong_t syscall = 0;

    // get the number of cpus in ncpu
    ncpu = perfstat_cpu(NULL, NULL, sizeof(perfstat_cpu_t), 0);
    if (ncpu <= 0) {
        psutil_oserror();
        goto error;
    }

    // allocate enough memory to hold the ncpu structures
    cpu = (perfstat_cpu_t *)malloc(ncpu * sizeof(perfstat_cpu_t));
    if (cpu == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, "");
    rc = perfstat_cpu(&id, cpu, sizeof(perfstat_cpu_t), ncpu);

    if (rc <= 0) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < ncpu; i++) {
        cswitches += cpu[i].invol_cswitch + cpu[i].vol_cswitch;
        devintrs += cpu[i].devintrs;
        softintrs += cpu[i].softintrs;
        syscall += cpu[i].syscall;
    }

    free(cpu);

    return Py_BuildValue("KKKK", cswitches, devintrs, softintrs, syscall);

error:
    if (cpu != NULL)
        free(cpu);
    return NULL;
}
