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

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"

#define PSUTIL_KPT2DOUBLE(t) (t ## _sec + t ## _usec / 1000000.0)
// #define PSUTIL_TV2DOUBLE(t) ((t).tv_sec + (t).tv_usec / 1000000.0)


// ============================================================================
// Utility functions
// ============================================================================


int
psutil_kinfo_proc(pid_t pid, struct kinfo_proc *proc) {
    // Fills a kinfo_proc struct based on process pid.
    int ret;
    int mib[6];
    size_t size = sizeof(struct kinfo_proc);

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;
    mib[4] = size;
    mib[5] = 1;

    ret = sysctl((int*)mib, 6, proc, &size, NULL, 0);
    if (ret == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(kinfo_proc)");
        return -1;
    }
    // sysctl stores 0 in the size if we can't find the process information.
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        return -1;
    }
    return 0;
}


struct kinfo_file *
kinfo_getfile(pid_t pid, int* cnt) {
    // Mimic's FreeBSD kinfo_file call, taking a pid and a ptr to an
    // int as arg and returns an array with cnt struct kinfo_file.
    int mib[6];
    size_t len;
    struct kinfo_file* kf;
    mib[0] = CTL_KERN;
    mib[1] = KERN_FILE;
    mib[2] = KERN_FILE_BYPID;
    mib[3] = pid;
    mib[4] = sizeof(struct kinfo_file);
    mib[5] = 0;

    /* get the size of what would be returned */
    if (sysctl(mib, 6, NULL, &len, NULL, 0) < 0) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(kinfo_file) (1/2)");
        return NULL;
    }
    if ((kf = malloc(len)) == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    mib[5] = (int)(len / sizeof(struct kinfo_file));
    if (sysctl(mib, 6, kf, &len, NULL, 0) < 0) {
        free(kf);
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(kinfo_file) (2/2)");
        return NULL;
    }

    *cnt = (int)(len / sizeof(struct kinfo_file));
    return kf;
}


// ============================================================================
// APIS
// ============================================================================

int
psutil_get_proc_list(struct kinfo_proc **procList, size_t *procCount) {
    // Returns a list of all BSD processes on the system.  This routine
    // allocates the list and puts it in *procList and a count of the
    // number of entries in *procCount.  You are responsible for freeing
    // this list (use "free" from System framework).
    // On success, the function returns 0.
    // On error, the function returns a BSD errno value.
    struct kinfo_proc *result;
    // Declaring name as const requires us to cast it when passing it to
    // sysctl because the prototype doesn't include the const modifier.
    char errbuf[_POSIX2_LINE_MAX];
    int cnt;
    kvm_t *kd;

    assert(procList != NULL);
    assert(*procList == NULL);
    assert(procCount != NULL);

    kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);
    if (! kd) {
        convert_kvm_err("kvm_openfiles", errbuf);
        return 1;
    }

    result = kvm_getprocs(kd, KERN_PROC_ALL, 0, sizeof(struct kinfo_proc), &cnt);
    if (result == NULL) {
        PyErr_Format(PyExc_RuntimeError, "kvm_getprocs syscall failed");
        kvm_close(kd);
        return 1;
    }

    *procCount = (size_t)cnt;

    size_t mlen = cnt * sizeof(struct kinfo_proc);

    if ((*procList = malloc(mlen)) == NULL) {
        PyErr_NoMemory();
        kvm_close(kd);
        return 1;
    }

    memcpy(*procList, result, mlen);
    assert(*procList != NULL);
    kvm_close(kd);

    return 0;
}


// TODO: refactor this (it's clunky)
PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    int mib[4];
    char **argv = NULL;
    char **p;
    size_t argv_size = 128;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC_ARGS;
    mib[2] = pid;
    mib[3] = KERN_PROC_ARGV;

    // Loop and reallocate until we have enough space to fit argv.
    for (;; argv_size *= 2) {
        if (argv_size >= 8192) {
            PyErr_SetString(PyExc_RuntimeError,
                            "can't allocate enough space for KERN_PROC_ARGV");
            goto error;
        }
        if ((argv = realloc(argv, argv_size)) == NULL)
            continue;
        if (sysctl(mib, 4, argv, &argv_size, NULL, 0) == 0)
            break;
        if (errno == ENOMEM)
            continue;
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (p = argv; *p != NULL; p++) {
        py_arg = PyUnicode_DecodeFSDefault(*p);
        if (!py_arg)
            goto error;
        if (PyList_Append(py_retlist, py_arg))
            goto error;
        Py_DECREF(py_arg);
    }

    free(argv);
    return py_retlist;

error:
    if (argv != NULL)
        free(argv);
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
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    kd = kvm_openfiles(0, 0, 0, O_RDONLY, errbuf);
    if (! kd) {
        // Usually fails due to EPERM against /dev/mem. We retry with
        // KVM_NO_FILES which apparently has the same effect.
        // https://stackoverflow.com/questions/22369736/
        psutil_debug("kvm_openfiles(O_RDONLY) failed");
        kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);
        if (! kd) {
            convert_kvm_err("kvm_openfiles()", errbuf);
            goto error;
        }
    }

    kp = kvm_getprocs(
        kd, KERN_PROC_PID | KERN_PROC_SHOW_THREADS | KERN_PROC_KTHREAD, pid,
        sizeof(*kp), &nentries);
    if (! kp) {
        if (strstr(errbuf, "Permission denied") != NULL)
            AccessDenied("kvm_getprocs");
        else
            PyErr_Format(PyExc_RuntimeError, "kvm_getprocs() syscall failed");
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
                PSUTIL_KPT2DOUBLE(kp[i].p_ustime));
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

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
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

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        return NULL;

    int name[] = { CTL_KERN, KERN_PROC_CWD, pid };
    if (sysctl(name, 3, path, &pathlen, NULL, 0) != 0) {
        if (errno == ENOENT) {
            psutil_debug("sysctl(KERN_PROC_CWD) -> ENOENT converted to ''");
            return Py_BuildValue("s", "");
        }
        else {
            PyErr_SetFromErrno(PyExc_OSError);
            return NULL;
        }
    }
    return PyUnicode_DecodeFSDefault(path);
}
