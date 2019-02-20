/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#ifndef __PROCESS_HANDLES_H__
#define __PROCESS_HANDLES_H__

#ifndef UNICODE
#define UNICODE
#endif

#include <Python.h>
#include <stdio.h>
#include <windows.h>
#include <strsafe.h>
#include <winternl.h>
#include <psapi.h>
#include "ntextapi.h"

// Undocumented FILE_INFORMATION_CLASS: FileNameInformation
static const SYSTEM_INFORMATION_CLASS SystemExtendedHandleInformation = (SYSTEM_INFORMATION_CLASS)64;

PyObject* psutil_get_open_files(long pid, HANDLE processHandle);

#endif // __PROCESS_HANDLES_H__
