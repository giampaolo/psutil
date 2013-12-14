/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

static PyObject* get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* get_proc_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* get_sysinfo(PyObject* self, PyObject* args);
static PyObject* get_users(PyObject* self, PyObject* args);
static PyObject* linux_ioprio_get(PyObject* self, PyObject* args);
static PyObject* linux_ioprio_set(PyObject* self, PyObject* args);
static PyObject* set_proc_cpu_affinity(PyObject* self, PyObject* args);
