/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#if !defined(PSUTIL_OPENBSD) && !defined(PSUTIL_AIX)
    #define PSUTIL_HAS_POSIX_USERS

    PyObject *psutil_users(PyObject *self, PyObject *args);
#endif

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    #include <sys/types.h>

    #define PSUTIL_HAS_SYSCTL

    int psutil_sysctl(int *mib, u_int miblen, void *buf, size_t buflen);
    int psutil_sysctl_malloc(int *mib, u_int miblen, char **buf, size_t *buflen);
    int psutil_sysctl_argmax();

    #if !defined(PSUTIL_OPENBSD)

        #define PSUTIL_HAS_SYSCTLBYNAME

        int psutil_sysctlbyname(const char *name, void *buf, size_t buflen);
        int psutil_sysctlbyname_malloc(const char *name, char **buf, size_t *buflen);
    #endif
#endif

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
    #define PSUTIL_HAS_NET_IF_DUPLEX_SPEED

    PyObject *psutil_net_if_duplex_speed(PyObject *self, PyObject *args);
#endif

int psutil_pid_exists(pid_t pid);
long psutil_getpagesize(void);
void psutil_raise_for_pid(pid_t pid, char *msg);

PyObject *psutil_getpagesize_pywrapper(PyObject *self, PyObject *args);
PyObject *psutil_net_if_addrs(PyObject *self, PyObject *args);
PyObject *psutil_net_if_flags(PyObject *self, PyObject *args);
PyObject *psutil_net_if_is_running(PyObject *self, PyObject *args);
PyObject *psutil_net_if_mtu(PyObject *self, PyObject *args);
PyObject *psutil_posix_getpriority(PyObject *self, PyObject *args);
PyObject *psutil_posix_setpriority(PyObject *self, PyObject *args);
