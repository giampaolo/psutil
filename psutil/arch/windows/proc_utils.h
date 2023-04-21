/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
HANDLE psutil_handle_from_pid(DWORD pid, DWORD dwDesiredAccess);
HANDLE psutil_check_phandle(HANDLE hProcess, DWORD pid, int check_exit_code);
int psutil_pid_is_running(DWORD pid);
int psutil_assert_pid_exists(DWORD pid, char *err);
int psutil_assert_pid_not_exists(DWORD pid, char *err);
