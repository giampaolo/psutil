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
#include <mach/host_info.h>
#include <sys/sysctl.h>
#include <mach/mach.h>

#include "../../_psutil_posix.h"


static int
psutil_sys_vminfo(vm_statistics64_t vmstat) {
    kern_return_t ret;
    mach_msg_type_number_t count = HOST_VM_INFO64_COUNT;
    mach_port_t mport;

    mport = mach_host_self();
    if (mport == MACH_PORT_NULL) {
        PyErr_SetString(PyExc_RuntimeError,
                        "mach_host_self() returned MACH_PORT_NULL");
        return 1;
    }

    ret = host_statistics64(mport, HOST_VM_INFO64, (host_info64_t)vmstat, &count);
    mach_port_deallocate(mach_task_self(), mport);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics64(HOST_VM_INFO64) syscall failed: %s",
            mach_error_string(ret)
        );
        return 1;
    }
    return 0;
}


/*
 * Return system virtual memory stats.
 * See:
 * https://opensource.apple.com/source/system_cmds/system_cmds-790/
 *     vm_stat.tproj/vm_stat.c.auto.html
 */
PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    return Py_BuildValue(
        "KKKKKK",
        1,
        1,
        1,
        1,
        1,
        1);
}


/*
 * Return stats about swap memory.
 */
PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    return Py_BuildValue(
        "KKKKK",
        1,
        1,
        1,
        1,
        1);
}
