/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <linux/sockios.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <linux/if.h>
#include <linux/version.h>
#include <unistd.h>

// see: https://github.com/giampaolo/psutil/issues/659
#ifdef PSUTIL_ETHTOOL_MISSING_TYPES
    #include <linux/types.h>
    typedef __u64 u64;
    typedef __u32 u32;
    typedef __u16 u16;
    typedef __u8 u8;
#endif

// Avoid redefinition of struct sysinfo with musl libc.
#define _LINUX_SYSINFO_H
#include <linux/ethtool.h>

#include "../../_psutil_common.h"


// * defined in linux/ethtool.h but not always available (e.g. Android)
// * #ifdef check needed for old kernels, see:
//   https://github.com/giampaolo/psutil/issues/2164
static inline uint32_t
psutil_ethtool_cmd_speed(const struct ethtool_cmd *ecmd) {
#if LINUX_VERSION_CODE < KERNEL_VERSION(2, 6, 27)
    return ecmd->speed;
#else
    return (ecmd->speed_hi << 16) | ecmd->speed;
#endif
}

// May happen on old RedHat versions, see:
// https://github.com/giampaolo/psutil/issues/607
#ifndef DUPLEX_UNKNOWN
    #define DUPLEX_UNKNOWN 0xff
#endif
// https://github.com/giampaolo/psutil/pull/2156
#ifndef SPEED_UNKNOWN
    #define SPEED_UNKNOWN -1
#endif


// References:
// * https://github.com/dpaleino/wicd/blob/master/wicd/backends/be-ioctl.py
// * http://www.i-scream.org/libstatgrab/
PyObject*
psutil_net_if_duplex_speed(PyObject* self, PyObject* args) {
    char *nic_name;
    int sock = 0;
    int ret;
    int duplex;
    __u32 uint_speed;
    int speed;
    struct ifreq ifr;
    struct ethtool_cmd ethcmd;
    PyObject *py_retlist = NULL;

    if (! PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        return PyErr_SetFromOSErrnoWithSyscall("socket()");
    PSUTIL_STRNCPY(ifr.ifr_name, nic_name, sizeof(ifr.ifr_name));

    // duplex and speed
    memset(&ethcmd, 0, sizeof ethcmd);
    ethcmd.cmd = ETHTOOL_GSET;
    ifr.ifr_data = (void *)&ethcmd;
    ret = ioctl(sock, SIOCETHTOOL, &ifr);

    if (ret != -1) {
        duplex = ethcmd.duplex;
        // speed is returned from ethtool as a __u32 ranging from 0 to INT_MAX
        // or SPEED_UNKNOWN (-1)
        uint_speed = psutil_ethtool_cmd_speed(&ethcmd);
        if (uint_speed == (__u32)SPEED_UNKNOWN || uint_speed > INT_MAX) {
            speed = 0;
        }
        else {
            speed = (int)uint_speed;
        }
    }
    else {
        if ((errno == EOPNOTSUPP) || (errno == EINVAL)) {
            // EOPNOTSUPP may occur in case of wi-fi cards.
            // For EINVAL see:
            // https://github.com/giampaolo/psutil/issues/797
            //     #issuecomment-202999532
            duplex = DUPLEX_UNKNOWN;
            speed = 0;
        }
        else {
            PyErr_SetFromOSErrnoWithSyscall("ioctl(SIOCETHTOOL)");
            goto error;
        }
    }

    py_retlist = Py_BuildValue("[ii]", duplex, speed);
    if (!py_retlist)
        goto error;
    close(sock);
    return py_retlist;

error:
    if (sock != -1)
        close(sock);
    return NULL;
}
