/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// processes
static PyObject* query_process_thread(PyObject* self, PyObject* args);
static PyObject* get_proc_basic_info(PyObject* self, PyObject* args);
static PyObject* get_proc_name_and_args(PyObject* self, PyObject* args);
static PyObject* get_proc_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_proc_cred(PyObject* self, PyObject* args);
static PyObject* get_proc_memory_maps(PyObject* self, PyObject* args);
static PyObject* get_proc_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* get_proc_connections(PyObject* self, PyObject* args);

// system
static PyObject* get_swap_mem(PyObject* self, PyObject* args);
static PyObject* get_system_users(PyObject* self, PyObject* args);
static PyObject* get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* get_system_per_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* get_net_io_counters(PyObject* self, PyObject* args);
static PyObject* get_boot_time(PyObject* self, PyObject* args);
static PyObject* get_num_phys_cpus(PyObject* self, PyObject* args);
