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

int psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                         PVOID *retBuffer);
PyObject* psutil_get_cmdline(long pid, int use_peb);
PyObject* psutil_get_cwd(long pid);
PyObject* psutil_get_environ(long pid);

#endif
