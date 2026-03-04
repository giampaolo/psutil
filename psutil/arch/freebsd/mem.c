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


// shorter alias for psutil_sysctlbyname()
static inline int
sbn(const char *name, void *oldp, size_t oldlen) {
    return psutil_sysctlbyname(name, oldp, oldlen);
}


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    unsigned long total;
    unsigned int active, inactive, wired, cached, free;
    long buffers;
    struct vmtotal vm;
    int mib[] = {CTL_VM, VM_METER};
    long pagesize = psutil_getpagesize();

    if (sbn("hw.physmem", &total, sizeof(total)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_active_count", &active, sizeof(active)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_inactive_count", &inactive, sizeof(inactive)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_wire_count", &wired, sizeof(wired)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_free_count", &free, sizeof(free)) != 0)
        return NULL;
    if (sbn("vfs.bufspace", &buffers, sizeof(buffers)) != 0)
        return NULL;

    // Optional; ignore error if not available
    if (sbn("vm.stats.vm.v_cache_count", &cached, sizeof(cached)) != 0) {
        PyErr_Clear();
        cached = 0;
    }

    if (psutil_sysctl(mib, 2, &vm, sizeof(vm)) != 0)
        return psutil_oserror_wsyscall("sysctl(CTL_VM | VM_METER)");

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
    unsigned int free, swapin, swapout, nodein, nodeout;
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

    if (sbn("vm.stats.vm.v_swapin", &swapin, sizeof(swapin)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_swapout", &swapout, sizeof(swapout)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_vnodein", &nodein, sizeof(nodein)) != 0)
        return NULL;
    if (sbn("vm.stats.vm.v_vnodeout", &nodeout, sizeof(nodeout)) != 0)
        return NULL;

    free = (kvmsw[0].ksw_total - kvmsw[0].ksw_used);

    return Py_BuildValue(
        "(KKKII)",
        (unsigned long long)kvmsw[0].ksw_total * pagesize,  // total
        (unsigned long long)kvmsw[0].ksw_used * pagesize,  // used
        (unsigned long long)free * pagesize,  // free
        swapin + swapout,  // swap in
        nodein + nodeout  // swap out
    );
}
