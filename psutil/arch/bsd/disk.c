/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/mount.h>
#if PSUTIL_NETBSD
    // getvfsstat()
    #include <sys/types.h>
    #include <sys/statvfs.h>
#else
    // getfsstat()
    #include <sys/param.h>
    #include <sys/ucred.h>
    #include <sys/mount.h>
#endif


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
        PyErr_SetFromErrno(PyExc_OSError);
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
        PyErr_SetFromErrno(PyExc_OSError);
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
            strlcat(opts, "ro", sizeof(opts));
        else
            strlcat(opts, "rw", sizeof(opts));
        if (flags & MNT_SYNCHRONOUS)
            strlcat(opts, ",sync", sizeof(opts));
        if (flags & MNT_NOEXEC)
            strlcat(opts, ",noexec", sizeof(opts));
        if (flags & MNT_NOSUID)
            strlcat(opts, ",nosuid", sizeof(opts));
        if (flags & MNT_ASYNC)
            strlcat(opts, ",async", sizeof(opts));
        if (flags & MNT_NOATIME)
            strlcat(opts, ",noatime", sizeof(opts));
        if (flags & MNT_SOFTDEP)
            strlcat(opts, ",softdep", sizeof(opts));
#ifdef PSUTIL_FREEBSD
        if (flags & MNT_UNION)
            strlcat(opts, ",union", sizeof(opts));
        if (flags & MNT_SUIDDIR)
            strlcat(opts, ",suiddir", sizeof(opts));
        if (flags & MNT_SOFTDEP)
            strlcat(opts, ",softdep", sizeof(opts));
        if (flags & MNT_NOSYMFOLLOW)
            strlcat(opts, ",nosymfollow", sizeof(opts));
#ifdef MNT_GJOURNAL
        if (flags & MNT_GJOURNAL)
            strlcat(opts, ",gjournal", sizeof(opts));
#endif
        if (flags & MNT_MULTILABEL)
            strlcat(opts, ",multilabel", sizeof(opts));
        if (flags & MNT_ACLS)
            strlcat(opts, ",acls", sizeof(opts));
        if (flags & MNT_NOCLUSTERR)
            strlcat(opts, ",noclusterr", sizeof(opts));
        if (flags & MNT_NOCLUSTERW)
            strlcat(opts, ",noclusterw", sizeof(opts));
#ifdef MNT_NFS4ACLS
        if (flags & MNT_NFS4ACLS)
            strlcat(opts, ",nfs4acls", sizeof(opts));
#endif
#elif PSUTIL_NETBSD
        if (flags & MNT_NODEV)
            strlcat(opts, ",nodev", sizeof(opts));
        if (flags & MNT_UNION)
            strlcat(opts, ",union", sizeof(opts));
        if (flags & MNT_NOCOREDUMP)
            strlcat(opts, ",nocoredump", sizeof(opts));
#ifdef MNT_RELATIME
        if (flags & MNT_RELATIME)
            strlcat(opts, ",relatime", sizeof(opts));
#endif
        if (flags & MNT_IGNORE)
            strlcat(opts, ",ignore", sizeof(opts));
#ifdef MNT_DISCARD
        if (flags & MNT_DISCARD)
            strlcat(opts, ",discard", sizeof(opts));
#endif
#ifdef MNT_EXTATTR
        if (flags & MNT_EXTATTR)
            strlcat(opts, ",extattr", sizeof(opts));
#endif
        if (flags & MNT_LOG)
            strlcat(opts, ",log", sizeof(opts));
        if (flags & MNT_SYMPERM)
            strlcat(opts, ",symperm", sizeof(opts));
        if (flags & MNT_NODEVMTIME)
            strlcat(opts, ",nodevmtime", sizeof(opts));
#endif
        py_dev = PyUnicode_DecodeFSDefault(fs[i].f_mntfromname);
        if (! py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(fs[i].f_mntonname);
        if (! py_mountp)
            goto error;
        py_tuple = Py_BuildValue("(OOss)",
                                 py_dev,               // device
                                 py_mountp,            // mount point
                                 fs[i].f_fstypename,   // fs type
                                 opts);                // options
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
