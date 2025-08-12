/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
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
