/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdlib.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/user.h>

#include "../../arch/all/init.h"


int
_psutil_pids(pid_t **pids_array, int *pids_count) {
    int mib[3] = {CTL_KERN, KERN_PROC, KERN_PROC_ALL};
    size_t len = 0;
    char *buf = NULL;
    struct kinfo_proc *proc_list = NULL;
    size_t num_procs = 0;

    *pids_array = NULL;
    *pids_count = 0;

    if (psutil_sysctl_malloc(mib, 3, &buf, &len) != 0)
        return -1;

    if (len == 0) {
        psutil_runtime_error("no PIDs found");
        goto error;
    }

    proc_list = (struct kinfo_proc *)buf;
    num_procs = len / sizeof(struct kinfo_proc);

    *pids_array = malloc(num_procs * sizeof(pid_t));
    if (!*pids_array) {
        PyErr_NoMemory();
        goto error;
    }

    for (size_t i = 0; i < num_procs; i++) {
        (*pids_array)[i] = proc_list[i].kp_proc.p_pid;
    }

    *pids_count = (int)num_procs;
    free(buf);
    return 0;

error:
    if (buf != NULL)
        free(buf);
    return -1;
}


// Return a {pid: ppid, ...} dict for all running processes in one
// shot. Used to speed up Process.children(). The kernel walks its whole
// process list on every sysctl(KERN_PROC_PID) call, so one read of the
// table costs much less than one Process.ppid() call for each PID.
PyObject *
psutil_ppid_map(PyObject *self, PyObject *args) {
    int mib[3] = {CTL_KERN, KERN_PROC, KERN_PROC_ALL};
    size_t len = 0;
    char *buf = NULL;
    struct kinfo_proc *proc_list = NULL;
    size_t num_procs = 0;
    PyObject *py_pid = NULL;
    PyObject *py_ppid = NULL;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    if (psutil_sysctl_malloc(mib, 3, &buf, &len) != 0)
        goto error;

    proc_list = (struct kinfo_proc *)buf;
    num_procs = len / sizeof(struct kinfo_proc);

    for (size_t i = 0; i < num_procs; i++) {
        py_pid = PyLong_FromPid(proc_list[i].kp_proc.p_pid);
        if (py_pid == NULL)
            goto error;
        py_ppid = PyLong_FromPid(proc_list[i].kp_eproc.e_ppid);
        if (py_ppid == NULL)
            goto error;
        if (PyDict_SetItem(py_retdict, py_pid, py_ppid))
            goto error;
        Py_CLEAR(py_pid);
        Py_CLEAR(py_ppid);
    }

    free(buf);
    return py_retdict;

error:
    Py_XDECREF(py_pid);
    Py_XDECREF(py_ppid);
    Py_DECREF(py_retdict);
    if (buf != NULL)
        free(buf);
    return NULL;
}
