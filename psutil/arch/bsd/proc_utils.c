/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <errno.h>
#include <limits.h>
#include <stdlib.h>
#include <stdint.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/proc.h>
#include <limits.h>
#include <unistd.h>
#ifdef PSUTIL_FREEBSD
#include <sys/user.h>
#endif

#include "../../arch/all/init.h"


// Fills a kinfo_proc or kinfo_proc2 struct based on process PID.
int
psutil_kinfo_proc(pid_t pid, void *proc) {
#if defined(PSUTIL_FREEBSD)
    size_t size = sizeof(struct kinfo_proc);
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, pid};
    int len = 4;
#elif defined(PSUTIL_OPENBSD)
    size_t size = sizeof(struct kinfo_proc);
    int mib[] = {CTL_KERN, KERN_PROC, KERN_PROC_PID, pid, (int)size, 1};
    int len = 6;
#elif defined(PSUTIL_NETBSD)
    size_t size = sizeof(struct kinfo_proc2);
    int mib[] = {CTL_KERN, KERN_PROC2, KERN_PROC_PID, pid, (int)size, 1};
    int len = 6;
#else
#error "unsupported BSD variant"
#endif

    if (pid < 0 || proc == NULL)
        return psutil_badargs("psutil_kinfo_proc");

    if (sysctl(mib, len, proc, &size, NULL, 0) == -1) {
        psutil_oserror_wsyscall("sysctl(kinfo_proc)");
        return -1;
    }

    // sysctl stores 0 in size if the process doesn't exist.
    if (size == 0) {
        psutil_oserror_nsp("sysctl(kinfo_proc), size = 0");
        return -1;
    }

    return 0;
}


// Mimic's FreeBSD kinfo_file call, taking a pid and a ptr to an
// int as arg and returns an array with cnt struct kinfo_file.
// Caller is responsible for freeing the returned pointer with free().
#ifdef PSUTIL_HASNT_KINFO_GETFILE
struct kinfo_file *
kinfo_getfile(pid_t pid, int *cnt) {
    if (pid < 0 || !cnt) {
        psutil_badargs("kinfo_getfile");
        return NULL;
    }

    int mib[6];
    size_t len;
    struct kinfo_file *kf = NULL;

    mib[0] = CTL_KERN;
    mib[1] = KERN_FILE;
    mib[2] = KERN_FILE_BYPID;
    mib[3] = pid;
    mib[4] = sizeof(struct kinfo_file);
    mib[5] = 0;

    if (psutil_sysctl_malloc(mib, 6, (char **)&kf, &len) != 0) {
        return NULL;
    }

    // Calculate number of entries and check for overflow
    if (len / sizeof(struct kinfo_file) > INT_MAX) {
        psutil_debug("exceeded INT_MAX");
        free(kf);
        errno = EOVERFLOW;
        return NULL;
    }

    *cnt = (int)(len / sizeof(struct kinfo_file));
    return kf;
}
#endif  // PSUTIL_HASNT_KINFO_GETFILE


int
is_zombie(size_t pid) {
#ifdef PSUTIL_NETBSD
    struct kinfo_proc2 kp;
#else
    struct kinfo_proc kp;
#endif
    if (psutil_kinfo_proc(pid, &kp) == -1) {
        errno = 0;
        PyErr_Clear();
        return 0;
    }

#if defined(PSUTIL_FREEBSD)
    return kp.ki_stat == SZOMB;
#elif defined(PSUTIL_OPENBSD)
    // According to /usr/include/sys/proc.h SZOMB is unused.
    // test_zombie_process() shows that SDEAD is the right
    // equivalent.
    return ((kp.p_stat == SZOMB) || (kp.p_stat == SDEAD));
#else
    return kp.p_stat == SZOMB;
#endif
}
