/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <unistd.h>

#include "../../_psutil_common.h"

#define DUPLEX_UNKNOWN 0xff

PyObject*
psutil_net_if_duplex_speed(PyObject* self, PyObject* args) {
    PyObject *py_retlist = NULL;
    int duplex = DUPLEX_UNKNOWN;
    int speed = 0;

    py_retlist = Py_BuildValue("[ii]", duplex, speed);
    return py_retlist;
}
