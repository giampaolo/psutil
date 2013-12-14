/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

// --- per-process functions

static PyObject* get_proc_cmdline(PyObject* self, PyObject* args);
static PyObject* get_proc_exe(PyObject* self, PyObject* args);
static PyObject* get_proc_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_proc_create_time(PyObject* self, PyObject* args);
static PyObject* get_proc_memory_info(PyObject* self, PyObject* args);
static PyObject* get_proc_cwd(PyObject* self, PyObject* args);
static PyObject* get_proc_open_files(PyObject* self, PyObject* args);
static PyObject* get_proc_username(PyObject* self, PyObject* args);
static PyObject* get_proc_connections(PyObject* self, PyObject* args);
static PyObject* get_proc_num_threads(PyObject* self, PyObject* args);
static PyObject* get_proc_threads(PyObject* self, PyObject* args);
static PyObject* get_proc_priority(PyObject* self, PyObject* args);
static PyObject* set_proc_priority(PyObject* self, PyObject* args);
#if (PSUTIL_WINVER >= 0x0600)  // Windows Vista
static PyObject* get_proc_io_priority(PyObject* self, PyObject* args);
static PyObject* set_proc_io_priority(PyObject* self, PyObject* args);
#endif
static PyObject* get_proc_io_counters(PyObject* self, PyObject* args);
static PyObject* get_proc_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* set_proc_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* get_proc_num_handles(PyObject* self, PyObject* args);
static PyObject* get_proc_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* get_proc_memory_maps(PyObject* self, PyObject* args);
static PyObject* get_ppid_map(PyObject* self, PyObject* args);

static PyObject* get_proc_cpu_times_2(PyObject* self, PyObject* args);
static PyObject* get_proc_create_time_2(PyObject* self, PyObject* args);
static PyObject* get_proc_num_handles_2(PyObject* self, PyObject* args);
static PyObject* get_proc_io_counters_2(PyObject* self, PyObject* args);
static PyObject* get_proc_memory_info_2(PyObject* self, PyObject* args);

static PyObject* suspend_process(PyObject* self, PyObject* args);
static PyObject* resume_process(PyObject* self, PyObject* args);
static PyObject* is_process_suspended(PyObject* self, PyObject* args);
static PyObject* process_wait(PyObject* self, PyObject* args);
static PyObject* kill_process(PyObject* self, PyObject* args);

// --- system-related functions

static PyObject* get_pids(PyObject* self, PyObject* args);
static PyObject* get_num_cpus(PyObject* self, PyObject* args);
static PyObject* get_num_phys_cpus(PyObject* self, PyObject* args);
static PyObject* get_boot_time(PyObject* self, PyObject* args);
static PyObject* get_virtual_mem(PyObject* self, PyObject* args);
static PyObject* get_sys_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_sys_per_cpu_times(PyObject* self, PyObject* args);
static PyObject* pid_exists(PyObject* self, PyObject* args);
static PyObject* get_disk_usage(PyObject* self, PyObject* args);
static PyObject* get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* get_net_io_counters(PyObject* self, PyObject* args);
static PyObject* get_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* get_users(PyObject* self, PyObject* args);

// --- windows API bindings

static PyObject* win32_QueryDosDevice(PyObject* self, PyObject* args);

// --- internal
int suspend_resume_process(DWORD pid, int suspend);
