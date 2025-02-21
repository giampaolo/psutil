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
handle_message(struct cn_msg *cn_hdr) {
    struct proc_event *ev;
    __kernel_pid_t pid;
    __kernel_pid_t parent_pid;
    __u32 exit_code;
    // PyObject *py_retdict = PyDict_New();
    // if (py_retdict == NULL)
    //     return NULL;
    ev = (struct proc_event *)cn_hdr->data;

    switch(ev->what){
        case PROC_EVENT_FORK:
            pid = ev->event_data.fork.child_pid;
            parent_pid = ev->event_data.fork.parent_pid;
            // printf("FORK, parent=%d, child=%d\n",
            //        ev->event_data.fork.parent_pid,
            //        ev->event_data.fork.child_pid);
            break;
        case PROC_EVENT_EXEC:
            pid = ev->event_data.exec.process_pid;
            // printf("EXEC, pid=%d\n", ev->event_data.exec.process_pid);
            break;
        case PROC_EVENT_EXIT:
            pid = ev->event_data.exit.process_pid;
            exit_code = ev->event_data.exit.exit_code;
            // printf("EXIT, pid=%d, exit code=%d\n",
            //        ev->event_data.exit.process_pid,
            //        ev->event_data.exit.exit_code);
            break;
        default:
            break;
    }

    return 0;
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

    if (! PyArg_ParseTuple(args, "i", &sk_nl))
        return NULL;

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
        if (handle_message(cn_hdr) != 0) {
            PyErr_SetString(PyExc_RuntimeError, "recv() len mismatch");
            return NULL;
        }
        if (nlh->nlmsg_type == NLMSG_DONE) {
            break;
        }
        nlh = NLMSG_NEXT(nlh, recv_len);
    }

    Py_RETURN_NONE;
}
