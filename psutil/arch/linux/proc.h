/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/syscall.h>  // __NR_*
#include <sched.h> // CPU_ALLOC

// Linux >= 2.6.13
#if defined(__NR_ioprio_get) && defined(__NR_ioprio_set)
    #define PSUTIL_HAVE_IOPRIO

    PyObject *psutil_proc_ioprio_get(PyObject *self, PyObject *args);
    PyObject *psutil_proc_ioprio_set(PyObject *self, PyObject *args);
#endif

// Should exist starting from CentOS 6 (year 2011).
#ifdef CPU_ALLOC
    #define PSUTIL_HAVE_CPU_AFFINITY

    PyObject *psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args);
    PyObject *psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args);
#endif
