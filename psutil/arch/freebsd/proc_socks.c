/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Retrieves per-process open socket connections.
 */

#include <Python.h>
#include <sys/user.h>
#include <sys/socketvar.h>    // for struct xsocket
#include <sys/un.h>
#include <sys/sysctl.h>
#include <netinet/in.h>   // for xinpcb struct
#include <netinet/in_pcb.h>
#include <netinet/tcp_var.h>   // for struct xtcpcb
#include <arpa/inet.h>         // for inet_ntop()
#include <libutil.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


// The tcplist fetching and walking is borrowed from netstat/inet.c.
static char *
psutil_fetch_tcplist(void) {
    char *buf;
    size_t len;

    for (;;) {
        if (sysctlbyname("net.inet.tcp.pcblist", NULL, &len, NULL, 0) < 0) {
            PyErr_SetFromErrno(PyExc_OSError);
            return NULL;
        }
        buf = malloc(len);
        if (buf == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        if (sysctlbyname("net.inet.tcp.pcblist", buf, &len, NULL, 0) < 0) {
            free(buf);
            PyErr_SetFromErrno(PyExc_OSError);
            return NULL;
        }
        return buf;
    }
}


static int
psutil_sockaddr_port(int family, struct sockaddr_storage *ss) {
    struct sockaddr_in6 *sin6;
    struct sockaddr_in *sin;

    if (family == AF_INET) {
        sin = (struct sockaddr_in *)ss;
        return (sin->sin_port);
    }
    else {
        sin6 = (struct sockaddr_in6 *)ss;
        return (sin6->sin6_port);
    }
}


static void *
psutil_sockaddr_addr(int family, struct sockaddr_storage *ss) {
    struct sockaddr_in6 *sin6;
    struct sockaddr_in *sin;

    if (family == AF_INET) {
        sin = (struct sockaddr_in *)ss;
        return (&sin->sin_addr);
    }
    else {
        sin6 = (struct sockaddr_in6 *)ss;
        return (&sin6->sin6_addr);
    }
}


static socklen_t
psutil_sockaddr_addrlen(int family) {
    if (family == AF_INET)
        return (sizeof(struct in_addr));
    else
        return (sizeof(struct in6_addr));
}


static int
psutil_sockaddr_matches(int family, int port, void *pcb_addr,
                        struct sockaddr_storage *ss) {
    if (psutil_sockaddr_port(family, ss) != port)
        return (0);
    return (memcmp(psutil_sockaddr_addr(family, ss), pcb_addr,
                   psutil_sockaddr_addrlen(family)) == 0);
}


#if __FreeBSD_version >= 1200026
static struct xtcpcb *
psutil_search_tcplist(char *buf, struct kinfo_file *kif) {
    struct xtcpcb *tp;
    struct xinpcb *inp;
#else
static struct tcpcb *
psutil_search_tcplist(char *buf, struct kinfo_file *kif) {
    struct tcpcb *tp;
    struct inpcb *inp;
#endif
    struct xinpgen *xig, *oxig;
    struct xsocket *so;

    oxig = xig = (struct xinpgen *)buf;
    for (xig = (struct xinpgen *)((char *)xig + xig->xig_len);
            xig->xig_len > sizeof(struct xinpgen);
            xig = (struct xinpgen *)((char *)xig + xig->xig_len)) {

#if __FreeBSD_version >= 1200026
        tp = (struct xtcpcb *)xig;
        inp = &tp->xt_inp;
        so = &inp->xi_socket;
#else
        tp = &((struct xtcpcb *)xig)->xt_tp;
        inp = &((struct xtcpcb *)xig)->xt_inp;
        so = &((struct xtcpcb *)xig)->xt_socket;
#endif

        if (so->so_type != kif->kf_sock_type ||
                so->xso_family != kif->kf_sock_domain ||
                so->xso_protocol != kif->kf_sock_protocol)
            continue;

        if (kif->kf_sock_domain == AF_INET) {
            if (!psutil_sockaddr_matches(
                    AF_INET, inp->inp_lport, &inp->inp_laddr,
#if __FreeBSD_version < 1200031
                    &kif->kf_sa_local))
#else
                    &kif->kf_un.kf_sock.kf_sa_local))
#endif
                continue;
            if (!psutil_sockaddr_matches(
                    AF_INET, inp->inp_fport, &inp->inp_faddr,
#if __FreeBSD_version < 1200031
                    &kif->kf_sa_peer))
#else
                    &kif->kf_un.kf_sock.kf_sa_peer))
#endif
                continue;
        } else {
            if (!psutil_sockaddr_matches(
                    AF_INET6, inp->inp_lport, &inp->in6p_laddr,
#if __FreeBSD_version < 1200031
                    &kif->kf_sa_local))
#else
                    &kif->kf_un.kf_sock.kf_sa_local))
#endif
                continue;
            if (!psutil_sockaddr_matches(
                    AF_INET6, inp->inp_fport, &inp->in6p_faddr,
#if __FreeBSD_version < 1200031
                    &kif->kf_sa_peer))
#else
                    &kif->kf_un.kf_sock.kf_sa_peer))
#endif
                continue;
        }

        return (tp);
    }
    return NULL;
}



PyObject *
psutil_proc_connections(PyObject *self, PyObject *args) {
    // Return connections opened by process.
    pid_t pid;
    int i;
    int cnt;
    struct kinfo_file *freep = NULL;
    struct kinfo_file *kif;
    char *tcplist = NULL;
#if __FreeBSD_version >= 1200026
    struct xtcpcb *tcp;
#else
    struct tcpcb *tcp;
#endif

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;
    PyObject *py_family = NULL;
    PyObject *py_type = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "OO", &pid,
                           &py_af_filter, &py_type_filter))
    {
        goto error;
    }
    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    errno = 0;
    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_for_pid(pid, "kinfo_getfile()");
        goto error;
    }

    tcplist = psutil_fetch_tcplist();
    if (tcplist == NULL) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    for (i = 0; i < cnt; i++) {
        int lport, rport, state;
        char lip[200], rip[200];
        char path[PATH_MAX];
        int inseq;
        py_tuple = NULL;
        py_laddr = NULL;
        py_raddr = NULL;

        kif = &freep[i];
        if (kif->kf_type == KF_TYPE_SOCKET) {
            // apply filters
            py_family = PyLong_FromLong((long)kif->kf_sock_domain);
            inseq = PySequence_Contains(py_af_filter, py_family);
            Py_DECREF(py_family);
            if (inseq == 0)
                continue;
            py_type = PyLong_FromLong((long)kif->kf_sock_type);
            inseq = PySequence_Contains(py_type_filter, py_type);
            Py_DECREF(py_type);
            if (inseq == 0)
                continue;
            // IPv4 / IPv6 socket
            if ((kif->kf_sock_domain == AF_INET) ||
                    (kif->kf_sock_domain == AF_INET6)) {
                // fill status
                state = PSUTIL_CONN_NONE;
                if (kif->kf_sock_type == SOCK_STREAM) {
                    tcp = psutil_search_tcplist(tcplist, kif);
                    if (tcp != NULL)
                        state = (int)tcp->t_state;
                }

                // build addr and port
                inet_ntop(
                    kif->kf_sock_domain,
                    psutil_sockaddr_addr(kif->kf_sock_domain,
#if __FreeBSD_version < 1200031
                                         &kif->kf_sa_local),
#else
                                         &kif->kf_un.kf_sock.kf_sa_local),
#endif
                    lip,
                    sizeof(lip));
                inet_ntop(
                    kif->kf_sock_domain,
                    psutil_sockaddr_addr(kif->kf_sock_domain,
#if __FreeBSD_version < 1200031
                                         &kif->kf_sa_peer),
#else
                                         &kif->kf_un.kf_sock.kf_sa_peer),
#endif
                    rip,
                    sizeof(rip));
                lport = htons(psutil_sockaddr_port(kif->kf_sock_domain,
#if __FreeBSD_version < 1200031
                                                   &kif->kf_sa_local));
#else
                                                   &kif->kf_un.kf_sock.kf_sa_local));
#endif
                rport = htons(psutil_sockaddr_port(kif->kf_sock_domain,
#if __FreeBSD_version < 1200031
                                                   &kif->kf_sa_peer));
#else
                                                   &kif->kf_un.kf_sock.kf_sa_peer));
#endif

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
                    "(iiiNNi)",
                    kif->kf_fd,
                    kif->kf_sock_domain,
                    kif->kf_sock_type,
                    py_laddr,
                    py_raddr,
                    state
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_DECREF(py_tuple);
            }
            // UNIX socket.
            // Note: remote path cannot be determined.
            else if (kif->kf_sock_domain == AF_UNIX) {
                struct sockaddr_un *sun;

#if __FreeBSD_version < 1200031
                sun = (struct sockaddr_un *)&kif->kf_sa_local;
#else
                sun = (struct sockaddr_un *)&kif->kf_un.kf_sock.kf_sa_local;
#endif
                snprintf(
                    path, sizeof(path), "%.*s",
                    (int)(sun->sun_len - (sizeof(*sun) - sizeof(sun->sun_path))),
                    sun->sun_path);

                py_laddr = PyUnicode_DecodeFSDefault(path);
                if (! py_laddr)
                    goto error;

                py_tuple = Py_BuildValue(
                    "(iiiOsi)",
                    kif->kf_fd,
                    kif->kf_sock_domain,
                    kif->kf_sock_type,
                    py_laddr,
                    "",  // raddr can't be determined
                    PSUTIL_CONN_NONE
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_DECREF(py_tuple);
                Py_DECREF(py_laddr);
            }
        }
    }
    free(freep);
    free(tcplist);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    Py_DECREF(py_retlist);
    if (freep != NULL)
        free(freep);
    if (tcplist != NULL)
        free(tcplist);
    return NULL;
}
