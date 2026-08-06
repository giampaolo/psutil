/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// AIX support is experimental at this time.
// The following functions and methods are unsupported on the AIX platform:
// - psutil.Process.memory_maps
//
// Known limitations:
// - psutil.Process.io_counters read count is always 0
// - psutil.Process.io_counters may not be available on older AIX versions
// - psutil.Process.threads may not be available on older AIX versions
// - psutil.net_io_counters may not be available on older AIX versions
// - reading basic process info may fail or return incorrect values when
//   process is starting (see IBM APAR IV58499 - fixed in newer AIX versions)
// - sockets and pipes may not be counted in num_fds (fixed in newer AIX
//   versions)
//
// Useful resources:
// - proc filesystem:
// http://www-01.ibm.com/support/knowledgecenter/ssw_aix_72/com.ibm.aix.files/proc.htm
// - libperfstat:
// http://www-01.ibm.com/support/knowledgecenter/ssw_aix_72/com.ibm.aix.files/libperfstat.h.htm

#include <Python.h>
#include <sys/limits.h>
#include <sys/proc.h>
#include <sys/procfs.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/sysinfo.h>
#include <sys/thread.h>
#include <sys/types.h>
#include <fcntl.h>
#include <utmp.h>
#include <utmpx.h>
#include <mntent.h>
#include <sys/ioctl.h>
#include <sys/tihdr.h>
#include <stropts.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <net/if.h>
#include <libperfstat.h>
#include <unistd.h>

#include "../../arch/all/init.h"
#include "ifaddrs.h"
#include "net_connections.h"
#include "common.h"


#define TV2DOUBLE(t) (((t).tv_nsec * 0.000000001) + (t).tv_sec)


static PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    perfstat_netinterface_t *statp = NULL;
    int tot, i;
    perfstat_id_t first;

    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;

    if (py_retdict == NULL)
        return NULL;

    // check how many perfstat_netinterface_t structures are available
    tot = perfstat_netinterface(
        NULL, NULL, sizeof(perfstat_netinterface_t), 0
    );
    if (tot == 0) {
        // no network interfaces - return empty dict
        return py_retdict;
    }
    if (tot < 0) {
        psutil_oserror();
        goto error;
    }
    statp = (perfstat_netinterface_t *)malloc(
        tot * sizeof(perfstat_netinterface_t)
    );
    if (statp == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    strcpy(first.name, FIRST_NETINTERFACE);
    tot = perfstat_netinterface(
        &first, statp, sizeof(perfstat_netinterface_t), tot
    );
    if (tot < 0) {
        psutil_oserror();
        goto error;
    }

    for (i = 0; i < tot; i++) {
        py_ifc_info = Py_BuildValue(
            "(KKKKKKKK)",
            statp[i].obytes,  // bytes sent
            statp[i].ibytes,  // bytes received
            statp[i].opackets,  // packets sent
            statp[i].ipackets,  // packets received
            statp[i].ierrors,  // input errors
            statp[i].oerrors,  // output errors
            statp[i].if_iqdrops,  // dropped on input
            statp[i].xmitdrops  // not transmitted
        );
        if (!py_ifc_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, statp[i].name, py_ifc_info))
            goto error;
        Py_DECREF(py_ifc_info);
    }

    free(statp);
    return py_retdict;

error:
    if (statp != NULL)
        free(statp);
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    return NULL;
}


static PyObject *
psutil_net_if_stats(PyObject *self, PyObject *args) {
    char *nic_name;
    int sock = 0;
    int ret;
    int mtu;
    struct ifreq ifr;
    PyObject *py_is_up = NULL;
    PyObject *py_retlist = NULL;

    if (!PyArg_ParseTuple(args, "s", &nic_name))
        return NULL;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1)
        goto error;

    str_copy(ifr.ifr_name, sizeof(ifr.ifr_name), nic_name);

    // is up?
    Py_BEGIN_ALLOW_THREADS
    ret = ioctl(sock, SIOCGIFFLAGS, &ifr);
    Py_END_ALLOW_THREADS
    if (ret == -1)
        goto error;
    if ((ifr.ifr_flags & IFF_UP) != 0)
        py_is_up = Py_True;
    else
        py_is_up = Py_False;
    Py_INCREF(py_is_up);

    // MTU
    Py_BEGIN_ALLOW_THREADS
    ret = ioctl(sock, SIOCGIFMTU, &ifr);
    Py_END_ALLOW_THREADS
    if (ret == -1)
        goto error;
    mtu = ifr.ifr_mtu;

    close(sock);
    py_retlist = Py_BuildValue("[Oi]", py_is_up, mtu);
    if (!py_retlist)
        goto error;
    Py_DECREF(py_is_up);
    return py_retlist;

error:
    Py_XDECREF(py_is_up);
    if (sock != 0)
        close(sock);
    psutil_oserror();
    return NULL;
}
