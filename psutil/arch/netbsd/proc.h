/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

typedef struct kinfo_proc2 kinfo_proc;

int psutil_kinfo_proc(pid_t pid, kinfo_proc *proc);
struct kinfo_file * kinfo_getfile(pid_t pid, int* cnt);
int psutil_get_proc_list(kinfo_proc **procList, size_t *procCount);
char *psutil_get_cmd_args(pid_t pid, size_t *argsize);

PyObject *psutil_proc_cmdline(PyObject *self, PyObject *args);
PyObject *psutil_proc_cwd(PyObject *self, PyObject *args);
PyObject *psutil_proc_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_fds(PyObject *self, PyObject *args);
PyObject *psutil_proc_threads(PyObject *self, PyObject *args);
PyObject* psutil_proc_exe(PyObject* self, PyObject* args);
PyObject* psutil_proc_num_threads(PyObject* self, PyObject* args);
