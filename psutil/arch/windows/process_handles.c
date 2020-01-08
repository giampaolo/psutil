/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 */

#include <windows.h>
#include <Python.h>

#include "../../_psutil_common.h"
#include "process_utils.h"


CRITICAL_SECTION g_cs;
BOOL g_initialized = FALSE;
NTSTATUS g_status;
HANDLE g_hFile = NULL;
HANDLE g_hEvtStart = NULL;
HANDLE g_hEvtFinish = NULL;
HANDLE g_hThread = NULL;
PUNICODE_STRING g_pNameBuffer = NULL;
ULONG g_dwSize = 0;
ULONG g_dwLength = 0;

#define NTQO_TIMEOUT 100
#define MALLOC_ZERO(x) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (x))


static VOID
psutil_init_threads() {
    if (g_initialized == TRUE)
        return;

    // Create events for signalling work between threads
    g_hEvtStart = CreateEvent(NULL, FALSE, FALSE, NULL);
    g_hEvtFinish = CreateEvent(NULL, FALSE, FALSE, NULL);
    InitializeCriticalSection(&g_cs);
    g_initialized = TRUE;
}


static DWORD WINAPI
psutil_wait_thread(LPVOID lpvParam) {
    // Loop infinitely waiting for work
    while (TRUE) {
        WaitForSingleObject(g_hEvtStart, INFINITE);

        // TODO: return code not checked
        g_status = NtQueryObject(
            g_hFile,
            ObjectNameInformation,
            g_pNameBuffer,
            g_dwSize,
            &g_dwLength);
        SetEvent(g_hEvtFinish);
    }
}


static DWORD
psutil_create_thread() {
    DWORD dwWait = 0;

    if (g_hThread == NULL)
        g_hThread = CreateThread(
            NULL,
            0,
            psutil_wait_thread,
            NULL,
            0,
            NULL);
    if (g_hThread == NULL)
        return GetLastError();

    // Signal the worker thread to start
    SetEvent(g_hEvtStart);

    // Wait for the worker thread to finish
    dwWait = WaitForSingleObject(g_hEvtFinish, NTQO_TIMEOUT);

    // If the thread hangs, kill it and cleanup
    if (dwWait == WAIT_TIMEOUT) {
        SuspendThread(g_hThread);
        TerminateThread(g_hThread, 1);
        WaitForSingleObject(g_hThread, INFINITE);
        CloseHandle(g_hThread);

        g_hThread = NULL;
    }

    return dwWait;
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
        PyErr_SetFromOSErrnoWithSyscall("NtQuerySystemInformation");
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
    int                                 ret;
    DWORD                               i = 0;
    BOOLEAN                             error_occurred = FALSE;
    DWORD                               dwWait = 0;
    PyObject*                           py_retlist = NULL;
    PyObject*                           py_path = NULL;

    py_retlist = PyList_New(0);
    if (!py_retlist)
        return NULL;

    if (g_initialized == FALSE)
        psutil_init_threads();

    goto exit;

error:
    error_occurred = TRUE;
    goto exit;

exit:
    Py_DECREF(py_retlist);
    if (error_occurred == TRUE)
        return NULL;
    return py_retlist;
}


/*
    if (g_initialized == FALSE)
        psutil_get_open_files_init(TRUE);

    // Due to the use of global variables, ensure only 1 call
    // to psutil_get_open_files() is running
    EnterCriticalSection(&g_cs);

    if (g_hEvtStart == NULL || g_hEvtFinish == NULL) {
        PyErr_SetFromWindowsErr(0);
        error = TRUE;
        goto cleanup;
    }

    // Py_BuildValue raises an exception if NULL is returned
    py_retlist = PyList_New(0);
    if (py_retlist == NULL) {
        error = TRUE;
        goto cleanup;
    }

    ret = psutil_enum_handles(&handlesList);
    if (ret != 0)
        goto cleanup;

    for (i = 0; i < handlesList->NumberOfHandles; i++) {
        hHandle = &handlesList->Handles[i];

        // Check if this hHandle belongs to the PID the user specified.
        if ((ULONG_PTR)hHandle->UniqueProcessId != dwPid)
            goto loop_cleanup;

        if (!DuplicateHandle(hProcess,
                             (HANDLE)hHandle->HandleValue,
                             GetCurrentProcess(),
                             &g_hFile,
                             0,
                             TRUE,
                             DUPLICATE_SAME_ACCESS))
        {
            goto loop_cleanup;
        }

        // Guess buffer size is MAX_PATH + 1
        g_dwLength = (MAX_PATH+1) * sizeof(WCHAR);

        do {
            // Release any previously allocated buffer
            if (g_pNameBuffer != NULL) {
                FREE(g_pNameBuffer);
                g_pNameBuffer = NULL;
                g_dwSize = 0;
            }

            // NtQueryObject puts the required buffer size in g_dwLength
            // WinXP edge case puts g_dwLength == 0, just skip this handle
            if (g_dwLength == 0)
                goto loop_cleanup;

            g_dwSize = g_dwLength;
            if (g_dwSize > 0) {
                g_pNameBuffer = malloc(g_dwSize);

                if (g_pNameBuffer == NULL)
                    goto loop_cleanup;
            }

            dwWait = psutil_create_thread();

            // If the call does not return, skip this handle
            if (dwWait != WAIT_OBJECT_0)
                goto loop_cleanup;

        } while (g_status == STATUS_INFO_LENGTH_MISMATCH);

        // NtQueryObject stopped returning STATUS_INFO_LENGTH_MISMATCH
        if (!NT_SUCCESS(g_status))
            goto loop_cleanup;

        // Convert to PyUnicode and append it to the return list
        if (g_pNameBuffer->Length > 0) {
            py_path = PyUnicode_FromWideChar(g_pNameBuffer->Buffer,
                                             g_pNameBuffer->Length / 2);
            if (py_path == NULL) {
                error = TRUE;
                goto loop_cleanup;
            }

            if (PyList_Append(py_retlist, py_path)) {
                error = TRUE;
                goto loop_cleanup;
            }
        }

loop_cleanup:
    Py_XDECREF(py_path);
    py_path = NULL;
    if (g_pNameBuffer != NULL)
        FREE(g_pNameBuffer);
    g_pNameBuffer = NULL;
    g_dwSize = 0;
    g_dwLength = 0;
    if (g_hFile != NULL)
        CloseHandle(g_hFile);
    g_hFile = NULL;
}

cleanup:
    if (g_pNameBuffer != NULL)
        FREE(g_pNameBuffer);
    g_pNameBuffer = NULL;
    g_dwSize = 0;
    g_dwLength = 0;

    if (g_hFile != NULL)
        CloseHandle(g_hFile);
    g_hFile = NULL;

    if (handlesList != NULL)
        FREE(handlesList);
    handlesList = NULL;

    if (error) {
        Py_XDECREF(py_retlist);
        py_retlist = NULL;
    }

    LeaveCriticalSection(&g_cs);
    return py_retlist;
*/
