/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

PyObject *psutil_pids(PyObject *self, PyObject *args);
PyObject *psutil_proc_cmdline(PyObject *self, PyObject *args);
PyObject *psutil_proc_cwd(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_exe(PyObject *self, PyObject *args);
PyObject *psutil_proc_kinfo_oneshot(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_uss(PyObject *self, PyObject *args);
PyObject *psutil_proc_name(PyObject *self, PyObject *args);
PyObject *psutil_proc_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_fds(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
PyObject *psutil_proc_pidtaskinfo_oneshot(PyObject *self, PyObject *args);
PyObject *psutil_proc_threads(PyObject *self, PyObject *args);
