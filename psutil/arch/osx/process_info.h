/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

typedef struct kinfo_proc kinfo_proc;

int psutil_get_kinfo_proc(pid_t pid, struct kinfo_proc *kp);
int psutil_get_proc_list(kinfo_proc **procList, size_t *procCount);
int psutil_proc_pidinfo(
    pid_t pid, int flavor, uint64_t arg, void *pti, int size);

PyObject *psutil_proc_cmdline(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
