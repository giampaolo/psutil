/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>

#include "../../arch/all/init.h"


// Return a Python float indicating the system boot time expressed in
// seconds since the epoch.
PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    // fetch sysctl "kern.boottime"
    static int request[2] = {CTL_KERN, KERN_BOOTTIME};
    struct timeval boottime;

    if (psutil_sysctl(request, 2, &boottime, sizeof(boottime)) != 0)
        return NULL;
    return Py_BuildValue("d", (double)boottime.tv_sec);
}
