/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#if PSUTIL_NETBSD  // getvfsstat()
#include <sys/types.h>
#include <sys/statvfs.h>
#else  // getfsstat()
#include <sys/param.h>
#include <sys/ucred.h>
#include <sys/mount.h>
#endif

#include "../../arch/all/init.h"


PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    int num;
    int i;
    long len;
    uint64_t flags;
    char opts[200];
#ifdef PSUTIL_NETBSD
    struct statvfs *fs = NULL;
#else
    struct statfs *fs = NULL;
#endif
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;

    // get the number of mount points
    Py_BEGIN_ALLOW_THREADS
#ifdef PSUTIL_NETBSD
    num = getvfsstat(NULL, 0, MNT_NOWAIT);
#else
    num = getfsstat(NULL, 0, MNT_NOWAIT);
#endif
    Py_END_ALLOW_THREADS
    if (num == -1) {
        psutil_oserror();
        goto error;
    }

    len = sizeof(*fs) * num;
    fs = malloc(len);
    if (fs == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    Py_BEGIN_ALLOW_THREADS
#ifdef PSUTIL_NETBSD
    num = getvfsstat(fs, len, MNT_NOWAIT);
#else
    num = getfsstat(fs, len, MNT_NOWAIT);
#endif
    Py_END_ALLOW_THREADS
    if (num == -1) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < num; i++) {
        py_tuple = NULL;
        opts[0] = 0;
#ifdef PSUTIL_NETBSD
        flags = fs[i].f_flag;
#else
        flags = fs[i].f_flags;
#endif

        // see sys/mount.h
        if (flags & MNT_RDONLY)
            str_append(opts, sizeof(opts), "ro");
        else
            str_append(opts, sizeof(opts), "rw");
        if (flags & MNT_SYNCHRONOUS)
            str_append(opts, sizeof(opts), ",sync");
        if (flags & MNT_NOEXEC)
            str_append(opts, sizeof(opts), ",noexec");
        if (flags & MNT_NOSUID)
            str_append(opts, sizeof(opts), ",nosuid");
        if (flags & MNT_ASYNC)
            str_append(opts, sizeof(opts), ",async");
        if (flags & MNT_NOATIME)
            str_append(opts, sizeof(opts), ",noatime");
        if (flags & MNT_SOFTDEP)
            str_append(opts, sizeof(opts), ",softdep");
#ifdef PSUTIL_FREEBSD
        if (flags & MNT_UNION)
            str_append(opts, sizeof(opts), ",union");
        if (flags & MNT_SUIDDIR)
            str_append(opts, sizeof(opts), ",suiddir");
        if (flags & MNT_NOSYMFOLLOW)
            str_append(opts, sizeof(opts), ",nosymfollow");
#ifdef MNT_GJOURNAL
        if (flags & MNT_GJOURNAL)
            str_append(opts, sizeof(opts), ",gjournal");
#endif
        if (flags & MNT_MULTILABEL)
            str_append(opts, sizeof(opts), ",multilabel");
        if (flags & MNT_ACLS)
            str_append(opts, sizeof(opts), ",acls");
        if (flags & MNT_NOCLUSTERR)
            str_append(opts, sizeof(opts), ",noclusterr");
        if (flags & MNT_NOCLUSTERW)
            str_append(opts, sizeof(opts), ",noclusterw");
#ifdef MNT_NFS4ACLS
        if (flags & MNT_NFS4ACLS)
            str_append(opts, sizeof(opts), ",nfs4acls");
#endif
#elif PSUTIL_NETBSD
        if (flags & MNT_NODEV)
            str_append(opts, sizeof(opts), ",nodev");
        if (flags & MNT_UNION)
            str_append(opts, sizeof(opts), ",union");
        if (flags & MNT_NOCOREDUMP)
            str_append(opts, sizeof(opts), ",nocoredump");
#ifdef MNT_RELATIME
        if (flags & MNT_RELATIME)
            str_append(opts, sizeof(opts), ",relatime");
#endif
        if (flags & MNT_IGNORE)
            str_append(opts, sizeof(opts), ",ignore");
#ifdef MNT_DISCARD
        if (flags & MNT_DISCARD)
            str_append(opts, sizeof(opts), ",discard");
#endif
#ifdef MNT_EXTATTR
        if (flags & MNT_EXTATTR)
            str_append(opts, sizeof(opts), ",extattr");
#endif
        if (flags & MNT_LOG)
            str_append(opts, sizeof(opts), ",log");
        if (flags & MNT_SYMPERM)
            str_append(opts, sizeof(opts), ",symperm");
        if (flags & MNT_NODEVMTIME)
            str_append(opts, sizeof(opts), ",nodevmtime");
#endif
        py_dev = PyUnicode_DecodeFSDefault(fs[i].f_mntfromname);
        if (!py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(fs[i].f_mntonname);
        if (!py_mountp)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOss)",
            py_dev,  // device
            py_mountp,  // mount point
            fs[i].f_fstypename,  // fs type
            opts  // options
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
    }

    free(fs);
    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (fs != NULL)
        free(fs);
    return NULL;
}
