/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// processes
static PyObject* psutil_get_proc_basic_info(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_connections(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cred(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_memory_maps(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_name_and_args(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* psutil_query_process_thread(PyObject* self, PyObject* args);

// system
static PyObject* psutil_get_boot_time(PyObject* self, PyObject* args);
static PyObject* psutil_get_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* psutil_get_net_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_get_num_phys_cpus(PyObject* self, PyObject* args);
static PyObject* psutil_get_swap_mem(PyObject* self, PyObject* args);
static PyObject* psutil_get_sys_per_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_get_users(PyObject* self, PyObject* args);
