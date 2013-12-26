/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

// --- per-process functions

static PyObject* psutil_proc_cmdline(PyObject* self, PyObject* args);
static PyObject* psutil_proc_connections(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_proc_create_time(PyObject* self, PyObject* args);
static PyObject* psutil_proc_exe(PyObject* self, PyObject* args);
static PyObject* psutil_proc_gids(PyObject* self, PyObject* args);
static PyObject* psutil_proc_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_proc_memory_info(PyObject* self, PyObject* args);
static PyObject* psutil_proc_memory_maps(PyObject* self, PyObject* args);
static PyObject* psutil_proc_name(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_ctx_switches(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_fds(PyObject* self, PyObject* args);
static PyObject* psutil_proc_num_threads(PyObject* self, PyObject* args);
static PyObject* psutil_proc_ppid(PyObject* self, PyObject* args);
static PyObject* psutil_proc_status(PyObject* self, PyObject* args);
static PyObject* psutil_proc_threads(PyObject* self, PyObject* args);
static PyObject* psutil_proc_tty_nr(PyObject* self, PyObject* args);
static PyObject* psutil_proc_uids(PyObject* self, PyObject* args);

#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
static PyObject* psutil_proc_open_files(PyObject* self, PyObject* args);
static PyObject* psutil_proc_cwd(PyObject* self, PyObject* args);
#endif

// --- system-related functions

static PyObject* psutil_boot_time(PyObject* self, PyObject* args);
static PyObject* psutil_cpu_count_logical(PyObject* self, PyObject* args);
static PyObject* psutil_cpu_count_phys(PyObject* self, PyObject* args);
static PyObject* psutil_cpu_times(PyObject* self, PyObject* args);
static PyObject* psutil_disk_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_disk_partitions(PyObject* self, PyObject* args);
static PyObject* psutil_net_io_counters(PyObject* self, PyObject* args);
static PyObject* psutil_pids(PyObject* self, PyObject* args);
static PyObject* psutil_swap_mem(PyObject* self, PyObject* args);
static PyObject* psutil_users(PyObject* self, PyObject* args);
static PyObject* psutil_virtual_mem(PyObject* self, PyObject* args);

#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
static PyObject* psutil_per_cpu_times(PyObject* self, PyObject* args);
#endif