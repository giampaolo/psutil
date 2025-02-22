/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>

#include <sys/socket.h>
#include <sys/types.h>

#include <linux/connector.h>
#include <linux/netlink.h>
#include <linux/cn_proc.h>


#define MIN(X, Y) (((X) < (Y)) ? (X) : (Y))
#define MAX(X, Y) (((X) > (Y)) ? (X) : (Y))

#define SEND_MESSAGE_LEN ( \
    NLMSG_LENGTH(sizeof(struct cn_msg) + sizeof(enum proc_cn_mcast_op)) \
)
#define RECV_MESSAGE_LEN ( \
    NLMSG_LENGTH(sizeof(struct cn_msg) + sizeof(struct proc_event)) \
)

#define BUFF_SIZE (MAX(MAX(SEND_MESSAGE_SIZE, RECV_MESSAGE_SIZE), 1024))
#define SEND_MESSAGE_SIZE (NLMSG_SPACE(SEND_MESSAGE_LEN))
#define RECV_MESSAGE_SIZE (NLMSG_SPACE(RECV_MESSAGE_LEN))


// Send an AF_NETLINK packet that tells the kernel to start sending
// data any time a process PID is updated (new, gone, etc.).
PyObject *
psutil_netlink_procs_send(PyObject *self, PyObject *args) {
    int sockfd;
    char buf[BUFF_SIZE];
    struct nlmsghdr *nl_hdr;
    ssize_t bytes_sent;

    if (! PyArg_ParseTuple(args, "i", &sockfd))
        return NULL;

    nl_hdr = (struct nlmsghdr *)buf;
    nl_hdr->nlmsg_len = SEND_MESSAGE_LEN;
    nl_hdr->nlmsg_type = NLMSG_DONE;
    nl_hdr->nlmsg_flags = 0;
    nl_hdr->nlmsg_seq = 0;
    nl_hdr->nlmsg_pid = getpid();

    bytes_sent = send(sockfd, nl_hdr, nl_hdr->nlmsg_len, 0);
    if (bytes_sent == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (bytes_sent != nl_hdr->nlmsg_len) {
        PyErr_SetString(PyExc_RuntimeError, "send() len mismatch");
        return NULL;
    }

    Py_RETURN_NONE;
}


static int
handle_message(struct cn_msg *cn_hdr, PyObject *py_callback) {
    struct proc_event *ev;
    __kernel_pid_t pid = -1;
    __kernel_pid_t parent_pid = -1;
    unsigned int event = 0;
    int exit_code = -1;
    PyObject *py_dict = PyDict_New();
    PyObject *py_item = NULL;

    if (py_dict == NULL)
        return -1;

    ev = (struct proc_event *)cn_hdr->data;

    switch (ev->what) {
        case PROC_EVENT_FORK:
            event = ev->what;
            pid = ev->event_data.fork.child_pid;
            parent_pid = ev->event_data.fork.parent_pid;
            // printf("FORK, parent=%d, child=%d\n",
            //        ev->event_data.fork.parent_pid,
            //        ev->event_data.fork.child_pid);
            break;
        case PROC_EVENT_EXEC:
            event = ev->what;
            pid = ev->event_data.exec.process_pid;
            // printf("EXEC, pid=%d\n", ev->event_data.exec.process_pid);
            break;
        case PROC_EVENT_EXIT:
            event = ev->what;
            pid = ev->event_data.exit.process_pid;
            exit_code = (int)ev->event_data.exit.exit_code;
            // printf("EXIT, pid=%d, exit code=%d\n",
            //        ev->event_data.exit.process_pid,
            //        ev->event_data.exit.exit_code);
            break;
        default:
            // printf("skip\n");
            break;
    }

    if (event == 0) {
        Py_DECREF(py_dict);
        return 0;
    }

    // event
    py_item = Py_BuildValue("I", event);
    if (!py_item)
        goto error;
    if (PyDict_SetItemString(py_dict, "event", py_item))
        goto error;
    Py_CLEAR(py_item);

    // pid
    if (pid != -1) {
        py_item = Py_BuildValue(_Py_PARSE_PID, pid);
        if (!py_item)
            goto error;
        if (PyDict_SetItemString(py_dict, "pid", py_item))
            goto error;
        Py_CLEAR(py_item);
    }

    // parent pid
    if (parent_pid != -1) {
        py_item = Py_BuildValue(_Py_PARSE_PID, parent_pid);
        if (!py_item)
            goto error;
        if (PyDict_SetItemString(py_dict, "parent_pid", py_item))
            goto error;
        Py_CLEAR(py_item);
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

    if (! PyObject_CallFunctionObjArgs(py_callback, py_dict, NULL))
        goto error;

    return 0;

error:
    Py_XDECREF(py_item);
    Py_DECREF(py_dict);
    return -1;
}


PyObject *
psutil_netlink_procs_recv(PyObject *self, PyObject *args) {
    int sk_nl;
    struct sockaddr_nl from_nla;
    struct cn_msg *cn_hdr;
    struct nlmsghdr *nlh;
    socklen_t from_nla_len;
    char buff[BUFF_SIZE];
    ssize_t recv_len;
    PyObject *py_callback;

    if (! PyArg_ParseTuple(args, "iO", &sk_nl, &py_callback))
        return NULL;
    if (! PyCallable_Check(py_callback)) {
        PyErr_SetString(PyExc_TypeError, "second argument must be a callable");
        return NULL;
    }

    // Receive data.
    memset(buff, 0, sizeof(buff));
    from_nla_len = sizeof(from_nla);
    recv_len = recvfrom(
        sk_nl, buff, sizeof(buff), 0, (struct sockaddr *)&from_nla, &from_nla_len);
    if (recv_len == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (from_nla_len != sizeof(from_nla)) {
        PyErr_SetString(PyExc_RuntimeError, "recv() len mismatch");
        return NULL;
    }


    nlh = (struct nlmsghdr *)buff;
    while (NLMSG_OK(nlh, recv_len)) {
        cn_hdr = NLMSG_DATA(nlh);

        if (nlh->nlmsg_type == NLMSG_NOOP) {
            nlh = NLMSG_NEXT(nlh, recv_len);
            continue;
        }
        if ((nlh->nlmsg_type == NLMSG_ERROR) ||
            (nlh->nlmsg_type == NLMSG_OVERRUN)) {
            break;
        }

        if (handle_message(cn_hdr, py_callback) != 0) {
            return NULL;
        }
        if (nlh->nlmsg_type == NLMSG_DONE) {
            break;
        }
        nlh = NLMSG_NEXT(nlh, recv_len);
    }

    Py_RETURN_NONE;
}
