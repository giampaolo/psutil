/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/disk.h>


PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    int i, dk_ndrive, mib[3];
    size_t len;
    struct diskstats *stats = NULL;

    PyObject *py_retdict = PyDict_New();
    PyObject *py_disk_info = NULL;
    if (py_retdict == NULL)
        return NULL;

    mib[0] = CTL_HW;
    mib[1] = HW_DISKSTATS;
    len = 0;
    if (sysctl(mib, 2, NULL, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    dk_ndrive = (int)(len / sizeof(struct diskstats));

    stats = malloc(len);
    if (stats == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    if (sysctl(mib, 2, stats, &len, NULL, 0) < 0 ) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < dk_ndrive; i++) {
        py_disk_info = Py_BuildValue(
            "(KKKK)",
            stats[i].ds_rxfer,  // num reads
            stats[i].ds_wxfer,  // num writes
            stats[i].ds_rbytes,  // read bytes
            stats[i].ds_wbytes  // write bytes
        );
        if (!py_disk_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, stats[i].ds_name, py_disk_info))
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
