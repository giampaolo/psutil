/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 */
#include "process_handles.h"

static _NtQuerySystemInformation __NtQuerySystemInformation = NULL;
static _NtQueryObject __NtQueryObject = NULL;

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
PVOID g_fiber = NULL;

PVOID
GetLibraryProcAddress(PSTR LibraryName, PSTR ProcName)
{
    return GetProcAddress(GetModuleHandleA(LibraryName), ProcName);
}

VOID
psutil_get_open_files_init(void)
{
    if (g_initialized == TRUE)
        return;

    // Resolve the Windows API calls
    __NtQuerySystemInformation =
        GetLibraryProcAddress("ntdll.dll", "NtQuerySystemInformation");
    __NtQueryObject = GetLibraryProcAddress("ntdll.dll", "NtQueryObject");
    
    // Create events for signalling work between threads
    g_hEvtStart = CreateEvent(NULL, FALSE, FALSE, NULL);
    g_hEvtFinish = CreateEvent(NULL, FALSE, FALSE, NULL);
    InitializeCriticalSection(&g_cs);

    g_initialized = TRUE;
}

PyObject *
psutil_get_open_files(long dwPid, HANDLE hProcess)
{
    NTSTATUS                            status;
    PSYSTEM_HANDLE_INFORMATION_EX       pHandleInfo = NULL;
    DWORD                               dwInfoSize = 0x60000;
    PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX  hHandle = NULL;
    DWORD                               i = 0;
    BOOLEAN                             error = FALSE;
    PyObject*                           pyListFiles = NULL;
    PyObject*                           pyFilePath = NULL;
    DWORD                               dwWait = 0;

    if (g_initialized == FALSE)
        psutil_get_open_files_init();

    if (__NtQuerySystemInformation == NULL || 
        __NtQueryObject == NULL ||
        g_hEvtStart == NULL ||
        g_hEvtFinish == NULL)
    {
        PyErr_SetFromWindowsErr(0);
        error = TRUE;
        goto cleanup;
    }

    // Due to the use of global variables, ensure only 1 call
    // to psutil_get_open_files() is running
    EnterCriticalSection(&g_cs);

    // Py_BuildValue raises an exception if NULL is returned
    pyListFiles = PyList_New(0);
    if (pyListFiles == NULL)
    {
        error = TRUE;
        goto cleanup;
    }

    do
    {
        if (pHandleInfo != NULL)
        {
            HeapFree(GetProcessHeap(), 0, pHandleInfo);
            pHandleInfo = NULL;
        }

        pHandleInfo = HeapAlloc(GetProcessHeap(),
                                HEAP_ZERO_MEMORY,
                                dwInfoSize);

        if (pHandleInfo == NULL)
        {
            PyErr_NoMemory();
            error = TRUE;
            goto cleanup;
        }
    } while ((status = __NtQuerySystemInformation(
                            SystemExtendedHandleInformation,
                            pHandleInfo,
                            dwInfoSize,
                            &dwInfoSize)) == STATUS_INFO_LENGTH_MISMATCH);

    // NtQuerySystemInformation stopped giving us STATUS_INFO_LENGTH_MISMATCH
    if (!NT_SUCCESS(status))
    {
        PyErr_SetFromWindowsErr(HRESULT_FROM_NT(status));
        error = TRUE;
        goto cleanup;
    }

    for (i = 0; i < pHandleInfo->NumberOfHandles; i++)
    {
        hHandle = &pHandleInfo->Handles[i];

        // Check if this hHandle belongs to the PID the user specified.
        if (hHandle->UniqueProcessId != (HANDLE)dwPid ||
            hHandle->ObjectTypeIndex != HANDLE_TYPE_FILE)
            goto loop_cleanup;

        if (!DuplicateHandle(hProcess,
                             hHandle->HandleValue,
                             GetCurrentProcess(),
                             &g_hFile,
                             0,
                             TRUE,
                             DUPLICATE_SAME_ACCESS))
            goto loop_cleanup;

        // Guess buffer size is MAX_PATH + 1
        g_dwLength = (MAX_PATH+1) * sizeof(WCHAR);

        do
        {
            // Release any previously allocated buffer
            if (g_pNameBuffer != NULL)
            {
                HeapFree(GetProcessHeap(), 0, g_pNameBuffer);
                g_pNameBuffer = NULL;
                g_dwSize = 0;
            }

            // NtQueryObject puts the required buffer size in g_dwLength
            // WinXP edge case puts g_dwLength == 0, just skip this handle
            if (g_dwLength == 0)
                goto loop_cleanup;

            g_dwSize = g_dwLength;
            if (g_dwSize > 0)
            {
                g_pNameBuffer = HeapAlloc(GetProcessHeap(),
                                          HEAP_ZERO_MEMORY, 
                                          g_dwSize);

                if (g_pNameBuffer == NULL)
                    goto loop_cleanup;

            }

            dwWait = psutil_NtQueryObject();

            // If the call does not return, skip this handle
            if (dwWait != WAIT_OBJECT_0)
                goto loop_cleanup;

        } while (g_status == STATUS_INFO_LENGTH_MISMATCH);

        // NtQueryObject stopped returning STATUS_INFO_LENGTH_MISMATCH
        if (!NT_SUCCESS(g_status))
            goto loop_cleanup;

        // Convert to PyUnicode and append it to the return list
        if (g_pNameBuffer->Length > 0)
        {
            pyFilePath = PyUnicode_FromWideChar(g_pNameBuffer->Buffer,
                                                g_pNameBuffer->Length/2);
            if (pyFilePath == NULL)
            {
                error = TRUE;
                goto loop_cleanup;
            }

            if (PyList_Append(pyListFiles, pyFilePath))
            {
                error = TRUE;
                goto loop_cleanup;
            }
        }

loop_cleanup:
        Py_XDECREF(pyFilePath);
        pyFilePath = NULL;

        if (g_hFile != NULL)
            CloseHandle(g_hFile);
        g_hFile = NULL;

        if (g_pNameBuffer != NULL)
            HeapFree(GetProcessHeap(), 0, g_pNameBuffer);
        g_pNameBuffer = NULL;
        g_dwSize = 0;
        g_dwLength = 0;
    }

cleanup:
    if (pHandleInfo != NULL)
        HeapFree(GetProcessHeap(), 0, pHandleInfo);
    pHandleInfo = NULL;

    if (g_hFile != NULL)
        CloseHandle(g_hFile);
    g_hFile = NULL;

    if (g_pNameBuffer != NULL)
        HeapFree(GetProcessHeap(), 0, g_pNameBuffer);
    g_pNameBuffer = NULL;
    g_dwSize = 0;
    g_dwLength = 0;

    if (error)
    {
        Py_XDECREF(pyListFiles);
        pyListFiles = NULL;
    }

    LeaveCriticalSection(&g_cs);
    return pyListFiles;
}

DWORD
psutil_NtQueryObject()
{
    DWORD dwWait = 0;

    if (g_hThread == NULL)
        g_hThread = CreateThread(NULL,
                                 0,
                                 (LPTHREAD_START_ROUTINE)psutil_NtQueryObjectThread,
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
    if (dwWait == WAIT_TIMEOUT)
    {
        SuspendThread(g_hThread);
        TerminateThread(g_hThread, 1);
        // TerminateThread is async
        WaitForSingleObject(g_hThread, NTQO_TIMEOUT);
        
        // Cleanup Fiber
        if (g_fiber != NULL)
            DeleteFiber(g_fiber);
        g_fiber = NULL;

        CloseHandle(g_hThread);
        g_hThread = NULL;
    }

    return dwWait;
}

void
psutil_NtQueryObjectThread()
{
    // Prevent the thread stack from leaking when this
    // thread gets terminated due to NTQueryObject hanging
    g_fiber = ConvertThreadToFiber(NULL);

    // Loop infinitely waiting for work
    while (TRUE)
    {
        WaitForSingleObject(g_hEvtStart, INFINITE);
        g_status = __NtQueryObject(g_hFile, 
                                   ObjectNameInformation,
                                   g_pNameBuffer,
                                   g_dwSize,
                                   &g_dwLength);
        SetEvent(g_hEvtFinish);
    }
}
