/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Platform-specific module methods for OpenBSD.
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/param.h>
#include <sys/sysctl.h>
#include <sys/user.h>
#include <sys/proc.h>
#include <sys/swap.h>  // for swap_mem
#include <signal.h>
#include <kvm.h>

#include "openbsd.h"


#define KPT2DOUBLE(t)   (t ## _sec + t ## _usec / 1000000.0)


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
        PyErr_SetFromErrno(PyExc_OSError);
        return -1;
    }
    // sysctl stores 0 in the size if we can't find the process information.
    if (size == 0) {
        NoSuchProcess();
        return -1;
    }
    return 0;
}


struct kinfo_file *
psutil_kinfo_getfile(long pid, int* cnt) {
    // Mimic's FreeBSD kinfo_file call, taking a pid and a ptr to an
    // int as arg and returns an array with cnt struct kinfo_file.
    int mib[6];
    size_t len;
    struct kinfo_file* kf;
    mib[0] = CTL_KERN;
    mib[1] = KERN_FILE;
    mib[2] = KERN_FILE_BYPID;
    mib[3] = (int) pid;
    mib[4] = sizeof(struct kinfo_file);
    mib[5] = 0;

    /* get the size of what would be returned */
    if (sysctl(mib, 6, NULL, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if ((kf = malloc(len)) == NULL) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    mib[5] = (int)(len / sizeof(struct kinfo_file));
    if (sysctl(mib, 6, kf, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    *cnt = (int)(len / sizeof(struct kinfo_file));
    return kf;
}


int
psutil_pid_exists(long pid) {
    // Return 1 if PID exists in the current process list, else 0, -1
    // on error.
    // TODO: this should live in _psutil_posix.c but for some reason if I
    // move it there I get a "include undefined symbol" error.
    int ret;
    if (pid < 0)
        return 0;
    ret = kill(pid , 0);
    if (ret == 0)
        return 1;
    else {
        if (ret == ESRCH)
            return 0;
        else if (ret == EPERM)
            return 1;
        else {
            PyErr_SetFromErrno(PyExc_OSError);
            return -1;
        }
    }
}


int
psutil_raise_ad_or_nsp(long pid) {
    // Set exception to AccessDenied if pid exists else NoSuchProcess.
    if (psutil_pid_exists(pid) == 0)
        NoSuchProcess();
    else
        AccessDenied();
}


// ============================================================================
// Process related APIS
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
    int done;
    static const int name[] = { CTL_KERN, KERN_PROC, KERN_PROC, 0 };
    // Declaring name as const requires us to cast it when passing it to
    // sysctl because the prototype doesn't include the const modifier.
    size_t              length;
    char errbuf[_POSIX2_LINE_MAX];
    struct kinfo_proc *x;
    int cnt;
    kvm_t *kd;

    assert( procList != NULL);
    assert(*procList == NULL);
    assert(procCount != NULL);

    kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);

    if (kd == NULL) {
        return errno;
    }

    result = kvm_getprocs(kd, KERN_PROC_ALL, 0, sizeof(struct kinfo_proc), &cnt);
    if (result == NULL) {
        err(1, NULL);
        return errno;
    }

    *procCount = (size_t)cnt;

    size_t mlen = cnt * sizeof(struct kinfo_proc);

    if ((*procList = malloc(mlen)) == NULL) {
        err(1, NULL);
        return errno;
    }

    memcpy(*procList, result, mlen);
    assert(*procList != NULL);
    kvm_close(kd);

    return 0;
}


char **
_psutil_get_argv(long pid) {
    static char **argv;
    char **p;
    int argv_mib[] = {CTL_KERN, KERN_PROC_ARGS, pid, KERN_PROC_ARGV};
    size_t argv_size = 128;
    /* Loop and reallocate until we have enough space to fit argv. */
    for (;; argv_size *= 2) {
        if ((argv = realloc(argv, argv_size)) == NULL)
            err(1, NULL);
        if (sysctl(argv_mib, 4, argv, &argv_size, NULL, 0) == 0)
            return argv;
        if (errno == ESRCH) {
            PyErr_SetFromErrno(PyExc_OSError);
            return NULL;
        }
        if (errno != ENOMEM)
            err(1, NULL);
    }
}

// returns the command line as a python list object
PyObject *
psutil_get_cmdline(long pid) {
    static char **argv;
    char **p;
    PyObject *py_arg = NULL;
    PyObject *py_retlist = Py_BuildValue("[]");

    if (!py_retlist)
        return NULL;
    if (pid < 0)
        return py_retlist;

    if ((argv = _psutil_get_argv(pid)) == NULL)
        goto error;

    for (p = argv; *p != NULL; p++) {
        py_arg = Py_BuildValue("s", *p);
        if (!py_arg)
            goto error;
        if (PyList_Append(py_retlist, py_arg))
            goto error;
        Py_DECREF(py_arg);
    }
    return py_retlist;

error:
    Py_XDECREF(py_arg);
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    long pid;
    kvm_t *kd = NULL;
    int nentries, i;
    char errbuf[4096];
    struct kinfo_proc *kp;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;

    kd = kvm_openfiles(0, 0, 0, O_RDONLY, errbuf);
    if (! kd) {
        if (strstr(errbuf, "Permission denied") != NULL)
            AccessDenied();
        else
            PyErr_Format(PyExc_RuntimeError, "kvm_openfiles() failed");
        goto error;
    }

    kp = kvm_getprocs(
        kd, KERN_PROC_PID | KERN_PROC_SHOW_THREADS | KERN_PROC_KTHREAD, pid,
        sizeof(*kp), &nentries);
    if (! kp) {
        if (strstr(errbuf, "Permission denied") != NULL)
            AccessDenied();
        else
            PyErr_Format(PyExc_RuntimeError, "kvm_getprocs() failed");
        goto error;
    }

    for (i = 0; i < nentries; i++) {
        if (kp[i].p_tid < 0)
            continue;
        if (kp[i].p_pid == pid) {
            py_tuple = Py_BuildValue(
                "Idd",
                kp[i].p_tid,
                KPT2DOUBLE(kp[i].p_uutime),
                KPT2DOUBLE(kp[i].p_ustime));
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
psutil_virtual_mem(PyObject *self, PyObject *args) {
    unsigned int   total, active, inactive, wired, cached, free;
    size_t         size = sizeof(total);
    struct uvmexp  uvmexp;
    int            mib[] = {CTL_VM, VM_UVMEXP};
    long           pagesize = getpagesize();
    size = sizeof(uvmexp);

    if (sysctl(mib, 2, &uvmexp, &size, NULL, 0) < 0) {
        warn("failed to get vm.uvmexp");
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    return Py_BuildValue("KKKKKKKK",
        (unsigned long long) uvmexp.npages    * pagesize,
        (unsigned long long) uvmexp.free     * pagesize,
        (unsigned long long) uvmexp.active   * pagesize,
        (unsigned long long) uvmexp.inactive * pagesize,
        (unsigned long long) uvmexp.wired    * pagesize,
        (unsigned long long) 0,
        (unsigned long long) 0,
        (unsigned long long) 0
    );
}


PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    uint64_t swap_total, swap_free;
    struct swapent *swdev;
    int nswap, i;

    if ((nswap = swapctl(SWAP_NSWAP, 0, 0)) == 0) {
        warn("failed to get swap device count");
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    if ((swdev = calloc(nswap, sizeof(*swdev))) == NULL) {
        warn("failed to allocate memory for swdev structures");
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    if (swapctl(SWAP_STATS, swdev, nswap) == -1) {
        free(swdev);
        warn("failed to get swap stats");
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    /* Total things up */
    swap_total = swap_free = 0;
    for (i = 0; i < nswap; i++) {
        if (swdev[i].se_flags & SWF_ENABLE) {
            swap_free += (swdev[i].se_nblks - swdev[i].se_inuse);
            swap_total += swdev[i].se_nblks;
        }
    }
    return Py_BuildValue("(LLLII)",
                         swap_total * DEV_BSIZE,
                         (swap_total - swap_free) * DEV_BSIZE,
                         swap_free * DEV_BSIZE,
                         0 /* XXX swap in */,
                         0 /* XXX swap out */);
}
