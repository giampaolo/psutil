/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <psapi.h>

#include "../../arch/all/init.h"


int
_psutil_pids(DWORD **pids_array, int *pids_count) {
    DWORD *proc_array = NULL;
    DWORD proc_array_bytes;
    int proc_array_sz = 0;
    DWORD enum_return_bytes = 0;

    *pids_array = NULL;
    *pids_count = 0;

    do {
        proc_array_sz += 1024;
        if (proc_array != NULL)
            free(proc_array);

        proc_array_bytes = proc_array_sz * sizeof(DWORD);
        proc_array = malloc(proc_array_bytes);
        if (proc_array == NULL) {
            PyErr_NoMemory();
            return -1;
        }

        if (!EnumProcesses(proc_array, proc_array_bytes, &enum_return_bytes)) {
            free(proc_array);
            psutil_oserror();
            return -1;
        }

        // Retry if our buffer was too small.
    } while (enum_return_bytes == proc_array_bytes);

    *pids_count = (int)(enum_return_bytes / sizeof(DWORD));
    *pids_array = proc_array;
    return 0;
}
