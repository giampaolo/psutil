/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

// --- per-process functions

static PyObject* psutil_get_ppid_map(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cmdline(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_connections(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cpu_times_2(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_create_time(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_create_time_2(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_cwd(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_exe(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_io_counters_2(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_memory_info(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_memory_info_2(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_memory_maps(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_num_handles(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_num_handles_2(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_num_threads(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_open_files(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_priority(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_threads(PyObject* self, PyObject* args);
static PyObject* psutil_get_proc_username(PyObject* self, PyObject* args);
static PyObject* psutil_is_process_suspended(PyObject* self, PyObject* args);
static PyObject* psutil_kill_process(PyObject* self, PyObject* args);
static PyObject* psutil_process_wait(PyObject* self, PyObject* args);
static PyObject* psutil_resume_process(PyObject* self, PyObject* args);
static PyObject* psutil_set_proc_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* psutil_set_proc_priority(PyObject* self, PyObject* args);
static PyObject* psutil_suspend_process(PyObject* self, PyObject* args);

#if (PSUTIL_WINVER >= 0x0600)  // Windows Vista
static PyObject* psutil_get_proc_io_priority(PyObject* self, PyObject* args);
static PyObject* psutil_set_proc_io_priority(PyObject* self, PyObject* args);
#endif

// --- system-related functions

static PyObject* psutil_get_boot_time(PyObject* self, PyObject* args);
static PyObject* psutil_get_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* psutil_get_disk_usage(PyObject* self, PyObject* args);
static PyObject* psutil_get_net_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_get_num_cpus(PyObject* self, PyObject* args);
static PyObject* psutil_get_num_phys_cpus(PyObject* self, PyObject* args);
static PyObject* psutil_get_pids(PyObject* self, PyObject* args);
static PyObject* psutil_get_sys_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_get_sys_per_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_get_users(PyObject* self, PyObject* args);
static PyObject* psutil_get_virtual_mem(PyObject* self, PyObject* args);
static PyObject* psutil_pid_exists(PyObject* self, PyObject* args);

// --- windows API bindings

static PyObject* psutil_win32_QueryDosDevice(PyObject* self, PyObject* args);

// --- internal
int suspend_resume_process(DWORD pid, int suspend);
