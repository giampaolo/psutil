/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "../../arch/all/init.h"

#ifdef PSUTIL_HAS_SYSCTL
#include <Python.h>
#include <sys/types.h>
#include <sys/sysctl.h>


static const int MAX_RETRIES = 10;


// A thin wrapper on top of sysctl().
int
psutil_sysctl(int *mib, u_int miblen, void *buf, size_t buflen) {
    size_t len = buflen;

    if (!mib || miblen == 0 || !buf || buflen == 0)
        return psutil_badargs("psutil_sysctl");

    if (sysctl(mib, miblen, buf, &len, NULL, 0) == -1) {
        psutil_oserror_wsyscall("sysctl()");
        return -1;
    }

    if (len != buflen) {
        psutil_runtime_error("sysctl() size mismatch");
        return -1;
    }

    return 0;
}


// Allocate buffer for sysctl with retry on ENOMEM or buffer size mismatch.
// The caller is responsible for freeing the memory.
int
psutil_sysctl_malloc(int *mib, u_int miblen, char **buf, size_t *buflen) {
    size_t needed = 0;
    char *buffer = NULL;
    int ret;
    int max_retries = MAX_RETRIES;

    if (!mib || miblen == 0 || !buf || !buflen)
        return psutil_badargs("psutil_sysctl_malloc");

    // First query to determine required size
    ret = sysctl(mib, miblen, NULL, &needed, NULL, 0);
    if (ret == -1) {
        psutil_oserror_wsyscall("sysctl() malloc 1/3");
        return -1;
    }

    if (needed == 0) {
        psutil_debug("psutil_sysctl_malloc() size = 0");
    }

    while (max_retries-- > 0) {
        // zero-initialize buffer to prevent uninitialized bytes
        buffer = calloc(1, needed);
        if (buffer == NULL) {
            PyErr_NoMemory();
            return -1;
        }

        size_t len = needed;
        ret = sysctl(mib, miblen, buffer, &len, NULL, 0);

        if (ret == 0) {
            // Success: return buffer and length
            *buf = buffer;
            *buflen = len;
            return 0;
        }

        // Handle buffer too small
        if (errno == ENOMEM) {
            free(buffer);
            buffer = NULL;

            // Re-query needed size for next attempt
            if (sysctl(mib, miblen, NULL, &needed, NULL, 0) == -1) {
                psutil_oserror_wsyscall("sysctl() malloc 2/3");
                return -1;
            }

            psutil_debug("psutil_sysctl_malloc() retry");
            continue;
        }

        // Other errors: clean up and give up
        free(buffer);
        psutil_oserror_wsyscall("sysctl() malloc 3/3");
        return -1;
    }

    psutil_runtime_error("sysctl() buffer allocation retry limit exceeded");
    return -1;
}


// Get the maximum process arguments size. Return 0 on error.
size_t
psutil_sysctl_argmax() {
    int argmax;
    int mib[2] = {CTL_KERN, KERN_ARGMAX};

    if (psutil_sysctl(mib, 2, &argmax, sizeof(argmax)) != 0) {
        return 0;
    }

    if (argmax <= 0) {
        psutil_runtime_error("sysctl(KERN_ARGMAX) return <= 0");
        return 0;
    }

    return (size_t)argmax;
}


#ifdef PSUTIL_HAS_SYSCTLBYNAME
// A thin wrapper on top of sysctlbyname().
int
psutil_sysctlbyname(const char *name, void *buf, size_t buflen) {
    size_t len = buflen;
    char errbuf[256];

    if (!name || !buf || buflen == 0)
        return psutil_badargs("psutil_sysctlbyname");

    if (sysctlbyname(name, buf, &len, NULL, 0) == -1) {
        str_format(errbuf, sizeof(errbuf), "sysctlbyname('%s')", name);
        psutil_oserror_wsyscall(errbuf);
        return -1;
    }

    if (len != buflen) {
        str_format(
            errbuf,
            sizeof(errbuf),
            "sysctlbyname('%s') size mismatch: returned %zu, expected %zu",
            name,
            len,
            buflen
        );
        psutil_runtime_error(errbuf);
        return -1;
    }

    return 0;
}


// Allocate buffer for sysctlbyname with retry on ENOMEM or size mismatch.
// The caller is responsible for freeing the memory.
int
psutil_sysctlbyname_malloc(const char *name, char **buf, size_t *buflen) {
    int ret;
    int max_retries = MAX_RETRIES;
    size_t needed = 0;
    size_t len = 0;
    char *buffer = NULL;
    char errbuf[256];

    if (!name || !buf || !buflen)
        return psutil_badargs("psutil_sysctlbyname_malloc");

    // First query to determine required size.
    ret = sysctlbyname(name, NULL, &needed, NULL, 0);
    if (ret == -1) {
        str_format(
            errbuf, sizeof(errbuf), "sysctlbyname('%s') malloc 1/3", name
        );
        psutil_oserror_wsyscall(errbuf);
        return -1;
    }

    if (needed == 0) {
        psutil_debug("psutil_sysctlbyname_malloc() size = 0");
    }

    while (max_retries-- > 0) {
        // Zero-initialize buffer to prevent uninitialized bytes.
        buffer = calloc(1, needed);
        if (buffer == NULL) {
            PyErr_NoMemory();
            return -1;
        }

        len = needed;
        ret = sysctlbyname(name, buffer, &len, NULL, 0);
        if (ret == 0) {
            // Success: return buffer and actual length.
            *buf = buffer;
            *buflen = len;
            return 0;
        }

        // Handle buffer too small. Re-query and retry.
        if (errno == ENOMEM) {
            free(buffer);
            buffer = NULL;

            if (sysctlbyname(name, NULL, &needed, NULL, 0) == -1) {
                str_format(
                    errbuf,
                    sizeof(errbuf),
                    "sysctlbyname('%s') malloc 2/3",
                    name
                );
                psutil_oserror_wsyscall(errbuf);
                return -1;
            }

            psutil_debug("psutil_sysctlbyname_malloc() retry");
            continue;
        }

        // Other errors: clean up and give up.
        free(buffer);
        str_format(
            errbuf, sizeof(errbuf), "sysctlbyname('%s') malloc 3/3", name
        );
        psutil_oserror_wsyscall(errbuf);
        return -1;
    }

    str_format(
        errbuf,
        sizeof(errbuf),
        "sysctlbyname('%s') buffer allocation retry limit exceeded",
        name
    );
    psutil_runtime_error(errbuf);
    return -1;
}
#endif  // PSUTIL_HAS_SYSCTLBYNAME
#endif  // PSUTIL_HAS_SYSCTL
