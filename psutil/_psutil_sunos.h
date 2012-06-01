/*
 * $Id$
 *
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Sun OS specific module functions for _psutil_sunos extension
 */

#include <Python.h>

static PyObject* get_process_basic_info(PyObject* self, PyObject* args);
static PyObject* get_process_name_and_args(PyObject* self, PyObject* args);
static PyObject* get_process_cpu_times(PyObject* self, PyObject* args);

static PyObject* get_system_users(PyObject* self, PyObject* args);
static PyObject* get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* get_system_per_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_disk_io_counters(PyObject* self, PyObject* args);
