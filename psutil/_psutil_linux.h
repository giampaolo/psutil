/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

static PyObject* psutil_get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* psutil_get_sysinfo(PyObject* self, PyObject* args);
static PyObject* psutil_get_users(PyObject* self, PyObject* args);
static PyObject* psutil_linux_ioprio_get(PyObject* self, PyObject* args);
static PyObject* psutil_linux_ioprio_set(PyObject* self, PyObject* args);
static PyObject* psutil_set_proc_cpu_affinity(PyObject* self, PyObject* args);
