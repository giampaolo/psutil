/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information. Used by _psutil_mswindows
 * module methods.
 */

#include <Python.h>
#include <windows.h>

HANDLE psutil_handle_from_pid_waccess(DWORD pid, DWORD dwDesiredAccess);
HANDLE psutil_handle_from_pid(DWORD pid);
PVOID psutil_get_peb_address(HANDLE ProcessHandle);
HANDLE psutil_handle_from_pid(DWORD pid);
int psutil_pid_in_proclist(DWORD pid);
int psutil_pid_is_running(DWORD pid);
int psutil_handlep_is_running(HANDLE hProcess);
PyObject* psutil_get_arg_list(long pid);
PyObject* psutil_get_ppid(long pid);
PyObject* psutil_get_name(long pid);
DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
