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
    int mib[4] = {CTL_KERN, KERN_PROC, KERN_PROC_PROC, 0};
    size_t len = 0;
    char *buf = NULL;
    struct kinfo_proc *proc_list = NULL;
    size_t num_procs = 0;

    *pids_array = NULL;
    *pids_count = 0;

    if (psutil_sysctl_malloc(mib, 4, &buf, &len) != 0)
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
        (*pids_array)[i] = proc_list[i].ki_pid;  // FreeBSD PID field
    }

    *pids_count = (int)num_procs;
    free(buf);
    return 0;

error:
    if (buf != NULL)
        free(buf);
    return -1;
}
