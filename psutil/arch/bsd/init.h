/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/types.h>


#define PSUTIL_KPT2DOUBLE(t) (t##_sec + t##_usec / 1000000.0)

#if defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
#define PSUTIL_HASNT_KINFO_GETFILE
struct kinfo_file *kinfo_getfile(pid_t pid, int *cnt);
#endif

int psutil_kinfo_proc(pid_t pid, void *proc);
void convert_kvm_err(const char *syscall, char *errbuf);
int is_zombie(size_t pid);

PyObject *psutil_boot_time(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_logical(PyObject *self, PyObject *args);
PyObject *psutil_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_heap_info(PyObject *self, PyObject *args);
PyObject *psutil_heap_trim(PyObject *self, PyObject *args);
PyObject *psutil_net_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_name(PyObject *self, PyObject *args);
PyObject *psutil_proc_oneshot_info(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
