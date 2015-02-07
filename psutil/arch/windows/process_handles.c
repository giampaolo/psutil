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

void PrintError(LPTSTR lpszFunction)
{
    // Retrieve the system error message for the last-error code

    LPVOID lpMsgBuf;
    LPVOID lpDisplayBuf;
    DWORD dw = GetLastError();

    FormatMessage(
        FORMAT_MESSAGE_ALLOCATE_BUFFER |
        FORMAT_MESSAGE_FROM_SYSTEM |
        FORMAT_MESSAGE_IGNORE_INSERTS,
        NULL,
        dw,
        MAKELANGID(LANG_NEUTRAL, SUBLANG_DEFAULT),
        (LPTSTR) &lpMsgBuf,
        0, NULL );

    // Display the error message
    lpDisplayBuf = (LPVOID)LocalAlloc(LMEM_ZEROINIT,
        (lstrlen((LPCTSTR)lpMsgBuf) + lstrlen((LPCTSTR)lpszFunction) + 40) * sizeof(TCHAR));
    StringCchPrintf((LPTSTR)lpDisplayBuf,
        LocalSize(lpDisplayBuf) / sizeof(TCHAR),
        TEXT("%s failed with error %d: %s"),
        lpszFunction, dw, lpMsgBuf);

    wprintf(lpDisplayBuf);
    LocalFree(lpMsgBuf);
    LocalFree(GetLastError);
}

PyObject *
psutil_get_open_files(long pid, HANDLE processHandle)
{
    _NtQuerySystemInformation NtQuerySystemInformation =
        GetLibraryProcAddress("ntdll.dll", "NtQuerySystemInformation");

    _NtQueryObject NtQueryObject =
        GetLibraryProcAddress("ntdll.dll", "NtQueryObject");

    NTSTATUS                    status;
    PSYSTEM_HANDLE_INFORMATION_EX  handleInfo;
    ULONG                       handleInfoSize = 0x10000;
    ULONG                       i;
    ULONG                       fileNameLength;
    PyObject                    *filesList = Py_BuildValue("[]");
    PyObject                    *arg = NULL;
    PyObject                    *fileFromWchar = NULL;
    DWORD nReturn = 0;

    if (filesList == NULL)
        return NULL;

    handleInfo = (PSYSTEM_HANDLE_INFORMATION_EX)HeapAlloc(GetProcessHeap(), 0,
            handleInfoSize);

    if (handleInfo == NULL) {
        Py_DECREF(filesList);
        PyErr_NoMemory();
        return NULL;
    }

    // NtQuerySystemInformation won't give us the correct buffer size,
    // so we guess by doubling the buffer size.
    while ((status = NtQuerySystemInformation(
                         SystemExtendedHandleInformation,
                         handleInfo,
                         handleInfoSize,
                         &nReturn
                     )) == STATUS_INFO_LENGTH_MISMATCH)
    {
        handleInfoSize *=2;
        HeapFree(GetProcessHeap(), 0, handleInfo);
        handleInfo = (PSYSTEM_HANDLE_INFORMATION_EX)HeapAlloc(
            GetProcessHeap(), 0, handleInfoSize);
    }

    // NtQuerySystemInformation stopped giving us STATUS_INFO_LENGTH_MISMATCH
    if (!NT_SUCCESS(status)) {
        Py_DECREF(filesList);
        HeapFree(GetProcessHeap(), 0, handleInfo);
        return NULL;
    }

     for (i = 0; i < handleInfo->NumberOfHandles; i++) {
        PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX handle = &handleInfo->Handles[i];
        HANDLE                   dupHandle = NULL;
        HANDLE                   mapHandle = NULL;
        POBJECT_TYPE_INFORMATION objectTypeInfo = NULL;
        PVOID                    objectNameInfo;
        UNICODE_STRING           objectName;
        ULONG                    returnLength;
        DWORD                    error = 0;
        fileFromWchar = NULL;
        arg = NULL;

        // Check if this handle belongs to the PID the user specified.
        if (handle->UniqueProcessId != (HANDLE)pid ||
                handle->ObjectTypeIndex != HANDLE_TYPE_FILE)
        {
            continue;
        }

        // Skip handles with the following access codes as the next call
        // to NtDuplicateObject() or NtQueryObject() might hang forever.
        if ((handle->GrantedAccess == 0x0012019f)
                || (handle->GrantedAccess == 0x001a019f)
                || (handle->GrantedAccess == 0x00120189)
                || (handle->GrantedAccess == 0x00100000)) {
            continue;
        }

       if (!DuplicateHandle(processHandle,
                             handle->HandleValue,
                             GetCurrentProcess(),
                             &dupHandle,
                             0,
                             TRUE,
                             DUPLICATE_SAME_ACCESS))
         {
             //printf("[%#x] Error: %d \n", handle->HandleValue, GetLastError());
             continue;
         }

        mapHandle = CreateFileMapping(dupHandle,
                                      NULL,
                                      PAGE_READONLY,
                                      0,
                                      0,
                                      NULL);
        if (mapHandle == NULL) {
            error = GetLastError();
            if (error == ERROR_INVALID_HANDLE || error == ERROR_BAD_EXE_FORMAT) {
                CloseHandle(dupHandle);
                //printf("CreateFileMapping Error: %d\n", error);
                continue;
            }
        }
        CloseHandle(mapHandle);

        // Query the object type.
        objectTypeInfo = (POBJECT_TYPE_INFORMATION)malloc(0x1000);
        if (!NT_SUCCESS(NtQueryObject(
                            dupHandle,
                            ObjectTypeInformation,
                            objectTypeInfo,
                            0x1000,
                            NULL
                        )))
        {
            free(objectTypeInfo);
            CloseHandle(dupHandle);
            continue;
        }

        objectNameInfo = malloc(0x1000);
        if (!NT_SUCCESS(NtQueryObject(
                            dupHandle,
                            ObjectNameInformation,
                            objectNameInfo,
                            0x1000,
                            &returnLength
                        )))
        {
            // Reallocate the buffer and try again.
            objectNameInfo = realloc(objectNameInfo, returnLength);
            if (!NT_SUCCESS(NtQueryObject(
                                dupHandle,
                                ObjectNameInformation,
                                objectNameInfo,
                                returnLength,
                                NULL
                            )))
            {
                // We have the type name, so just display that.
                /*
                printf(
                    "[%#x] %.*S: (could not get name)\n",
                    handle->HandleValue,
                    objectTypeInfo->Name.Length / 2,
                    objectTypeInfo->Name.Buffer
                    );
                */
                free(objectTypeInfo);
                free(objectNameInfo);
                CloseHandle(dupHandle);
                continue;

            }
        }

        // Cast our buffer into an UNICODE_STRING.
        objectName = *(PUNICODE_STRING)objectNameInfo;

        // Print the information!
        if (objectName.Length)
        {
            // The object has a name.  Make sure it is a file otherwise
            // ignore it
            fileNameLength = objectName.Length / 2;
            if (wcscmp(objectTypeInfo->Name.Buffer, L"File") == 0) {
                // printf("%.*S\n", objectName.Length / 2, objectName.Buffer);
                fileFromWchar = PyUnicode_FromWideChar(objectName.Buffer,
                                                       fileNameLength);
                if (fileFromWchar == NULL)
                    goto error_py_fun;
#if PY_MAJOR_VERSION >= 3
                arg = Py_BuildValue("N",
                                    PyUnicode_AsUTF8String(fileFromWchar));
#else
                arg = Py_BuildValue("N",
                                    PyUnicode_FromObject(fileFromWchar));
#endif
                if (!arg)
                    goto error_py_fun;
                Py_XDECREF(fileFromWchar);
                fileFromWchar = NULL;
                if (PyList_Append(filesList, arg))
                    goto error_py_fun;
                Py_XDECREF(arg);
            }
            /*
            printf(
                "[%#x] %.*S: %.*S\n",
                handle->Handle,
                objectTypeInfo->Name.Length / 2,
                objectTypeInfo->Name.Buffer,
                objectName.Length / 2,
                objectName.Buffer
                );
            */
        }
        else
        {
            // Print something else.
            /*
            printf(
                "[%#x] %.*S: (unnamed)\n",
                handle->Handle,
                objectTypeInfo->Name.Length / 2,
                objectTypeInfo->Name.Buffer
                );
            */
            ;;
        }
        free(objectTypeInfo);
        free(objectNameInfo);
        CloseHandle(dupHandle);
    }
    HeapFree(GetProcessHeap(), 0, handleInfo);
    CloseHandle(processHandle);
    return filesList;

error_py_fun:
    Py_XDECREF(arg);
    Py_XDECREF(fileFromWchar);
    Py_DECREF(filesList);
    return NULL;
}
