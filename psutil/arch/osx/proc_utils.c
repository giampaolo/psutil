/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/user.h>
#include <unistd.h>
#include <mach/mach.h>
#include <libproc.h>
#include <stdint.h>
#include <stdbool.h>

#include "../../arch/all/init.h"


int
psutil_get_kinfo_proc(pid_t pid, struct kinfo_proc *kp) {
    int mib[4];
    size_t len;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    if (pid < 0 || !kp)
        return psutil_badargs("psutil_get_kinfo_proc");

    len = sizeof(struct kinfo_proc);

    if (sysctl(mib, 4, kp, &len, NULL, 0) == -1) {
        // raise an exception and throw errno as the error
        psutil_oserror_wsyscall("sysctl");
        return -1;
    }

    // sysctl succeeds but len is zero, happens when process has gone away
    if (len == 0) {
        psutil_oserror_nsp("sysctl(kinfo_proc), len == 0");
        return -1;
    }
    return 0;
}


// Return 1 if PID a zombie, else 0 (including on error).
int
is_zombie(size_t pid) {
    struct kinfo_proc kp;

    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
        errno = 0;
        PyErr_Clear();
        return 0;
    }
    return kp.kp_proc.p_stat == SZOMB;
}


// Read process argument space.
int
psutil_sysctl_procargs(pid_t pid, char *procargs, size_t *argmax) {
    int mib[3];

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROCARGS2;
    mib[2] = pid;

    if (pid < 0 || !procargs || !argmax || *argmax == 0)
        return psutil_badargs("psutil_sysctl_procargs");

    if (sysctl(mib, 3, procargs, argmax, NULL, 0) < 0) {
        if (psutil_pid_exists(pid) == 0) {
            psutil_oserror_nsp("psutil_pid_exists -> 0");
            return -1;
        }

        if (is_zombie(pid) == 1) {
            PyErr_SetString(ZombieProcessError, "");
            return -1;
        }

        if (errno == EINVAL) {
            psutil_debug("sysctl(KERN_PROCARGS2) -> EINVAL translated to AD");
            psutil_oserror_ad("sysctl(KERN_PROCARGS2) -> EINVAL");
            return -1;
        }

        if (errno == EIO) {
            psutil_debug("sysctl(KERN_PROCARGS2) -> EIO translated to AD");
            psutil_oserror_ad("sysctl(KERN_PROCARGS2) -> EIO");
            return -1;
        }
        psutil_oserror_wsyscall("sysctl(KERN_PROCARGS2)");
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
    int ret;

    if (pid < 0 || !pti || size <= 0)
        return psutil_badargs("psutil_proc_pidinfo");

    errno = 0;
    ret = proc_pidinfo(pid, flavor, arg, pti, size);
    if (ret <= 0) {
        psutil_raise_for_pid(pid, "proc_pidinfo()");
        return -1;
    }

    // check for truncated return size
    if (ret < size) {
        psutil_raise_for_pid(
            pid, "proc_pidinfo() returned less data than requested buffer size"
        );
        return -1;
    }

    return 0;
}


/*
 * A wrapper around task_for_pid() which sucks big time:
 * - it's not documented
 * - errno is set only sometimes
 * - sometimes errno is ENOENT (?!?)
 * - for PIDs != getpid() or PIDs which are not members of the procmod
 *   it requires root
 * As such we can only guess what the heck went wrong and fail either
 * with NoSuchProcess or give up with AccessDenied.
 * References:
 * https://github.com/giampaolo/psutil/issues/1181
 * https://github.com/giampaolo/psutil/issues/1209
 * https://github.com/giampaolo/psutil/issues/1291#issuecomment-396062519
 */
int
psutil_task_for_pid(pid_t pid, mach_port_t *task) {
    kern_return_t err;

    if (pid < 0 || !task)
        return psutil_badargs("psutil_task_for_pid");

    err = task_for_pid(mach_task_self(), pid, task);
    if (err != KERN_SUCCESS) {
        if (psutil_pid_exists(pid) == 0) {
            psutil_oserror_nsp("task_for_pid");
        }
        else if (is_zombie(pid) == 1) {
            PyErr_SetString(
                ZombieProcessError, "task_for_pid -> psutil_is_zombie -> 1"
            );
        }
        else {
            psutil_debug(
                "task_for_pid() failed (pid=%ld, err=%i, errno=%i, msg='%s'); "
                "setting EACCES",
                (long)pid,
                err,
                errno,
                mach_error_string(err)
            );
            psutil_oserror_ad("task_for_pid");
        }
        return -1;
    }

    return 0;
}


/*
 * A wrapper around proc_pidinfo(PROC_PIDLISTFDS), which dynamically sets
 * the buffer size.
 */
struct proc_fdinfo *
psutil_proc_list_fds(pid_t pid, int *num_fds) {
    int ret;
    int fds_size = 0;
    int max_size = 24 * 1024 * 1024;  // 24M
    struct proc_fdinfo *fds_pointer = NULL;

    if (pid < 0 || num_fds == NULL) {
        psutil_badargs("psutil_proc_list_fds");
        return NULL;
    }

    errno = 0;
    ret = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (ret <= 0) {
        psutil_raise_for_pid(pid, "proc_pidinfo(PROC_PIDLISTFDS) 1/2");
        goto error;
    }

    while (1) {
        if (ret > fds_size) {
            while (ret > fds_size) {
                fds_size += PROC_PIDLISTFD_SIZE * 32;
                if (fds_size > max_size) {
                    psutil_runtime_error("prevent malloc() to allocate > 24M");
                    goto error;
                }
            }

            if (fds_pointer != NULL) {
                free(fds_pointer);
            }
            fds_pointer = malloc(fds_size);

            if (fds_pointer == NULL) {
                PyErr_NoMemory();
                goto error;
            }
        }

        errno = 0;
        ret = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fds_pointer, fds_size);
        if (ret <= 0) {
            psutil_raise_for_pid(pid, "proc_pidinfo(PROC_PIDLISTFDS) 2/2");
            goto error;
        }

        if (ret + (int)PROC_PIDLISTFD_SIZE >= fds_size) {
            psutil_debug("PROC_PIDLISTFDS: make room for 1 extra fd");
            ret = fds_size + (int)PROC_PIDLISTFD_SIZE;
            continue;
        }

        break;
    }

    *num_fds = (ret / (int)PROC_PIDLISTFD_SIZE);
    return fds_pointer;

error:
    if (fds_pointer != NULL)
        free(fds_pointer);
    return NULL;
}
