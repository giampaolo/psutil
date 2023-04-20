/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information.
 * Used by _psutil_osx module methods.
 */


#include <Python.h>
#include <errno.h>
#include <sys/sysctl.h>
#include <libproc.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"
#include "process_info.h"


/*
 * Returns a list of all BSD processes on the system.  This routine
 * allocates the list and puts it in *procList and a count of the
 * number of entries in *procCount.  You are responsible for freeing
 * this list (use "free" from System framework).
 * On success, the function returns 0.
 * On error, the function returns a BSD errno value.
 */
int
psutil_get_proc_list(kinfo_proc **procList, size_t *procCount) {
    int mib[3];
    size_t size, size2;
    void *ptr;
    int err;
    int lim = 8;  // some limit

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_ALL;
    *procCount = 0;

    /*
     * We start by calling sysctl with ptr == NULL and size == 0.
     * That will succeed, and set size to the appropriate length.
     * We then allocate a buffer of at least that size and call
     * sysctl with that buffer.  If that succeeds, we're done.
     * If that call fails with ENOMEM, we throw the buffer away
     * and try again.
     * Note that the loop calls sysctl with NULL again.  This is
     * is necessary because the ENOMEM failure case sets size to
     * the amount of data returned, not the amount of data that
     * could have been returned.
     */
    while (lim-- > 0) {
        size = 0;
        if (sysctl((int *)mib, 3, NULL, &size, NULL, 0) == -1) {
            PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_ALL)");
            return 1;
        }
        size2 = size + (size >> 3);  // add some
        if (size2 > size) {
            ptr = malloc(size2);
            if (ptr == NULL)
                ptr = malloc(size);
            else
                size = size2;
        }
        else {
            ptr = malloc(size);
        }
        if (ptr == NULL) {
            PyErr_NoMemory();
            return 1;
        }

        if (sysctl((int *)mib, 3, ptr, &size, NULL, 0) == -1) {
            err = errno;
            free(ptr);
            if (err != ENOMEM) {
                PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_ALL)");
                return 1;
            }
        }
        else {
            *procList = (kinfo_proc *)ptr;
            *procCount = size / sizeof(kinfo_proc);
            if (procCount <= 0) {
                PyErr_Format(PyExc_RuntimeError, "no PIDs found");
                return 1;
            }
            return 0;  // success
        }
    }

    PyErr_Format(PyExc_RuntimeError, "couldn't collect PIDs list");
    return 1;
}


// Read the maximum argument size for processes
int
psutil_sysctl_argmax() {
    int argmax;
    int mib[2];
    size_t size = sizeof(argmax);

    mib[0] = CTL_KERN;
    mib[1] = KERN_ARGMAX;

    if (sysctl(mib, 2, &argmax, &size, NULL, 0) == 0)
        return argmax;
    PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_ARGMAX)");
    return 0;
}


// Read process argument space.
int
psutil_sysctl_procargs(pid_t pid, char *procargs, size_t *argmax) {
    int mib[3];

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROCARGS2;
    mib[2] = pid;

    if (sysctl(mib, 3, procargs, argmax, NULL, 0) < 0) {
        if (psutil_pid_exists(pid) == 0) {
            NoSuchProcess("psutil_pid_exists -> 0");
            return 1;
        }
        // In case of zombie process we'll get EINVAL. We translate it
        // to NSP and _psosx.py will translate it to ZP.
        if (errno == EINVAL) {
            psutil_debug("sysctl(KERN_PROCARGS2) -> EINVAL translated to NSP");
            NoSuchProcess("sysctl(KERN_PROCARGS2) -> EINVAL");
            return 1;
        }
        // There's nothing we can do other than raising AD.
        if (errno == EIO) {
            psutil_debug("sysctl(KERN_PROCARGS2) -> EIO translated to AD");
            AccessDenied("sysctl(KERN_PROCARGS2) -> EIO");
            return 1;
        }
        PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROCARGS2)");
        return 1;
    }
    return 0;
}


int
psutil_get_kinfo_proc(pid_t pid, struct kinfo_proc *kp) {
    int mib[4];
    size_t len;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    // fetch the info with sysctl()
    len = sizeof(struct kinfo_proc);

    // now read the data from sysctl
    if (sysctl(mib, 4, kp, &len, NULL, 0) == -1) {
        // raise an exception and throw errno as the error
        PyErr_SetFromOSErrnoWithSyscall("sysctl");
        return -1;
    }

    // sysctl succeeds but len is zero, happens when process has gone away
    if (len == 0) {
        NoSuchProcess("sysctl(kinfo_proc), len == 0");
        return -1;
    }
    return 0;
}


/*
 * A wrapper around proc_pidinfo().
 * https://opensource.apple.com/source/xnu/xnu-2050.7.9/bsd/kern/proc_info.c
 * Returns 0 on failure.
 */
int
psutil_proc_pidinfo(pid_t pid, int flavor, uint64_t arg, void *pti, int size) {
    errno = 0;
    int ret;

    ret = proc_pidinfo(pid, flavor, arg, pti, size);
    if (ret <= 0) {
        psutil_raise_for_pid(pid, "proc_pidinfo()");
        return 0;
    }
    if ((unsigned long)ret < sizeof(pti)) {
        psutil_raise_for_pid(
            pid, "proc_pidinfo() return size < sizeof(struct_pointer)");
        return 0;
    }
    return ret;
}
