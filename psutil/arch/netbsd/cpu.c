/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <fcntl.h>
#include <kvm.h>
#include <limits.h>
#include <nlist.h>
#include <sys/sched.h>
#include <sys/sysctl.h>
#include <uvm/uvm_extern.h>

#include "../../arch/all/init.h"

// CPU related functions. Original code was refactored and moved from
// psutil/arch/netbsd/specific.c in 2023 (and was moved in there previously
// already) from cset 84219ad. For reference, here's the git history with
// original(ish) implementations:
// - per CPU times: 312442ad2a5b5d0c608476c5ab3e267735c3bc59 (Jan 2016)
// - CPU stats: a991494e4502e1235ebc62b5ba450287d0dedec0 (Jan 2016)


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    struct uvmexp_sysctl uv;
    int uvmexp_mib[] = {CTL_VM, VM_UVMEXP2};
    const int cpu_count_nintr = 3;
    char errbuf[_POSIX2_LINE_MAX];

    if (psutil_sysctl(uvmexp_mib, 2, &uv, sizeof(uv)) != 0)
        return NULL;

    kvm_t *kd = kvm_open(NULL, NULL, NULL, O_RDONLY, errbuf);
    if (!kd) {
        fprintf(stderr, "kvm_open: %s\n", errbuf);
        return NULL;
    }

    struct nlist nl[] = {
        { .n_name = "_cpu_counts" },
        { .n_name = NULL          }
    };

    if (kvm_nlist(kd, nl) != 0 || nl[0].n_value == 0) {
        fprintf(stderr, "kvm_nlist(_cpu_counts): %s\n", kvm_geterr(kd));
        kvm_close(kd);
        return NULL;
    }

    /* Read cpu_counts[CPU_COUNT_NINTR] — a single int64_t */
    uintptr_t addr = nl[0].n_value + cpu_count_nintr * sizeof(int64_t);
    int64_t nintr = 0;

    if (kvm_read(kd, addr, &nintr, sizeof(nintr)) != sizeof(nintr)) {
        fprintf(stderr, "kvm_read(cpu_counts[NINTR]): %s\n",
                kvm_geterr(kd));
        kvm_close(kd);
        return NULL;
    }

    kvm_close(kd);

    return Py_BuildValue(
        "KKKKKKK",
        (uint64_t)uv.swtch,    // ctx switches
        (uint64_t)nintr,        // interrupts
        (uint64_t)uv.softs,    // soft interrupts
        (uint64_t)uv.syscalls, // syscalls - XXX always 0
        (uint64_t)uv.traps,    // traps
        (uint64_t)uv.faults,   // faults
        (uint64_t)uv.forks     // forks
    );
}


PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int mib[3];
    int ncpu;
    size_t len;
    size_t size;
    int i;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    // retrieve the number of cpus
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    if (psutil_sysctl(mib, 2, &ncpu, sizeof(ncpu)) != 0)
        goto error;

    uint64_t cpu_time[CPUSTATES];

    for (i = 0; i < ncpu; i++) {
        // per-cpu info
        mib[0] = CTL_KERN;
        mib[1] = KERN_CP_TIME;
        mib[2] = i;
        if (psutil_sysctl(mib, 3, &cpu_time, sizeof(cpu_time)) != 0)
            goto error;
        if (!pylist_append_fmt(
                py_retlist,
                "(ddddd)",
                (double)cpu_time[CP_USER] / CLOCKS_PER_SEC,
                (double)cpu_time[CP_NICE] / CLOCKS_PER_SEC,
                (double)cpu_time[CP_SYS] / CLOCKS_PER_SEC,
                (double)cpu_time[CP_IDLE] / CLOCKS_PER_SEC,
                (double)cpu_time[CP_INTR] / CLOCKS_PER_SEC
            ))
        {
            goto error;
        }
    }

    return py_retlist;

error:
    Py_DECREF(py_retlist);
    return NULL;
}
