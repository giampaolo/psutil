/*
 * Copyright (c) 2009, Giampaolo Rodola.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdlib.h>
#include <kvm.h>
#include <sys/sysctl.h>

#include "../../arch/all/init.h"


int
_psutil_pids(pid_t **pids_array, int *pids_count) {
    char errbuf[_POSIX2_LINE_MAX];
    kvm_t *kd;
    struct kinfo_proc *proc_list = NULL;
    struct kinfo_proc *result;
    int cnt;
    size_t i;

    *pids_array = NULL;
    *pids_count = 0;

    kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);
    if (kd == NULL) {
        psutil_runtime_error("kvm_openfiles() failed: %s", errbuf);
        return -1;
    }

    result = kvm_getprocs(
        kd, KERN_PROC_ALL, 0, sizeof(struct kinfo_proc), &cnt
    );
    if (result == NULL) {
        psutil_runtime_error("kvm_getproc2() failed");
        kvm_close(kd);
        return -1;
    }

    if (cnt == 0) {
        psutil_runtime_error("no PIDs found");
        kvm_close(kd);
        return -1;
    }

    *pids_array = malloc(cnt * sizeof(pid_t));
    if (!*pids_array) {
        PyErr_NoMemory();
        kvm_close(kd);
        return -1;
    }

    for (i = 0; i < (size_t)cnt; i++) {
        (*pids_array)[i] = result[i].p_pid;
    }

    *pids_count = cnt;
    kvm_close(kd);
    return 0;
}
