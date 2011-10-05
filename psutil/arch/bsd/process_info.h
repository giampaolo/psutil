/*
 * $Id$
 *
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information. Used by _psutil_bsd
 * module methods.
 */

#include <Python.h>

typedef struct kinfo_proc kinfo_proc;

int get_proc_list(struct kinfo_proc **procList, size_t *procCount);
char *getcmdargs(long pid, size_t *argsize);
char *getcmdpath(long pid, size_t *pathsize);
PyObject* get_arg_list(long pid);
int pid_exists(long pid);

