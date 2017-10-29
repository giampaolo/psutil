/*
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/* Baded on code from lsof:
 * http://www.ibm.com/developerworks/aix/library/au-lsof.html
 * - dialects/aix/dproc.c:gather_proc_info
 * - lib/prfp.c:process_file
 * - dialects/aix/dsock.c:process_socket
 * - dialects/aix/dproc.c:get_kernel_access
*/

#include <Python.h>
#include <stdlib.h>
#include <fcntl.h>
#define _KERNEL
#include <sys/file.h>
#undef _KERNEL
#include <sys/types.h>
#include <sys/core.h>
#include <sys/domain.h>
#include <sys/un.h>
#include <netinet/in_pcb.h>
#include <arpa/inet.h>

#include "../../_psutil_common.h"
#include "net_kernel_structs.h"
#include "net_connections.h"
#include "common.h"

#define NO_SOCKET       (PyObject *)(-1)

static int
read_unp_addr(
    int Kd,
    KA_T unp_addr,
    char *buf,
    size_t buflen
) {
    struct sockaddr_un *ua = (struct sockaddr_un *)NULL;
    struct sockaddr_un un;
    struct mbuf64 mb;
    int uo;

    if (psutil_kread(Kd, unp_addr, (char *)&mb, sizeof(mb))) {
        return 1;
    }

    uo = (int)(mb.m_hdr.mh_data - unp_addr);
    if ((uo + sizeof(struct sockaddr)) <= sizeof(mb))
        ua = (struct sockaddr_un *)((char *)&mb + uo);
    else {
        if (psutil_kread(Kd, (KA_T)mb.m_hdr.mh_data,
                         (char *)&un, sizeof(un))) {
            return 1;
        }
        ua = &un;
    }
    if (ua && ua->sun_path[0]) {
        if (mb.m_len > sizeof(struct sockaddr_un))
            mb.m_len = sizeof(struct sockaddr_un);
        *((char *)ua + mb.m_len - 1) = '\0';
        snprintf(buf, buflen, "%s", ua->sun_path);
    }
    return 0;
}

static PyObject *
process_file(int Kd, pid32_t pid, int fd, KA_T fp) {
    struct file64 f;
    struct socket64 s;
    struct protosw64 p;
    struct domain d;
    struct inpcb64 inp;
    int fam;
    struct tcpcb64 t;
    int state = PSUTIL_CONN_NONE;
    unsigned char *laddr = (unsigned char *)NULL;
    unsigned char *raddr = (unsigned char *)NULL;
    int rport, lport;
    char laddr_str[INET6_ADDRSTRLEN];
    char raddr_str[INET6_ADDRSTRLEN];
    struct unpcb64 unp;
    char unix_laddr_str[PATH_MAX] = { 0 };
    char unix_raddr_str[PATH_MAX] = { 0 };

    /* Read file structure */
    if (psutil_kread(Kd, fp, (char *)&f, sizeof(f))) {
        return NULL;
    }
    if (!f.f_count || f.f_type != DTYPE_SOCKET) {
        return NO_SOCKET;
    }

    if (psutil_kread(Kd, (KA_T) f.f_data, (char *) &s, sizeof(s))) {
        return NULL;
    }

    if (!s.so_type) {
        return NO_SOCKET;
    }

    if (!s.so_proto) {
        PyErr_SetString(PyExc_RuntimeError, "invalid socket protocol handle");
        return NULL;
    }
    if (psutil_kread(Kd, (KA_T)s.so_proto, (char *)&p, sizeof(p))) {
        return NULL;
    }

    if (!p.pr_domain) {
        PyErr_SetString(PyExc_RuntimeError, "invalid socket protocol domain");
        return NULL;
    }
    if (psutil_kread(Kd, (KA_T)p.pr_domain, (char *)&d, sizeof(d))) {
        return NULL;
    }

    fam = d.dom_family;
    if (fam == AF_INET || fam == AF_INET6) {
        /* Read protocol control block */
        if (!s.so_pcb) {
            PyErr_SetString(PyExc_RuntimeError, "invalid socket PCB");
            return NULL;
        }
        if (psutil_kread(Kd, (KA_T) s.so_pcb, (char *) &inp, sizeof(inp))) {
            return NULL;
        }

        if (p.pr_protocol == IPPROTO_TCP) {
            /* If this is a TCP socket, read its control block */
            if (inp.inp_ppcb
                &&  !psutil_kread(Kd, (KA_T)inp.inp_ppcb,
                                  (char *)&t, sizeof(t)))
                state = t.t_state;
        }

        if (fam == AF_INET6) {
            laddr = (unsigned char *)&inp.inp_laddr6;
            if (!IN6_IS_ADDR_UNSPECIFIED(&inp.inp_faddr6)) {
                raddr = (unsigned char *)&inp.inp_faddr6;
                rport = (int)ntohs(inp.inp_fport);
            }
        }
        if (fam == AF_INET) {
            laddr = (unsigned char *)&inp.inp_laddr;
            if (inp.inp_faddr.s_addr != INADDR_ANY || inp.inp_fport != 0) {
                raddr =  (unsigned char *)&inp.inp_faddr;
                rport = (int)ntohs(inp.inp_fport);
            }
        }
        lport = (int)ntohs(inp.inp_lport);

        inet_ntop(fam, laddr, laddr_str, sizeof(laddr_str));

        if (raddr != NULL) {
            inet_ntop(fam, raddr, raddr_str, sizeof(raddr_str));
            return Py_BuildValue("(iii(si)(si)ii)", fd, fam,
                                 s.so_type, laddr_str, lport, raddr_str,
                                 rport, state, pid);
        }
        else {
            return Py_BuildValue("(iii(si)()ii)", fd, fam,
                                 s.so_type, laddr_str, lport, state,
                                 pid);
        }
    }


    if (fam == AF_UNIX) {
        if (psutil_kread(Kd, (KA_T) s.so_pcb, (char *)&unp, sizeof(unp))) {
            return NULL;
        }
        if ((KA_T) f.f_data != (KA_T) unp.unp_socket) {
            PyErr_SetString(PyExc_RuntimeError, "unp_socket mismatch");
            return NULL;
        }

        if (unp.unp_addr) {
            if (read_unp_addr(Kd, unp.unp_addr, unix_laddr_str,
                              sizeof(unix_laddr_str))) {
                return NULL;
            }
        }

        if (unp.unp_conn) {
            if (psutil_kread(Kd, (KA_T) unp.unp_conn, (char *)&unp,
                sizeof(unp))) {
                return NULL;
            }
            if (read_unp_addr(Kd, unp.unp_addr, unix_raddr_str,
                              sizeof(unix_raddr_str))) {
                return NULL;
            }
        }

        return Py_BuildValue("(iiissii)", fd, d.dom_family,
                 s.so_type, unix_laddr_str, unix_raddr_str, PSUTIL_CONN_NONE,
                 pid);
    }
    return NO_SOCKET;
}

PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    KA_T fp;
    int Kd = -1;
    int i, np;
    struct procentry64 *p;
    struct fdsinfo64 *fds = (struct fdsinfo64 *)NULL;
    pid32_t requested_pid;
    pid32_t pid;
    struct procentry64 *processes = (struct procentry64 *)NULL;
                    /* the process table */

    if (py_retlist == NULL)
        goto error;
    if (! PyArg_ParseTuple(args, "i", &requested_pid))
        goto error;

    Kd = open(KMEM, O_RDONLY, 0);
    if (Kd < 0) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, KMEM);
        goto error;
    }

    processes = psutil_read_process_table(&np);
    if (!processes)
        goto error;

    /* Loop through processes */
    for (p = processes; np > 0; np--, p++) {
        pid = p->pi_pid;
        if (requested_pid != -1 && requested_pid != pid)
            continue;
        if (p->pi_state == 0 || p->pi_state == SZOMB)
            continue;

        if (!fds) {
            fds = (struct fdsinfo64 *)malloc((size_t)FDSINFOSIZE);
            if (!fds) {
                PyErr_NoMemory();
                goto error;
            }
        }
        if (getprocs64((struct procentry64 *)NULL, PROCSIZE, fds, FDSINFOSIZE,
              &pid, 1)
        != 1)
            continue;

        /* loop over file descriptors */
        for (i = 0; i < p->pi_maxofile; i++) {
            fp = (KA_T)fds->pi_ufd[i].fp;
            if (fp) {
                py_tuple = process_file(Kd, p->pi_pid, i, fp);
                if (py_tuple == NULL)
                    goto error;
                if (py_tuple != NO_SOCKET) {
                    if (PyList_Append(py_retlist, py_tuple))
                        goto error;
                    Py_DECREF(py_tuple);
                }
            }
        }
    }
    close(Kd);
    free(processes);
    if (fds != NULL)
        free(fds);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (Kd > 0)
        close(Kd);
    if (processes != NULL)
        free(processes);
    if (fds != NULL)
        free(fds);
    return NULL;
}
