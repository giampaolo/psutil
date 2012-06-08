/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Security related functions for Windows platform (Set privileges such as
 * SeDebug), as well as security helper functions.
 */

#include <windows.h>


BOOL SetPrivilege(HANDLE hToken, LPCTSTR Privilege, BOOL bEnablePrivilege);
int SetSeDebug();
int UnsetSeDebug();
HANDLE token_from_handle(HANDLE hProcess);
int HasSystemPrivilege(HANDLE hProcess);

