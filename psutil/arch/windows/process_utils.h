/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

DWORD* psutil_get_pids(DWORD *numberOfReturnedPIDs);
HANDLE psutil_handle_from_pid(pid_t pid, DWORD dwDesiredAccess);
int psutil_pid_is_running(pid_t pid);
int psutil_assert_pid_exists(pid_t pid, char *err);
int psutil_assert_pid_not_exists(pid_t pid, char *err);
