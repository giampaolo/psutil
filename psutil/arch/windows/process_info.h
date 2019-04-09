/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#if !defined(__PROCESS_INFO_H)
#define __PROCESS_INFO_H

#include <Python.h>
#include <windows.h>
#include "security.h"
#include "ntextapi.h"

#define HANDLE_TO_PYNUM(handle) PyLong_FromUnsignedLong((unsigned long) handle)
#define PYNUM_TO_HANDLE(obj) ((HANDLE)PyLong_AsUnsignedLong(obj))

DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
HANDLE psutil_handle_from_pid(DWORD pid, DWORD dwDesiredAccess);
int psutil_pid_is_running(DWORD pid);
int psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                         PVOID *retBuffer);

int psutil_assert_pid_exists(DWORD pid, char *err);
int psutil_assert_pid_not_exists(DWORD pid, char *err);

PyObject* psutil_get_cmdline(long pid, int use_peb);
PyObject* psutil_get_cwd(long pid);
PyObject* psutil_get_environ(long pid);

#endif
