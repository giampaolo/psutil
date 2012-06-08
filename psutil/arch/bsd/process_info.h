/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information. Used by _psutil_bsd
 * module methods.
 */

#include <Python.h>

typedef struct kinfo_proc kinfo_proc;

int  psutil_get_proc_list(struct kinfo_proc **procList, size_t *procCount);
char *psutil_get_cmd_args(long pid, size_t *argsize);
char *psutil_get_cmd_path(long pid, size_t *pathsize);
int  psutil_pid_exists(long pid);
PyObject* psutil_get_arg_list(long pid);
