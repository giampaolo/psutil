/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// System memory related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c

#include <Python.h>
#include <mach/host_info.h>
#include <sys/sysctl.h>
#include <mach/mach.h>

#include "../../_psutil_posix.h"


static int
psutil_sys_vminfo(vm_statistics_data_t *vmstat) {
    kern_return_t ret;
    mach_msg_type_number_t count = sizeof(*vmstat) / sizeof(integer_t);
    mach_port_t mport = mach_host_self();

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)vmstat, &count);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_VM_INFO) syscall failed: %s",
            mach_error_string(ret));
        return 0;
    }
    mach_port_deallocate(mach_task_self(), mport);
    return 1;
}


/*
 * Return system virtual memory stats.
 * See:
 * https://opensource.apple.com/source/system_cmds/system_cmds-790/
 *     vm_stat.tproj/vm_stat.c.auto.html
 */
PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    int      mib[2];
    uint64_t total;
    size_t   len = sizeof(total);
    vm_statistics_data_t vm;
    long pagesize = psutil_getpagesize();
    // physical mem
    mib[0] = CTL_HW;
    mib[1] = HW_MEMSIZE;

    // This is also available as sysctlbyname("hw.memsize").
    if (sysctl(mib, 2, &total, &len, NULL, 0)) {
        if (errno != 0)
            PyErr_SetFromErrno(PyExc_OSError);
        else
            PyErr_Format(
                PyExc_RuntimeError, "sysctl(HW_MEMSIZE) syscall failed");
        return NULL;
    }

    // vm
    if (!psutil_sys_vminfo(&vm))
        return NULL;

    return Py_BuildValue(
        "KKKKKK",
        total,
        (unsigned long long) vm.active_count * pagesize,  // active
        (unsigned long long) vm.inactive_count * pagesize,  // inactive
        (unsigned long long) vm.wire_count * pagesize,  // wired
        (unsigned long long) vm.free_count * pagesize,  // free
        (unsigned long long) vm.speculative_count * pagesize  // speculative
    );
}


/*
 * Return stats about swap memory.
 */
PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    int mib[2];
    size_t size;
    struct xsw_usage totals;
    vm_statistics_data_t vmstat;
    long pagesize = psutil_getpagesize();

    mib[0] = CTL_VM;
    mib[1] = VM_SWAPUSAGE;
    size = sizeof(totals);
    if (sysctl(mib, 2, &totals, &size, NULL, 0) == -1) {
        if (errno != 0)
            PyErr_SetFromErrno(PyExc_OSError);
        else
            PyErr_Format(
                PyExc_RuntimeError, "sysctl(VM_SWAPUSAGE) syscall failed");
        return NULL;
    }
    if (!psutil_sys_vminfo(&vmstat))
        return NULL;

    return Py_BuildValue(
        "LLLKK",
        totals.xsu_total,
        totals.xsu_used,
        totals.xsu_avail,
        (unsigned long long)vmstat.pageins * pagesize,
        (unsigned long long)vmstat.pageouts * pagesize);
}
