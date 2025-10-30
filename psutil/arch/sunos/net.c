/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <inet/mib2.h>
#include <kstat.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stropts.h>
#include <sys/fcntl.h>
#include <sys/types.h>
#include <sys/socket.h>
#include <sys/sockio.h>
#include <netinet/in.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <sys/stropts.h>
#include <sys/tihdr.h>
#include <net/if.h>
#include <fcntl.h>

#include "../../arch/all/init.h"


PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    kstat_ctl_t *kc = NULL;
    kstat_t *ksp;
    kstat_named_t *rbytes, *wbytes, *rpkts, *wpkts, *ierrs, *oerrs;
    int ret;
    int sock = -1;
    struct lifreq ifr;

    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;

    if (py_retdict == NULL)
        return NULL;
    kc = kstat_open();
    if (kc == NULL)
        goto error;

    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1) {
        psutil_oserror();
        goto error;
    }

    ksp = kc->kc_chain;
    while (ksp != NULL) {
        if (ksp->ks_type != KSTAT_TYPE_NAMED)
            goto next;
        if (strcmp(ksp->ks_class, "net") != 0)
            goto next;
        // skip 'lo' (localhost) because it doesn't have the statistics we need
        // and it makes kstat_data_lookup() fail
        if (strcmp(ksp->ks_module, "lo") == 0)
            goto next;

        // check if this is a network interface by sending a ioctl
        str_copy(ifr.lifr_name, sizeof(ifr.lifr_name), ksp->ks_name);
        ret = ioctl(sock, SIOCGLIFFLAGS, &ifr);
        if (ret == -1)
            goto next;

        if (kstat_read(kc, ksp, NULL) == -1) {
            errno = 0;
            goto next;
        }

        rbytes = (kstat_named_t *)kstat_data_lookup(ksp, "rbytes");
        wbytes = (kstat_named_t *)kstat_data_lookup(ksp, "obytes");
        rpkts = (kstat_named_t *)kstat_data_lookup(ksp, "ipackets");
        wpkts = (kstat_named_t *)kstat_data_lookup(ksp, "opackets");
        ierrs = (kstat_named_t *)kstat_data_lookup(ksp, "ierrors");
        oerrs = (kstat_named_t *)kstat_data_lookup(ksp, "oerrors");

        if ((rbytes == NULL) || (wbytes == NULL) || (rpkts == NULL)
            || (wpkts == NULL) || (ierrs == NULL) || (oerrs == NULL))
        {
            psutil_runtime_error("kstat_data_lookup() failed");
            goto error;
        }

        if (rbytes->data_type == KSTAT_DATA_UINT64) {
            py_ifc_info = Py_BuildValue(
                "(KKKKIIii)",
                wbytes->value.ui64,
                rbytes->value.ui64,
                wpkts->value.ui64,
                rpkts->value.ui64,
                ierrs->value.ui32,
                oerrs->value.ui32,
                0,  // dropin not supported
                0  // dropout not supported
            );
        }
        else {
            py_ifc_info = Py_BuildValue(
                "(IIIIIIii)",
                wbytes->value.ui32,
                rbytes->value.ui32,
                wpkts->value.ui32,
                rpkts->value.ui32,
                ierrs->value.ui32,
                oerrs->value.ui32,
                0,  // dropin not supported
                0  // dropout not supported
            );
        }
        if (!py_ifc_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, ksp->ks_name, py_ifc_info))
            goto error;
        Py_CLEAR(py_ifc_info);
        goto next;

    next:
        ksp = ksp->ks_next;
    }

    kstat_close(kc);
    close(sock);
    return py_retdict;

error:
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    if (kc != NULL)
        kstat_close(kc);
    if (sock != -1) {
        close(sock);
    }
    return NULL;
}


// Return stats about a particular network interface. Refs:
// * https://github.com/dpaleino/wicd/blob/master/wicd/backends/be-ioctl.py
// * http://www.i-scream.org/libstatgrab/
PyObject *
psutil_net_if_stats(PyObject *self, PyObject *args) {
    kstat_ctl_t *kc = NULL;
    kstat_t *ksp;
    kstat_named_t *knp;
    int ret;
    int sock = -1;
    int duplex;
    int speed;

    PyObject *py_retdict = PyDict_New();
    PyObject *py_ifc_info = NULL;
    PyObject *py_is_up = NULL;

    if (py_retdict == NULL)
        return NULL;
    kc = kstat_open();
    if (kc == NULL)
        goto error;
    sock = socket(AF_INET, SOCK_DGRAM, 0);
    if (sock == -1) {
        psutil_oserror();
        goto error;
    }

    for (ksp = kc->kc_chain; ksp; ksp = ksp->ks_next) {
        if (strcmp(ksp->ks_class, "net") == 0) {
            struct lifreq ifr;

            kstat_read(kc, ksp, NULL);
            if (ksp->ks_type != KSTAT_TYPE_NAMED)
                continue;
            if (strcmp(ksp->ks_class, "net") != 0)
                continue;

            str_copy(ifr.lifr_name, sizeof(ifr.lifr_name), ksp->ks_name);
            ret = ioctl(sock, SIOCGLIFFLAGS, &ifr);
            if (ret == -1)
                continue;  // not a network interface

            // is up?
            if ((ifr.lifr_flags & IFF_UP) != 0) {
                if ((knp = kstat_data_lookup(ksp, "link_up")) != NULL) {
                    if (knp->value.ui32 != 0u)
                        py_is_up = Py_True;
                    else
                        py_is_up = Py_False;
                }
                else {
                    py_is_up = Py_True;
                }
            }
            else {
                py_is_up = Py_False;
            }
            Py_INCREF(py_is_up);

            // duplex
            duplex = 0;  // unknown
            if ((knp = kstat_data_lookup(ksp, "link_duplex")) != NULL) {
                if (knp->value.ui32 == 1)
                    duplex = 1;  // half
                else if (knp->value.ui32 == 2)
                    duplex = 2;  // full
            }

            // speed
            if ((knp = kstat_data_lookup(ksp, "ifspeed")) != NULL)
                // expressed in bits per sec, we want mega bits per sec
                speed = (int)knp->value.ui64 / 1000000;
            else
                speed = 0;

            // mtu
            ret = ioctl(sock, SIOCGLIFMTU, &ifr);
            if (ret == -1)
                goto error;

            py_ifc_info = Py_BuildValue(
                "(Oiii)", py_is_up, duplex, speed, ifr.lifr_mtu
            );
            if (!py_ifc_info)
                goto error;
            if (PyDict_SetItemString(py_retdict, ksp->ks_name, py_ifc_info))
                goto error;
            Py_CLEAR(py_ifc_info);
        }
    }

    close(sock);
    kstat_close(kc);
    return py_retdict;

error:
    Py_XDECREF(py_is_up);
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    if (sock != -1)
        close(sock);
    if (kc != NULL)
        kstat_close(kc);
    psutil_oserror();
    return NULL;
}


/*
 * Return TCP and UDP connections opened by process.
 * UNIX sockets are excluded.
 *
 * Thanks to:
 * https://github.com/DavidGriffith/finx/blob/master/
 *     nxsensor-3.5.0-1/src/sysdeps/solaris.c
 * ...and:
 * https://hg.java.net/hg/solaris~on-src/file/tip/usr/src/cmd/
 *     cmd-inet/usr.bin/netstat/netstat.c
 */
PyObject *
psutil_net_connections(PyObject *self, PyObject *args) {
    long pid;
    int sd = 0;
    mib2_tcpConnEntry_t tp;
    mib2_udpEntry_t ude;
#if defined(AF_INET6)
    mib2_tcp6ConnEntry_t tp6;
    mib2_udp6Entry_t ude6;
#endif
    char buf[512];
    int i, flags, getcode, num_ent, state, ret;
    char lip[INET6_ADDRSTRLEN], rip[INET6_ADDRSTRLEN];
    int lport, rport;
    int processed_pid;
    int databuf_init = 0;
    struct strbuf ctlbuf, databuf;
    struct T_optmgmt_req tor = {0};
    struct T_optmgmt_ack toa = {0};
    struct T_error_ack tea = {0};
    struct opthdr mibhdr = {0};

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, "l", &pid))
        goto error;

    sd = open("/dev/arp", O_RDWR);
    if (sd == -1) {
        PyErr_SetFromErrnoWithFilename(PyExc_OSError, "/dev/arp");
        goto error;
    }

    ret = ioctl(sd, I_PUSH, "tcp");
    if (ret == -1) {
        psutil_oserror();
        goto error;
    }
    ret = ioctl(sd, I_PUSH, "udp");
    if (ret == -1) {
        psutil_oserror();
        goto error;
    }
    //
    // OK, this mess is basically copied and pasted from nxsensor project
    // which copied and pasted it from netstat source code, mibget()
    // function.  Also see:
    // http://stackoverflow.com/questions/8723598/
    tor.PRIM_type = T_SVR4_OPTMGMT_REQ;
    tor.OPT_offset = sizeof(struct T_optmgmt_req);
    tor.OPT_length = sizeof(struct opthdr);
    tor.MGMT_flags = T_CURRENT;
    mibhdr.level = MIB2_IP;
    mibhdr.name = 0;

    mibhdr.len = 1;
    memcpy(buf, &tor, sizeof tor);
    memcpy(buf + tor.OPT_offset, &mibhdr, sizeof mibhdr);

    ctlbuf.buf = buf;
    ctlbuf.len = tor.OPT_offset + tor.OPT_length;
    flags = 0;  // request to be sent in non-priority

    if (putmsg(sd, &ctlbuf, (struct strbuf *)0, flags) == -1) {
        psutil_oserror();
        goto error;
    }

    ctlbuf.maxlen = sizeof(buf);
    for (;;) {
        flags = 0;
        getcode = getmsg(sd, &ctlbuf, (struct strbuf *)0, &flags);
        memcpy(&toa, buf, sizeof toa);
        memcpy(&tea, buf, sizeof tea);

        if (getcode != MOREDATA
            || ctlbuf.len < (int)sizeof(struct T_optmgmt_ack)
            || toa.PRIM_type != T_OPTMGMT_ACK || toa.MGMT_flags != T_SUCCESS)
        {
            break;
        }
        if (ctlbuf.len >= (int)sizeof(struct T_error_ack)
            && tea.PRIM_type == T_ERROR_ACK)
        {
            psutil_runtime_error("ERROR_ACK");
            goto error;
        }
        if (getcode == 0 && ctlbuf.len >= (int)sizeof(struct T_optmgmt_ack)
            && toa.PRIM_type == T_OPTMGMT_ACK && toa.MGMT_flags == T_SUCCESS)
        {
            psutil_runtime_error("ERROR_T_OPTMGMT_ACK");
            goto error;
        }

        memset(&mibhdr, 0x0, sizeof(mibhdr));
        memcpy(&mibhdr, buf + toa.OPT_offset, toa.OPT_length);

        databuf.maxlen = mibhdr.len;
        databuf.len = 0;
        databuf.buf = (char *)malloc((int)mibhdr.len);
        if (!databuf.buf) {
            PyErr_NoMemory();
            goto error;
        }
        databuf_init = 1;

        flags = 0;
        getcode = getmsg(sd, (struct strbuf *)0, &databuf, &flags);
        if (getcode < 0) {
            psutil_oserror();
            goto error;
        }

        // TCPv4
        if (mibhdr.level == MIB2_TCP && mibhdr.name == MIB2_TCP_13) {
            num_ent = mibhdr.len / sizeof(mib2_tcpConnEntry_t);
            for (i = 0; i < num_ent; i++) {
                memcpy(&tp, databuf.buf + i * sizeof tp, sizeof tp);
                processed_pid = tp.tcpConnCreationProcess;
                if (pid != -1 && processed_pid != pid)
                    continue;
                // construct local/remote addresses
                inet_ntop(AF_INET, &tp.tcpConnLocalAddress, lip, sizeof(lip));
                inet_ntop(AF_INET, &tp.tcpConnRemAddress, rip, sizeof(rip));
                lport = tp.tcpConnLocalPort;
                rport = tp.tcpConnRemPort;

                // construct python tuple/list
                py_laddr = Py_BuildValue("(si)", lip, lport);
                if (!py_laddr)
                    goto error;
                if (rport != 0)
                    py_raddr = Py_BuildValue("(si)", rip, rport);
                else {
                    py_raddr = Py_BuildValue("()");
                }
                if (!py_raddr)
                    goto error;
                state = tp.tcpConnEntryInfo.ce_state;

                // add item
                py_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET,
                    SOCK_STREAM,
                    py_laddr,
                    py_raddr,
                    state,
                    processed_pid
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
            }
        }
#if defined(AF_INET6)
        // TCPv6
        else if (mibhdr.level == MIB2_TCP6 && mibhdr.name == MIB2_TCP6_CONN) {
            num_ent = mibhdr.len / sizeof(mib2_tcp6ConnEntry_t);

            for (i = 0; i < num_ent; i++) {
                memcpy(&tp6, databuf.buf + i * sizeof tp6, sizeof tp6);
                processed_pid = tp6.tcp6ConnCreationProcess;
                if (pid != -1 && processed_pid != pid)
                    continue;
                // construct local/remote addresses
                inet_ntop(
                    AF_INET6, &tp6.tcp6ConnLocalAddress, lip, sizeof(lip)
                );
                inet_ntop(AF_INET6, &tp6.tcp6ConnRemAddress, rip, sizeof(rip));
                lport = tp6.tcp6ConnLocalPort;
                rport = tp6.tcp6ConnRemPort;

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
                state = tp6.tcp6ConnEntryInfo.ce_state;

                // add item
                py_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET6,
                    SOCK_STREAM,
                    py_laddr,
                    py_raddr,
                    state,
                    processed_pid
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
            }
        }
#endif
        // UDPv4
        else if (mibhdr.level == MIB2_UDP && mibhdr.name == MIB2_UDP_ENTRY) {
            num_ent = mibhdr.len / sizeof(mib2_udpEntry_t);
            assert(num_ent * sizeof(mib2_udpEntry_t) == mibhdr.len);
            for (i = 0; i < num_ent; i++) {
                memcpy(&ude, databuf.buf + i * sizeof ude, sizeof ude);
                processed_pid = ude.udpCreationProcess;
                if (pid != -1 && processed_pid != pid)
                    continue;
                // XXX Very ugly hack! It seems we get here only the first
                // time we bump into a UDPv4 socket.  PID is a very high
                // number (clearly impossible) and the address does not
                // belong to any valid interface.  Not sure what else
                // to do other than skipping.
                if (processed_pid > 131072)
                    continue;
                inet_ntop(AF_INET, &ude.udpLocalAddress, lip, sizeof(lip));
                lport = ude.udpLocalPort;
                py_laddr = Py_BuildValue("(si)", lip, lport);
                if (!py_laddr)
                    goto error;
                py_raddr = Py_BuildValue("()");
                if (!py_raddr)
                    goto error;
                py_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET,
                    SOCK_DGRAM,
                    py_laddr,
                    py_raddr,
                    PSUTIL_CONN_NONE,
                    processed_pid
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
            }
        }
#if defined(AF_INET6)
        // UDPv6
        else if (mibhdr.level == MIB2_UDP6 || mibhdr.level == MIB2_UDP6_ENTRY)
        {
            num_ent = mibhdr.len / sizeof(mib2_udp6Entry_t);
            for (i = 0; i < num_ent; i++) {
                memcpy(&ude6, databuf.buf + i * sizeof ude6, sizeof ude6);
                processed_pid = ude6.udp6CreationProcess;
                if (pid != -1 && processed_pid != pid)
                    continue;
                inet_ntop(AF_INET6, &ude6.udp6LocalAddress, lip, sizeof(lip));
                lport = ude6.udp6LocalPort;
                py_laddr = Py_BuildValue("(si)", lip, lport);
                if (!py_laddr)
                    goto error;
                py_raddr = Py_BuildValue("()");
                if (!py_raddr)
                    goto error;
                py_tuple = Py_BuildValue(
                    "(iiiNNiI)",
                    -1,
                    AF_INET6,
                    SOCK_DGRAM,
                    py_laddr,
                    py_raddr,
                    PSUTIL_CONN_NONE,
                    processed_pid
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
            }
        }
#endif
        free(databuf.buf);
    }

    close(sd);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    Py_DECREF(py_retlist);
    if (databuf_init == 1)
        free(databuf.buf);
    if (sd != 0)
        close(sd);
    return NULL;
}
