/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/sched.h>  // for CPUSTATES & CP_*

#include "../../arch/all/init.h"


PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int mib[3];
    int ncpu;
    size_t len;
    int i;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    // retrieve the number of cpus
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    if (psutil_sysctl(mib, 2, &ncpu, sizeof(ncpu)) != 0)
        goto error;

    uint64_t cpu_time[CPUSTATES];

    for (i = 0; i < ncpu; i++) {
        mib[0] = CTL_KERN;
        mib[1] = KERN_CPTIME2;
        mib[2] = i;

        if (psutil_sysctl(mib, 3, &cpu_time, sizeof(cpu_time)) != 0)
            goto error;

        py_cputime = Py_BuildValue(
            "(ddddd)",
            (double)cpu_time[CP_USER] / CLOCKS_PER_SEC,
            (double)cpu_time[CP_NICE] / CLOCKS_PER_SEC,
            (double)cpu_time[CP_SYS] / CLOCKS_PER_SEC,
            (double)cpu_time[CP_IDLE] / CLOCKS_PER_SEC,
            (double)cpu_time[CP_INTR] / CLOCKS_PER_SEC
        );
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_DECREF(py_cputime);
    }

    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    struct uvmexp uv;
    int uvmexp_mib[] = {CTL_VM, VM_UVMEXP};

    if (psutil_sysctl(uvmexp_mib, 2, &uv, sizeof(uv)) != 0)
        return NULL;

    return Py_BuildValue(
        "IIIIIII",
        uv.swtch,  // ctx switches
        uv.intrs,  // interrupts - XXX always 0, will be determined via /proc
        uv.softs,  // soft interrupts
        uv.syscalls,  // syscalls - XXX always 0
        uv.traps,  // traps
        uv.faults,  // faults
        uv.forks  // forks
    );
}


PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    int freq;
    int mib[2] = {CTL_HW, HW_CPUSPEED};

    // On VirtualBox I get "sysctl hw.cpuspeed=2593" (never changing),
    // which appears to be expressed in Mhz.
    if (psutil_sysctl(mib, 2, &freq, sizeof(freq)) != 0)
        return NULL;

    return Py_BuildValue("i", freq);
}
