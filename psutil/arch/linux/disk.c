/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <mntent.h>

#include "../../_psutil_common.h"


// Return disk mounted partitions as a list of tuples including device,
// mount point and filesystem type.
PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    FILE *file = NULL;
    struct mntent *entry;
    char *mtab_path;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (!PyArg_ParseTuple(args, "s", &mtab_path))
        return NULL;

    Py_BEGIN_ALLOW_THREADS
    file = setmntent(mtab_path, "r");
    Py_END_ALLOW_THREADS
    if ((file == 0) || (file == NULL)) {
        psutil_debug("setmntent() failed");
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, mtab_path);
        goto error;
    }

    while ((entry = getmntent(file))) {
        if (entry == NULL) {
            PyErr_Format(PyExc_RuntimeError, "getmntent() syscall failed");
            goto error;
        }
        py_dev = PyUnicode_DecodeFSDefault(entry->mnt_fsname);
        if (! py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(entry->mnt_dir);
        if (! py_mountp)
            goto error;
        py_tuple = Py_BuildValue("(OOss)",
                                 py_dev,             // device
                                 py_mountp,          // mount point
                                 entry->mnt_type,    // fs type
                                 entry->mnt_opts);   // options
        if (! py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
    }
    endmntent(file);
    return py_retlist;

error:
    if (file != NULL)
        endmntent(file);
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}
