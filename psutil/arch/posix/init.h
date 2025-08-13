/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include "net.h"
#include "proc.h"
#if !defined(PSUTIL_OPENBSD) && !defined(PSUTIL_AIX)
    #include "users.h"
#endif

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    #include <sys/types.h>

    int psutil_sysctl_fixed(int *mib, u_int miblen, void *buf, size_t buflen);
    int psutil_sysctl_malloc(int *mib, u_int miblen, char **buf, size_t *buflen);
    int psutil_sysctlbyname_fixed(const char *name, void *buf, size_t buflen);
    int psutil_sysctl_argmax();
#endif

long psutil_getpagesize(void);
PyObject *psutil_getpagesize_pywrapper(PyObject *self, PyObject *args);
PyObject *psutil_users(PyObject *self, PyObject *args);
