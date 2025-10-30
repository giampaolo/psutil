/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * Copyright (c) 2015, Ryo ONODERA.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/socket.h>
#include <arpa/inet.h>
#include <sys/queue.h>
#include <sys/un.h>

#include "../../arch/all/init.h"


// kinfo_file results
struct kif {
    SLIST_ENTRY(kif) kifs;
    struct kinfo_file *kif;
    char *buf;
    int has_buf;
};

// kinfo_file results list
SLIST_HEAD(kifhead, kif) kihead = SLIST_HEAD_INITIALIZER(kihead);


// kinfo_pcb results
struct kpcb {
    SLIST_ENTRY(kpcb) kpcbs;
    struct kinfo_pcb *kpcb;
    struct kinfo_pcb *buf;
    int has_buf;
};

// kinfo_pcb results list
SLIST_HEAD(kpcbhead, kpcb) kpcbhead = SLIST_HEAD_INITIALIZER(kpcbhead);


// Initialize kinfo_file results list.
static void
psutil_kiflist_init(void) {
    SLIST_INIT(&kihead);
}


// Clear kinfo_file results list.
static void
psutil_kiflist_clear(void) {
    while (!SLIST_EMPTY(&kihead)) {
        struct kif *kif = SLIST_FIRST(&kihead);
        if (kif->has_buf == 1)
            free(kif->buf);
        free(kif);
        SLIST_REMOVE_HEAD(&kihead, kifs);
    }
}


// Initialize kinof_pcb result list.
static void
psutil_kpcblist_init(void) {
    SLIST_INIT(&kpcbhead);
}


// Clear kinof_pcb result list.
static void
psutil_kpcblist_clear(void) {
    while (!SLIST_EMPTY(&kpcbhead)) {
        struct kpcb *kpcb = SLIST_FIRST(&kpcbhead);
        if (kpcb->has_buf == 1)
            free(kpcb->buf);
        free(kpcb);
        SLIST_REMOVE_HEAD(&kpcbhead, kpcbs);
    }
}


// Get all open files including socket.
static int
psutil_get_files(void) {
    size_t len;
    size_t j;
    int mib[6];
    char *buf = NULL;
    off_t offset;

    mib[0] = CTL_KERN;
    mib[1] = KERN_FILE2;
    mib[2] = KERN_FILE_BYFILE;
    mib[3] = 0;
    mib[4] = sizeof(struct kinfo_file);
    mib[5] = 0;

    if (sysctl(mib, 6, NULL, &len, NULL, 0) == -1) {
        psutil_oserror();
        goto error;
    }

    offset = len % sizeof(off_t);
    mib[5] = len / sizeof(struct kinfo_file);

    if ((buf = malloc(len + offset)) == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    if (sysctl(mib, 6, buf + offset, &len, NULL, 0) == -1) {
        psutil_oserror();
        goto error;
    }

    len /= sizeof(struct kinfo_file);
    struct kinfo_file *ki = (struct kinfo_file *)(buf + offset);

    if (len > 0) {
        for (j = 0; j < len; j++) {
            struct kif *kif = malloc(sizeof(struct kif));
            if (kif == NULL) {
                PyErr_NoMemory();
                goto error;
            }
            kif->kif = &ki[j];
            if (j == 0) {
                kif->has_buf = 1;
                kif->buf = buf;
            }
            else {
                kif->has_buf = 0;
                kif->buf = NULL;
            }
            SLIST_INSERT_HEAD(&kihead, kif, kifs);
        }
    }
    else {
        free(buf);
    }

    return 0;

error:
    if (buf != NULL)
        free(buf);
    return -1;
}


// Get open sockets.
static int
psutil_get_sockets(const char *name) {
    size_t namelen;
    int mib[8];
    struct kinfo_pcb *pcb = NULL;
    size_t len;
    size_t j;

    memset(mib, 0, sizeof(mib));

    if (sysctlnametomib(name, mib, &namelen) == -1) {
        psutil_oserror();
        goto error;
    }

    if (sysctl(mib, __arraycount(mib), NULL, &len, NULL, 0) == -1) {
        psutil_oserror();
        goto error;
    }

    if ((pcb = malloc(len)) == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    memset(pcb, 0, len);

    mib[6] = sizeof(*pcb);
    mib[7] = len / sizeof(*pcb);

    if (sysctl(mib, __arraycount(mib), pcb, &len, NULL, 0) == -1) {
        psutil_oserror();
        goto error;
    }

    len /= sizeof(struct kinfo_pcb);
    struct kinfo_pcb *kp = (struct kinfo_pcb *)pcb;

    if (len > 0) {
        for (j = 0; j < len; j++) {
            struct kpcb *kpcb = malloc(sizeof(struct kpcb));
            if (kpcb == NULL) {
                PyErr_NoMemory();
                goto error;
            }
            kpcb->kpcb = &kp[j];
            if (j == 0) {
                kpcb->has_buf = 1;
                kpcb->buf = pcb;
            }
            else {
                kpcb->has_buf = 0;
                kpcb->buf = NULL;
            }
            SLIST_INSERT_HEAD(&kpcbhead, kpcb, kpcbs);
        }
    }
    else {
        free(pcb);
    }

    return 0;

error:
    if (pcb != NULL)
        free(pcb);
    return -1;
}


// Collect open file and connections.
static int
psutil_get_info(char *kind) {
    if (strcmp(kind, "inet") == 0) {
        if (psutil_get_sockets("net.inet.tcp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet.udp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.tcp6.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.udp6.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "inet4") == 0) {
        if (psutil_get_sockets("net.inet.tcp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet.udp.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "inet6") == 0) {
        if (psutil_get_sockets("net.inet6.tcp6.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.udp6.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "tcp") == 0) {
        if (psutil_get_sockets("net.inet.tcp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.tcp6.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "tcp4") == 0) {
        if (psutil_get_sockets("net.inet.tcp.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "tcp6") == 0) {
        if (psutil_get_sockets("net.inet6.tcp6.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "udp") == 0) {
        if (psutil_get_sockets("net.inet.udp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.udp6.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "udp4") == 0) {
        if (psutil_get_sockets("net.inet.udp.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "udp6") == 0) {
        if (psutil_get_sockets("net.inet6.udp6.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "unix") == 0) {
        if (psutil_get_sockets("net.local.stream.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.local.seqpacket.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.local.dgram.pcblist") != 0)
            return -1;
    }
    else if (strcmp(kind, "all") == 0) {
        if (psutil_get_sockets("net.inet.tcp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet.udp.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.tcp6.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.inet6.udp6.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.local.stream.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.local.seqpacket.pcblist") != 0)
            return -1;
        if (psutil_get_sockets("net.local.dgram.pcblist") != 0)
            return -1;
    }
    else {
        PyErr_SetString(PyExc_ValueError, "invalid kind value");
        return -1;
    }
    return 0;
}


/*
 * Return system-wide connections (unless a pid != -1 is passed).
 */
PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    char laddr[PATH_MAX];
    char raddr[PATH_MAX];
    char *kind;
    int32_t lport;
    int32_t rport;
    int32_t status;
    pid_t pid;
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "s", &pid, &kind)) {
        goto error;
    }

    psutil_kiflist_init();
    psutil_kpcblist_init();

    if (psutil_get_files() != 0)
        goto error;
    if (psutil_get_info(kind) != 0)
        goto error;

    struct kif *k;
    SLIST_FOREACH(k, &kihead, kifs) {
        struct kpcb *kp;
        if ((pid != -1) && (k->kif->ki_pid != (unsigned int)pid))
            continue;
        SLIST_FOREACH(kp, &kpcbhead, kpcbs) {
            if (k->kif->ki_fdata != kp->kpcb->ki_sockaddr)
                continue;

            // IPv4 or IPv6
            if ((kp->kpcb->ki_family == AF_INET)
                || (kp->kpcb->ki_family == AF_INET6))
            {
                if (kp->kpcb->ki_family == AF_INET) {
                    // IPv4
                    struct sockaddr_in *sin_src = (struct sockaddr_in *)&kp
                                                      ->kpcb->ki_src;
                    struct sockaddr_in *sin_dst = (struct sockaddr_in *)&kp
                                                      ->kpcb->ki_dst;
                    // source addr and port
                    inet_ntop(
                        AF_INET, &sin_src->sin_addr, laddr, sizeof(laddr)
                    );
                    lport = ntohs(sin_src->sin_port);
                    // remote addr and port
                    inet_ntop(
                        AF_INET, &sin_dst->sin_addr, raddr, sizeof(raddr)
                    );
                    rport = ntohs(sin_dst->sin_port);
                }
                else {
                    // IPv6
                    struct sockaddr_in6 *sin6_src = (struct sockaddr_in6 *)&kp
                                                        ->kpcb->ki_src;
                    struct sockaddr_in6 *sin6_dst = (struct sockaddr_in6 *)&kp
                                                        ->kpcb->ki_dst;
                    // local addr and port
                    inet_ntop(
                        AF_INET6, &sin6_src->sin6_addr, laddr, sizeof(laddr)
                    );
                    lport = ntohs(sin6_src->sin6_port);
                    // remote addr and port
                    inet_ntop(
                        AF_INET6, &sin6_dst->sin6_addr, raddr, sizeof(raddr)
                    );
                    rport = ntohs(sin6_dst->sin6_port);
                }

                // status
                if (kp->kpcb->ki_type == SOCK_STREAM)
                    status = kp->kpcb->ki_tstate;
                else
                    status = PSUTIL_CONN_NONE;

                // build addr tuple
                py_laddr = Py_BuildValue("(si)", laddr, lport);
                if (!py_laddr)
                    goto error;
                if (rport != 0)
                    py_raddr = Py_BuildValue("(si)", raddr, rport);
                else
                    py_raddr = Py_BuildValue("()");
                if (!py_raddr)
                    goto error;
            }
            else if (kp->kpcb->ki_family == AF_UNIX) {
                // UNIX sockets
                struct sockaddr_un *sun_src = (struct sockaddr_un *)&kp->kpcb
                                                  ->ki_src;
                struct sockaddr_un *sun_dst = (struct sockaddr_un *)&kp->kpcb
                                                  ->ki_dst;
                str_copy(laddr, sizeof(sun_src->sun_path), sun_src->sun_path);
                str_copy(raddr, sizeof(sun_dst->sun_path), sun_dst->sun_path);
                status = PSUTIL_CONN_NONE;
                py_laddr = PyUnicode_DecodeFSDefault(laddr);
                if (!py_laddr)
                    goto error;
                py_raddr = PyUnicode_DecodeFSDefault(raddr);
                if (!py_raddr)
                    goto error;
            }
            else {
                continue;
            }

            // append tuple to list
            py_tuple = Py_BuildValue(
                "(iiiOOii)",
                k->kif->ki_fd,
                kp->kpcb->ki_family,
                kp->kpcb->ki_type,
                py_laddr,
                py_raddr,
                status,
                k->kif->ki_pid
            );
            if (!py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_DECREF(py_laddr);
            Py_DECREF(py_raddr);
            Py_DECREF(py_tuple);
        }
    }

    psutil_kiflist_clear();
    psutil_kpcblist_clear();
    return py_retlist;

error:
    psutil_kiflist_clear();
    psutil_kpcblist_clear();
    Py_DECREF(py_retlist);
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    return NULL;
}
