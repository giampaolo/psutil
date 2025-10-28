/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/resource.h>
#include <sys/types.h>
#include <sys/sched.h>  // CP_* on OpenBSD

#include "../../arch/all/init.h"


PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    int mib[2];
    int ncpu;
    size_t len;

    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);

    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1)
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", ncpu);
}


PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
#ifdef PSUTIL_NETBSD
    u_int64_t cpu_time[CPUSTATES];
#else
    long cpu_time[CPUSTATES];
#endif
    size_t size = sizeof(cpu_time);
    int ret;

#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_NETBSD)
    ret = psutil_sysctlbyname("kern.cp_time", &cpu_time, size);
#elif PSUTIL_OPENBSD
    int mib[] = {CTL_KERN, KERN_CPTIME};
    ret = psutil_sysctl(mib, 2, &cpu_time, size);
#endif
    if (ret != 0)
        return NULL;
    return Py_BuildValue(
        "(ddddd)",
        (double)cpu_time[CP_USER] / CLOCKS_PER_SEC,
        (double)cpu_time[CP_NICE] / CLOCKS_PER_SEC,
        (double)cpu_time[CP_SYS] / CLOCKS_PER_SEC,
        (double)cpu_time[CP_IDLE] / CLOCKS_PER_SEC,
        (double)cpu_time[CP_INTR] / CLOCKS_PER_SEC
    );
}
