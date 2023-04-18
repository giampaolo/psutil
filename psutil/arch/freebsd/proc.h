/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

typedef struct kinfo_proc kinfo_proc;

int psutil_get_proc_list(struct kinfo_proc **procList, size_t *procCount);
int psutil_kinfo_proc(const pid_t pid, struct kinfo_proc *proc);

PyObject* psutil_proc_cmdline(PyObject* self, PyObject* args);
PyObject* psutil_proc_cpu_affinity_get(PyObject* self, PyObject* args);
PyObject* psutil_proc_cpu_affinity_set(PyObject* self, PyObject* args);
PyObject* psutil_proc_cwd(PyObject* self, PyObject* args);
PyObject* psutil_proc_exe(PyObject* self, PyObject* args);
PyObject* psutil_proc_getrlimit(PyObject* self, PyObject* args);
PyObject* psutil_proc_memory_maps(PyObject* self, PyObject* args);
PyObject* psutil_proc_num_fds(PyObject* self, PyObject* args);
PyObject* psutil_proc_num_threads(PyObject* self, PyObject* args);
PyObject* psutil_proc_setrlimit(PyObject* self, PyObject* args);
PyObject* psutil_proc_threads(PyObject* self, PyObject* args);
