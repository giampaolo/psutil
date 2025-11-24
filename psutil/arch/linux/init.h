/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/syscall.h>  // __NR_*
#include <sched.h>  // CPU_ALLOC

PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_linux_sysinfo(PyObject *self, PyObject *args);
PyObject *psutil_net_if_duplex_speed(PyObject *self, PyObject *args);

// Linux >= 2.6.13
#if defined(__NR_ioprio_get) && defined(__NR_ioprio_set)
#define PSUTIL_HAS_IOPRIO
PyObject *psutil_proc_ioprio_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_ioprio_set(PyObject *self, PyObject *args);
#endif

// Should exist starting from CentOS 6 (year 2011).
#ifdef CPU_ALLOC
#define PSUTIL_HAS_CPU_AFFINITY
PyObject *psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args);
PyObject *psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args);
#endif

// Does not exist on MUSL / Alpine Linux.
#if defined(__GLIBC__)
#define PSUTIL_HAS_HEAP_INFO
#define PSUTIL_HAS_HEAP_TRIM
PyObject *psutil_heap_trim(PyObject *self, PyObject *args);
PyObject *psutil_heap_info(PyObject *self, PyObject *args);
#endif
