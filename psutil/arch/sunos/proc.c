/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <fcntl.h>
#include <libproc.h>

#include "proc.h"


// Read a file content and fills a C structure with it.
int
psutil_file_to_struct(char *path, void *fstruct, size_t size) {
    int fd;
    ssize_t nbytes;
    fd = open(path, O_RDONLY);
    if (fd == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, path);
        return 0;
    }
    nbytes = read(fd, fstruct, size);
    if (nbytes == -1) {
        close(fd);
        PyErr_SetFromErrno(PyExc_OSError);
        return 0;
    }
    if (nbytes != (ssize_t) size) {
        close(fd);
        PyErr_SetString(
            PyExc_RuntimeError, "read() file structure size mismatch");
        return 0;
    }
    close(fd);
    return nbytes;
}


/*
 * Return process ppid, rss, vms, ctime, nice, nthreads, status and tty
 * as a Python tuple.
 */
PyObject *
psutil_proc_basic_info(PyObject *self, PyObject *args) {
    int pid;
    char path[1000];
    psinfo_t info;
    const char *procfs_path;

    if (! PyArg_ParseTuple(args, "is", &pid, &procfs_path))
        return NULL;

    sprintf(path, "%s/%i/psinfo", procfs_path, pid);
    if (! psutil_file_to_struct(path, (void *)&info, sizeof(info)))
        return NULL;
    return Py_BuildValue(
        "ikkdiiikiiii",
        info.pr_ppid,              // parent pid
        info.pr_rssize,            // rss
        info.pr_size,              // vms
        PSUTIL_TV2DOUBLE(info.pr_start),  // create time
        info.pr_lwp.pr_nice,       // nice
        info.pr_nlwp,              // no. of threads
        info.pr_lwp.pr_state,      // status code
        info.pr_ttydev,            // tty nr
        (int)info.pr_uid,          // real user id
        (int)info.pr_euid,         // effective user id
        (int)info.pr_gid,          // real group id
        (int)info.pr_egid          // effective group id
        );
}
