/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <string.h>
#include <net/if.h>
#include <net/if_dl.h>
#include <net/route.h>

#include "../../arch/all/init.h"


PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    char *buf = NULL, *lim, *next;
    struct if_msghdr *ifm;
    int mib[6];
    size_t len;
    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;

    if (py_retdict == NULL)
        return NULL;

    mib[0] = CTL_NET;  // networking subsystem
    mib[1] = PF_ROUTE;  // type of information
    mib[2] = 0;  // protocol (IPPROTO_xxx)
    mib[3] = 0;  // address family
    mib[4] = NET_RT_IFLIST;  // operation
    mib[5] = 0;

    if (psutil_sysctl_malloc(mib, 6, &buf, &len) != 0)
        goto error;

    lim = buf + len;

    for (next = buf; next < lim;) {
        py_ifc_info = NULL;
        ifm = (struct if_msghdr *)next;
        next += ifm->ifm_msglen;

        if (ifm->ifm_type == RTM_IFINFO) {
            struct if_msghdr *if2m = (struct if_msghdr *)ifm;
            struct sockaddr_dl *sdl = (struct sockaddr_dl *)(if2m + 1);
            char ifc_name[32];

            strncpy(ifc_name, sdl->sdl_data, sdl->sdl_nlen);
            ifc_name[sdl->sdl_nlen] = '\0';

            // XXX: ignore usbus interfaces:
            // http://lists.freebsd.org/pipermail/freebsd-current/
            //     2011-October/028752.html
            // 'ifconfig -a' doesn't show them, nor do we.
            if (strncmp(ifc_name, "usbus", 5) == 0)
                continue;

            py_ifc_info = Py_BuildValue(
                "(kkkkkkki)",
                if2m->ifm_data.ifi_obytes,
                if2m->ifm_data.ifi_ibytes,
                if2m->ifm_data.ifi_opackets,
                if2m->ifm_data.ifi_ipackets,
                if2m->ifm_data.ifi_ierrors,
                if2m->ifm_data.ifi_oerrors,
                if2m->ifm_data.ifi_iqdrops,
#ifdef _IFI_OQDROPS
                if2m->ifm_data.ifi_oqdrops
#else
                0
#endif
            );
            if (!py_ifc_info)
                goto error;
            if (PyDict_SetItemString(py_retdict, ifc_name, py_ifc_info) != 0)
                goto error;
            Py_CLEAR(py_ifc_info);
        }
    }

    free(buf);
    return py_retdict;

error:
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    free(buf);
    return NULL;
}
