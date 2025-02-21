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
