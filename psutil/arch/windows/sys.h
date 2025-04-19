/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject *psutil_uptime(PyObject *self, PyObject *args);
PyObject *psutil_users(PyObject *self, PyObject *args);
PyObject *psutil_RtlDosPathNameToNtPathName(PyObject *self, PyObject *args);
PyObject *psutil_GetFinalPathName(PyObject *self, PyObject *args, PyObject *kwargs);
