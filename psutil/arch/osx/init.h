/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/user.h>
#include <sys/types.h>
#include <libproc.h>
#include <mach/mach_time.h>

extern struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;

int psutil_setup_osx(void);
int _psutil_pids(pid_t **pids_array, int *pids_count);
int is_zombie(size_t pid);

int psutil_get_kinfo_proc(pid_t pid, struct kinfo_proc *kp);
int psutil_sysctl_procargs(pid_t pid, char *procargs, size_t *argmax);
int psutil_proc_pidinfo(
    pid_t pid, int flavor, uint64_t arg, void *pti, int size
);
int psutil_task_for_pid(pid_t pid, mach_port_t *task);
struct proc_fdinfo *psutil_proc_list_fds(pid_t pid, int *num_fds);

PyObject *psutil_boot_time(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_cores(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_logical(PyObject *self, PyObject *args);
PyObject *psutil_cpu_freq(PyObject *self, PyObject *args);
PyObject *psutil_cpu_stats(PyObject *self, PyObject *args);
PyObject *psutil_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_disk_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_disk_usage_used(PyObject *self, PyObject *args);
PyObject *psutil_has_cpu_freq(PyObject *self, PyObject *args);
PyObject *psutil_heap_info(PyObject *self, PyObject *args);
PyObject *psutil_heap_trim(PyObject *self, PyObject *args);
PyObject *psutil_net_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_per_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_proc_cmdline(PyObject *self, PyObject *args);
PyObject *psutil_proc_cwd(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_exe(PyObject *self, PyObject *args);
PyObject *psutil_proc_kinfo_oneshot(PyObject *self, PyObject *args);
PyObject *psutil_proc_memory_uss(PyObject *self, PyObject *args);
PyObject *psutil_proc_name(PyObject *self, PyObject *args);
PyObject *psutil_proc_net_connections(PyObject *self, PyObject *args);
PyObject *psutil_proc_num_fds(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
PyObject *psutil_proc_pidtaskinfo_oneshot(PyObject *self, PyObject *args);
PyObject *psutil_proc_threads(PyObject *self, PyObject *args);
PyObject *psutil_sensors_battery(PyObject *self, PyObject *args);
PyObject *psutil_swap_mem(PyObject *self, PyObject *args);
PyObject *psutil_virtual_mem(PyObject *self, PyObject *args);
