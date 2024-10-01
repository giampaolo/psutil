/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */


#include <Python.h>
#include <sys/param.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <vm/vm_param.h>
#include <devstat.h>
#include <paths.h>
#include <fcntl.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


#ifndef _PATH_DEVNULL
    #define _PATH_DEVNULL "/dev/null"
#endif


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    unsigned long  total;
    unsigned int   active, inactive, wired, cached, free;
    size_t         size = sizeof(total);
    struct vmtotal vm;
    int            mib[] = {CTL_VM, VM_METER};
    long           pagesize = psutil_getpagesize();
#if __FreeBSD_version > 702101
    long buffers;
#else
    int buffers;
#endif
    size_t buffers_size = sizeof(buffers);

    if (sysctlbyname("hw.physmem", &total, &size, NULL, 0)) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('hw.physmem')"
        );
    }
    if (sysctlbyname("vm.stats.vm.v_active_count", &active, &size, NULL, 0)) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_active_count')");
    }
    if (sysctlbyname("vm.stats.vm.v_inactive_count", &inactive, &size, NULL, 0))
    {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_inactive_count')");
    }
    if (sysctlbyname("vm.stats.vm.v_wire_count", &wired, &size, NULL, 0)) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_wire_count')"
        );
    }
    // https://github.com/giampaolo/psutil/issues/997
    if (sysctlbyname("vm.stats.vm.v_cache_count", &cached, &size, NULL, 0)) {
        cached = 0;
    }
    if (sysctlbyname("vm.stats.vm.v_free_count", &free, &size, NULL, 0)) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_free_count')"
        );
    }
    if (sysctlbyname("vfs.bufspace", &buffers, &buffers_size, NULL, 0)) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vfs.bufspace')"
        );
    }

    size = sizeof(vm);
    if (sysctl(mib, 2, &vm, &size, NULL, 0) != 0) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctl(CTL_VM | VM_METER)"
        );
    }

    return Py_BuildValue("KKKKKKKK",
        (unsigned long long) total,
        (unsigned long long) free     * pagesize,
        (unsigned long long) active   * pagesize,
        (unsigned long long) inactive * pagesize,
        (unsigned long long) wired    * pagesize,
        (unsigned long long) cached   * pagesize,
        (unsigned long long) buffers,
        (unsigned long long) (vm.t_vmshr + vm.t_rmshr) * pagesize  // shared
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
        PyErr_SetString(PyExc_RuntimeError, "kvm_open() syscall failed");
        return NULL;
    }

    if (kvm_getswapinfo(kd, kvmsw, 1, 0) < 0) {
        kvm_close(kd);
        PyErr_SetString(PyExc_RuntimeError,
                        "kvm_getswapinfo() syscall failed");
        return NULL;
    }

    kvm_close(kd);

    if (sysctlbyname("vm.stats.vm.v_swapin", &swapin, &size, NULL, 0) == -1) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_swapin)'"
        );
    }
    if (sysctlbyname("vm.stats.vm.v_swapout", &swapout, &size, NULL, 0) == -1){
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_swapout)'"
        );
    }
    if (sysctlbyname("vm.stats.vm.v_vnodein", &nodein, &size, NULL, 0) == -1) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_vnodein)'"
        );
    }
    if (sysctlbyname("vm.stats.vm.v_vnodeout", &nodeout, &size, NULL, 0) == -1) {
        return psutil_PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.vm.v_vnodeout)'"
        );
    }

    return Py_BuildValue(
        "(KKKII)",
        (unsigned long long)kvmsw[0].ksw_total * pagesize,  // total
        (unsigned long long)kvmsw[0].ksw_used * pagesize,  // used
        (unsigned long long)kvmsw[0].ksw_total * pagesize - // free
                                kvmsw[0].ksw_used * pagesize,
        swapin + swapout,  // swap in
        nodein + nodeout  // swap out
    );
}
