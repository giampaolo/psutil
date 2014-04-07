/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

// --- per-process functions

static PyObject* psutil_proc_cmdline(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cpu_affinity_get(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cpu_affinity_set(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cpu_times_2(PyObject* self, PyObject* args);
static PyObject* psutil_proc_create_time(PyObject* self, PyObject* args);
static PyObject* psutil_proc_create_time_2(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cwd(PyObject* self, PyObject* args);
static PyObject* psutil_proc_exe(PyObject* self, PyObject* args);
static PyObject* psutil_proc_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_proc_io_counters_2(PyObject* self, PyObject* args);
static PyObject* psutil_proc_is_suspended(PyObject* self, PyObject* args);
static PyObject* psutil_proc_kill(PyObject* self, PyObject* args);
static PyObject* psutil_proc_memory_info(PyObject* self, PyObject* args);
static PyObject* psutil_proc_memory_info_2(PyObject* self, PyObject* args);
static PyObject* psutil_proc_memory_maps(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_handles(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_handles_2(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_threads(PyObject* self, PyObject* args);
static PyObject* psutil_proc_open_files(PyObject* self, PyObject* args);
static PyObject* psutil_proc_priority_get(PyObject* self, PyObject* args);
static PyObject* psutil_proc_priority_set(PyObject* self, PyObject* args);
static PyObject* psutil_proc_resume(PyObject* self, PyObject* args);
static PyObject* psutil_proc_suspend(PyObject* self, PyObject* args);
static PyObject* psutil_proc_threads(PyObject* self, PyObject* args);
static PyObject* psutil_proc_username(PyObject* self, PyObject* args);
static PyObject* psutil_proc_wait(PyObject* self, PyObject* args);

#if (PSUTIL_WINVER >= 0x0600)  // Windows Vista
static PyObject* psutil_proc_io_priority_get(PyObject* self, PyObject* args);
static PyObject* psutil_proc_io_priority_set(PyObject* self, PyObject* args);
#endif

// --- system-related functions

static PyObject* psutil_boot_time(PyObject* self, PyObject* args);
static PyObject* psutil_cpu_count_logical(PyObject* self, PyObject* args);
static PyObject* psutil_cpu_count_phys(PyObject* self, PyObject* args);
static PyObject* psutil_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_disk_partitions(PyObject* self, PyObject* args);
static PyObject* psutil_disk_usage(PyObject* self, PyObject* args);
static PyObject* psutil_net_connections(PyObject* self, PyObject* args);
static PyObject* psutil_net_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_per_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_pid_exists(PyObject* self, PyObject* args);
static PyObject* psutil_pids(PyObject* self, PyObject* args);
static PyObject* psutil_ppid_map(PyObject* self, PyObject* args);
static PyObject* psutil_users(PyObject* self, PyObject* args);
static PyObject* psutil_virtual_mem(PyObject* self, PyObject* args);

// --- windows API bindings

static PyObject* psutil_win32_QueryDosDevice(PyObject* self, PyObject* args);

// --- internal

int psutil_proc_suspend_or_resume(DWORD pid, int suspend);
