/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
Disk related functions. Original code was refactored and moved from
psutil/arch/netbsd/specific.c in 2023 (and was moved in there previously
already) from cset 84219ad. For reference, here's the git history with
original(ish) implementations:
- disk IO counters: 312442ad2a5b5d0c608476c5ab3e267735c3bc59 (Jan 2016)
*/

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/disk.h>

#include "../../arch/all/init.h"


PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    int i, dk_ndrive;
    int mib[3];
    struct io_sysctl *stats = NULL;
    size_t stats_len;
    PyObject *py_disk_info = NULL;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    mib[0] = CTL_HW;
    mib[1] = HW_IOSTATS;
    mib[2] = sizeof(struct io_sysctl);

    // Use helper to allocate and fill buffer
    if (psutil_sysctl_malloc(mib, 3, (char **)&stats, &stats_len) == -1)
        goto error;

    dk_ndrive = (int)(stats_len / sizeof(struct io_sysctl));

    for (i = 0; i < dk_ndrive; i++) {
        py_disk_info = Py_BuildValue(
            "(KKKK)",
            stats[i].rxfer,
            stats[i].wxfer,
            stats[i].rbytes,
            stats[i].wbytes
        );
        if (!py_disk_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, stats[i].name, py_disk_info))
            goto error;
        Py_DECREF(py_disk_info);
    }

    free(stats);
    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (stats != NULL)
        free(stats);
    return NULL;
}
