/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 * Define Windows structs and constants which are considered private.
 */

#if !defined(__NTEXTAPI_H__)
#define __NTEXTAPI_H__
#include <winternl.h>
#include <iphlpapi.h>

#ifndef PSUTIL_MAYBE_EXTERN
#define PSUTIL_MAYBE_EXTERN extern
#endif

typedef LONG NTSTATUS;

// https://github.com/ajkhoury/TestDll/blob/master/nt_ddk.h
#define STATUS_INFO_LENGTH_MISMATCH ((NTSTATUS)0xC0000004L)
#define STATUS_BUFFER_TOO_SMALL ((NTSTATUS)0xC0000023L)
#define STATUS_ACCESS_DENIED ((NTSTATUS)0xC0000022L)
#define STATUS_NOT_FOUND ((NTSTATUS)0xC0000225L)
#define STATUS_BUFFER_OVERFLOW ((NTSTATUS)0x80000005L)

// WtsApi32.h
#define WTS_CURRENT_SERVER_HANDLE  ((HANDLE)NULL)
#define WINSTATIONNAME_LENGTH    32
#define DOMAIN_LENGTH            17
#define USERNAME_LENGTH          20

// ================================================================
// Enums
// ================================================================

#undef  SystemExtendedHandleInformation
#define SystemExtendedHandleInformation 64
#undef  MemoryWorkingSetInformation
#define MemoryWorkingSetInformation 0x1
#undef  ObjectNameInformation
#define ObjectNameInformation 1
#undef  ProcessIoPriority
#define ProcessIoPriority 33
#undef  ProcessWow64Information
#define ProcessWow64Information 26
#undef  SystemProcessIdInformation
#define SystemProcessIdInformation 88

// process suspend() / resume()
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

// users()
typedef enum _WTS_INFO_CLASS {
    WTSInitialProgram,
    WTSApplicationName,
    WTSWorkingDirectory,
    WTSOEMId,
    WTSSessionId,
    WTSUserName,
    WTSWinStationName,
    WTSDomainName,
    WTSConnectState,
    WTSClientBuildNumber,
    WTSClientName,
    WTSClientDirectory,
    WTSClientProductId,
    WTSClientHardwareId,
    WTSClientAddress,
    WTSClientDisplay,
    WTSClientProtocolType,
    WTSIdleTime,
    WTSLogonTime,
    WTSIncomingBytes,
    WTSOutgoingBytes,
    WTSIncomingFrames,
    WTSOutgoingFrames,
    WTSClientInfo,
    WTSSessionInfo,
    WTSSessionInfoEx,
    WTSConfigInfo,
    WTSValidationInfo,   // Info Class value used to fetch Validation Information through the WTSQuerySessionInformation
    WTSSessionAddressV4,
    WTSIsRemoteSession
} WTS_INFO_CLASS;

typedef enum _WTS_CONNECTSTATE_CLASS {
    WTSActive,              // User logged on to WinStation
    WTSConnected,           // WinStation connected to client
    WTSConnectQuery,        // In the process of connecting to client
    WTSShadow,              // Shadowing another WinStation
    WTSDisconnected,        // WinStation logged on without client
    WTSIdle,                // Waiting for client to connect
    WTSListen,              // WinStation is listening for connection
    WTSReset,               // WinStation is being reset
    WTSDown,                // WinStation is down due to error
    WTSInit,                // WinStation in initialization
} WTS_CONNECTSTATE_CLASS;

// ================================================================
// Structs.
// ================================================================

// cpu_stats(), per_cpu_times()
typedef struct {
    LARGE_INTEGER IdleTime;
    LARGE_INTEGER KernelTime;
    LARGE_INTEGER UserTime;
    LARGE_INTEGER DpcTime;
    LARGE_INTEGER InterruptTime;
    ULONG InterruptCount;
} _SYSTEM_PROCESSOR_PERFORMANCE_INFORMATION;

// cpu_stats()
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

// cpu_stats()
typedef struct {
    ULONG ContextSwitches;
    ULONG DpcCount;
    ULONG DpcRate;
    ULONG TimeIncrement;
    ULONG DpcBypassCount;
    ULONG ApcBypassCount;
} _SYSTEM_INTERRUPT_INFORMATION;

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

// cpu_freq()
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

// PEB / cmdline(), cwd(), environ()
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

// users()
typedef struct _WTS_SESSION_INFOW {
    DWORD SessionId;             // session id
    LPWSTR pWinStationName;      // name of WinStation this session is
                                 // connected to
    WTS_CONNECTSTATE_CLASS State; // connection state (see enum)
} WTS_SESSION_INFOW, * PWTS_SESSION_INFOW;

#define PWTS_SESSION_INFO PWTS_SESSION_INFOW

typedef struct _WTS_CLIENT_ADDRESS {
    DWORD AddressFamily;  // AF_INET, AF_INET6, AF_IPX, AF_NETBIOS, AF_UNSPEC
    BYTE  Address[20];    // client network address
} WTS_CLIENT_ADDRESS, * PWTS_CLIENT_ADDRESS;

typedef struct _WTSINFOW {
    WTS_CONNECTSTATE_CLASS State; // connection state (see enum)
    DWORD SessionId;             // session id
    DWORD IncomingBytes;
    DWORD OutgoingBytes;
    DWORD IncomingFrames;
    DWORD OutgoingFrames;
    DWORD IncomingCompressedBytes;
    DWORD OutgoingCompressedBytes;
    WCHAR WinStationName[WINSTATIONNAME_LENGTH];
    WCHAR Domain[DOMAIN_LENGTH];
    WCHAR UserName[USERNAME_LENGTH + 1];// name of WinStation this session is
                                 // connected to
    LARGE_INTEGER ConnectTime;
    LARGE_INTEGER DisconnectTime;
    LARGE_INTEGER LastInputTime;
    LARGE_INTEGER LogonTime;
    LARGE_INTEGER CurrentTime;

} WTSINFOW, * PWTSINFOW;

#define PWTSINFO PWTSINFOW

// cpu_count_cores()
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
} SYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX, \
    *PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX;
#endif

// memory_uss()
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

// memory_uss()
typedef struct _MEMORY_WORKING_SET_INFORMATION {
    ULONG_PTR NumberOfEntries;
    MEMORY_WORKING_SET_BLOCK WorkingSetInfo[1];
} MEMORY_WORKING_SET_INFORMATION, *PMEMORY_WORKING_SET_INFORMATION;

// memory_uss()
typedef struct _PSUTIL_PROCESS_WS_COUNTERS {
    SIZE_T NumberOfPages;
    SIZE_T NumberOfPrivatePages;
    SIZE_T NumberOfSharedPages;
    SIZE_T NumberOfShareablePages;
} PSUTIL_PROCESS_WS_COUNTERS, *PPSUTIL_PROCESS_WS_COUNTERS;

// exe()
typedef struct _SYSTEM_PROCESS_ID_INFORMATION {
    HANDLE ProcessId;
    UNICODE_STRING ImageName;
} SYSTEM_PROCESS_ID_INFORMATION, *PSYSTEM_PROCESS_ID_INFORMATION;

// ====================================================================
// PEB structs for cmdline(), cwd(), environ()
// ====================================================================

#ifdef _WIN64
typedef struct {
    BYTE Reserved1[2];
    BYTE BeingDebugged;
    BYTE Reserved2[21];
    PVOID LoaderData;
    PRTL_USER_PROCESS_PARAMETERS_ ProcessParameters;
    // more fields...
} PEB_;

// When we are a 64 bit process accessing a 32 bit (WoW64)
// process we need to use the 32 bit structure layout.
typedef struct {
    USHORT Length;
    USHORT MaxLength;
    DWORD Buffer;
} UNICODE_STRING32;

typedef struct {
    BYTE Reserved1[16];
    DWORD Reserved2[5];
    UNICODE_STRING32 CurrentDirectoryPath;
    DWORD CurrentDirectoryHandle;
    UNICODE_STRING32 DllPath;
    UNICODE_STRING32 ImagePathName;
    UNICODE_STRING32 CommandLine;
    DWORD env;
} RTL_USER_PROCESS_PARAMETERS32;

typedef struct {
    BYTE Reserved1[2];
    BYTE BeingDebugged;
    BYTE Reserved2[1];
    DWORD Reserved3[2];
    DWORD Ldr;
    DWORD ProcessParameters;
    // more fields...
} PEB32;
#else  // ! _WIN64
typedef struct {
    BYTE Reserved1[2];
    BYTE BeingDebugged;
    BYTE Reserved2[1];
    PVOID Reserved3[2];
    PVOID Ldr;
    PRTL_USER_PROCESS_PARAMETERS_ ProcessParameters;
    // more fields...
} PEB_;

// When we are a 32 bit (WoW64) process accessing a 64 bit process
// we need to use the 64 bit structure layout and a special function
// to read its memory.
typedef NTSTATUS (NTAPI *_NtWow64ReadVirtualMemory64)(
    HANDLE ProcessHandle,
    PVOID64 BaseAddress,
    PVOID Buffer,
    ULONG64 Size,
    PULONG64 NumberOfBytesRead);

typedef struct {
    PVOID Reserved1[2];
    PVOID64 PebBaseAddress;
    PVOID Reserved2[4];
    PVOID UniqueProcessId[2];
    PVOID Reserved3[2];
} PROCESS_BASIC_INFORMATION64;

typedef struct {
    USHORT Length;
    USHORT MaxLength;
    PVOID64 Buffer;
} UNICODE_STRING64;

typedef struct {
    BYTE Reserved1[16];
    PVOID64 Reserved2[5];
    UNICODE_STRING64 CurrentDirectoryPath;
    PVOID64 CurrentDirectoryHandle;
    UNICODE_STRING64 DllPath;
    UNICODE_STRING64 ImagePathName;
    UNICODE_STRING64 CommandLine;
    PVOID64 env;
} RTL_USER_PROCESS_PARAMETERS64;

typedef struct {
    BYTE Reserved1[2];
    BYTE BeingDebugged;
    BYTE Reserved2[21];
    PVOID64 LoaderData;
    PVOID64 ProcessParameters;
    // more fields...
} PEB64;
#endif  // _WIN64

// ================================================================
// Type defs for modules loaded at runtime.
// ================================================================

PSUTIL_MAYBE_EXTERN BOOL (WINAPI *_GetLogicalProcessorInformationEx) (
    LOGICAL_PROCESSOR_RELATIONSHIP relationship,
    PSYSTEM_LOGICAL_PROCESSOR_INFORMATION_EX Buffer,
    PDWORD ReturnLength);

#define GetLogicalProcessorInformationEx _GetLogicalProcessorInformationEx

PSUTIL_MAYBE_EXTERN BOOLEAN (WINAPI * _WinStationQueryInformationW) (
    HANDLE ServerHandle,
    ULONG SessionId,
    WINSTATIONINFOCLASS WinStationInformationClass,
    PVOID pWinStationInformation,
    ULONG WinStationInformationLength,
    PULONG pReturnLength);

#define WinStationQueryInformationW _WinStationQueryInformationW

PSUTIL_MAYBE_EXTERN NTSTATUS (NTAPI *_NtQueryInformationProcess) (
    HANDLE ProcessHandle,
    DWORD ProcessInformationClass,
    PVOID ProcessInformation,
    DWORD ProcessInformationLength,
    PDWORD ReturnLength);

#define NtQueryInformationProcess _NtQueryInformationProcess

PSUTIL_MAYBE_EXTERN NTSTATUS (NTAPI *_NtQuerySystemInformation) (
    ULONG SystemInformationClass,
    PVOID SystemInformation,
    ULONG SystemInformationLength,
    PULONG ReturnLength);

#define NtQuerySystemInformation _NtQuerySystemInformation

PSUTIL_MAYBE_EXTERN NTSTATUS (NTAPI *_NtSetInformationProcess) (
    HANDLE ProcessHandle,
    DWORD ProcessInformationClass,
    PVOID ProcessInformation,
    DWORD ProcessInformationLength);

#define NtSetInformationProcess _NtSetInformationProcess

PSUTIL_MAYBE_EXTERN PSTR (NTAPI * _RtlIpv4AddressToStringA) (
    struct in_addr *Addr,
    PSTR S);

#define RtlIpv4AddressToStringA _RtlIpv4AddressToStringA

PSUTIL_MAYBE_EXTERN PSTR (NTAPI * _RtlIpv6AddressToStringA) (
    struct in6_addr *Addr,
    PSTR P);

#define RtlIpv6AddressToStringA _RtlIpv6AddressToStringA

PSUTIL_MAYBE_EXTERN DWORD (WINAPI * _GetExtendedTcpTable) (
    PVOID pTcpTable,
    PDWORD pdwSize,
    BOOL bOrder,
    ULONG ulAf,
    TCP_TABLE_CLASS TableClass,
    ULONG Reserved);

#define GetExtendedTcpTable _GetExtendedTcpTable

PSUTIL_MAYBE_EXTERN DWORD (WINAPI * _GetExtendedUdpTable) (
    PVOID pUdpTable,
    PDWORD pdwSize,
    BOOL bOrder,
    ULONG ulAf,
    UDP_TABLE_CLASS TableClass,
    ULONG Reserved);

#define GetExtendedUdpTable _GetExtendedUdpTable

PSUTIL_MAYBE_EXTERN DWORD (CALLBACK *_GetActiveProcessorCount) (
    WORD GroupNumber);

#define GetActiveProcessorCount _GetActiveProcessorCount

PSUTIL_MAYBE_EXTERN BOOL(CALLBACK *_WTSQuerySessionInformationW) (
    HANDLE hServer,
    DWORD SessionId,
    WTS_INFO_CLASS WTSInfoClass,
    LPWSTR* ppBuffer,
    DWORD* pBytesReturned
    );

#define WTSQuerySessionInformationW _WTSQuerySessionInformationW

PSUTIL_MAYBE_EXTERN BOOL(CALLBACK *_WTSEnumerateSessionsW)(
    HANDLE hServer,
    DWORD Reserved,
    DWORD Version,
    PWTS_SESSION_INFO* ppSessionInfo,
    DWORD* pCount
    );

#define WTSEnumerateSessionsW _WTSEnumerateSessionsW

PSUTIL_MAYBE_EXTERN VOID(CALLBACK *_WTSFreeMemory)(
    IN PVOID pMemory
    );

#define WTSFreeMemory _WTSFreeMemory

PSUTIL_MAYBE_EXTERN ULONGLONG (CALLBACK *_GetTickCount64) (
    void);

#define GetTickCount64 _GetTickCount64

PSUTIL_MAYBE_EXTERN NTSTATUS (NTAPI *_NtQueryObject) (
    HANDLE Handle,
    OBJECT_INFORMATION_CLASS ObjectInformationClass,
    PVOID ObjectInformation,
    ULONG ObjectInformationLength,
    PULONG ReturnLength);

#define NtQueryObject _NtQueryObject

PSUTIL_MAYBE_EXTERN NTSTATUS (WINAPI *_RtlGetVersion) (
    PRTL_OSVERSIONINFOW lpVersionInformation
);

#define RtlGetVersion _RtlGetVersion

PSUTIL_MAYBE_EXTERN NTSTATUS (WINAPI *_NtResumeProcess) (
    HANDLE hProcess
);

#define NtResumeProcess _NtResumeProcess

PSUTIL_MAYBE_EXTERN NTSTATUS (WINAPI *_NtSuspendProcess) (
    HANDLE hProcess
);

#define NtSuspendProcess _NtSuspendProcess

PSUTIL_MAYBE_EXTERN NTSTATUS (NTAPI *_NtQueryVirtualMemory) (
    HANDLE ProcessHandle,
    PVOID BaseAddress,
    int MemoryInformationClass,
    PVOID MemoryInformation,
    SIZE_T MemoryInformationLength,
    PSIZE_T ReturnLength
);

#define NtQueryVirtualMemory _NtQueryVirtualMemory

PSUTIL_MAYBE_EXTERN ULONG (WINAPI *_RtlNtStatusToDosErrorNoTeb) (
    NTSTATUS status
);

#define RtlNtStatusToDosErrorNoTeb _RtlNtStatusToDosErrorNoTeb

#endif // __NTEXTAPI_H__
