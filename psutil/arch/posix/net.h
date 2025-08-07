/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#if defined(PSUTIL_BSD) || defined(PSUTIL_OSX)
PyObject *psutil_net_if_duplex_speed(PyObject *self, PyObject *args);
#endif
PyObject *psutil_net_if_addrs(PyObject* self, PyObject* args);
PyObject *psutil_net_if_flags(PyObject *self, PyObject *args);
PyObject *psutil_net_if_is_running(PyObject *self, PyObject *args);
PyObject *psutil_net_if_mtu(PyObject *self, PyObject *args);
