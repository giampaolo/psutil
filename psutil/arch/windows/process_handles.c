/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 */

#include <windows.h>
#include <Python.h>
#include <tchar.h>

#include "../../_psutil_common.h"
#include "process_utils.h"

#define BUFSIZE MAX_PATH
#define NTQO_TIMEOUT 2000
#define MALLOC_ZERO(x) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (x))


// Global objects used by threads.
CRITICAL_SECTION g_cs;
BOOL g_initialized = FALSE;


static DWORD
psutil_init_threads() {
    if (g_initialized == TRUE)
        return 0;
    InitializeCriticalSection(&g_cs);
    g_initialized = TRUE;
    return 0;
}


static int
psutil_get_filename(LPVOID lpvParam) {
    HANDLE hFile = *((HANDLE*)lpvParam);
    TCHAR Path[BUFSIZE];
    DWORD dwRet;

    dwRet = GetFinalPathNameByHandle(hFile, Path, BUFSIZE, VOLUME_NAME_NT);
    if(dwRet < BUFSIZE)
    {
        _tprintf(TEXT("The final path is: %s\n"), Path);
    }
    else printf("The required buffer size is %d.\n", dwRet);
    return 0;
}


static DWORD
psutil_threaded_get_filename(HANDLE hFile) {
    DWORD dwWait = 0;
    HANDLE hThread = NULL;
    DWORD threadRetValue;

    hThread = CreateThread(NULL, 0, psutil_get_filename, &hFile, 0, NULL);
    if (hThread == NULL) {
        PyErr_SetFromOSErrnoWithSyscall("CreateThread");
        return 1;
    }

    // Wait for the worker thread to finish
    dwWait = WaitForSingleObject(hThread, NTQO_TIMEOUT);

    // If the thread hangs, kill it and cleanup.
    if (dwWait == WAIT_TIMEOUT) {
        psutil_debug("thread for getting file handle name timed out");
        SuspendThread(hThread);
        TerminateThread(hThread, 1);
        CloseHandle(hThread);
        return 0;
    }
    else {
        if (GetExitCodeThread(hThread, &threadRetValue) == 0) {
            CloseHandle(hThread);
            PyErr_SetFromOSErrnoWithSyscall("GetExitCodeThread");
            return 1;
        }
        CloseHandle(hThread);
        return threadRetValue;
    }
}


// Taken from Process Hacker.
int
psutil_enum_handles(PSYSTEM_HANDLE_INFORMATION_EX *handles) {
    static ULONG initialBufferSize = 0x10000;
    NTSTATUS status;
    PVOID buffer;
    ULONG bufferSize;

    bufferSize = initialBufferSize;
    buffer = malloc(bufferSize);

    while ((status = NtQuerySystemInformation(
        SystemExtendedHandleInformation,
        buffer,
        bufferSize,
        NULL
        )) == STATUS_INFO_LENGTH_MISMATCH)
    {
        free(buffer);
        bufferSize *= 2;

        // Fail if we're resizing the buffer to something very large.
        if (bufferSize > 256 * 1024 * 1024) {
            psutil_debug("SystemExtendedHandleInformation: buffer too big");
            PyErr_NoMemory();
            return 1;
        }

        buffer = malloc(bufferSize);
    }

    if (! NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr("NtQuerySystemInformation");
        free(buffer);
        return 1;
    }

    *handles = (PSYSTEM_HANDLE_INFORMATION_EX)buffer;
    return 0;
}



PyObject *
psutil_get_open_files(DWORD dwPid, HANDLE hProcess) {
    PSYSTEM_HANDLE_INFORMATION_EX       handlesList = NULL;
    PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX  hHandle = NULL;
    HANDLE                              hFile = NULL;
    DWORD                               i = 0;
    BOOLEAN                             error_occurred = FALSE;
    DWORD                               dwWait = 0;
    PyObject*                           py_retlist = NULL;
    PyObject*                           py_path = NULL;

    py_retlist = PyList_New(0);
    if (!py_retlist)
        return NULL;
    if (psutil_init_threads() != 0)
        goto error;
    if (psutil_enum_handles(&handlesList) != 0)
        goto error;

    for (i = 0; i < handlesList->NumberOfHandles; i++) {
        hHandle = &handlesList->Handles[i];
        if ((ULONG_PTR)hHandle->UniqueProcessId != dwPid)
            continue;

        if (! DuplicateHandle(
                hProcess,
                hHandle->HandleValue,
                GetCurrentProcess(),
                &hFile,
                0,
                TRUE,
                DUPLICATE_SAME_ACCESS))
        {
            // Will fail if not a regular file; just skip it.
            continue;
        }

        if (psutil_threaded_get_filename(hFile) != 0)
            goto error;

        // cleanup section
        CloseHandle(hFile);
    }

    goto exit;

error:
    error_occurred = TRUE;
    goto exit;

exit:
    Py_DECREF(py_retlist);
    if (hFile != NULL)
        CloseHandle(hFile);
    if (handlesList != NULL)
        FREE(handlesList);
    if (error_occurred == TRUE)
        return NULL;
    return py_retlist;
}

