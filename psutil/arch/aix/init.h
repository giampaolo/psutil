/*
 * Copyright (c) 2009, Giampaolo Rodola'
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/core.h>

#define PROCINFO_INCR (256)
#define PROCSIZE (sizeof(struct procentry64))
#define FDSINFOSIZE (sizeof(struct fdsinfo64))
#define KMEM "/dev/kmem"

typedef u_longlong_t KA_T;

struct procentry64 *psutil_read_process_table(int *num);

PyObject *psutil_boot_time(PyObject *self, PyObject *args);
PyObject *psutil_cpu_stats(PyObject *self, PyObject *args);
PyObject *psutil_disk_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_net_if_stats(PyObject *self, PyObject *args);
PyObject *psutil_net_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_per_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_swap_mem(PyObject *self, PyObject *args);
PyObject *psutil_virtual_mem(PyObject *self, PyObject *args);
