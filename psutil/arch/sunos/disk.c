/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <sys/mntent.h>
#include <sys/mnttab.h>
#include <kstat.h>

#include "../../arch/all/init.h"


PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    kstat_ctl_t *kc;
    kstat_t *ksp;
    kstat_io_t kio;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_disk_info = NULL;

    if (py_retdict == NULL)
        return NULL;
    kc = kstat_open();
    if (kc == NULL) {
        psutil_oserror();
        goto error;
    }
    ksp = kc->kc_chain;
    while (ksp != NULL) {
        if (ksp->ks_type == KSTAT_TYPE_IO) {
            if (strcmp(ksp->ks_class, "disk") == 0) {
                if (kstat_read(kc, ksp, &kio) == -1) {
                    kstat_close(kc);
                    return psutil_oserror();
                    ;
                }
                py_disk_info = Py_BuildValue(
                    "(IIKKLL)",
                    kio.reads,
                    kio.writes,
                    kio.nread,
                    kio.nwritten,
                    kio.rtime / 1000 / 1000,  // from nano to milli secs
                    kio.wtime / 1000 / 1000  // from nano to milli secs
                );
                if (!py_disk_info)
                    goto error;
                if (PyDict_SetItemString(
                        py_retdict, ksp->ks_name, py_disk_info
                    ))
                    goto error;
                Py_CLEAR(py_disk_info);
            }
        }
        ksp = ksp->ks_next;
    }
    kstat_close(kc);

    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (kc != NULL)
        kstat_close(kc);
    return NULL;
}


PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    FILE *file;
    struct mnttab mt;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    file = fopen(MNTTAB, "rb");
    if (file == NULL) {
        psutil_oserror();
        goto error;
    }

    while (getmntent(file, &mt) == 0) {
        py_dev = PyUnicode_DecodeFSDefault(mt.mnt_special);
        if (!py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(mt.mnt_mountp);
        if (!py_mountp)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOss)",
            py_dev,  // device
            py_mountp,  // mount point
            mt.mnt_fstype,  // fs type
            mt.mnt_mntopts  // options
        );
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
    }
    fclose(file);
    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (file != NULL)
        fclose(file);
    return NULL;
}
