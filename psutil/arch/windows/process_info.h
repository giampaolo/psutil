/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

int psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                         PVOID *retBuffer);
PyObject* psutil_get_cmdline(long pid, int use_peb);
PyObject* psutil_get_cwd(long pid);
PyObject* psutil_get_environ(long pid);
PyObject* psutil_proc_info(PyObject *self, PyObject *args);
