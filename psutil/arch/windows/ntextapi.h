/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */
#if !defined(__NTEXTAPI_H__)
#define __NTEXTAPI_H__
#include <winternl.h>
#include <iphlpapi.h>

typedef LONG NTSTATUS;

#define STATUS_INFO_LENGTH_MISMATCH 0xc0000004
#define STATUS_BUFFER_TOO_SMALL 0xC0000023L
#define SystemExtendedHandleInformation 64
#define MemoryWorkingSetInformation 0x1
#define STATUS_ACCESS_DENIED ((NTSTATUS)0xC0000022L)

/*
 * ================================================================
 * Enums.
 * ================================================================
 */

typedef enum _PROCESSINFOCLASS2 {
    _ProcessBasicInformation,
    ProcessQuotaLimits,
    ProcessIoCounters,
    ProcessVmCounters,
    ProcessTimes,
    ProcessBasePriority,
    ProcessRaisePriority,
    _ProcessDebugPort,
    ProcessExceptionPort,
    ProcessAccessToken,
    ProcessLdtInformation,
    ProcessLdtSize,
    ProcessDefaultHardErrorMode,
    ProcessIoPortHandlers,
    ProcessPooledUsageAndLimits,
    ProcessWorkingSetWatch,
    ProcessUserModeIOPL,
    ProcessEnableAlignmentFaultFixup,
    ProcessPriorityClass,
    ProcessWx86Information,
    ProcessHandleCount,
    ProcessAffinityMask,
    ProcessPriorityBoost,
    ProcessDeviceMap,
    ProcessSessionInformation,
    ProcessForegroundInformation,
    _ProcessWow64Information,
    /* added after XP+ */
    _ProcessImageFileName,
    ProcessLUIDDeviceMapsEnabled,
    _ProcessBreakOnTermination,
    ProcessDebugObjectHandle,
    ProcessDebugFlags,
    ProcessHandleTracing,
    ProcessIoPriority,
    ProcessExecuteFlags,
    ProcessResourceManagement,
    ProcessCookie,
    ProcessImageInformation,
    MaxProcessInfoClass
} PROCESSINFOCLASS2;

#define PROCESSINFOCLASS PROCESSINFOCLASS2
#define ProcessBasicInformation _ProcessBasicInformation
#define ProcessWow64Information _ProcessWow64Information
#define ProcessDebugPort _ProcessDebugPort
#define ProcessImageFileName _ProcessImageFileName
#define ProcessBreakOnTermination _ProcessBreakOnTermination

/*
 * ================================================================
 * Structs.
 * ================================================================
 */

typedef struct {
    LARGE_INTEGER IdleTime;
    LARGE_INTEGER KernelTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER DpcTime;
    LARGE_INTEGER InterruptTime;
    ULONG InterruptCount;
} _SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION;

typedef struct {
    LARGE_INTEGER IdleProcessTime;
    LARGE_INTEGER IoReadTransferCount;
    LARGE_INTEGER IoWriteTransferCount;
    LARGE_INTEGER IoOtherTransferCount;
    ULONG IoReadOperationCount;
    ULONG IoWriteOperationCount;
    ULONG IoOtherOperationCount;
    ULONG AvailablePages;
    ULONG CommittedPages;
    ULONG CommitLimit;
    ULONG PeakCommitment;
    ULONG PageFaultCount;
    ULONG CopyOnWriteCount;
    ULONG TransitionCount;
    ULONG CacheTransitionCount;
    ULONG DemandZeroCount;
    ULONG PageReadCount;
    ULONG PageReadIoCount;
    ULONG CacheReadCount;
    ULONG CacheIoCount;
    ULONG DirtyPagesWriteCount;
    ULONG DirtyWriteIoCount;
    ULONG MappedPagesWriteCount;
    ULONG MappedWriteIoCount;
    ULONG PagedPoolPages;
    ULONG NonPagedPoolPages;
    ULONG PagedPoolAllocs;
    ULONG PagedPoolFrees;
    ULONG NonPagedPoolAllocs;
    ULONG NonPagedPoolFrees;
    ULONG FreeSystemPtes;
    ULONG ResidentSystemCodePage;
    ULONG TotalSystemDriverPages;
    ULONG TotalSystemCodePages;
    ULONG NonPagedPoolLookasideHits;
    ULONG PagedPoolLookasideHits;
    ULONG AvailablePagedPoolPages;
    ULONG ResidentSystemCachePage;
    ULONG ResidentPagedPoolPage;
    ULONG ResidentSystemDriverPage;
    ULONG CcFastReadNoWait;
    ULONG CcFastReadWait;
    ULONG CcFastReadResourceMiss;
    ULONG CcFastReadNotPossible;
    ULONG CcFastMdlReadNoWait;
    ULONG CcFastMdlReadWait;
    ULONG CcFastMdlReadResourceMiss;
    ULONG CcFastMdlReadNotPossible;
    ULONG CcMapDataNoWait;
    ULONG CcMapDataWait;
    ULONG CcMapDataNoWaitMiss;
    ULONG CcMapDataWaitMiss;
    ULONG CcPinMappedDataCount;
    ULONG CcPinReadNoWait;
    ULONG CcPinReadWait;
    ULONG CcPinReadNoWaitMiss;
    ULONG CcPinReadWaitMiss;
    ULONG CcCopyReadNoWait;
    ULONG CcCopyReadWait;
    ULONG CcCopyReadNoWaitMiss;
    ULONG CcCopyReadWaitMiss;
    ULONG CcMdlReadNoWait;
    ULONG CcMdlReadWait;
    ULONG CcMdlReadNoWaitMiss;
    ULONG CcMdlReadWaitMiss;
    ULONG CcReadAheadIos;
    ULONG CcLazyWriteIos;
    ULONG CcLazyWritePages;
    ULONG CcDataFlushes;
    ULONG CcDataPages;
    ULONG ContextSwitches;
    ULONG FirstLevelTbFills;
    ULONG SecondLevelTbFills;
    ULONG SystemCalls;
} _SYSTEM_PERFORMANCE_INFORMATION;

typedef struct {
    ULONG ContextSwitches;
    ULONG DpcCount;
    ULONG DpcRate;
    ULONG TimeIncrement;
    ULONG DpcBypassCount;
    ULONG ApcBypassCount;
} _SYSTEM_INTERRUPT_INFORMATION;

typedef enum _KTHREAD_STATE {
    Initialized,
    Ready,
    Running,
    Standby,
    Terminated,
    Waiting,
    Transition,
    DeferredReady,
    GateWait,
    MaximumThreadState
} KTHREAD_STATE, *PKTHREAD_STATE;

typedef enum _KWAIT_REASON {
    Executive,
    FreePage,
    PageIn,
    PoolAllocation,
    DelayExecution,
    Suspended,
    UserRequest,
    WrExecutive,
    WrFreePage,
    WrPageIn,
    WrPoolAllocation,
    WrDelayExecution,
    WrSuspended,
    WrUserRequest,
    WrEventPair,
    WrQueue,
    WrLpcReceive,
    WrLpcReply,
    WrVirtualMemory,
    WrPageOut,
    WrRendezvous,
    WrKeyedEvent,
    WrTerminated,
    WrProcessInSwap,
    WrCpuRateControl,
    WrCalloutStack,
    WrKernel,
    WrResource,
    WrPushLock,
    WrMutex,
    WrQuantumEnd,
    WrDispatchInt,
    WrPreempted,
    WrYieldExecution,
    WrFastMutex,
    WrGuardedMutex,
    WrRundown,
    WrAlertByThreadId,
    WrDeferredPreempt,
    MaximumWaitReason
} KWAIT_REASON, *PKWAIT_REASON;

typedef struct _SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX {
    PVOID Object;
    HANDLE UniqueProcessId;
    HANDLE HandleValue;
    ULONG GrantedAccess;
    USHORT CreatorBackTraceIndex;
    USHORT ObjectTypeIndex;
    ULONG HandleAttributes;
    ULONG Reserved;
} SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX, *PSYSTEM_HANDLE_TABLE_ENTRY_INFO_EX;

typedef struct _SYSTEM_HANDLE_INFORMATION_EX {
    ULONG_PTR NumberOfHandles;
    ULONG_PTR Reserved;
    SYSTEM_HANDLE_TABLE_ENTRY_INFO_EX Handles[1];
} SYSTEM_HANDLE_INFORMATION_EX, *PSYSTEM_HANDLE_INFORMATION_EX;

typedef struct _CLIENT_ID2 {
    HANDLE UniqueProcess;
    HANDLE UniqueThread;
} CLIENT_ID2, *PCLIENT_ID2;

#define CLIENT_ID CLIENT_ID2
#define PCLIENT_ID PCLIENT_ID2

typedef struct _SYSTEM_THREAD_INFORMATION2 {
    LARGE_INTEGER KernelTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER CreateTime;
    ULONG WaitTime;
    PVOID StartAddress;
    CLIENT_ID ClientId;
    LONG Priority;
    LONG BasePriority;
    ULONG ContextSwitches;
    ULONG ThreadState;
    KWAIT_REASON WaitReason;
} SYSTEM_THREAD_INFORMATION2, *PSYSTEM_THREAD_INFORMATION2;

#define SYSTEM_THREAD_INFORMATION SYSTEM_THREAD_INFORMATION2
#define PSYSTEM_THREAD_INFORMATION PSYSTEM_THREAD_INFORMATION2

typedef struct _TEB *PTEB;

typedef struct _SYSTEM_EXTENDED_THREAD_INFORMATION {
    SYSTEM_THREAD_INFORMATION ThreadInfo;
    PVOID StackBase;
    PVOID StackLimit;
    PVOID Win32StartAddress;
    PTEB TebBase;
    ULONG_PTR Reserved2;
    ULONG_PTR Reserved3;
    ULONG_PTR Reserved4;
} SYSTEM_EXTENDED_THREAD_INFORMATION, *PSYSTEM_EXTENDED_THREAD_INFORMATION;

typedef struct _SYSTEM_PROCESS_INFORMATION2 {
    ULONG NextEntryOffset;
    ULONG NumberOfThreads;
    LARGE_INTEGER SpareLi1;
    LARGE_INTEGER SpareLi2;
    LARGE_INTEGER SpareLi3;
    LARGE_INTEGER CreateTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER KernelTime;
    UNICODE_STRING ImageName;
    LONG BasePriority;
    HANDLE UniqueProcessId;
    HANDLE InheritedFromUniqueProcessId;
    ULONG HandleCount;
    ULONG SessionId;
    ULONG_PTR PageDirectoryBase;
    SIZE_T PeakVirtualSize;
    SIZE_T VirtualSize;
    DWORD PageFaultCount;
    SIZE_T PeakWorkingSetSize;
    SIZE_T WorkingSetSize;
    SIZE_T QuotaPeakPagedPoolUsage;
    SIZE_T QuotaPagedPoolUsage;
    SIZE_T QuotaPeakNonPagedPoolUsage;
    SIZE_T QuotaNonPagedPoolUsage;
    SIZE_T PagefileUsage;
    SIZE_T PeakPagefileUsage;
    SIZE_T PrivatePageCount;
    LARGE_INTEGER ReadOperationCount;
    LARGE_INTEGER WriteOperationCount;
    LARGE_INTEGER OtherOperationCount;
    LARGE_INTEGER ReadTransferCount;
    LARGE_INTEGER WriteTransferCount;
    LARGE_INTEGER OtherTransferCount;
    SYSTEM_THREAD_INFORMATION Threads[1];
} SYSTEM_PROCESS_INFORMATION2, *PSYSTEM_PROCESS_INFORMATION2;

#define SYSTEM_PROCESS_INFORMATION SYSTEM_PROCESS_INFORMATION2
#define PSYSTEM_PROCESS_INFORMATION PSYSTEM_PROCESS_INFORMATION2

typedef struct _PROCESSOR_POWER_INFORMATION {
   ULONG Number;
   ULONG MaxMhz;
   ULONG CurrentMhz;
   ULONG MhzLimit;
   ULONG MaxIdleState;
   ULONG CurrentIdleState;
} PROCESSOR_POWER_INFORMATION, *PPROCESSOR_POWER_INFORMATION;

#ifndef __IPHLPAPI_H__
typedef struct in6_addr {
    union {
        UCHAR Byte[16];
        USHORT Word[8];
    } u;
} IN6_ADDR, *PIN6_ADDR, FAR *LPIN6_ADDR;
#endif

// http://msdn.microsoft.com/en-us/library/aa813741(VS.85).aspx
typedef struct {
    BYTE Reserved1[16];
    PVOID Reserved2[5];
    UNICODE_STRING CurrentDirectoryPath;
    PVOID CurrentDirectoryHandle;
    UNICODE_STRING DllPath;
    UNICODE_STRING ImagePathName;
    UNICODE_STRING CommandLine;
    LPCWSTR env;
} RTL_USER_PROCESS_PARAMETERS_, *PRTL_USER_PROCESS_PARAMETERS_;

typedef struct _WINSTATION_INFO {
    BYTE Reserved1[72];
    ULONG SessionId;
    BYTE Reserved2[4];
    FILETIME ConnectTime;
    FILETIME DisconnectTime;
    FILETIME LastInputTime;
    FILETIME LoginTime;
    BYTE Reserved3[1096];
    FILETIME CurrentTime;
} WINSTATION_INFO, *PWINSTATION_INFO;

#if (_WIN32_WINNT < 0x0601)  // Windows < 7 (Vista and XP)
typedef struct _SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX {
    LOGICAL_PROCESSOR_RELATIONSHIP Relationship;
    DWORD Size;
    _ANONYMOUS_UNION
    union {
        PROCESSOR_RELATIONSHIP Processor;
        NUMA_NODE_RELATIONSHIP NumaNode;
        CACHE_RELATIONSHIP Cache;
        GROUP_RELATIONSHIP Group;
    } DUMMYUNIONNAME;
} SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX, *PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX;
#endif

typedef struct _MEMORY_WORKING_SET_BLOCK {
    ULONG_PTR Protection : 5;
    ULONG_PTR ShareCount : 3;
    ULONG_PTR Shared : 1;
    ULONG_PTR Node : 3;
#ifdef _WIN64
    ULONG_PTR VirtualPage : 52;
#else
    ULONG VirtualPage : 20;
#endif
} MEMORY_WORKING_SET_BLOCK, *PMEMORY_WORKING_SET_BLOCK;

typedef struct _MEMORY_WORKING_SET_INFORMATION {
    ULONG_PTR NumberOfEntries;
    MEMORY_WORKING_SET_BLOCK WorkingSetInfo[1];
} MEMORY_WORKING_SET_INFORMATION, *PMEMORY_WORKING_SET_INFORMATION;

typedef struct _PSUTIL_PROCESS_WS_COUNTERS {
    SIZE_T NumberOfPages;
    SIZE_T NumberOfPrivatePages;
    SIZE_T NumberOfSharedPages;
    SIZE_T NumberOfShareablePages;
} PSUTIL_PROCESS_WS_COUNTERS, *PPSUTIL_PROCESS_WS_COUNTERS;

/*
 * ================================================================
 * Type defs for modules loaded at runtime.
 * ================================================================
 */

typedef BOOL (WINAPI *_GetLogicalProcessorInformationEx)(
    LOGICAL_PROCESSOR_RELATIONSHIP relationship,
    PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX Buffer,
    PDWORD ReturnLength);

typedef BOOLEAN (WINAPI * _WinStationQueryInformationW)(
    HANDLE ServerHandle,
    ULONG SessionId,
    WINSTATIONINFOCLASS WinStationInformationClass,
    PVOID pWinStationInformation,
    ULONG WinStationInformationLength,
    PULONG pReturnLength);

typedef NTSTATUS (NTAPI *_NtQueryInformationProcess)(
    HANDLE ProcessHandle,
    DWORD ProcessInformationClass,
    PVOID ProcessInformation,
    DWORD ProcessInformationLength,
    PDWORD ReturnLength);

typedef NTSTATUS (NTAPI *_NtQuerySystemInformation)(
    ULONG SystemInformationClass,
    PVOID SystemInformation,
    ULONG SystemInformationLength,
    PULONG ReturnLength);

typedef NTSTATUS (NTAPI *_NtSetInformationProcess)(
    HANDLE ProcessHandle,
    DWORD ProcessInformationClass,
    PVOID ProcessInformation,
    DWORD ProcessInformationLength);

typedef PSTR (NTAPI * _RtlIpv4AddressToStringA)(
    struct in_addr *Addr,
    PSTR S);

typedef PSTR (NTAPI * _RtlIpv6AddressToStringA)(
    struct in6_addr *Addr,
    PSTR P);

typedef DWORD (WINAPI * _GetExtendedTcpTable)(
    PVOID pTcpTable,
    PDWORD pdwSize,
    BOOL bOrder,
    ULONG ulAf,
    TCP_TABLE_CLASS TableClass,
    ULONG Reserved);

typedef DWORD (WINAPI * _GetExtendedUdpTable)(
    PVOID pUdpTable,
    PDWORD pdwSize,
    BOOL bOrder,
    ULONG ulAf,
    UDP_TABLE_CLASS TableClass,
    ULONG Reserved);

typedef DWORD (CALLBACK *_GetActiveProcessorCount)(
    WORD GroupNumber);

typedef ULONGLONG (CALLBACK *_GetTickCount64)(
    void);

typedef NTSTATUS (NTAPI *_NtQueryObject)(
    HANDLE Handle,
    OBJECT_INFORMATION_CLASS ObjectInformationClass,
    PVOID ObjectInformation,
    ULONG ObjectInformationLength,
    PULONG ReturnLength);

typedef NTSTATUS (WINAPI *_RtlGetVersion) (
    PRTL_OSVERSIONINFOW lpVersionInformation
);

typedef NTSTATUS (WINAPI *_NtResumeProcess) (
    HANDLE hProcess
);

typedef NTSTATUS (WINAPI *_NtSuspendProcess) (
    HANDLE hProcess
);

typedef NTSTATUS (NTAPI *_NtQueryVirtualMemory) (
    HANDLE ProcessHandle,
    PVOID BaseAddress,
    int MemoryInformationClass,
    PVOID MemoryInformation,
    SIZE_T MemoryInformationLength,
    PSIZE_T ReturnLength
);

typedef ULONG (WINAPI *_RtlNtStatusToDosErrorNoTeb) (
    NTSTATUS status
);

#endif // __NTEXTAPI_H__
