/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <sys/sysinfo.h>
#include <kstat.h>

#include "../../arch/all/init.h"


// System-wide CPU times.
PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    kstat_ctl_t *kc;
    kstat_t *ksp;
    cpu_stat_t cs;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    kc = kstat_open();
    if (kc == NULL) {
        psutil_oserror();
        goto error;
    }

    for (ksp = kc->kc_chain; ksp != NULL; ksp = ksp->ks_next) {
        if (strcmp(ksp->ks_module, "cpu_stat") == 0) {
            if (kstat_read(kc, ksp, &cs) == -1) {
                psutil_oserror();
                goto error;
            }
            py_cputime = Py_BuildValue(
                "ffff",
                (float)cs.cpu_sysinfo.cpu[CPU_USER],
                (float)cs.cpu_sysinfo.cpu[CPU_KERNEL],
                (float)cs.cpu_sysinfo.cpu[CPU_IDLE],
                (float)cs.cpu_sysinfo.cpu[CPU_WAIT]
            );
            if (py_cputime == NULL)
                goto error;
            if (PyList_Append(py_retlist, py_cputime))
                goto error;
            Py_CLEAR(py_cputime);
        }
    }

    kstat_close(kc);
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    if (kc != NULL)
        kstat_close(kc);
    return NULL;
}


// Return the number of CPU cores on the system.
PyObject *
psutil_cpu_count_cores(PyObject *self, PyObject *args) {
    kstat_ctl_t *kc;
    kstat_t *ksp;
    int ncpus = 0;

    kc = kstat_open();
    if (kc == NULL)
        goto error;
    ksp = kstat_lookup(kc, "cpu_info", -1, NULL);
    if (ksp == NULL)
        goto error;

    for (ksp = kc->kc_chain; ksp; ksp = ksp->ks_next) {
        if (strcmp(ksp->ks_module, "cpu_info") != 0)
            continue;
        if (kstat_read(kc, ksp, NULL) == -1)
            goto error;
        ncpus += 1;
    }

    kstat_close(kc);
    if (ncpus > 0)
        return Py_BuildValue("i", ncpus);
    else
        goto error;

error:
    // mimic os.cpu_count()
    if (kc != NULL)
        kstat_close(kc);
    Py_RETURN_NONE;
}


// Return CPU statistics.
PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    kstat_ctl_t *kc;
    kstat_t *ksp;
    cpu_stat_t cs;
    unsigned int ctx_switches = 0;
    unsigned int interrupts = 0;
    unsigned int traps = 0;
    unsigned int syscalls = 0;

    kc = kstat_open();
    if (kc == NULL) {
        psutil_oserror();
        goto error;
    }

    for (ksp = kc->kc_chain; ksp != NULL; ksp = ksp->ks_next) {
        if (strcmp(ksp->ks_module, "cpu_stat") == 0) {
            if (kstat_read(kc, ksp, &cs) == -1) {
                psutil_oserror();
                goto error;
            }
            // voluntary + involuntary
            ctx_switches += cs.cpu_sysinfo.pswitch + cs.cpu_sysinfo.inv_swtch;
            interrupts += cs.cpu_sysinfo.intr;
            traps += cs.cpu_sysinfo.trap;
            syscalls += cs.cpu_sysinfo.syscall;
        }
    }

    kstat_close(kc);
    return Py_BuildValue("IIII", ctx_switches, interrupts, syscalls, traps);

error:
    if (kc != NULL)
        kstat_close(kc);
    return NULL;
}
