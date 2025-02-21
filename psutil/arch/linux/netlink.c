/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <linux/netlink.h>

#define SEND_MESSAGE_LEN (NLMSG_LENGTH(sizeof(struct cn_msg) + \
                       sizeof(enum proc_cn_mcast_op)))
#define RECV_MESSAGE_LEN (NLMSG_LENGTH(sizeof(struct cn_msg) + \
                       sizeof(struct proc_event)))


PyObject *
psutil_netlink_subscribe_proc(PyObject *self, PyObject *args) {
    int sk_nl;

    if (! PyArg_ParseTuple(args, "i", &sk_nl))
        return NULL;

    return Py_BuildValue("i", sk_nl);
}
