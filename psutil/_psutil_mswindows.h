/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Windows platform-specific module methods for _psutil_mswindows
 */

#include <Python.h>
#include <windows.h>

// --- per-process functions

static PyObject* get_process_name(PyObject* self, PyObject* args);
static PyObject* get_process_cmdline(PyObject* self, PyObject* args);
static PyObject* get_process_exe(PyObject* self, PyObject* args);
static PyObject* get_process_ppid(PyObject* self, PyObject* args);
static PyObject* get_process_cpu_times(PyObject* self, PyObject* args);
static PyObject* get_process_create_time(PyObject* self, PyObject* args);
static PyObject* get_process_memory_info(PyObject* self, PyObject* args);
static PyObject* get_process_cwd(PyObject* self, PyObject* args);
static PyObject* get_process_open_files(PyObject* self, PyObject* args);
static PyObject* get_process_username(PyObject* self, PyObject* args);
static PyObject* get_process_connections(PyObject* self, PyObject* args);
static PyObject* get_process_num_threads(PyObject* self, PyObject* args);
static PyObject* get_process_threads(PyObject* self, PyObject* args);
static PyObject* get_process_priority(PyObject* self, PyObject* args);
static PyObject* set_process_priority(PyObject* self, PyObject* args);
#if (_WIN32_WINNT >= 0x0600)  // Windows Vista
static PyObject* get_process_io_priority(PyObject* self, PyObject* args);
static PyObject* set_process_io_priority(PyObject* self, PyObject* args);
#endif
static PyObject* get_process_io_counters(PyObject* self, PyObject* args);
static PyObject* get_process_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* set_process_cpu_affinity(PyObject* self, PyObject* args);
static PyObject* get_process_num_handles(PyObject* self, PyObject* args);
static PyObject* get_process_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* get_process_memory_maps(PyObject* self, PyObject* args);

static PyObject* get_process_cpu_times_2(PyObject* self, PyObject* args);
static PyObject* get_process_create_time_2(PyObject* self, PyObject* args);
static PyObject* get_process_num_handles_2(PyObject* self, PyObject* args);
static PyObject* get_process_io_counters_2(PyObject* self, PyObject* args);
static PyObject* get_process_memory_info_2(PyObject* self, PyObject* args);

static PyObject* suspend_process(PyObject* self, PyObject* args);
static PyObject* resume_process(PyObject* self, PyObject* args);
static PyObject* is_process_suspended(PyObject* self, PyObject* args);
static PyObject* process_wait(PyObject* self, PyObject* args);
static PyObject* kill_process(PyObject* self, PyObject* args);

// --- system-related functions

static PyObject* get_pid_list(PyObject* self, PyObject* args);
static PyObject* get_num_cpus(PyObject* self, PyObject* args);
static PyObject* get_system_boot_time(PyObject* self, PyObject* args);
static PyObject* get_virtual_mem(PyObject* self, PyObject* args);
static PyObject* get_system_cpu_times(PyObject* self, PyObject* args);
static PyObject* pid_exists(PyObject* self, PyObject* args);
static PyObject* get_disk_usage(PyObject* self, PyObject* args);
static PyObject* get_disk_partitions(PyObject* self, PyObject* args);
static PyObject* get_network_io_counters(PyObject* self, PyObject* args);
static PyObject* get_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* get_system_users(PyObject* self, PyObject* args);

// --- windows API bindings

static PyObject* win32_QueryDosDevice(PyObject* self, PyObject* args);

// --- internal
int suspend_resume_process(DWORD pid, int suspend);
