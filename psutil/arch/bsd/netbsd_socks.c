/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * Copyright (c) 2015, Ryo ONODERA.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */
#include <Python.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/sysctl.h>
#include <sys/socket.h>
#include <sys/types.h>
#include <netinet/in.h>
#include <string.h>
#include <sys/cdefs.h>
#include <arpa/inet.h>
#include <sys/queue.h>
#include <sys/un.h>
#include <sys/file.h>

// a signaler for connections without an actual status
int PSUTIL_CONN_NONE = 128;

// Address family filter
enum af_filter {
    INET,
    INET4,
    INET6,
    TCP,
    TCP4,
    TCP6,
    UDP,
    UDP4,
    UDP6,
    UNIX,
    ALL,
};

// kinfo_file results
struct kif {
    SLIST_ENTRY(kif) kifs;
    struct kinfo_file *kif;
};

// kinfo_file results list
SLIST_HEAD(kifhead, kif) kihead = SLIST_HEAD_INITIALIZER(kihead);


// kinfo_pcb results
struct kpcb {
    SLIST_ENTRY(kpcb) kpcbs;
    struct kinfo_pcb *kpcb;
};

// kinfo_pcb results list
SLIST_HEAD(kpcbhead, kpcb) kpcbhead = SLIST_HEAD_INITIALIZER(kpcbhead);

static void kiflist_init(void);
static void kiflist_clear(void);
static void kpcblist_init(void);
static void kpcblist_clear(void);
static int get_files(void);
static int get_sockets(const char *name);
static void get_info(int aff);

// Initialize kinfo_file results list
static void
kiflist_init(void) {
    SLIST_INIT(&kihead);
    return;
}

// Clear kinfo_file results list
static void
kiflist_clear(void) {
     while (!SLIST_EMPTY(&kihead)) {
             SLIST_REMOVE_HEAD(&kihead, kifs);
     }

    return;
}

// Initialize kinof_pcb result list
static void
kpcblist_init(void) {
    SLIST_INIT(&kpcbhead);
    return;
}

// Clear kinof_pcb result list
static void
kpcblist_clear(void) {
     while (!SLIST_EMPTY(&kpcbhead)) {
             SLIST_REMOVE_HEAD(&kpcbhead, kpcbs);
     }

    return;
}


// Get all open files including socket
static int
get_files(void) {
    size_t len;
    int mib[6];
    char *buf;
    off_t offset;
    int j;

    mib[0] = CTL_KERN;
    mib[1] = KERN_FILE2;
    mib[2] = KERN_FILE_BYFILE;
    mib[3] = 0;
    mib[4] = sizeof(struct kinfo_file);
    mib[5] = 0;

    if (sysctl(mib, 6, NULL, &len, NULL, 0) == -1)
        return -1;
    offset = len % sizeof(off_t);
    mib[5] = len / sizeof(struct kinfo_file);
    if ((buf = malloc(len + offset)) == NULL)
        return -1;
    if (sysctl(mib, 6, buf + offset, &len, NULL, 0) == -1) {
        free(buf);
        return -1;
    }

    len /= sizeof(struct kinfo_file);
    struct kinfo_file *ki = (struct kinfo_file *)(buf + offset);

    for (j = 0; j < len; j++) {
        struct kif *kif = malloc(sizeof(struct kif));
        kif->kif = &ki[j];
        SLIST_INSERT_HEAD(&kihead, kif, kifs);
    }

#if 0
    // debug
    struct kif *k;
    SLIST_FOREACH(k, &kihead, kifs) {
            printf("%d\n", k->kif->ki_pid);
    }
#endif

    return 0;
}

// Get open sockets
static int
get_sockets(const char *name) {
    size_t namelen;
    int mib[8];
    int ret, j;
    struct kinfo_pcb *pcb;
    size_t len;

    memset(mib, 0, sizeof(mib));

    if (sysctlnametomib(name, mib, &namelen) == -1)
        return -1;

    if (sysctl(mib, __arraycount(mib), NULL, &len, NULL, 0) == -1)
        return -1;

    if ((pcb = malloc(len)) == NULL) {
        return -1;
    }
    memset(pcb, 0, len);

    mib[6] = sizeof(*pcb);
    mib[7] = len / sizeof(*pcb);

    if (sysctl(mib, __arraycount(mib), pcb, &len, NULL, 0) == -1) {
        free(pcb);
        return -1;
    }

    len /= sizeof(struct kinfo_pcb);
    struct kinfo_pcb *kp = (struct kinfo_pcb *)pcb;

    for (j = 0; j < len; j++) {
        struct kpcb *kpcb = malloc(sizeof(struct kpcb));
        kpcb->kpcb = &kp[j];
        SLIST_INSERT_HEAD(&kpcbhead, kpcb, kpcbs);
    }

#if 0
    // debug
    struct kif *k;
    struct kpcb *k;
    SLIST_FOREACH(k, &kpcbhead, kpcbs) {
            printf("ki_type: %d\n", k->kpcb->ki_type);
            printf("ki_family: %d\n", k->kpcb->ki_family);
    }
#endif

    return 0;
}


// Collect connections by PID
PyObject *
psutil_proc_connections(PyObject *self, PyObject *args) {
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;
    pid_t pid;

    if (py_retlist == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;

    kiflist_init();
    kpcblist_init();
    get_info(ALL);

    struct kif *k;
    SLIST_FOREACH(k, &kihead, kifs) {
        struct kpcb *kp;
        if (k->kif->ki_pid == pid) {
        SLIST_FOREACH(kp, &kpcbhead, kpcbs) {
            if (k->kif->ki_fdata == kp->kpcb->ki_sockaddr) {
                pid_t pid;
                int32_t fd;
                int32_t family;
                int32_t type;
                char laddr[PATH_MAX];
                int32_t lport;
                char raddr[PATH_MAX];
                int32_t rport;
                int32_t status;

                pid = k->kif->ki_pid;
                fd = k->kif->ki_fd;
                family = kp->kpcb->ki_family;
                type = kp->kpcb->ki_type;

                if (kp->kpcb->ki_family == AF_INET) {
                    // IPv4
                    struct sockaddr_in *sin_src =
                        (struct sockaddr_in *)&kp->kpcb->ki_src;
                    struct sockaddr_in *sin_dst =
                        (struct sockaddr_in *)&kp->kpcb->ki_dst;
                    // source addr
                    if (inet_ntop(AF_INET, &sin_src->sin_addr, laddr,
                        sizeof(laddr)) != NULL)
                    lport = ntohs(sin_src->sin_port);
                    py_laddr = Py_BuildValue("(si)", laddr, lport);
                    if (!py_laddr)
                        goto error;
                    // remote addr
                    if (inet_ntop(AF_INET, &sin_dst->sin_addr, raddr,
                                  sizeof(raddr)) != NULL)
                        rport = ntohs(sin_dst->sin_port);

                    if (rport != 0)
                        py_raddr = Py_BuildValue("(si)", raddr, rport);
                    else
                        py_raddr = Py_BuildValue("()");
                    if (!py_raddr)
                        goto error;
                    // status
                    if (kp->kpcb->ki_type == SOCK_STREAM)
                        status = kp->kpcb->ki_tstate;
                    else
                        status = PSUTIL_CONN_NONE;
                    // construct python tuple
                    py_tuple = Py_BuildValue("(iiiNNi)", fd, AF_INET,
                                type, py_laddr, py_raddr, status);
                    if (!py_tuple)
                        goto error;
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                }
                else if (kp->kpcb->ki_family == AF_INET6) {
                    // IPv6
                    struct sockaddr_in6 *sin6_src =
                        (struct sockaddr_in6 *)&kp->kpcb->ki_src;
                    struct sockaddr_in6 *sin6_dst =
                        (struct sockaddr_in6 *)&kp->kpcb->ki_dst;
                    // local addr
                    if (inet_ntop(AF_INET6, &sin6_src->sin6_addr, laddr,
                                  sizeof(laddr)) != NULL)
                        lport = ntohs(sin6_src->sin6_port);
                    py_laddr = Py_BuildValue("(si)", laddr, lport);
                    if (!py_laddr)
                        goto error;
                    // remote addr
                    if (inet_ntop(AF_INET6, &sin6_dst->sin6_addr, raddr,
                        sizeof(raddr)) != NULL)
                    rport = ntohs(sin6_dst->sin6_port);
                    if (rport != 0)
                        py_raddr = Py_BuildValue("(si)", raddr, rport);
                    else
                        py_raddr = Py_BuildValue("()");
                    if (!py_raddr)
                        goto error;
                    // status
                    if (kp->kpcb->ki_type == SOCK_STREAM)
                        status = kp->kpcb->ki_tstate;
                    else
                        status = PSUTIL_CONN_NONE;
                    // construct python tuple
                    py_tuple = Py_BuildValue("(iiiNNi)", fd, AF_INET6,
                                type, py_laddr, py_raddr, status);
                    if (!py_tuple)
                        goto error;
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                }
                else if (kp->kpcb->ki_family == AF_UNIX) {
                    // UNIX sockets
                    struct sockaddr_un *sun_src =
                        (struct sockaddr_un *)&kp->kpcb->ki_src;
                    struct sockaddr_un *sun_dst =
                        (struct sockaddr_un *)&kp->kpcb->ki_dst;
                    strcpy(laddr, sun_src->sun_path);
                    strcpy(raddr, sun_dst->sun_path);
                    status = PSUTIL_CONN_NONE;

                    py_tuple = Py_BuildValue("(iiissi)", fd, AF_UNIX,
                                type, laddr, raddr, status);
                    if (!py_tuple)
                        goto error;
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                }
            }
        }}
    }

    kiflist_clear();
    kpcblist_clear();
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    return 0;
}


// Collect open file and connections
static void
get_info(int aff) {
    get_files();

    switch (aff) {
        case INET:
            get_sockets("net.inet.tcp.pcblist");
            get_sockets("net.inet.udp.pcblist");
            get_sockets("net.inet6.tcp6.pcblist");
            get_sockets("net.inet6.udp6.pcblist");
            break;
        case INET4:
            get_sockets("net.inet.tcp.pcblist");
            get_sockets("net.inet.udp.pcblist");
            break;
        case INET6:
            get_sockets("net.inet6.tcp6.pcblist");
            get_sockets("net.inet6.udp6.pcblist");
            break;
        case TCP:
            get_sockets("net.inet.tcp.pcblist");
            get_sockets("net.inet6.tcp6.pcblist");
            break;
        case TCP4:
            get_sockets("net.inet.tcp.pcblist");
            break;
        case TCP6:
            get_sockets("net.inet6.tcp6.pcblist");
            break;
        case UDP:
            get_sockets("net.inet.udp.pcblist");
            get_sockets("net.inet6.udp6.pcblist");
            break;
        case UDP4:
            get_sockets("net.inet.udp.pcblist");
            break;
        case UDP6:
            get_sockets("net.inet6.udp6.pcblist");
            break;
        case UNIX:
            get_sockets("net.local.stream.pcblist");
            get_sockets("net.local.seqpacket.pcblist");
            get_sockets("net.local.dgram.pcblist");
            break;
        case ALL:
            get_sockets("net.inet.tcp.pcblist");
            get_sockets("net.inet.udp.pcblist");
            get_sockets("net.inet6.tcp6.pcblist");
            get_sockets("net.inet6.udp6.pcblist");
            get_sockets("net.local.stream.pcblist");
            get_sockets("net.local.seqpacket.pcblist");
            get_sockets("net.local.dgram.pcblist");
            break;
    }
    return;
}

// Collect system wide connections by address family filter
PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;

    if (py_retlist == NULL)
        return NULL;

    kiflist_init();
    kpcblist_init();
    get_info(ALL);

    struct kif *k;
    SLIST_FOREACH(k, &kihead, kifs) {
        struct kpcb *kp;
        SLIST_FOREACH(kp, &kpcbhead, kpcbs) {
            if (k->kif->ki_fdata == kp->kpcb->ki_sockaddr) {
                pid_t pid;
                int32_t fd;
                int32_t family;
                int32_t type;
                char laddr[PATH_MAX];
                int32_t lport;
                char raddr[PATH_MAX];
                int32_t rport;
                int32_t status;

                pid = k->kif->ki_pid;
                fd = k->kif->ki_fd;
                family = kp->kpcb->ki_family;
                type = kp->kpcb->ki_type;
                if (kp->kpcb->ki_family == AF_INET) {
                    // IPv4
                    struct sockaddr_in *sin_src =
                        (struct sockaddr_in *)&kp->kpcb->ki_src;
                    struct sockaddr_in *sin_dst =
                        (struct sockaddr_in *)&kp->kpcb->ki_dst;
                    // local addr
                    if (inet_ntop(AF_INET, &sin_src->sin_addr, laddr,
                                  sizeof(laddr)) != NULL)
                        lport = ntohs(sin_src->sin_port);
                    py_laddr = Py_BuildValue("(si)", laddr, lport);
                    if (!py_laddr)
                        goto error;
                    // remote addr
                    if (inet_ntop(AF_INET, &sin_dst->sin_addr, raddr,
                                  sizeof(raddr)) != NULL)
                        rport = ntohs(sin_dst->sin_port);
                    if (rport != 0)
                        py_raddr = Py_BuildValue("(si)", raddr, rport);
                    else
                        py_raddr = Py_BuildValue("()");
                    if (!py_raddr)
                        goto error;
                    // status
                    if (kp->kpcb->ki_type == SOCK_STREAM)
                        status = kp->kpcb->ki_tstate;
                    else
                        status = PSUTIL_CONN_NONE;
                    // construct python tuple
                    py_tuple = Py_BuildValue("(iiiNNii)", fd, AF_INET,
                                type, py_laddr, py_raddr, status, pid);
                    if (!py_tuple)
                        goto error;
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                }
                else if (kp->kpcb->ki_family == AF_INET6) {
                    // IPv6
                    struct sockaddr_in6 *sin6_src =
                        (struct sockaddr_in6 *)&kp->kpcb->ki_src;
                    struct sockaddr_in6 *sin6_dst =
                        (struct sockaddr_in6 *)&kp->kpcb->ki_dst;
                    // local addr
                    if (inet_ntop(AF_INET6, &sin6_src->sin6_addr, laddr,
                                  sizeof(laddr)) != NULL)
                        lport = ntohs(sin6_src->sin6_port);
                    py_laddr = Py_BuildValue("(si)", laddr, lport);
                    if (!py_laddr)
                        goto error;
                    // remote addr
                    if (inet_ntop(AF_INET6, &sin6_dst->sin6_addr, raddr,
                                  sizeof(raddr)) != NULL)
                        rport = ntohs(sin6_dst->sin6_port);
                    if (rport != 0)
                        py_raddr = Py_BuildValue("(si)", raddr, rport);
                    else
                        py_raddr = Py_BuildValue("()");
                    if (!py_raddr)
                        goto error;
                    // status
                    if (kp->kpcb->ki_type == SOCK_STREAM)
                        status = kp->kpcb->ki_tstate;
                    else
                        status = PSUTIL_CONN_NONE;
                    // construct python tuple
                    py_tuple = Py_BuildValue("(iiiNNii)", fd, AF_INET6,
                                type, py_laddr, py_raddr, status, pid);
                    if (!py_tuple)
                        goto error;
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                }
                else if (kp->kpcb->ki_family == AF_UNIX) {
                    // UNIX sockets
                    struct sockaddr_un *sun_src =
                        (struct sockaddr_un *)&kp->kpcb->ki_src;
                    struct sockaddr_un *sun_dst =
                        (struct sockaddr_un *)&kp->kpcb->ki_dst;
                    strcpy(laddr, sun_src->sun_path);
                    strcpy(raddr, sun_dst->sun_path);
                    status = PSUTIL_CONN_NONE;
                    py_tuple = Py_BuildValue("(iiissii)", fd, AF_UNIX,
                                type, laddr, raddr, status, pid);
                    if (!py_tuple)
                        goto error;
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                }
            }
        }
    }

    kiflist_clear();
    kpcblist_clear();
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    return 0;
}
