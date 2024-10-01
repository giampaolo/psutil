/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/socket.h>
#include <kvm.h>
#define _KERNEL  // silence compiler warning
#include <sys/file.h>  // DTYPE_SOCKET
#include <netdb.h>  // INET6_ADDRSTRLEN, in6_addr
#undef _KERNEL

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    pid_t pid;
    int i;
    int cnt;
    int state;
    int lport;
    int rport;
    char lip[INET6_ADDRSTRLEN];
    char rip[INET6_ADDRSTRLEN];
    int inseq;

    char errbuf[_POSIX2_LINE_MAX];
    kvm_t *kd = NULL;

    struct kinfo_file *kif;
    struct kinfo_file *ikf;
    struct in6_addr laddr6;

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;
    PyObject *py_lpath = NULL;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;
    PyObject *py_family = NULL;
    PyObject *_type = NULL;


    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "OO", &pid, &py_af_filter,
                           &py_type_filter)) {
        goto error;
    }
    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);
    if (! kd) {
        convert_kvm_err("kvm_openfiles", errbuf);
        goto error;
    }

    ikf = kvm_getfiles(kd, KERN_FILE_BYPID, -1, sizeof(*ikf), &cnt);
    if (! ikf) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("kvm_getfiles");
        goto error;
    }

    for (int i = 0; i < cnt; i++) {
        const struct kinfo_file *kif = ikf + i;
        py_tuple = NULL;
        py_laddr = NULL;
        py_raddr = NULL;
        py_lpath = NULL;

        // apply filters
        if (kif->f_type != DTYPE_SOCKET)
            continue;
        if (pid != -1 && kif->p_pid != (uint32_t)pid)
            continue;
        py_family = PyLong_FromLong((long)kif->so_family);
        inseq = PySequence_Contains(py_af_filter, py_family);
        Py_DECREF(py_family);
        if (inseq == 0)
            continue;
        _type = PyLong_FromLong((long)kif->so_type);
        inseq = PySequence_Contains(py_type_filter, _type);
        Py_DECREF(_type);
        if (inseq == 0)
            continue;

        // IPv4 / IPv6 socket
        if ((kif->so_family == AF_INET) || (kif->so_family == AF_INET6)) {
            // status
            if (kif->so_type == SOCK_STREAM)
                state = kif->t_state;
            else
                state = PSUTIL_CONN_NONE;

            // local & remote port
            lport = ntohs(kif->inp_lport);
            rport = ntohs(kif->inp_fport);

            // local addr
            inet_ntop(kif->so_family, &kif->inp_laddru, lip, sizeof(lip));
            py_laddr = Py_BuildValue("(si)", lip, lport);
            if (! py_laddr)
                goto error;

            // remote addr
            if (rport != 0) {
                inet_ntop(kif->so_family, &kif->inp_faddru, rip, sizeof(rip));
                py_raddr = Py_BuildValue("(si)", rip, rport);
            }
            else {
                py_raddr = Py_BuildValue("()");
            }
            if (! py_raddr)
                goto error;

            // populate tuple and list
            py_tuple = Py_BuildValue(
                "(iiiNNil)",
                kif->fd_fd,
                kif->so_family,
                kif->so_type,
                py_laddr,
                py_raddr,
                state,
                kif->p_pid
            );
            if (! py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_DECREF(py_tuple);
        }
        // UNIX socket
        else if (kif->so_family == AF_UNIX) {
            py_lpath = PyUnicode_DecodeFSDefault(kif->unp_path);
            if (! py_lpath)
                goto error;

            py_tuple = Py_BuildValue(
                "(iiiOsil)",
                kif->fd_fd,
                kif->so_family,
                kif->so_type,
                py_lpath,
                "",  // raddr
                PSUTIL_CONN_NONE,
                kif->p_pid
            );
            if (! py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_DECREF(py_lpath);
            Py_DECREF(py_tuple);
            Py_INCREF(Py_None);
        }
    }

    kvm_close(kd);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    Py_DECREF(py_retlist);
    if (kd != NULL)
        kvm_close(kd);
    return NULL;
}
