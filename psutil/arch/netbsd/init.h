/*
 * Copyright (c) 2009, Giampaolo Rodola'.
 * Copyright (c) 2015, Ryo ONODERA.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/types.h>

int _psutil_pids(pid_t **pids_array, int *pids_count);

PyObject *psutil_cpu_stats(PyObject *self, PyObject *args);
PyObject *psutil_disk_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_net_connections(PyObject *, PyObject *);
PyObject *psutil_per_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_proc_cmdline(PyObject *self, PyObject *args);
PyObject *psutil_proc_cwd(PyObject *self, PyObject *args);
PyObject *psutil_proc_exe(PyObject *self, PyObject *args);
PyObject *psutil_proc_net_connections(PyObject *, PyObject *);
PyObject *psutil_proc_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_fds(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_threads(PyObject *self, PyObject *args);
PyObject *psutil_proc_threads(PyObject *self, PyObject *args);
PyObject *psutil_swap_mem(PyObject *self, PyObject *args);
PyObject *psutil_virtual_mem(PyObject *self, PyObject *args);
