/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// process

static PyObject* psutil_proc_cpu_affinity_get(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cpu_affinity_set(PyObject* self, PyObject* args);
static PyObject* psutil_proc_ioprio_get(PyObject* self, PyObject* args);
static PyObject* psutil_proc_ioprio_get(PyObject* self, PyObject* args);

// system

static PyObject* psutil_disk_partitions(PyObject* self, PyObject* args);
static PyObject* psutil_linux_sysinfo(PyObject* self, PyObject* args);
static PyObject* psutil_users(PyObject* self, PyObject* args);
