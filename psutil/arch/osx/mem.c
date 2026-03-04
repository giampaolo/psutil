/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// System memory related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c

// See:
// https://github.com/apple-open-source/macos/blob/master/system_cmds/vm_stat/vm_stat.c

#include <Python.h>
#include <math.h>
#include <mach/host_info.h>
#include <sys/sysctl.h>
#include <mach/mach.h>

#include "../../arch/all/init.h"


static int
psutil_sys_vminfo(vm_statistics64_t vmstat) {
    kern_return_t ret;
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    mach_port_t mport;

    mport = mach_host_self();
    if (mport == MACH_PORT_NULL) {
        psutil_runtime_error("mach_host_self() returned MACH_PORT_NULL");
        return -1;
    }

    ret = host_statistics64(
        mport, HOST_VM_INFO64, (host_info64_t)vmstat, &count
    );
    mach_port_deallocate(mach_task_self(), mport);
    if (ret != KERN_SUCCESS) {
        psutil_runtime_error(
            "host_statistics64(HOST_VM_INFO64) syscall failed: %s",
            mach_error_string(ret)
        );
        return -1;
    }
    return 0;
}


/*
 * Return system virtual memory stats.
 * See:
 * https://opensource.apple.com/source/system_cmds/system_cmds-790/vm_stat.tproj/vm_stat.c.auto.html
 */
PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    uint64_t total;
    unsigned long long active, inactive, wired, free, _speculative;
    unsigned long long available, used;
    double percent;
    int mib[2] = {CTL_HW, HW_MEMSIZE};
    vm_statistics64_data_t vm;
    long pagesize = psutil_getpagesize();
    Py_ssize_t pos = 0;
    static PyTypeObject *svmem_type = NULL;
    PyObject *obj = NULL;

    if (!svmem_type) {
        svmem_type = psutil_structseq_type_new(
            "svmem",
            NULL,
            "total",
            "available",
            "percent",
            "used",
            "free",
            "active",
            "inactive",
            "wired",
            NULL
        );
        if (!svmem_type)
            return NULL;
    }

    // This is also available as sysctlbyname("hw.memsize").
    if (psutil_sysctl(mib, 2, &total, sizeof(total)) != 0)
        return NULL;
    if (psutil_sys_vminfo(&vm) != 0)
        return NULL;

    active = (unsigned long long)vm.active_count * pagesize;
    inactive = (unsigned long long)vm.inactive_count * pagesize;
    wired = (unsigned long long)vm.wire_count * pagesize;
    free = (unsigned long long)vm.free_count * pagesize;
    _speculative = (unsigned long long)vm.speculative_count * pagesize;

    // This is how Zabbix calculates avail and used mem:
    // https://github.com/zabbix/zabbix/blob/master/src/libs/zbxsysinfo/osx/memory.c
    // Also see: https://github.com/giampaolo/psutil/issues/1277
    available = inactive + free;
    used = active + wired;

    // This is NOT how Zabbix calculates free mem but it matches "free"
    // CLI utility.
    free -= _speculative;

    percent = total > 0
                  ? round(((double)(total - available) / total) * 100.0 * 10.0)
                        / 10.0
                  : 0.0;

    obj = PyStructSequence_New(svmem_type);
    if (!obj)
        return NULL;

    // clang-format off
    if (!pystructseq_add(obj, &pos, "total",    "K", (unsigned long long)total)) goto error;
    if (!pystructseq_add(obj, &pos, "available","K", available))                 goto error;
    if (!pystructseq_add(obj, &pos, "percent",  "d", percent))                   goto error;
    if (!pystructseq_add(obj, &pos, "used",     "K", used))                      goto error;
    if (!pystructseq_add(obj, &pos, "free",     "K", free))                      goto error;
    if (!pystructseq_add(obj, &pos, "active",   "K", active))                    goto error;
    if (!pystructseq_add(obj, &pos, "inactive", "K", inactive))                  goto error;
    if (!pystructseq_add(obj, &pos, "wired",    "K", wired))                     goto error;
    // clang-format on

    return obj;

error:
    Py_DECREF(obj);
    return NULL;
}


/*
 * Return stats about swap memory.
 */
PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    struct xsw_usage totals;
    vm_statistics64_data_t vmstat;
    long pagesize = psutil_getpagesize();
    int mib[2] = {CTL_VM, VM_SWAPUSAGE};
    double percent;
    Py_ssize_t pos = 0;
    static PyTypeObject *sswap_type = NULL;
    PyObject *obj = NULL;

    if (!sswap_type) {
        sswap_type = psutil_structseq_type_new(
            "sswap",
            NULL,
            "total",
            "used",
            "free",
            "percent",
            "sin",
            "sout",
            NULL
        );
        if (!sswap_type)
            return NULL;
    }

    if (psutil_sysctl(mib, 2, &totals, sizeof(totals)) != 0)
        return NULL;
    if (psutil_sys_vminfo(&vmstat) != 0)
        return NULL;

    percent = totals.xsu_total > 0
                  ? round(
                        ((double)totals.xsu_used / totals.xsu_total) * 100.0
                        * 10.0
                    ) / 10.0
                  : 0.0;

    obj = PyStructSequence_New(sswap_type);
    if (!obj)
        return NULL;

    // clang-format off
    if (!pystructseq_add(obj, &pos, "total",   "K", (unsigned long long)totals.xsu_total))           goto error;
    if (!pystructseq_add(obj, &pos, "used",    "K", (unsigned long long)totals.xsu_used))             goto error;
    if (!pystructseq_add(obj, &pos, "free",    "K", (unsigned long long)totals.xsu_avail))            goto error;
    if (!pystructseq_add(obj, &pos, "percent", "d", percent))                                         goto error;
    if (!pystructseq_add(obj, &pos, "sin",     "K", (unsigned long long)vmstat.pageins * pagesize))   goto error;
    if (!pystructseq_add(obj, &pos, "sout",    "K", (unsigned long long)vmstat.pageouts * pagesize))  goto error;
    // clang-format on

    return obj;

error:
    Py_DECREF(obj);
    return NULL;
}
