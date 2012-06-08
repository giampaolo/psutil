/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information. Used by _psutil_osx
 * module methods.
 */

#include <Python.h>


typedef struct kinfo_proc kinfo_proc;

int psutil_get_proc_list(kinfo_proc **procList, size_t *procCount);
int psutil_get_kinfo_proc(pid_t pid, struct kinfo_proc *kp);
int psutil_get_argmax(void);
int psutil_pid_exists(long pid);
int psutil_proc_pidinfo(long pid, int flavor, void *pti, int size);
PyObject* psutil_get_arg_list(long pid);
