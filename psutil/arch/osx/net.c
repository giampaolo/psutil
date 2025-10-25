/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Networks related functions. Original code was refactored and moved
// from psutil/_psutil_osx.c in 2023. This is the GIT blame before the move:
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/_psutil_osx.c

#include <Python.h>
#include <sys/socket.h>
#include <sys/sysctl.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <net/route.h>

#include "../../arch/all/init.h"


PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    char *buf = NULL, *lim, *next;
    struct if_msghdr *ifm;
    int mib[6];
    size_t len = 0;
    PyObject *py_ifc_info = NULL;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    mib[0] = CTL_NET;  // networking subsystem
    mib[1] = PF_ROUTE;  // type of information
    mib[2] = 0;  // protocol (IPPROTO_xxx)
    mib[3] = 0;  // address family
    mib[4] = NET_RT_IFLIST2;  // operation
    mib[5] = 0;

    if (psutil_sysctl_malloc(mib, 6, &buf, &len) != 0)
        goto error;

    lim = buf + len;

    for (next = buf; next < lim;) {
        if ((size_t)(lim - next) < sizeof(struct if_msghdr)) {
            psutil_debug("struct if_msghdr size mismatch (skip entry)");
            break;
        }

        ifm = (struct if_msghdr *)next;

        if (ifm->ifm_msglen == 0 || next + ifm->ifm_msglen > lim) {
            psutil_debug("ifm_msglen size mismatch (skip entry)");
            break;
        }

        next += ifm->ifm_msglen;

        if (ifm->ifm_type == RTM_IFINFO2) {
            py_ifc_info = NULL;
            struct if_msghdr2 *if2m = (struct if_msghdr2 *)ifm;

            if ((char *)if2m + sizeof(struct if_msghdr2) > lim) {
                psutil_debug("if_msghdr2 + sockaddr_dl mismatch (skip entry)");
                continue;
            }

            struct sockaddr_dl *sdl = (struct sockaddr_dl *)(if2m + 1);

            if ((char *)sdl + sizeof(struct sockaddr_dl) > lim) {
                psutil_debug("not enough buffer for sockaddr_dl (skip entry)");
                continue;
            }

            char ifc_name[IFNAMSIZ];
            size_t namelen = sdl->sdl_nlen;
            if (namelen >= IFNAMSIZ)
                namelen = IFNAMSIZ - 1;

            memcpy(ifc_name, sdl->sdl_data, namelen);
            ifc_name[namelen] = '\0';

            py_ifc_info = Py_BuildValue(
                "(KKKKKKKi)",
                (unsigned long long)if2m->ifm_data.ifi_obytes,
                (unsigned long long)if2m->ifm_data.ifi_ibytes,
                (unsigned long long)if2m->ifm_data.ifi_opackets,
                (unsigned long long)if2m->ifm_data.ifi_ipackets,
                (unsigned long long)if2m->ifm_data.ifi_ierrors,
                (unsigned long long)if2m->ifm_data.ifi_oerrors,
                (unsigned long long)if2m->ifm_data.ifi_iqdrops,
                0
            );  // dropout not supported

            if (!py_ifc_info)
                goto error;

            if (PyDict_SetItemString(py_retdict, ifc_name, py_ifc_info)) {
                Py_CLEAR(py_ifc_info);
                goto error;
            }

            Py_CLEAR(py_ifc_info);
        }
    }

    free(buf);
    return py_retdict;

error:
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    if (buf != NULL)
        free(buf);
    return NULL;
}
