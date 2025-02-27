/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// See:
// * https://github.com/ColinIanKing/forkstat/blob/master/forkstat.c.
// * https://www.kernel.org/doc/Documentation/connector/connector.txt
//
// If Python is run as a normal user, this will require CAP_NET_ADMIN
// or CAP_SYS_ADMIN capabilities to run. You can check if you have them
// with `capsh --print`.

#include <Python.h>

#include <sys/socket.h>
#include <sys/uio.h>
#include <linux/connector.h>
#include <linux/netlink.h>
#include <linux/cn_proc.h>

#include "../../_psutil_common.h"


#define RECV_BUF_SIZE 4096


// Accepts an AF_NETLINK socket and tells the kernel to start sending
// data to it every time a process PID is updated (new, gone, etc.).
PyObject *
psutil_netlink_proc_register(PyObject *self, PyObject *args) {
    int sockfd;
    ssize_t bytes_sent;
    struct nlmsghdr nl_header;
    enum proc_cn_mcast_op op;
    struct cn_msg cn_msg;
    struct iovec iov[3];

    if (! PyArg_ParseTuple(args, "i", &sockfd))
        return NULL;

    memset(&nl_header, 0, sizeof(nl_header));
    nl_header.nlmsg_len = NLMSG_LENGTH(sizeof(cn_msg) + sizeof(op));
    nl_header.nlmsg_type = NLMSG_DONE;
    nl_header.nlmsg_pid = getpid();
    iov[0].iov_base = &nl_header;
    iov[0].iov_len = sizeof(nl_header);

    memset(&cn_msg, 0, sizeof(cn_msg));
    cn_msg.id.idx = CN_IDX_PROC;
    cn_msg.id.val = CN_VAL_PROC;
    cn_msg.len = sizeof(enum proc_cn_mcast_op);
    iov[1].iov_base = &cn_msg;
    iov[1].iov_len = sizeof(cn_msg);

    op = PROC_CN_MCAST_LISTEN;
    iov[2].iov_base = &op;
    iov[2].iov_len = sizeof(op);

    bytes_sent = writev(sockfd, iov, 3);
    if (bytes_sent == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("writev");
        return NULL;
    }
    if (bytes_sent != nl_header.nlmsg_len) {
        PyErr_SetString(PyExc_RuntimeError, "writev() len mismatch");
        return NULL;
    }

    Py_RETURN_NONE;
}


static PyObject *
handle_message(struct cn_msg *cn_message) {
    struct proc_event *ev;
    __kernel_pid_t pid = -1;
    __kernel_pid_t parent_pid = -1;
    int euid = -1;
    int egid = -1;
    int exit_code = -1;
    PyObject *py_is_thread = NULL;
    PyObject *py_dict = NULL;
    PyObject *py_item = NULL;

    ev = (struct proc_event *)cn_message->data;

    switch (ev->what) {
        case PROC_EVENT_FORK:  // a new process is created (child)
            pid = ev->event_data.fork.child_pid;
            if (ev->event_data.fork.child_pid != ev->event_data.fork.child_tgid) {
                py_is_thread = Py_True;
                parent_pid = ev->event_data.fork.child_tgid;
            }
            else {
                py_is_thread = Py_False;
                parent_pid = ev->event_data.fork.parent_pid;
            }
            Py_INCREF(py_is_thread);
            break;
        case PROC_EVENT_EXEC:  // process executed new program via execv*()
            pid = ev->event_data.exec.process_pid;
            break;
        case PROC_EVENT_EXIT:  // process gone
            pid = ev->event_data.exit.process_pid;
            exit_code = (int)ev->event_data.exit.exit_code;
            break;
        // NOTE: does not work as expected. Apparently we only ever get
        // PROC_EVENT_EXIT.
        // case PROC_EVENT_NONZERO_EXIT:  // process gone with exit code != 0
        //     pid = ev->event_data.exit.process_pid;
        //     exit_code = (int)ev->event_data.exit.exit_code;
        //     break;
        case PROC_EVENT_UID:  // process user changed
            pid = ev->event_data.exec.process_pid;
            euid = (unsigned int)ev->event_data.id.e.euid;
            break;
        case PROC_EVENT_GID:  // process group changed
            pid = ev->event_data.exec.process_pid;
            egid = (unsigned int)ev->event_data.id.e.egid;
            break;
        case PROC_EVENT_SID:  // process SID changed (e.g. sudo was used)
            pid = ev->event_data.exec.process_pid;
            break;
        case PROC_EVENT_COMM:  // process changed its name or command line
            pid = ev->event_data.exec.process_pid;
            break;
        case PROC_EVENT_PTRACE:  // process via being traced via ptrace() (debug)
            pid = ev->event_data.exec.process_pid;
            break;
        case PROC_EVENT_COREDUMP:  // process generated a coredump
            pid = ev->event_data.fork.child_pid;
            parent_pid = ev->event_data.fork.parent_pid;
            break;
        default:
            psutil_debug("ignore event %d", ev->what);
            return NULL;
    }

    py_dict = PyDict_New();
    if (py_dict == NULL)
        goto error;

    // event
    py_item = Py_BuildValue("I", ev->what);
    if (!py_item)
        goto error;
    if (PyDict_SetItemString(py_dict, "event", py_item))
        goto error;
    Py_CLEAR(py_item);

    // pid
    py_item = Py_BuildValue(_Py_PARSE_PID, pid);
    if (!py_item)
        goto error;
    if (PyDict_SetItemString(py_dict, "pid", py_item))
        goto error;
    Py_CLEAR(py_item);

    // parent pid
    if (parent_pid != -1) {
        py_item = Py_BuildValue(_Py_PARSE_PID, parent_pid);
        if (!py_item)
            goto error;
        if (PyDict_SetItemString(py_dict, "parent_pid", py_item))
            goto error;
        Py_CLEAR(py_item);
    }

    // is thread? (fork)
    if (py_is_thread != NULL) {
        if (PyDict_SetItemString(py_dict, "is_thread", py_is_thread))
            goto error;
        Py_CLEAR(py_is_thread);
    }

    // exit code
    if (exit_code != -1) {
        py_item = Py_BuildValue("I", exit_code);
        if (!py_item)
            goto error;
        if (PyDict_SetItemString(py_dict, "exit_code", py_item))
            goto error;
        Py_CLEAR(py_item);
    }

    // euid
    if (euid != -1) {
        py_item = Py_BuildValue("I", euid);
        if (!py_item)
            goto error;
        if (PyDict_SetItemString(py_dict, "euid", py_item))
            goto error;
        Py_CLEAR(py_item);
    }

    // egid
    if (egid != -1) {
        py_item = Py_BuildValue("I", egid);
        if (!py_item)
            goto error;
        if (PyDict_SetItemString(py_dict, "egid", py_item))
            goto error;
        Py_CLEAR(py_item);
    }

    return py_dict;

error:
    Py_XDECREF(py_item);
    Py_XDECREF(py_dict);
    return NULL;
}


// Reads data from the AF_NETLINK socket (blocking). Returns a Python
// list of events (if any). You're supposed to use select() or poll()
// first, to check whether there is data to read.
PyObject *
psutil_netlink_proc_read(PyObject *self, PyObject *args) {
    int sockfd;
    struct cn_msg *cn_message;
    struct nlmsghdr *nlh;
    char buf[RECV_BUF_SIZE];
    ssize_t recv_len;
    PyObject *py_dict = NULL;
    PyObject *py_list = PyList_New(0);

    if (py_list == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "i", &sockfd))
        goto error;

    // Receive data.
    recv_len = recv(sockfd, buf, sizeof(buf), 0);
    if (recv_len == -1) {
        if (errno == ENOBUFS) {
            // printf("ENOBUFS ignored\n");
            psutil_debug("ENOBUFS ignored");
            return py_list;
        }
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    nlh = (struct nlmsghdr *)buf;
    while (NLMSG_OK(nlh, recv_len)) {
        cn_message = NLMSG_DATA(nlh);

        if ((cn_message->id.idx != CN_IDX_PROC) ||
            (cn_message->id.val != CN_VAL_PROC))
        {
            psutil_debug("CN_IDX_PROC | CN_VAL_PROC (skip)");
            continue;
        }

        if (nlh->nlmsg_type == NLMSG_NOOP) {
            psutil_debug("NLMSG_NOOP (skip)");
            nlh = NLMSG_NEXT(nlh, recv_len);
            continue;
        }

        if ((nlh->nlmsg_type == NLMSG_ERROR) ||
            (nlh->nlmsg_type == NLMSG_OVERRUN)) {
            psutil_debug("NLMSG_ERROR || NLMSG_OVERRUN");
            break;
        }

        // handle message
        py_dict = handle_message(cn_message);
        if (py_dict == NULL) {
            if (PyErr_Occurred())
                goto error;
        }
        else {
            if (PyList_Append(py_list, py_dict)) {
                Py_DECREF(py_dict);
                goto error;
            }
            Py_DECREF(py_dict);
        }

        if (nlh->nlmsg_type == NLMSG_DONE)
            break;
        nlh = NLMSG_NEXT(nlh, recv_len);
    }

    return py_list;

error:
    Py_XDECREF(py_dict);
    Py_XDECREF(py_list);
    return NULL;
}
