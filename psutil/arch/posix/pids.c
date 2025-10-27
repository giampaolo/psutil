/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <sys/types.h>
#include <signal.h>
#include <errno.h>

#include "../../arch/all/init.h"


static int
has_pid_zero(void) {
#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
    return 0;
#else
    return 1;
#endif
}


// Check if PID exists. Return values:
// 1: exists
// 0: does not exist
// -1: error (Python exception is set)
int
psutil_pid_exists(pid_t pid) {
    int ret;

    // No negative PID exists, plus -1 is an alias for sending signal
    // too all processes except system ones. Not what we want.
    if (pid < 0)
        return 0;

    // As per "man 2 kill" PID 0 is an alias for sending the signal to
    // every process in the process group of the calling process. Not
    // what we want. Some platforms have PID 0, some do not. We decide
    // that at runtime.
    if (pid == 0)
        return has_pid_zero();

    ret = kill(pid, 0);
    if (ret == 0)
        return 1;

    // ESRCH == No such process
    if (errno == ESRCH)
        return 0;

    // EPERM clearly indicates there's a process to deny access to.
    if (errno == EPERM)
        return 1;

    // According to "man 2 kill" possible error values are (EINVAL,
    // EPERM, ESRCH) therefore we should never get here.
    return -1;
}
