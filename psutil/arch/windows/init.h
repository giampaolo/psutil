/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>
#include <Winsvc.h>

#include "ntextapi.h"


extern int PSUTIL_WINVER;
extern SYSTEM_INFO PSUTIL_SYSTEM_INFO;
extern CRITICAL_SECTION PSUTIL_CRITICAL_SECTION;

#define PSUTIL_WINDOWS_VISTA 60
#define PSUTIL_WINDOWS_7 61
#define PSUTIL_WINDOWS_8 62
#define PSUTIL_WINDOWS_8_1 63
#define PSUTIL_WINDOWS_10 100
#define PSUTIL_WINDOWS_NEW MAXLONG

#define MALLOC(x) HeapAlloc(GetProcessHeap(), 0, (x))
#define MALLOC_ZERO(x) HeapAlloc(GetProcessHeap(), HEAP_ZERO_MEMORY, (x))
#define FREE(x) HeapFree(GetProcessHeap(), 0, (x))

#define _NT_FACILITY_MASK 0xfff
#define _NT_FACILITY_SHIFT 16
#define _NT_FACILITY(status) \
    ((((ULONG)(status)) >> _NT_FACILITY_SHIFT) & _NT_FACILITY_MASK)

#define NT_NTWIN32(status) (_NT_FACILITY(status) == FACILITY_WIN32)
#define WIN32_FROM_NTSTATUS(status) (((ULONG)(status)) & 0xffff)

#define LO_T 1e-7
#define HI_T 429.4967296

#ifndef AF_INET6
#define AF_INET6 23
#endif

#if defined(PSUTIL_WINDOWS) && defined(PYPY_VERSION)
#if !defined(PyErr_SetFromWindowsErrWithFilename)
PyObject *PyErr_SetFromWindowsErrWithFilename(int ierr, const char *filename);
#endif
#if !defined(PyErr_SetExcFromWindowsErrWithFilenameObject)
PyObject *PyErr_SetExcFromWindowsErrWithFilenameObject(
    PyObject *type, int ierr, PyObject *filename
);
#endif
#endif

double psutil_FiletimeToUnixTime(FILETIME ft);
double psutil_LargeIntegerToUnixTime(LARGE_INTEGER li);
int psutil_setup_windows(void);
PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
PVOID psutil_SetFromNTStatusErr(NTSTATUS status, const char *syscall);

PyObject *TimeoutExpired;
PyObject *TimeoutAbandoned;


int _psutil_pids(DWORD **pids_array, int *pids_count);
HANDLE psutil_check_phandle(HANDLE hProcess, DWORD pid, int check_exit_code);
HANDLE psutil_handle_from_pid(DWORD pid, DWORD dwDesiredAccess);
int psutil_assert_pid_exists(DWORD pid, char *err);
int psutil_assert_pid_not_exists(DWORD pid, char *err);
int psutil_pid_is_running(DWORD pid);
int psutil_set_se_debug();
SC_HANDLE psutil_get_service_handle(
    char service_name, DWORD scm_access, DWORD access
);

int psutil_get_proc_info(
    DWORD pid, PSYSTEM_PROCESS_INFORMATION *retProcess, PVOID *retBuffer
);

PyObject *psutil_cpu_count_cores(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_logical(PyObject *self, PyObject *args);
PyObject *psutil_cpu_freq(PyObject *self, PyObject *args);
PyObject *psutil_cpu_stats(PyObject *self, PyObject *args);
PyObject *psutil_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_disk_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_disk_usage(PyObject *self, PyObject *args);
PyObject *psutil_get_loadavg();
PyObject *psutil_get_open_files(DWORD pid, HANDLE hProcess);
PyObject *psutil_getpagesize(PyObject *self, PyObject *args);
PyObject *psutil_init_loadavg_counter();
PyObject *psutil_heap_info(PyObject *self, PyObject *args);
PyObject *psutil_heap_trim(PyObject *self, PyObject *args);
PyObject *psutil_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_net_if_addrs(PyObject *self, PyObject *args);
PyObject *psutil_net_if_stats(PyObject *self, PyObject *args);
PyObject *psutil_net_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_per_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_pid_exists(PyObject *self, PyObject *args);
PyObject *psutil_pids(PyObject *self, PyObject *args);
PyObject *psutil_ppid_map(PyObject *self, PyObject *args);
PyObject *psutil_proc_cmdline(PyObject *self, PyObject *args, PyObject *kw);
PyObject *psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args);
PyObject *psutil_proc_cwd(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_exe(PyObject *self, PyObject *args);
PyObject *psutil_proc_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_proc_io_priority_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_io_priority_set(PyObject *self, PyObject *args);
PyObject *psutil_proc_is_suspended(PyObject *self, PyObject *args);
PyObject *psutil_proc_kill(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_maps(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_uss(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_handles(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
PyObject *psutil_proc_priority_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_priority_set(PyObject *self, PyObject *args);
PyObject *psutil_proc_suspend_or_resume(PyObject *self, PyObject *args);
PyObject *psutil_proc_threads(PyObject *self, PyObject *args);
PyObject *psutil_proc_times(PyObject *self, PyObject *args);
PyObject *psutil_proc_username(PyObject *self, PyObject *args);
PyObject *psutil_proc_wait(PyObject *self, PyObject *args);
PyObject *psutil_QueryDosDevice(PyObject *self, PyObject *args);
PyObject *psutil_sensors_battery(PyObject *self, PyObject *args);
PyObject *psutil_swap_percent(PyObject *self, PyObject *args);
PyObject *psutil_uptime(PyObject *self, PyObject *args);
PyObject *psutil_users(PyObject *self, PyObject *args);
PyObject *psutil_virtual_mem(PyObject *self, PyObject *args);
PyObject *psutil_winservice_enumerate(PyObject *self, PyObject *args);
PyObject *psutil_winservice_query_config(PyObject *self, PyObject *args);
PyObject *psutil_winservice_query_descr(PyObject *self, PyObject *args);
PyObject *psutil_winservice_query_status(PyObject *self, PyObject *args);
PyObject *psutil_winservice_start(PyObject *self, PyObject *args);
PyObject *psutil_winservice_stop(PyObject *self, PyObject *args);
