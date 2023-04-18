/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sched.h>
#include <sys/sysctl.h>
#include <uvm/uvm_extern.h>


/*
CPU related functions. Original code was refactored and moved from
psutil/arch/netbsd/specific.c in 2023 (and was moved in there previously
already) from cset 84219ad. For reference, here's the git history with
original(ish) implementations:
- per CPU times: 312442ad2a5b5d0c608476c5ab3e267735c3bc59 (Jan 2016)
- CPU stats: a991494e4502e1235ebc62b5ba450287d0dedec0 (Jan 2016)
*/


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    size_t size;
    struct uvmexp_sysctl uv;
    int uvmexp_mib[] = {CTL_VM, VM_UVMEXP2};

    size = sizeof(uv);
    if (sysctl(uvmexp_mib, 2, &uv, &size, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

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
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int mib[3];
    int ncpu;
    size_t len;
    size_t size;
    int i;
    PyObject *py_cputime = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    // retrieve the number of cpus
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);
    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    uint64_t cpu_time[CPUSTATES];

    for (i = 0; i < ncpu; i++) {
        // per-cpu info
        mib[0] = CTL_KERN;
        mib[1] = KERN_CP_TIME;
        mib[2] = i;
        size = sizeof(cpu_time);
        if (sysctl(mib, 3, &cpu_time, &size, NULL, 0) == -1) {
            PyErr_SetFromErrno(PyExc_OSError);
            return NULL;
        }

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
