//***********************************************************************/
// Header definitions to access NtQueryInformationProcess in NTDLL.DLL
//
// Copyright © 2007 Steven Moore (OrionScorpion).  All Rights Reserved.
//
// NOTES: PEB_LDR_DATA, RTL_USER_PROCESS_PARAMETERS and PEB struct are
//        defined in Winternl.h and Ntddk.h.  The specs below are from
//        Microsoft MSDN web site as of Jul 2007.  I locally specified
//        them below since they can change in future versions and may
//        not reflect current winternl.h or ntddk.h
//***********************************************************************/
#ifndef _ORIONSCORPION_NTPROCESSINFO_H_
#define _ORIONSCORPION_NTPROCESSINFO_H_

#define _X86_ 

#pragma once

#include <winternl.h>
#include <psapi.h>
#include <windows.h>

#define STRSAFE_LIB
#include <strsafe.h>

#pragma comment(lib, "strsafe.lib")
#pragma comment(lib, "rpcrt4.lib")
#pragma comment(lib, "psapi.lib")

#ifndef NTSTATUS
#define LONG NTSTATUS
#endif

// Unicode path usually prefix with '\\?\'
#define MAX_UNICODE_PATH	32767L

// Used in PEB struct
typedef ULONG smPPS_POST_PROCESS_INIT_ROUTINE;

// Used in PEB struct
typedef struct _smPEB_LDR_DATA {
	BYTE Reserved1[8];
	PVOID Reserved2[3];
	LIST_ENTRY InMemoryOrderModuleList;
} smPEB_LDR_DATA, *smPPEB_LDR_DATA;

// Used in PEB struct
typedef struct _smRTL_USER_PROCESS_PARAMETERS {
	BYTE Reserved1[16];
	PVOID Reserved2[10];
	UNICODE_STRING ImagePathName;
	UNICODE_STRING CommandLine;
} smRTL_USER_PROCESS_PARAMETERS, *smPRTL_USER_PROCESS_PARAMETERS;

// Used in PROCESS_BASIC_INFORMATION struct
typedef struct _smPEB {
	BYTE Reserved1[2];
	BYTE BeingDebugged;
	BYTE Reserved2[1];
	PVOID Reserved3[2];
	smPPEB_LDR_DATA Ldr;
	smPRTL_USER_PROCESS_PARAMETERS ProcessParameters;
	BYTE Reserved4[104];
	PVOID Reserved5[52];
	smPPS_POST_PROCESS_INIT_ROUTINE PostProcessInitRoutine;
	BYTE Reserved6[128];
	PVOID Reserved7[1];
	ULONG SessionId;
} smPEB, *smPPEB;

// Used with NtQueryInformationProcess
typedef struct _smPROCESS_BASIC_INFORMATION {
    LONG ExitStatus;
    smPPEB PebBaseAddress;
    ULONG_PTR AffinityMask;
    LONG BasePriority;
    ULONG_PTR UniqueProcessId;
    ULONG_PTR InheritedFromUniqueProcessId;
} smPROCESS_BASIC_INFORMATION, *smPPROCESS_BASIC_INFORMATION;

// NtQueryInformationProcess in NTDLL.DLL
typedef NTSTATUS (NTAPI *pfnNtQueryInformationProcess)(
	IN	HANDLE ProcessHandle,
    IN	PROCESSINFOCLASS ProcessInformationClass,
    OUT	PVOID ProcessInformation,
    IN	ULONG ProcessInformationLength,
    OUT	PULONG ReturnLength	OPTIONAL
    );

pfnNtQueryInformationProcess gNtQueryInformationProcess;

typedef struct _smPROCESSINFO
{
	DWORD	dwPID;
	DWORD	dwParentPID;
	DWORD	dwSessionID;
	DWORD	dwPEBBaseAddress;
	DWORD	dwAffinityMask;
	LONG	dwBasePriority;
	LONG	dwExitStatus;
	BYTE	cBeingDebugged;
	TCHAR	szImgPath[MAX_UNICODE_PATH];
	TCHAR	szCmdLine[MAX_UNICODE_PATH];
} smPROCESSINFO;

HMODULE sm_LoadNTDLLFunctions(void);
void sm_FreeNTDLLFunctions(IN HMODULE hNtDll);
BOOL sm_EnableTokenPrivilege(IN LPCTSTR pszPrivilege);
BOOL sm_GetNtProcessInfo(IN const DWORD dwPID, OUT smPROCESSINFO *ppi);

#endif	// _ORIONSCORPION_NTPROCESSINFO_H_
