/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// This module retrieves file handles opened by a process. The
// handle-related calls below are listed in the order in which they
// are made.
//
// call                          | purpose                         | blocks
// ------------------------------+---------------------------------+-----------
// NtQueryObject(                | find the object type index for  | no
//     ObjectTypesInformation)   | "File"; cached until reboot     |
// ------------------------------+---------------------------------+-----------
// NtQueryInformationProcess(    | enumerate process handles       | no
//     ProcessHandleInformation) |                                 |
// ------------------------------+---------------------------------+-----------
// DuplicateHandle()             | copy each File handle into this | no
//                               | process so that we can query it |
// ------------------------------+---------------------------------+-----------
// GetFileType()                 | discard non-disk handles        | network
// ------------------------------+---------------------------------+-----------
// NtQueryInformationFile(       | reject directories and handles  | lock, wire
//     FileStandardInformation)  | pending deletion                |
// ------------------------------+---------------------------------+-----------
// NtQueryInformationFile(       | reject directory index streams  | lock, wire
//     FileBasicInformation)     | using FILE_ATTRIBUTE_DIRECTORY  |
// ------------------------------+---------------------------------+-----------
// NtQueryObject(                | get the path in device form:    | lock
//     ObjectNameInformation)    | \Device\HarddiskVolume2\x\y.txt |
// ------------------------------+---------------------------------+-----------
//
//   lock
//       Waits for the FILE_OBJECT lock. A blocking synchronous read
//       may hold this lock indefinitely, as with an idle pipe.
//       DuplicateHandle() creates another handle to the same
//       FILE_OBJECT, so the duplicate inherits the same wait.
//
//   wire
//       In addition to waiting for the FILE_OBJECT lock, the query
//       needs an answer from whatever serves the file behind
//       \Device\Mup: an SMB, WebDAV or NFS server, or a user-mode
//       filesystem provider. If it stops answering, the query blocks
//       until the session times out, about a minute for SMB.
//
//   network
//       Blocks on network handles only. NPFS and ConDrv answer
//       GetFileType() without taking the FILE_OBJECT lock.
//
// The first 3 calls run on the main thread. They are cheap and won't
// block. The rest can block, so they run in a worker thread with a
// timeout, created lazily and reused for every handle.
//
// On timeout, the worker is killed and replaced, or abandoned in the
// unlikely case it refuses to die. Killing it is safe only because its
// body is strictly syscalls: it never touches the heap, the Python C
// API or the CRT, and it never exits on its own. The old code killed
// a thread that did all of that and deadlocked, see #1967.
//
// Note: NtQueryInformationFile(FileVolumeNameInformation) (not used
// here) is the only syscall that never blocks, on any handle. It
// cannot replace any of the calls above though, because it returns the
// backing device (e.g. \Device\Mup) and not the path. Nor can it be
// used to skip the directory checks on network handles, since a
// network directory would then be reported as a file.
//
// This design mirrors SystemInformer when its kernel driver is not
// loaded:
// https://github.com/winsiderss/systeminformer/blob/245c808f011/phlib/hndlinfo.c#L521
//
// History:
// - https://github.com/giampaolo/psutil/pull/597
// - https://github.com/giampaolo/psutil/pull/2190
// - https://github.com/giampaolo/psutil/pull/2894
//
// CREDITS: the original implementation was written by Jeff Tang and
// later rewritten by Giampaolo Rodola. Final implementation was
// adapted using SystemInformer as a guide.

#include <windows.h>
#include <Python.h>

#include "../../arch/all/init.h"


#define THREAD_TIMEOUT 100  // ms
#define KILL_JOIN_TIMEOUT 1000  // ms

typedef struct {
    HANDLE hThread;
    HANDLE hStartEvent;  // auto-reset, main -> worker: work is ready
    HANDLE hDoneEvent;  // auto-reset, worker -> main: work is done
    HANDLE hFile;  // in: the handle to query
    PUNICODE_STRING fileName;  // in: caller-allocated result buffer
    ULONG bufferSize;  // in
    ULONG returnLength;  // out
    NTSTATUS status;  // out
    int quit;  // main thread asks the worker to exit
} Worker;


// ObjectTypesInformation buffer walking, adapted from SystemInformer's
// phnt headers. Entries are variable-size: each OBJECT_TYPE_INFORMATION
// is followed by its type name buffer, padded to pointer alignment.
// clang-format off
#define ALIGN_UP_PTR(x) \
    (((ULONG_PTR)(x) + sizeof(ULONG_PTR) - 1) & ~(sizeof(ULONG_PTR) - 1))

#define FIRST_OBJECT_TYPE(types) \
    ((POBJECT_TYPE_INFORMATION)ALIGN_UP_PTR( \
        (ULONG_PTR)(types) + sizeof(OBJECT_TYPES_INFORMATION)))

#define NEXT_OBJECT_TYPE(entry) \
    ((POBJECT_TYPE_INFORMATION)((ULONG_PTR)(entry) \
        + sizeof(OBJECT_TYPE_INFORMATION) \
        + ALIGN_UP_PTR((entry)->TypeName.MaximumLength)))
// clang-format on


// Find the kernel object type index for "File" handles, so that we
// can tell whether a handle refers to a file without touching it.
// The index is stable until reboot; resolve it once and cache it.
// Return 0 on success, -1 on error.
static int
get_file_type_index(ULONG *indexOut) {
    static ULONG cachedIndex = 0;
    NTSTATUS status;
    POBJECT_TYPES_INFORMATION typesInfo = NULL;
    POBJECT_TYPE_INFORMATION entry;
    ULONG bufferSize = 0x1000;
    ULONG returnLength = 0;
    ULONG i;
    int attempts = 8;

    if (cachedIndex != 0) {
        *indexOut = cachedIndex;
        return 0;
    }

    do {
        typesInfo = MALLOC_ZERO(bufferSize);
        if (typesInfo == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        status = NtQueryObject(
            NULL, ObjectTypesInformation, typesInfo, bufferSize, &returnLength
        );
        if (status != STATUS_INFO_LENGTH_MISMATCH)
            break;
        FREE(typesInfo);
        typesInfo = NULL;
        bufferSize = returnLength + 0x1000;
    } while (--attempts);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQueryObject");
        if (typesInfo != NULL)
            FREE(typesInfo);
        return -1;
    }

    entry = FIRST_OBJECT_TYPE(typesInfo);
    for (i = 0; i < typesInfo->NumberOfTypes; i++) {
        if (entry->TypeName.Length == 4 * sizeof(WCHAR)
            && memcmp(entry->TypeName.Buffer, L"File", 4 * sizeof(WCHAR)) == 0)
        {
            cachedIndex = entry->TypeIndex;
            *indexOut = cachedIndex;
            FREE(typesInfo);
            return 0;
        }
        entry = NEXT_OBJECT_TYPE(entry);
    }

    FREE(typesInfo);
    psutil_runtime_error("'File' object type not found");
    return -1;
}


static int
enum_process_handles(
    HANDLE hProcess, PPROCESS_HANDLE_SNAPSHOT_INFORMATION *snapshot
) {
    NTSTATUS status;
    PVOID buffer = NULL;
    ULONG bufferSize = 0x8000;
    DWORD returnLength = 0;
    int attempts = 8;

    do {
        // Zeroed buffer: some Windows versions return success for
        // minimal processes without writing anything, so make sure
        // NumberOfHandles reads as 0 in that case.
        buffer = MALLOC_ZERO(bufferSize);
        if (buffer == NULL) {
            PyErr_NoMemory();
            return -1;
        }
        status = NtQueryInformationProcess(
            hProcess,
            ProcessHandleInformation,
            buffer,
            bufferSize,
            &returnLength
        );
        if (status != STATUS_INFO_LENGTH_MISMATCH)
            break;
        FREE(buffer);
        buffer = NULL;
        // The handle table may grow between calls; leave some slack.
        bufferSize = returnLength + 0x1000;
    } while (--attempts);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQueryInformationProcess");
        if (buffer != NULL)
            FREE(buffer);
        return -1;
    }

    *snapshot = (PPROCESS_HANDLE_SNAPSHOT_INFORMATION)buffer;
    return 0;
}


// Runs in a separate thread. The body is strictly syscalls: no
// Python, no heap, no CRT. The main thread may TerminateThread()
// this thread at any point between the two events, so anything that
// can hold a user-mode lock is off limits. Buffers are allocated and
// freed by the main thread, which also reports errors.
static DWORD WINAPI
worker_loop(LPVOID lpvParam) {
    Worker *w = (Worker *)lpvParam;
    FILE_STANDARD_INFORMATION info;
    FILE_BASIC_INFORMATION basicInfo;
    IO_STATUS_BLOCK iosb;
    BOOLEAN wanted;

    while (1) {
        WaitForSingleObject(w->hStartEvent, INFINITE);
        if (w->quit)
            return 0;
        w->status = 0;  // success
        // These can block, which is why they run here. When we skip
        // the name query the buffer is left zeroed, meaning "no
        // name", and the caller skips the handle.
        wanted = FALSE;
        if (GetFileType(w->hFile) == FILE_TYPE_DISK
            && NT_SUCCESS(NtQueryInformationFile(
                w->hFile,
                &iosb,
                &info,
                sizeof(info),
                (FILE_INFORMATION_CLASS)FileStandardInformation
            ))
            && !info.Directory && !info.DeletePending)
        {
            wanted = TRUE;
            // A handle to the index stream of a directory reports
            // Directory = FALSE, e.g.
            // "C:\$Extend\$ObjId:$O:$INDEX_ALLOCATION". The file
            // attributes are what os.stat() looks at, and they get it
            // right.
            if (NT_SUCCESS(NtQueryInformationFile(
                    w->hFile,
                    &iosb,
                    &basicInfo,
                    sizeof(basicInfo),
                    (FILE_INFORMATION_CLASS)FileBasicInformation
                ))
                && (basicInfo.FileAttributes & FILE_ATTRIBUTE_DIRECTORY))
            {
                wanted = FALSE;
            }
        }

        if (wanted) {
            w->status = NtQueryObject(
                w->hFile,
                ObjectNameInformation,
                w->fileName,
                w->bufferSize,
                &w->returnLength
            );
        }
        SetEvent(w->hDoneEvent);
    }
}


static Worker *
worker_create(void) {
    Worker *w;

    w = MALLOC_ZERO(sizeof(Worker));
    if (w == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    w->hStartEvent = CreateEvent(NULL, FALSE, FALSE, NULL);
    w->hDoneEvent = CreateEvent(NULL, FALSE, FALSE, NULL);
    if (w->hStartEvent == NULL || w->hDoneEvent == NULL) {
        psutil_oserror_wsyscall("CreateEvent");
        goto error;
    }

    // Small stack: the thread only issues syscalls. Keeps the cost
    // down if the worker gets stuck and leaks.
    w->hThread = CreateThread(
        NULL, 0x10000, worker_loop, w, STACK_SIZE_PARAM_IS_A_RESERVATION, NULL
    );
    if (w->hThread == NULL) {
        psutil_oserror_wsyscall("CreateThread");
        goto error;
    }
    return w;

error:
    if (w->hStartEvent != NULL)
        CloseHandle(w->hStartEvent);
    if (w->hDoneEvent != NULL)
        CloseHandle(w->hDoneEvent);
    FREE(w);
    return NULL;
}


// Only for a live (not abandoned) worker: it's idle, so it exits
// right away and the wait is bounded.
static void
worker_destroy(Worker *w) {
    w->quit = 1;
    SetEvent(w->hStartEvent);
    Py_BEGIN_ALLOW_THREADS
    WaitForSingleObject(w->hThread, INFINITE);
    Py_END_ALLOW_THREADS
    CloseHandle(w->hThread);
    CloseHandle(w->hStartEvent);
    CloseHandle(w->hDoneEvent);
    FREE(w);
}


// Query the name of hFile on the worker thread, with a timeout. Return
// 0 on success (*nameOut set, may have Length 0), -1 on error (Python
// exception set), WAIT_TIMEOUT if the query got stuck. On WAIT_TIMEOUT
// the worker is killed and hFile is closed (or leaked if the kill
// fails); either way the caller must not touch hFile. *workerRef is
// reset to NULL; the next call creates a new worker.
static DWORD
worker_get_filename(
    Worker **workerRef, HANDLE hFile, PUNICODE_STRING *nameOut
) {
    Worker *w = NULL;
    DWORD dwWait;
    NTSTATUS status = 0;
    PUNICODE_STRING name = NULL;
    ULONG bufferSize = 0x200;
    ULONG attempts = 8;

    *nameOut = NULL;

    // A loop is needed because the I/O subsystem likes to give us the wrong
    // return lengths... Buffers are (re)allocated in here so that the worker
    // never touches the heap.
    do {
        name = MALLOC_ZERO(bufferSize);
        if (name == NULL) {
            PyErr_NoMemory();
            return -1;
        }

        w = *workerRef;
        if (w == NULL) {
            w = worker_create();
            if (w == NULL) {
                FREE(name);
                return -1;
            }
            *workerRef = w;
        }

        w->hFile = hFile;
        w->fileName = name;
        w->bufferSize = bufferSize;
        SetEvent(w->hStartEvent);

        // The worker may hang on a lock or on the wire, hence the
        // timeout. Don't make the rest of the interpreter wait with us.
        Py_BEGIN_ALLOW_THREADS
        dwWait = WaitForSingleObject(w->hDoneEvent, THREAD_TIMEOUT);
        Py_END_ALLOW_THREADS

        if (dwWait != WAIT_OBJECT_0) {
            if (dwWait == WAIT_FAILED)
                psutil_debug("WaitForSingleObject -> WAIT_FAILED");
            psutil_debug(
                "get handle name thread timed out after %i ms; killing it",
                THREAD_TIMEOUT
            );
            // The worker is stuck in the kernel. Kill it: its body is strictly
            // syscalls, so there is no user-mode lock it can orphan.
            if (!TerminateThread(w->hThread, 0))
                psutil_debug("TerminateThread -> FALSE");
            Py_BEGIN_ALLOW_THREADS
            dwWait = WaitForSingleObject(w->hThread, KILL_JOIN_TIMEOUT);
            Py_END_ALLOW_THREADS
            if (dwWait == WAIT_OBJECT_0) {
                // Worker is gone. Closing our duplicate won't block.
                CloseHandle(w->hThread);
                CloseHandle(w->hStartEvent);
                CloseHandle(w->hDoneEvent);
                CloseHandle(w->hFile);
                FREE(w->fileName);
                FREE(w);
            }
            else {
                // Should not happen: the thread is stuck in an unkillable
                // kernel wait. Leak it, along with hFile, the events and the
                // name buffer, which the kernel may still write to. The
                // pending termination will kill the thread before it ever runs
                // user code again.
                psutil_debug("killed worker did not exit; leaking it");
                CloseHandle(w->hThread);
            }
            *workerRef = NULL;
            return WAIT_TIMEOUT;
        }

        status = w->status;
        if (status == STATUS_BUFFER_OVERFLOW
            || status == STATUS_INFO_LENGTH_MISMATCH
            || status == STATUS_BUFFER_TOO_SMALL)
        {
            FREE(name);
            name = NULL;
            bufferSize = w->returnLength;
        }
        else {
            break;
        }
    } while (--attempts);

    if (!NT_SUCCESS(status)) {
        psutil_SetFromNTStatusErr(status, "NtQueryObject");
        if (name != NULL)
            FREE(name);
        return -1;
    }
    *nameOut = name;
    return 0;
}


PyObject *
psutil_get_open_files(HANDLE hProcess) {
    PPROCESS_HANDLE_SNAPSHOT_INFORMATION snapshot = NULL;
    PPROCESS_HANDLE_TABLE_ENTRY_INFO entry = NULL;
    Worker *worker = NULL;
    HANDLE hFile = NULL;
    PUNICODE_STRING fileName = NULL;
    ULONG_PTR i = 0;
    ULONG fileTypeIndex = 0;
    BOOLEAN errorOccurred = FALSE;
    DWORD dwRet;
    PyObject *py_retlist = PyList_New(0);

    if (!py_retlist)
        return NULL;

    if (get_file_type_index(&fileTypeIndex) != 0)
        goto error;
    if (enum_process_handles(hProcess, &snapshot) != 0)
        goto error;

    for (i = 0; i < snapshot->NumberOfHandles; i++) {
        entry = &snapshot->Handles[i];
        // Skip anything that is not a File object (events, keys,
        // threads, ...), which is usually most of the handles.
        if (entry->ObjectTypeIndex != fileTypeIndex)
            continue;
        if (!DuplicateHandle(
                hProcess,
                entry->HandleValue,
                GetCurrentProcess(),
                &hFile,
                0,
                TRUE,
                DUPLICATE_SAME_ACCESS
            ))
        {
            // The process may have closed it in the meantime.
            continue;
        }

        dwRet = worker_get_filename(&worker, hFile, &fileName);
        if (dwRet == WAIT_TIMEOUT) {
            // Already closed (or deliberately leaked) along with the
            // killed worker; skip this handle.
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
    if (worker != NULL)
        worker_destroy(worker);
    if (hFile != NULL)
        CloseHandle(hFile);
    if (fileName != NULL)
        FREE(fileName);
    if (snapshot != NULL)
        FREE(snapshot);

    if (errorOccurred == TRUE)
        return NULL;
    return py_retlist;
}
