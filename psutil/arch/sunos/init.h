/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <libproc.h>

#ifndef PROCESS_AS_UTILS_H
#define PROCESS_AS_UTILS_H

char **psutil_read_raw_args(
    psinfo_t info, const char *procfs_path, size_t *count
);

char **psutil_read_raw_env(
    psinfo_t info, const char *procfs_path, ssize_t *count
);

void psutil_free_cstrings_array(char **array, size_t count);
#endif  // PROCESS_AS_UTILS_H

PyObject *psutil_boot_time(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_cores(PyObject *self, PyObject *args);
PyObject *psutil_cpu_stats(PyObject *self, PyObject *args);
PyObject *psutil_disk_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_net_if_stats(PyObject *self, PyObject *args);
PyObject *psutil_net_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_per_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_proc_basic_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_cpu_num(PyObject *self, PyObject *args);
PyObject *psutil_proc_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_proc_cred(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_maps(PyObject *self, PyObject *args);
PyObject *psutil_proc_name_and_args(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_ctx_switches(PyObject *self, PyObject *args);
PyObject *psutil_proc_query_thread(PyObject *self, PyObject *args);
PyObject *psutil_swap_mem(PyObject *self, PyObject *args);
