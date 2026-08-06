/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <mntent.h>
#include <libperfstat.h>

#include "../../arch/all/init.h"
#include "init.h"


PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    FILE *file = NULL;
    struct mntent *mt = NULL;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    file = setmntent(MNTTAB, "rb");
    Py_END_ALLOW_THREADS
    if (file == NULL) {
        psutil_oserror();
        goto error;
    }

    // NOTE: getmntent() is MT-Unsafe (it returns a pointer to a static
    // buffer), so we can't release the GIL around it.
    while ((mt = getmntent(file)) != NULL) {
        py_dev = PyUnicode_DecodeFSDefault(mt->mnt_fsname);
        if (!py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(mt->mnt_dir);
        if (!py_mountp)
            goto error;
        if (!pylist_append_fmt(
                py_retlist,
                "(OOss)",
                py_dev,  // device
                py_mountp,  // mount point
                mt->mnt_type,  // fs type
                mt->mnt_opts  // options
            ))
        {
            goto error;
        }
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
    }
    endmntent(file);
    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_DECREF(py_retlist);
    if (file != NULL)
        endmntent(file);
    return NULL;
}


PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    PyObject *py_retdict = PyDict_New();
    PyObject *py_disk_info = NULL;
    perfstat_disk_t *diskt = NULL;
    perfstat_id_t id;
    int i, rc, disk_count;

    if (py_retdict == NULL)
        return NULL;

    // Get the count of disks
    disk_count = perfstat_disk(NULL, NULL, sizeof(perfstat_disk_t), 0);
    if (disk_count <= 0) {
        psutil_oserror();
        goto error;
    }

    // Allocate enough memory
    diskt = (perfstat_disk_t *)calloc(disk_count, sizeof(perfstat_disk_t));
    if (diskt == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    strcpy(id.name, FIRST_DISK);
    rc = perfstat_disk(&id, diskt, sizeof(perfstat_disk_t), disk_count);
    if (rc <= 0) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < disk_count; i++) {
        py_disk_info = Py_BuildValue(
            "KKKKKK",
            diskt[i].__rxfers,
            diskt[i].xfers - diskt[i].__rxfers,
            diskt[i].rblks * diskt[i].bsize,
            diskt[i].wblks * diskt[i].bsize,
            diskt[i].rserv / 1000 / 1000,  // from nano to milli secs
            diskt[i].wserv / 1000 / 1000  // from nano to milli secs
        );
        if (py_disk_info == NULL)
            goto error;
        if (PyDict_SetItemString(py_retdict, diskt[i].name, py_disk_info))
            goto error;
        Py_DECREF(py_disk_info);
    }
    free(diskt);
    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (diskt != NULL)
        free(diskt);
    return NULL;
}
