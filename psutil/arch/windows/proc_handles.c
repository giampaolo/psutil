/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// This module retrieves handles opened by a process.
//
// We use NtQuerySystemInformation to enumerate them and NtQueryObject
// to obtain the corresponding file name.
//
// NtQueryObject / GetFileType block forever on pipes with a pending
// blocking read, so we call them in a separate thread with a timeout.
// The thread is never killed: TerminateThread() can't terminate a
// thread waiting in the kernel, and if it lands while the thread is
// exiting it orphans the loader lock, deadlocking the next
// CreateThread(). On timeout we just abandon the thread; it cleans
// up after itself if it ever completes. See:
// https://github.com/giampaolo/psutil/pull/597
//
// CREDITS: original implementation was written by Jeff Tang. It was
// then rewritten by Giampaolo Rodola many years later. Utility
// functions for getting the file handles and names were re-adapted
// from the excellent ProcessHacker.

#include <windows.h>
#include <Python.h>

#include "../../arch/all/init.h"


#define THREAD_TIMEOUT 100  // ms

// Ownership handoff between the main thread and the query thread.
#define QS_RUNNING 0
#define QS_DONE 1  // thread finished, main thread consumes the result
#define QS_ABANDONED 2  // main thread timed out, thread cleans up

typedef struct {
    HANDLE hFile;
    PUNICODE_STRING fileName;
    NTSTATUS status;
    int oom;
    volatile LONG state;
} QueryCtx;


static int
psutil_enum_handles(PSYSTEM_HANDLE_INFORMATION_EX *handles) {
    static ULONG initialBufferSize = 0x10000;
    NTSTATUS status;
    PVOID buffer;
    ULONG bufferSize;

    bufferSize = initialBufferSize;
    buffer = MALLOC_ZERO(bufferSize);
    if (buffer == NULL) {
        PyErr_NoMemory();
        return -1;
    }

    while ((status = NtQuerySystemInformation(
                SystemExtendedHandleInformation, buffer, bufferSize, NULL
            ))
           == STATUS_INFO_LENGTH_MISMATCH)
    {
        FREE(buffer);
        bufferSize *= 2;

        // Fail if we're resizing the buffer to something very large.
        if (bufferSize > 256 * 1024 * 1024) {
            psutil_runtime_error(
                "SystemExtendedHandleInformation buffer too big"
            );
            return -1;
        }

        buffer = MALLOC_ZERO(bufferSize);
        if (buffer == NULL) {
            PyErr_NoMemory();
            return -1;
        }
    }

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQuerySystemInformation");
        FREE(buffer);
        return -1;
    }

    *handles = (PSYSTEM_HANDLE_INFORMATION_EX)buffer;
    return 0;
}


// Runs in a separate thread. No Python calls in here: the main
// thread holds the GIL and reports errors via ctx.
static DWORD WINAPI
psutil_get_filename(LPVOID lpvParam) {
    QueryCtx *ctx = (QueryCtx *)lpvParam;
    NTSTATUS status = 0;  // success
    ULONG bufferSize = 0x200;
    ULONG attempts = 8;
    PUNICODE_STRING name;

    name = MALLOC_ZERO(bufferSize);
    if (name == NULL) {
        ctx->oom = 1;
        goto done;
    }

    // Note: also this is supposed to hang, hence why we do it in here.
    if (GetFileType(ctx->hFile) != FILE_TYPE_DISK) {
        name->Length = 0;  // means "no name", skipped by the caller
        goto done;
    }

    // A loop is needed because the I/O subsystem likes to give us the
    // wrong return lengths...
    do {
        status = NtQueryObject(
            ctx->hFile, ObjectNameInformation, name, bufferSize, &bufferSize
        );
        if (status == STATUS_BUFFER_OVERFLOW
            || status == STATUS_INFO_LENGTH_MISMATCH
            || status == STATUS_BUFFER_TOO_SMALL)
        {
            FREE(name);
            name = MALLOC_ZERO(bufferSize);
            if (name == NULL) {
                ctx->oom = 1;
                goto done;
            }
        }
        else {
            break;
        }
    } while (--attempts);

done:
    ctx->fileName = name;
    ctx->status = status;
    if (InterlockedCompareExchange(&ctx->state, QS_DONE, QS_RUNNING)
        != QS_RUNNING)
    {
        // Main thread gave up on us: nobody consumes this.
        if (name != NULL)
            FREE(name);
        CloseHandle(ctx->hFile);
        FREE(ctx);
    }
    return 0;
}


// Return 0 on success (*nameOut set, may have Length 0), -1 on error
// (Python exception set), WAIT_TIMEOUT if the query thread is stuck.
// On WAIT_TIMEOUT ownership of hFile moves to the thread; the caller
// must not close it.
static DWORD
psutil_threaded_get_filename(HANDLE hFile, PUNICODE_STRING *nameOut) {
    DWORD dwWait;
    HANDLE hThread;
    QueryCtx *ctx;

    *nameOut = NULL;
    ctx = MALLOC_ZERO(sizeof(QueryCtx));
    if (ctx == NULL) {
        PyErr_NoMemory();
        return -1;
    }
    ctx->hFile = hFile;
    ctx->state = QS_RUNNING;

    hThread = CreateThread(NULL, 0, psutil_get_filename, ctx, 0, NULL);
    if (hThread == NULL) {
        FREE(ctx);
        psutil_oserror_wsyscall("CreateThread");
        return -1;
    }

    dwWait = WaitForSingleObject(hThread, THREAD_TIMEOUT);
    if (dwWait != WAIT_OBJECT_0) {
        if (dwWait == WAIT_FAILED)
            psutil_debug("WaitForSingleObject -> WAIT_FAILED");
        if (InterlockedCompareExchange(&ctx->state, QS_ABANDONED, QS_RUNNING)
            == QS_RUNNING)
        {
            // Abandon the stuck thread; it cleans up by itself if it
            // ever completes.
            psutil_debug(
                "get handle name thread timed out after %i ms", THREAD_TIMEOUT
            );
            CloseHandle(hThread);
            return WAIT_TIMEOUT;
        }
        // The thread completed right after the timeout: fall through
        // and consume its result.
    }
    CloseHandle(hThread);

    if (ctx->oom) {
        FREE(ctx);
        PyErr_NoMemory();
        return -1;
    }
    if (!NT_SUCCESS(ctx->status)) {
        psutil_SetFromNTStatusErr(ctx->status, "NtQueryObject");
        if (ctx->fileName != NULL)
            FREE(ctx->fileName);
        FREE(ctx);
        return -1;
    }
    *nameOut = ctx->fileName;
    FREE(ctx);
    return 0;
}


PyObject *
psutil_get_open_files(DWORD dwPid, HANDLE hProcess) {
    PSYSTEM_HANDLE_INFORMATION_EX handlesList = NULL;
    PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX hHandle = NULL;
    HANDLE hFile = NULL;
    PUNICODE_STRING fileName = NULL;
    ULONG i = 0;
    BOOLEAN errorOccurred = FALSE;
    DWORD dwRet;
    PyObject *py_retlist = PyList_New(0);
    ;

    if (!py_retlist)
        return NULL;

    if (psutil_enum_handles(&handlesList) != 0)
        goto error;

    for (i = 0; i < handlesList->NumberOfHandles; i++) {
        hHandle = &handlesList->Handles[i];
        if ((ULONG_PTR)hHandle->UniqueProcessId != dwPid)
            continue;
        if (!DuplicateHandle(
                hProcess,
                hHandle->HandleValue,
                GetCurrentProcess(),
                &hFile,
                0,
                TRUE,
                DUPLICATE_SAME_ACCESS
            ))
        {
            // Will fail if not a regular file; just skip it.
            continue;
        }

        dwRet = psutil_threaded_get_filename(hFile, &fileName);
        if (dwRet == WAIT_TIMEOUT) {
            // The abandoned thread owns hFile now. Closing it here
            // would block: the thread is stuck in the kernel holding
            // a lock on this handle's file object, and CloseHandle()
            // needs the same lock.
            hFile = NULL;
            continue;
        }
        if (dwRet != 0)
            goto error;

        if ((fileName != NULL) && (fileName->Length > 0)) {
            if (!pylist_append_obj(
                    py_retlist,
                    PyUnicode_FromWideChar(
                        fileName->Buffer, wcslen(fileName->Buffer)
                    )
                ))
                goto error;
        }

        // Loop cleanup section.
        if (fileName != NULL) {
            FREE(fileName);
            fileName = NULL;
        }
        CloseHandle(hFile);
        hFile = NULL;
    }

    goto exit;

error:
    Py_XDECREF(py_retlist);
    errorOccurred = TRUE;
    goto exit;

exit:
    if (hFile != NULL)
        CloseHandle(hFile);
    if (fileName != NULL)
        FREE(fileName);
    if (handlesList != NULL)
        FREE(handlesList);

    if (errorOccurred == TRUE)
        return NULL;
    return py_retlist;
}
