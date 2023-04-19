/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject *TimeoutExpired;
PyObject *TimeoutAbandoned;

PyObject *psutil_pid_exists(PyObject *self, PyObject *args);
PyObject *psutil_pids(PyObject *self, PyObject *args);
PyObject *psutil_ppid_map(PyObject *self, PyObject *args);
PyObject *psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args);
PyObject *psutil_proc_exe(PyObject *self, PyObject *args);
PyObject *psutil_proc_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_proc_io_priority_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_io_priority_set(PyObject *self, PyObject *args);
PyObject *psutil_proc_is_suspended(PyObject *self, PyObject *args);
PyObject *psutil_proc_kill(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_maps(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_uss(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_handles(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
PyObject *psutil_proc_priority_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_priority_set(PyObject *self, PyObject *args);
PyObject *psutil_proc_suspend_or_resume(PyObject *self, PyObject *args);
PyObject *psutil_proc_threads(PyObject *self, PyObject *args);
PyObject *psutil_proc_times(PyObject *self, PyObject *args);
PyObject *psutil_proc_username(PyObject *self, PyObject *args);
PyObject *psutil_proc_wait(PyObject *self, PyObject *args);
