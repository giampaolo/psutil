/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
HANDLE psutil_handle_from_pid(DWORD pid);
HANDLE psutil_handle_from_pid_waccess(DWORD pid, DWORD dwDesiredAccess);
int psutil_handlep_is_running(HANDLE hProcess);
int psutil_pid_in_proclist(DWORD pid);
int psutil_pid_is_running(DWORD pid);
PVOID psutil_get_peb_address(HANDLE ProcessHandle);
PyObject* psutil_get_arg_list(long pid);
