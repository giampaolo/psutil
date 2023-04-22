/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject *psutil_pids(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_name(PyObject *self, PyObject *args);
PyObject *psutil_proc_oneshot_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
