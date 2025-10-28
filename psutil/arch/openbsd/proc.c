/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/param.h>
#include <sys/sysctl.h>
#include <sys/proc.h>
#include <kvm.h>

#include "../../arch/all/init.h"


// TODO: refactor this (it's clunky)
PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    int mib[4];
    char *argv_buf = NULL;
    size_t argv_len = 0;
    char **argv = NULL;
    char **p;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC_ARGS;
    mib[2] = pid;
    mib[3] = KERN_PROC_ARGV;

    if (psutil_sysctl_malloc(mib, 4, &argv_buf, &argv_len) == -1)
        goto error;

    argv = (char **)argv_buf;

    for (p = argv; *p != NULL; p++) {
        py_arg = PyUnicode_DecodeFSDefault(*p);
        if (!py_arg)
            goto error;
        if (PyList_Append(py_retlist, py_arg))
            goto error;
        Py_DECREF(py_arg);
    }

    free(argv_buf);
    return py_retlist;

error:
    if (argv_buf != NULL)
        free(argv_buf);
    Py_XDECREF(py_arg);
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    // OpenBSD reference:
    // https://github.com/janmojzis/pstree/blob/master/proc_kvm.c
    // Note: this requires root access, else it will fail trying
    // to access /dev/kmem.
    pid_t pid;
    kvm_t *kd = NULL;
    int nentries, i;
    char errbuf[4096];
    struct kinfo_proc *kp;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    kd = kvm_openfiles(0, 0, 0, O_RDONLY, errbuf);
    if (!kd) {
        // Usually fails due to EPERM against /dev/mem. We retry with
        // KVM_NO_FILES which apparently has the same effect.
        // https://stackoverflow.com/questions/22369736/
        psutil_debug("kvm_openfiles(O_RDONLY) failed");
        kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);
        if (!kd) {
            convert_kvm_err("kvm_openfiles()", errbuf);
            goto error;
        }
    }

    kp = kvm_getprocs(
        kd,
        KERN_PROC_PID | KERN_PROC_SHOW_THREADS | KERN_PROC_KTHREAD,
        pid,
        sizeof(*kp),
        &nentries
    );
    if (!kp) {
        if (strstr(errbuf, "Permission denied") != NULL)
            psutil_oserror_ad("kvm_getprocs");
        else
            psutil_runtime_error("kvm_getprocs() syscall failed");
        goto error;
    }

    for (i = 0; i < nentries; i++) {
        if (kp[i].p_tid < 0)
            continue;
        if (kp[i].p_pid == pid) {
            py_tuple = Py_BuildValue(
                _Py_PARSE_PID "dd",
                kp[i].p_tid,
                PSUTIL_KPT2DOUBLE(kp[i].p_uutime),
                PSUTIL_KPT2DOUBLE(kp[i].p_ustime)
            );
            if (py_tuple == NULL)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_DECREF(py_tuple);
        }
    }

    kvm_close(kd);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (kd != NULL)
        kvm_close(kd);
    return NULL;
}


PyObject *
psutil_proc_num_fds(PyObject *self, PyObject *args) {
    pid_t pid;
    int cnt;

    struct kinfo_file *freep;
    struct kinfo_proc kipp;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (psutil_kinfo_proc(pid, &kipp) == -1)
        return NULL;

    freep = kinfo_getfile(pid, &cnt);

    if (freep == NULL) {
#if defined(PSUTIL_OPENBSD)
        if ((pid == 0) && (errno == ESRCH)) {
            psutil_debug(
                "num_fds() returned ESRCH for PID 0; forcing `return 0`"
            );
            PyErr_Clear();
            return Py_BuildValue("i", 0);
        }
#endif
        return NULL;
    }

    free(freep);
    return Py_BuildValue("i", cnt);
}


PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    // Reference:
    // https://github.com/openbsd/src/blob/
    //     588f7f8c69786211f2d16865c552afb91b1c7cba/bin/ps/print.c#L191
    pid_t pid;
    struct kinfo_proc kp;
    char path[MAXPATHLEN];
    size_t pathlen = sizeof path;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        return NULL;

    int name[] = {CTL_KERN, KERN_PROC_CWD, pid};
    if (sysctl(name, 3, path, &pathlen, NULL, 0) != 0) {
        if (errno == ENOENT) {
            psutil_debug("sysctl(KERN_PROC_CWD) -> ENOENT converted to ''");
            return Py_BuildValue("s", "");
        }
        else {
            psutil_oserror();
            return NULL;
        }
    }
    return PyUnicode_DecodeFSDefault(path);
}
