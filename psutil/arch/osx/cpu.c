/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
System-wide CPU related functions.

Original code was refactored and moved from psutil/_psutil_osx.c in 2020
right before a4c0a0eb0d2a872ab7a45e47fcf37ef1fde5b012.
For reference, here's the git history with original implementations:

- CPU count logical: 3d291d425b856077e65163e43244050fb188def1
- CPU count physical: 4263e354bb4984334bc44adf5dd2f32013d69fba
- CPU times: 32488bdf54aed0f8cef90d639c1667ffaa3c31c7
- CPU stat: fa00dfb961ef63426c7818899340866ced8d2418
- CPU frequency: 6ba1ac4ebfcd8c95fca324b15606ab0ec1412d39
*/

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>

#include <mach/mach_error.h>
#include <mach/mach_host.h>
#include <mach/mach_port.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"



PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    int num;
    size_t size = sizeof(int);

    if (sysctlbyname("hw.logicalcpu", &num, &size, NULL, 2))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_count_cores(PyObject *self, PyObject *args) {
    int num;
    size_t size = sizeof(int);

    if (sysctlbyname("hw.physicalcpu", &num, &size, NULL, 0))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
    kern_return_t error;
    host_cpu_load_info_data_t r_load;

    mach_port_t host_port = mach_host_self();
    error = host_statistics(host_port, HOST_CPU_LOAD_INFO,
                            (host_info_t)&r_load, &count);
    if (error != KERN_SUCCESS) {
        return PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_CPU_LOAD_INFO) syscall failed: %s",
            mach_error_string(error));
    }
    mach_port_deallocate(mach_task_self(), host_port);

    return Py_BuildValue(
        "(dddd)",
        (double)r_load.cpu_ticks[CPU_STATE_USER] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
    );
}


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    struct vmmeter vmstat;
    kern_return_t ret;
    mach_msg_type_number_t count = sizeof(vmstat) / sizeof(integer_t);
    mach_port_t mport = mach_host_self();

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)&vmstat, &count);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_VM_INFO) failed: %s",
            mach_error_string(ret));
        return NULL;
    }
    mach_port_deallocate(mach_task_self(), mport);

    return Py_BuildValue(
        "IIIII",
        vmstat.v_swtch,  // ctx switches
        vmstat.v_intr,  // interrupts
        vmstat.v_soft,  // software interrupts
        vmstat.v_syscall,  // syscalls
        vmstat.v_trap  // traps
    );
}


PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    unsigned int curr;
    int64_t min = 0;
    int64_t max = 0;
    int mib[2];
    size_t len = sizeof(curr);
    size_t size = sizeof(min);

    // also available as "hw.cpufrequency" but it's deprecated
    mib[0] = CTL_HW;
    mib[1] = HW_CPU_FREQ;

    if (sysctl(mib, 2, &curr, &len, NULL, 0) < 0)
        return PyErr_SetFromOSErrnoWithSyscall("sysctl(HW_CPU_FREQ)");

    if (sysctlbyname("hw.cpufrequency_min", &min, &size, NULL, 0))
        psutil_debug("sysct('hw.cpufrequency_min') failed (set to 0)");

    if (sysctlbyname("hw.cpufrequency_max", &max, &size, NULL, 0))
        psutil_debug("sysctl('hw.cpufrequency_min') failed (set to 0)");

    return Py_BuildValue(
        "IKK",
        curr / 1000 / 1000,
        min / 1000 / 1000,
        max / 1000 / 1000);
}
