/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// System related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c

#include <Python.h>
#include <sys/sysctl.h>

#include "../../arch/all/init.h"


PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    // fetch sysctl "kern.boottime"
    int mib[2] = {CTL_KERN, KERN_BOOTTIME};
    struct timeval result;
    time_t boot_time = 0;

    if (psutil_sysctl(mib, 2, &result, sizeof(result)) == -1)
        return NULL;
    boot_time = result.tv_sec;
    return Py_BuildValue("d", (double)boot_time);
}
