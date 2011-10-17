/*
 * $Id$
 *
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * LINUX specific module methods for _psutil_linux
 */

#include <Python.h>

static PyObject* linux_ioprio_get(PyObject* self, PyObject* args);
static PyObject* linux_ioprio_set(PyObject* self, PyObject* args);
static PyObject* get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* get_physmem(PyObject* self, PyObject* args);

