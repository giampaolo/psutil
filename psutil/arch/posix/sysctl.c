/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
#include <Python.h>
#include <sys/types.h>
#include <sys/sysctl.h>

#include "../../arch/all/init.h"


// A thin wrapper on top of sysctl().
int
psutil_sysctl_fixed(int *mib, u_int miblen, void *buf, size_t buflen) {
    size_t len = buflen;

    if (sysctl(mib, miblen, buf, &len, NULL, 0) == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl()");
        return -1;
    }

    if (len != buflen) {
        PyErr_SetString(PyExc_RuntimeError, "sysctl() size mismatch");
        return -1;
    }

    return 0;
}

// Allocate buffer for sysctl with retry on ENOMEM. The caller is
// supposed to free() memory after use.
int
psutil_sysctl_malloc(int *mib, u_int miblen, char **buf, size_t *buflen) {
    size_t needed = 0;
    char *buffer = NULL;
    int ret;
    int max_retries = 8;

    ret = sysctl(mib, miblen, NULL, &needed, NULL, 0);
    if (ret == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl() malloc 1/2");
        return -1;
    }

    while (max_retries-- > 0) {
        buffer = malloc(needed);
        if (!buffer) {
            PyErr_NoMemory();
            return -1;
        }

        ret = sysctl(mib, miblen, buffer, &needed, NULL, 0);
        if (ret == 0) {
            *buf = buffer;
            *buflen = needed;
            return 0;
        }

        if (errno != ENOMEM) {
            free(buffer);
            psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl() malloc 2/2");
            return -1;
        }

        free(buffer);
        buffer = NULL;
    }

    PyErr_SetString(
        PyExc_RuntimeError, "sysctl() buffer allocation retry limit exceeded"
    );
    return -1;
}


#if !defined(PSUTIL_OPENBSD)
// A thin wrapper on top of sysctlbyname().
int
psutil_sysctlbyname_fixed(const char *name, void *buf, size_t buflen) {
    size_t len = buflen;
    char errbuf[256];

    if (sysctlbyname(name, buf, &len, NULL, 0) == -1) {
        snprintf(errbuf, sizeof(errbuf), "sysctlbyname('%s')", name);
        psutil_PyErr_SetFromOSErrnoWithSyscall(errbuf);
        return -1;
    }

    if (len != buflen) {
        snprintf(
            errbuf,
            sizeof(errbuf),
            "sysctlbyname('%s') size mismatch: returned %zu, expected %zu",
            name,
            len,
            buflen
        );
        PyErr_SetString(PyExc_RuntimeError, errbuf);
        return -1;
    }

    return 0;
}
#endif  // !PSUTIL_OPENBSD


// Get the maximum process arguments size.
int
psutil_sysctl_argmax() {
    int argmax;
    int mib[2] = {CTL_KERN, KERN_ARGMAX};

    if (psutil_sysctl_fixed(mib, 2, &argmax, sizeof(argmax)) != 0) {
        PyErr_Clear();
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_ARGMAX)");
        return 0;
    }
    return argmax;
}
#endif  // defined(PLATFORMS…)
