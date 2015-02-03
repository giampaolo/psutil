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

DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
HANDLE psutil_handle_from_pid(DWORD pid);
HANDLE psutil_handle_from_pid_waccess(DWORD pid, DWORD dwDesiredAccess);
int psutil_handlep_is_running(HANDLE hProcess);
int psutil_pid_in_proclist(DWORD pid);
int psutil_pid_is_running(DWORD pid);
PVOID psutil_get_peb_address(HANDLE ProcessHandle);
PyObject* psutil_get_arg_list(long pid);
int psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                         PVOID *retBuffer);

#endif
