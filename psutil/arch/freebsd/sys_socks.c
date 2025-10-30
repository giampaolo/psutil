/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Retrieves system-wide open socket connections. This is based off of
 * sockstat utility source code:
 * https://github.com/freebsd/freebsd/blob/master/usr.bin/sockstat/sockstat.c
 */

#include <Python.h>
#include <sys/param.h>
#include <sys/user.h>
#include <sys/file.h>
#include <sys/socketvar.h>  // for struct xsocket
#include <sys/un.h>
#include <sys/unpcb.h>
#include <sys/sysctl.h>
#include <netinet/in.h>  // for xinpcb struct
#include <netinet/ip.h>
#include <netinet/in_pcb.h>
#include <netinet/tcp_var.h>  // for struct xtcpcb
#include <arpa/inet.h>  // for inet_ntop()

#include "../../arch/all/init.h"


static int
psutil_populate_xfiles(struct xfile **psutil_xfiles, int *psutil_nxfiles) {
    struct xfile *new_psutil_xfiles;
    size_t len = sizeof(struct xfile);

    while (sysctlbyname("kern.file", *psutil_xfiles, &len, 0, 0) == -1) {
        if (errno != ENOMEM) {
            psutil_oserror();
            return -1;
        }
        len *= 2;
        new_psutil_xfiles = realloc(*psutil_xfiles, len);
        if (new_psutil_xfiles == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        *psutil_xfiles = new_psutil_xfiles;
    }
    if (len > 0 && (*psutil_xfiles)->xf_size != sizeof(struct xfile)) {
        psutil_runtime_error("struct xfile size mismatch");
        return -1;
    }
    *psutil_nxfiles = len / sizeof(struct xfile);
    return 0;
}


static struct xfile *
psutil_get_file_from_sock(
    kvaddr_t sock, struct xfile *psutil_xfiles, int psutil_nxfiles
) {
    struct xfile *xf;
    int n;

    for (xf = psutil_xfiles, n = 0; n < psutil_nxfiles; ++n, ++xf) {
        if (xf->xf_data == sock)
            return xf;
    }
    return NULL;
}


// Reference:
// https://github.com/freebsd/freebsd/blob/master/usr.bin/sockstat/sockstat.c
static int
psutil_gather_inet(
    int proto,
    int include_v4,
    int include_v6,
    PyObject *py_retlist,
    struct xfile *psutil_xfiles,
    int psutil_nxfiles
) {
    struct xinpgen *xig, *exig;
    struct xinpcb *xip;
    struct xtcpcb *xtp;
#if __FreeBSD_version >= 1200026
    struct xinpcb *inp;
#else
    struct inpcb *inp;
#endif
    struct xsocket *so;
    const char *varname = NULL;
    size_t len, bufsize;
    void *buf;
    int retry;
    int type;

    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;

    switch (proto) {
        case IPPROTO_TCP:
            varname = "net.inet.tcp.pcblist";
            type = SOCK_STREAM;
            break;
        case IPPROTO_UDP:
            varname = "net.inet.udp.pcblist";
            type = SOCK_DGRAM;
            break;
    }

    buf = NULL;
    bufsize = 8192;
    retry = 5;
    do {
        for (;;) {
            buf = realloc(buf, bufsize);
            if (buf == NULL)
                continue;  // XXX
            len = bufsize;
            if (sysctlbyname(varname, buf, &len, NULL, 0) == 0)
                break;
            if (errno != ENOMEM) {
                psutil_oserror();
                goto error;
            }
            bufsize *= 2;
        }
        xig = (struct xinpgen *)buf;
        exig = (struct xinpgen *)(void *)((char *)buf + len - sizeof *exig);
        if (xig->xig_len != sizeof *xig || exig->xig_len != sizeof *exig) {
            psutil_runtime_error("struct xinpgen size mismatch");
            goto error;
        }
    } while (xig->xig_gen != exig->xig_gen && retry--);

    for (;;) {
        struct xfile *xf;
        int lport, rport, status, family;

        xig = (struct xinpgen *)(void *)((char *)xig + xig->xig_len);
        if (xig >= exig)
            break;

        switch (proto) {
            case IPPROTO_TCP:
                xtp = (struct xtcpcb *)xig;
                if (xtp->xt_len != sizeof *xtp) {
                    psutil_runtime_error("struct xtcpcb size mismatch");
                    goto error;
                }
                inp = &xtp->xt_inp;
#if __FreeBSD_version >= 1200026
                so = &inp->xi_socket;
                status = xtp->t_state;
#else
                so = &xtp->xt_socket;
                status = xtp->xt_tp.t_state;
#endif
                break;
            case IPPROTO_UDP:
                xip = (struct xinpcb *)xig;
                if (xip->xi_len != sizeof *xip) {
                    psutil_runtime_error("struct xinpcb size mismatch");
                    goto error;
                }
#if __FreeBSD_version >= 1200026
                inp = xip;
#else
                inp = &xip->xi_inp;
#endif
                so = &xip->xi_socket;
                status = PSUTIL_CONN_NONE;
                break;
            default:
                psutil_runtime_error("invalid proto");
                goto error;
        }

        // filter
        if ((inp->inp_vflag & INP_IPV4) && (include_v4 == 0))
            continue;
        if ((inp->inp_vflag & INP_IPV6) && (include_v6 == 0))
            continue;

        char lip[INET6_ADDRSTRLEN], rip[INET6_ADDRSTRLEN];

        xf = psutil_get_file_from_sock(
            so->xso_so, psutil_xfiles, psutil_nxfiles
        );
        if (xf == NULL)
            continue;
        lport = ntohs(inp->inp_lport);
        rport = ntohs(inp->inp_fport);

        if (inp->inp_vflag & INP_IPV4) {
            family = AF_INET;
            inet_ntop(AF_INET, &inp->inp_laddr.s_addr, lip, sizeof(lip));
            inet_ntop(AF_INET, &inp->inp_faddr.s_addr, rip, sizeof(rip));
        }
        else if (inp->inp_vflag & INP_IPV6) {
            family = AF_INET6;
            inet_ntop(AF_INET6, &inp->in6p_laddr.s6_addr, lip, sizeof(lip));
            inet_ntop(AF_INET6, &inp->in6p_faddr.s6_addr, rip, sizeof(rip));
        }

        // construct python tuple/list
        py_laddr = Py_BuildValue("(si)", lip, lport);
        if (!py_laddr)
            goto error;
        if (rport != 0)
            py_raddr = Py_BuildValue("(si)", rip, rport);
        else
            py_raddr = Py_BuildValue("()");
        if (!py_raddr)
            goto error;
        py_tuple = Py_BuildValue(
            "iiiNNi" _Py_PARSE_PID,
            xf->xf_fd,  // fd
            family,  // family
            type,  // type
            py_laddr,  // laddr
            py_raddr,  // raddr
            status,  // status
            xf->xf_pid  // pid
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
    }

    free(buf);
    return 0;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    free(buf);
    return -1;
}


static int
psutil_gather_unix(
    int proto,
    PyObject *py_retlist,
    struct xfile *psutil_xfiles,
    int psutil_nxfiles
) {
    struct xunpgen *xug, *exug;
    struct xunpcb *xup;
    const char *varname = NULL;
    const char *protoname = NULL;
    size_t len;
    size_t bufsize;
    void *buf;
    int retry;
    struct sockaddr_un *sun;
    char path[PATH_MAX];

    PyObject *py_tuple = NULL;
    PyObject *py_lpath = NULL;

    switch (proto) {
        case SOCK_STREAM:
            varname = "net.local.stream.pcblist";
            protoname = "stream";
            break;
        case SOCK_DGRAM:
            varname = "net.local.dgram.pcblist";
            protoname = "dgram";
            break;
    }

    buf = NULL;
    bufsize = 8192;
    retry = 5;

    do {
        for (;;) {
            buf = realloc(buf, bufsize);
            if (buf == NULL) {
                PyErr_NoMemory();
                goto error;
            }
            len = bufsize;
            if (sysctlbyname(varname, buf, &len, NULL, 0) == 0)
                break;
            if (errno != ENOMEM) {
                psutil_oserror();
                goto error;
            }
            bufsize *= 2;
        }
        xug = (struct xunpgen *)buf;
        exug = (struct xunpgen *)(void *)((char *)buf + len - sizeof *exug);
        if (xug->xug_len != sizeof *xug || exug->xug_len != sizeof *exug) {
            psutil_runtime_error("struct xinpgen size mismatch");
            goto error;
        }
    } while (xug->xug_gen != exug->xug_gen && retry--);

    for (;;) {
        struct xfile *xf;

        xug = (struct xunpgen *)(void *)((char *)xug + xug->xug_len);
        if (xug >= exug)
            break;
        xup = (struct xunpcb *)xug;
        if (xup->xu_len != sizeof *xup)
            goto error;

        xf = psutil_get_file_from_sock(
            xup->xu_socket.xso_so, psutil_xfiles, psutil_nxfiles
        );
        if (xf == NULL)
            continue;

        sun = (struct sockaddr_un *)&xup->xu_addr;
        str_format(
            path,
            sizeof(path),
            "%.*s",
            (int)(sun->sun_len - (sizeof(*sun) - sizeof(sun->sun_path))),
            sun->sun_path
        );
        py_lpath = PyUnicode_DecodeFSDefault(path);
        if (!py_lpath)
            goto error;

        py_tuple = Py_BuildValue(
            "(iiiOsii)",
            xf->xf_fd,  // fd
            AF_UNIX,  // family
            proto,  // type
            py_lpath,  // lpath
            "",  // rath
            PSUTIL_CONN_NONE,  // status
            xf->xf_pid  // pid
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_lpath);
        Py_DECREF(py_tuple);
    }

    free(buf);
    return 0;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_lpath);
    free(buf);
    return -1;
}


static int
psutil_int_in_seq(int value, PyObject *py_seq) {
    int inseq;
    PyObject *py_value;

    py_value = PyLong_FromLong((long)value);
    if (py_value == NULL)
        return -1;
    inseq = PySequence_Contains(py_seq, py_value);  // return -1 on failure
    Py_DECREF(py_value);
    return inseq;
}


PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    int include_v4, include_v6, include_unix, include_tcp, include_udp,
        psutil_nxfiles;
    struct xfile *psutil_xfiles;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, "OO", &py_af_filter, &py_type_filter)) {
        goto error;
    }
    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    if ((include_v4 = psutil_int_in_seq(AF_INET, py_af_filter)) == -1)
        goto error;
    if ((include_v6 = psutil_int_in_seq(AF_INET6, py_af_filter)) == -1)
        goto error;
    if ((include_unix = psutil_int_in_seq(AF_UNIX, py_af_filter)) == -1)
        goto error;
    if ((include_tcp = psutil_int_in_seq(SOCK_STREAM, py_type_filter)) == -1)
        goto error;
    if ((include_udp = psutil_int_in_seq(SOCK_DGRAM, py_type_filter)) == -1)
        goto error;

    psutil_xfiles = malloc(sizeof(struct xfile));
    if (psutil_xfiles == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    if (psutil_populate_xfiles(&psutil_xfiles, &psutil_nxfiles) != 0)
        goto error_free_psutil_xfiles;

    // TCP
    if (include_tcp == 1) {
        if (psutil_gather_inet(
                IPPROTO_TCP,
                include_v4,
                include_v6,
                py_retlist,
                psutil_xfiles,
                psutil_nxfiles
            )
            != 0)
        {
            goto error_free_psutil_xfiles;
        }
    }
    // UDP
    if (include_udp == 1) {
        if (psutil_gather_inet(
                IPPROTO_UDP,
                include_v4,
                include_v6,
                py_retlist,
                psutil_xfiles,
                psutil_nxfiles
            )
            != 0)
        {
            goto error_free_psutil_xfiles;
        }
    }
    // UNIX
    if (include_unix == 1) {
        if (psutil_gather_unix(
                SOCK_STREAM, py_retlist, psutil_xfiles, psutil_nxfiles
            )
            != 0)
            goto error_free_psutil_xfiles;
        if (psutil_gather_unix(
                SOCK_DGRAM, py_retlist, psutil_xfiles, psutil_nxfiles
            )
            != 0)
            goto error_free_psutil_xfiles;
    }

    free(psutil_xfiles);
    return py_retlist;

error_free_psutil_xfiles:
    free(psutil_xfiles);
error:
    Py_DECREF(py_retlist);
    return NULL;
}
