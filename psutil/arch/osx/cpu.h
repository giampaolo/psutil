/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject *psutil_cpu_count_cores(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_logical(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_sockets(PyObject *self, PyObject *args);
PyObject *psutil_cpu_flags(PyObject *self, PyObject *args);
PyObject *psutil_cpu_freq(PyObject *self, PyObject *args);
PyObject *psutil_cpu_l1d_cache(PyObject *self, PyObject *args);
PyObject *psutil_cpu_l1i_cache(PyObject *self, PyObject *args);
PyObject *psutil_cpu_l2_cache(PyObject *self, PyObject *args);
PyObject *psutil_cpu_l3_cache(PyObject *self, PyObject *args);
PyObject *psutil_cpu_model(PyObject *self, PyObject *args);
PyObject *psutil_cpu_stats(PyObject *self, PyObject *args);
PyObject *psutil_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_cpu_vendor(PyObject *self, PyObject *args);
