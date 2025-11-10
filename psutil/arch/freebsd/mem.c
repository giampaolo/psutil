/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <kvm.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <vm/vm_param.h>
#include <paths.h>
#include <fcntl.h>

#include "../../arch/all/init.h"

#ifndef _PATH_DEVNULL
#define _PATH_DEVNULL "/dev/null"
#endif


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    unsigned long total;
    unsigned int active, inactive, wired, cached, free;
    long buffers;
    struct vmtotal vm;
    int mib[] = {CTL_VM, VM_METER};
    long pagesize = psutil_getpagesize();

    size_t size_ul = sizeof(total);
    size_t size_ui = sizeof(active);
    size_t size_long = sizeof(buffers);
    size_t size_vm = sizeof(vm);

    PyObject *ret = NULL;

    if (psutil_sysctlbyname("hw.physmem", &total, size_ul) != 0)
        return NULL;

    if (psutil_sysctlbyname("vm.stats.vm.v_active_count", &active, size_ui)
        != 0)
        return NULL;

    if (psutil_sysctlbyname("vm.stats.vm.v_inactive_count", &inactive, size_ui)
        != 0)
        return NULL;

    if (psutil_sysctlbyname("vm.stats.vm.v_wire_count", &wired, size_ui) != 0)
        return NULL;

    // Optional; ignore error if not available
    if (psutil_sysctlbyname("vm.stats.vm.v_cache_count", &cached, size_ui)
        != 0)
    {
        PyErr_Clear();
        cached = 0;
    }

    if (psutil_sysctlbyname("vm.stats.vm.v_free_count", &free, size_ui) != 0)
        return NULL;

    if (psutil_sysctlbyname("vfs.bufspace", &buffers, size_long) != 0)
        return NULL;

    if (psutil_sysctl(mib, 2, &vm, size_vm) != 0) {
        return psutil_oserror_wsyscall("sysctl(CTL_VM | VM_METER)");
    }

    return Py_BuildValue(
        "KKKKKKKK",
        (unsigned long long)total,
        (unsigned long long)free * pagesize,
        (unsigned long long)active * pagesize,
        (unsigned long long)inactive * pagesize,
        (unsigned long long)wired * pagesize,
        (unsigned long long)cached * pagesize,
        (unsigned long long)buffers,
        (unsigned long long)(vm.t_vmshr + vm.t_rmshr) * pagesize  // shared
    );
}


PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    // Return swap memory stats (see 'swapinfo' cmdline tool)
    kvm_t *kd;
    struct kvm_swap kvmsw[1];
    unsigned int swapin, swapout, nodein, nodeout;
    size_t size = sizeof(unsigned int);
    long pagesize = psutil_getpagesize();

    kd = kvm_open(NULL, _PATH_DEVNULL, NULL, O_RDONLY, "kvm_open failed");
    if (kd == NULL) {
        psutil_runtime_error("kvm_open() syscall failed");
        return NULL;
    }

    if (kvm_getswapinfo(kd, kvmsw, 1, 0) < 0) {
        kvm_close(kd);
        psutil_runtime_error("kvm_getswapinfo() syscall failed");
        return NULL;
    }

    kvm_close(kd);

    if (psutil_sysctlbyname("vm.stats.vm.v_swapin", &swapin, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.vm.v_swapout", &swapout, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.vm.v_vnodein", &nodein, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.vm.v_vnodeout", &nodeout, size) != 0)
        return NULL;

    return Py_BuildValue(
        "(KKKII)",
        (unsigned long long)kvmsw[0].ksw_total * pagesize,  // total
        (unsigned long long)kvmsw[0].ksw_used * pagesize,  // used
        (unsigned long long)kvmsw[0].ksw_total * pagesize -  // free
            kvmsw[0].ksw_used * pagesize,
        swapin + swapout,  // swap in
        nodein + nodeout  // swap out
    );
}
