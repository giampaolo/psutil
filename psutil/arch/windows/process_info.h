/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#define PSUTIL_FIRST_PROCESS(Processes) ( \
    (PSYSTEM_PROCESS_INFORMATION)(Processes))
#define PSUTIL_NEXT_PROCESS(Process) ( \
   ((PSYSTEM_PROCESS_INFORMATION)(Process))->NextEntryOffset ? \
   (PSYSTEM_PROCESS_INFORMATION)((PCHAR)(Process) + \
        ((PSYSTEM_PROCESS_INFORMATION)(Process))->NextEntryOffset) : NULL)

int psutil_get_proc_info(DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess,
                         PVOID *retBuffer);
PyObject* psutil_get_cmdline(DWORD pid, int use_peb);
PyObject* psutil_get_cwd(DWORD pid);
PyObject* psutil_get_environ(DWORD pid);
PyObject* psutil_proc_info(PyObject *self, PyObject *args);
