/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
System-wide CPU related functions.
Original code was refactored and moved from psutil/arch/freebsd/specific.c
in 2020 (and was moved in there previously already) from cset.
a4c0a0eb0d2a872ab7a45e47fcf37ef1fde5b012
For reference, here's the git history with original(ish) implementations:
- CPU stats: fb0154ef164d0e5942ac85102ab660b8d2938fbb
- CPU freq: 459556dd1e2979cdee22177339ced0761caf4c83
- CPU cores: e0d6d7865df84dc9a1d123ae452fd311f79b1dde
*/


#include <Python.h>
#include <sys/sysctl.h>
#include <devstat.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    int i;
    struct statinfo stats;

    PyObject *py_retdict = PyDict_New();
    PyObject *py_disk_info = NULL;

    if (py_retdict == NULL)
        return NULL;
    if (devstat_checkversion(NULL) < 0) {
        PyErr_Format(PyExc_RuntimeError,
                     "devstat_checkversion() syscall failed");
        goto error;
    }

    stats.dinfo = (struct devinfo *)malloc(sizeof(struct devinfo));
    if (stats.dinfo == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    bzero(stats.dinfo, sizeof(struct devinfo));

    if (devstat_getdevs(NULL, &stats) == -1) {
        PyErr_Format(PyExc_RuntimeError, "devstat_getdevs() syscall failed");
        goto error;
    }

    for (i = 0; i < stats.dinfo->numdevs; i++) {
        py_disk_info = NULL;
        struct devstat current;
        char disk_name[128];
        current = stats.dinfo->devices[i];
        snprintf(disk_name, sizeof(disk_name), "%s%d",
                 current.device_name,
                 current.unit_number);

        py_disk_info = Py_BuildValue(
            "(KKKKLLL)",
            current.operations[DEVSTAT_READ],   // no reads
            current.operations[DEVSTAT_WRITE],  // no writes
            current.bytes[DEVSTAT_READ],        // bytes read
            current.bytes[DEVSTAT_WRITE],       // bytes written
            (long long) PSUTIL_BT2MSEC(current.duration[DEVSTAT_READ]),  // r time
            (long long) PSUTIL_BT2MSEC(current.duration[DEVSTAT_WRITE]),  // w time
            (long long) PSUTIL_BT2MSEC(current.busy_time)  // busy time
        );      // finished transactions
        if (!py_disk_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, disk_name, py_disk_info))
            goto error;
        Py_DECREF(py_disk_info);
    }

    if (stats.dinfo->mem_ptr)
        free(stats.dinfo->mem_ptr);
    free(stats.dinfo);
    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (stats.dinfo != NULL)
        free(stats.dinfo);
    return NULL;
}

