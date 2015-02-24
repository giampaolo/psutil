/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 */

#ifndef UNICODE
#define UNICODE
#endif

#include <Python.h>
#include <stdio.h>
#include <windows.h>
#include <strsafe.h>
#include "process_handles.h"

#ifndef NT_SUCCESS
#define NT_SUCCESS(x) ((x) >= 0)
#endif

#define STATUS_INFO_LENGTH_MISMATCH 0xc0000004

#include <winternl.h>
#define ObjectBasicInformation 0
#define ObjectNameInformation 1
#define ObjectTypeInformation 2

#define HANDLE_TYPE_FILE 28


typedef LONG NTSTATUS;

typedef NTSTATUS (NTAPI *_NtQuerySystemInformation)(
    ULONG SystemInformationClass,
    PVOID SystemInformation,
    ULONG SystemInformationLength,
    PULONG ReturnLength
);

typedef NTSTATUS (NTAPI *_NtDuplicateObject)(
    HANDLE SourceProcessHandle,
    HANDLE SourceHandle,
    HANDLE TargetProcessHandle,
    PHANDLE TargetHandle,
    ACCESS_MASK DesiredAccess,
    ULONG Attributes,
    ULONG Options
);

typedef NTSTATUS (NTAPI *_NtQueryObject)(
    HANDLE ObjectHandle,
    ULONG ObjectInformationClass,
    PVOID ObjectInformation,
    ULONG ObjectInformationLength,
    PULONG ReturnLength
);


// Undocumented FILE_INFORMATION_CLASS: FileNameInformation
const SYSTEM_INFORMATION_CLASS SystemExtendedHandleInformation = (SYSTEM_INFORMATION_CLASS)64;

typedef struct _SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX
{
    PVOID Object;
    HANDLE UniqueProcessId;
    HANDLE HandleValue;
    ULONG GrantedAccess;
    USHORT CreatorBackTraceIndex;
    USHORT ObjectTypeIndex;
    ULONG HandleAttributes;
    ULONG Reserved;
} SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX, *PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX;

typedef struct _SYSTEM_HANDLE_INFORMATION_EX
{
    ULONG_PTR NumberOfHandles;
    ULONG_PTR Reserved;
    SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX Handles[1];
} SYSTEM_HANDLE_INFORMATION_EX, *PSYSTEM_HANDLE_INFORMATION_EX;


typedef enum _POOL_TYPE {
    NonPagedPool,
    PagedPool,
    NonPagedPoolMustSucceed,
    DontUseThisType,
    NonPagedPoolCacheAligned,
    PagedPoolCacheAligned,
    NonPagedPoolCacheAlignedMustS
} POOL_TYPE, *PPOOL_TYPE;

typedef struct _OBJECT_TYPE_INFORMATION {
    UNICODE_STRING Name;
    ULONG TotalNumberOfObjects;
    ULONG TotalNumberOfHandles;
    ULONG TotalPagedPoolUsage;
    ULONG TotalNonPagedPoolUsage;
    ULONG TotalNamePoolUsage;
    ULONG TotalHandleTableUsage;
    ULONG HighWaterNumberOfObjects;
    ULONG HighWaterNumberOfHandles;
    ULONG HighWaterPagedPoolUsage;
    ULONG HighWaterNonPagedPoolUsage;
    ULONG HighWaterNamePoolUsage;
    ULONG HighWaterHandleTableUsage;
    ULONG InvalidAttributes;
    GENERIC_MAPPING GenericMapping;
    ULONG ValidAccess;
    BOOLEAN SecurityRequired;
    BOOLEAN MaintainHandleCount;
    USHORT MaintainTypeList;
    POOL_TYPE PoolType;
    ULONG PagedPoolUsage;
    ULONG NonPagedPoolUsage;
} OBJECT_TYPE_INFORMATION, *POBJECT_TYPE_INFORMATION;

PVOID
GetLibraryProcAddress(PSTR LibraryName, PSTR ProcName)
{
    return GetProcAddress(GetModuleHandleA(LibraryName), ProcName);
}

PyObject *
psutil_get_open_files(long pid, HANDLE processHandle)
{
    _NtQuerySystemInformation NtQuerySystemInformation =
        GetLibraryProcAddress("ntdll.dll", "NtQuerySystemInformation");

    _NtQueryObject NtQueryObject =
        GetLibraryProcAddress("ntdll.dll", "NtQueryObject");

    NTSTATUS                            status;
    HANDLE                              hHeap = NULL;
    PSYSTEM_HANDLE_INFORMATION_EX       pSystemHandleInformationInfo = NULL;
    ULONG                               systemHandleInformationInfoSize = 0x8000;
    PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX  hHandle = NULL;
    PUNICODE_STRING                     pObjectName = NULL;
    ULONG                               objectNameSize = 0;
    ULONG                               i = 0;
    DWORD                               nReturn = 0;
    BOOLEAN                             error = FALSE;
    PyObject*                           pyListFiles = Py_BuildValue("[]");
    PyObject*                           pyFilePath = NULL;
    HANDLE                              hFile = NULL;
    HANDLE                              hMap = NULL;
    LPTSTR                              lpszFilePath = NULL;


    if (!(hHeap = GetProcessHeap()))
    {
        PyErr_NoMemory();
        error = TRUE;
        goto cleanup;
    }

    // Py_BuildValue raises an exception if NULL is returned
    if (pyListFiles == NULL)
    {
        error = TRUE;
        goto cleanup;
    }

    // NtQuerySystemInformation won't give us the correct buffer size,
    // so we guess by doubling the buffer size.
    do {
        if (pSystemHandleInformationInfo != NULL)
            HeapFree(hHeap, 0, pSystemHandleInformationInfo);

        systemHandleInformationInfoSize *= 2;
        pSystemHandleInformationInfo = (PSYSTEM_HANDLE_INFORMATION_EX)
                        HeapAlloc(hHeap, 0, systemHandleInformationInfoSize);

        if (pSystemHandleInformationInfo == NULL)
        {
            PyErr_NoMemory();
            error = TRUE;
            goto cleanup;
        }
    } while ((status = NtQuerySystemInformation(
                            SystemExtendedHandleInformation,
                            pSystemHandleInformationInfo,
                            systemHandleInformationInfoSize,
                            &nReturn)) == STATUS_INFO_LENGTH_MISMATCH);
    // NtQuerySystemInformation stopped giving us STATUS_INFO_LENGTH_MISMATCH
    // Check to verify it returned a success condition
    if (!NT_SUCCESS(status)) {
        error = TRUE;
        goto cleanup;
    }

    for (i = 0; i < pSystemHandleInformationInfo->NumberOfHandles; i++)
    {
        hHandle = &pSystemHandleInformationInfo->Handles[i];

        // Check if this hHandle belongs to the PID the user specified.
        if (hHandle->UniqueProcessId != (HANDLE)pid ||
            hHandle->ObjectTypeIndex != HANDLE_TYPE_FILE)
        {
            goto loop_cleanup;
        }

        if (!DuplicateHandle(processHandle,
                             hHandle->HandleValue,
                             GetCurrentProcess(),
                             &hFile,
                             0,
                             TRUE,
                             DUPLICATE_SAME_ACCESS))
        {
            //printf("[%d] DuplicateHandle (%#x): %#x \n",
            //       pid,
            //       hHandle->HandleValue,
            //       GetLastError());
            goto loop_cleanup;
        }

        hMap = CreateFileMapping(hFile, NULL, PAGE_READONLY, 0, 0, NULL);
        if (hMap == NULL) {
            //printf("[%d] CreateFileMapping (%#x): %#x \n",
            //       pid,
            //       hHandle->HandleValue,
            //       GetLastError());
            if (GetLastError() == ERROR_BAD_EXE_FORMAT)
            {
                goto loop_cleanup;
            }
        }
        CloseHandle(hMap);
        
        //printf("[%#d] Pre-NtQueryObject (%#x)\n", pid, hHandle->HandleValue);

        // Call NtQueryObject to determine the correct size
        NtQueryObject(hFile,
                      ObjectNameInformation,
                      pObjectName,
                      0,
                      &objectNameSize);
        pObjectName = HeapAlloc(hHeap, HEAP_ZERO_MEMORY, objectNameSize);
        if (!NT_SUCCESS(NtQueryObject(hFile, 
                                      ObjectNameInformation,
                                      pObjectName,
                                      objectNameSize,
                                      NULL)))
        {
            //printf("[%d] ObjectNameInformation (%#x): %#x \n",
            //       pid,
            //       hHandle->HandleValue,
            //       GetLastError());
            goto loop_cleanup;
        }

        if (pObjectName->Length)
        {
            //printf("DEBUG: pObjectName->Buffer = %S \n",
            //       pObjectName->Buffer);

            pyFilePath = PyUnicode_FromWideChar(pObjectName->Buffer,
                                                pObjectName->Length / 2);

            if (pyFilePath == NULL)
            {
                error = TRUE;
                goto cleanup;
            }

            if (PyList_Append(pyListFiles, pyFilePath))
            {
                error = TRUE;
                goto cleanup;
            }
        }

loop_cleanup:
        Py_XDECREF(pyFilePath);
        pyFilePath = NULL;
        if (hMap) {
            CloseHandle(hMap);
            hMap = NULL;
        }
        if (pObjectName)
        {
            HeapFree(hHeap, 0, pObjectName);
            pObjectName = NULL;
        }
        if (hFile)
        {
            CloseHandle(hFile);
            hFile = NULL;
        }
        if (lpszFilePath)
        {
            HeapFree(hHeap, 0, lpszFilePath);
            lpszFilePath = NULL;
        }
    }

cleanup:
    Py_XDECREF(pyFilePath);
    if (hMap)
        CloseHandle(hMap);
    hMap = NULL;
    if (pObjectName)
        HeapFree(hHeap, 0, pObjectName);
    pObjectName = NULL;
    if (lpszFilePath)
        HeapFree(hHeap, 0, lpszFilePath);
    lpszFilePath = NULL;
    if (pSystemHandleInformationInfo != NULL)
        HeapFree(hHeap, 0, pSystemHandleInformationInfo);
    pSystemHandleInformationInfo = NULL;
    if (hHeap)
        CloseHandle(hHeap);
    hHeap = NULL;
    if (hFile)
        CloseHandle(hFile);
    hFile = NULL;
    if (error)
    {
        Py_XDECREF(pyListFiles);
        return NULL;
    }
    else 
    {
        return pyListFiles;
    }
}
