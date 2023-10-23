/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/syscall.h>
#include <sched.h>
#include <unistd.h>

#include "proc.h"
#include "../../_psutil_common.h"


#ifdef PSUTIL_HAVE_IOPRIO
enum {
    IOPRIO_WHO_PROCESS = 1,
};

static inline int
ioprio_get(int which, int who) {
    return syscall(__NR_ioprio_get, which, who);
}

static inline int
ioprio_set(int which, int who, int ioprio) {
    return syscall(__NR_ioprio_set, which, who, ioprio);
}

#define IOPRIO_CLASS_SHIFT 13
#define IOPRIO_PRIO_MASK ((1UL << IOPRIO_CLASS_SHIFT) - 1)

#define IOPRIO_PRIO_CLASS(mask) ((mask) >> IOPRIO_CLASS_SHIFT)
#define IOPRIO_PRIO_DATA(mask) ((mask) & IOPRIO_PRIO_MASK)
#define IOPRIO_PRIO_VALUE(class, data) (((class) << IOPRIO_CLASS_SHIFT) | data)


// Return a (ioclass, iodata) Python tuple representing process I/O
// priority.
PyObject *
psutil_proc_ioprio_get(PyObject *self, PyObject *args) {
    pid_t pid;
    int ioprio, ioclass, iodata;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    ioprio = ioprio_get(IOPRIO_WHO_PROCESS, pid);
    if (ioprio == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    ioclass = IOPRIO_PRIO_CLASS(ioprio);
    iodata = IOPRIO_PRIO_DATA(ioprio);
    return Py_BuildValue("ii", ioclass, iodata);
}


// A wrapper around ioprio_set(); sets process I/O priority. ioclass
// can be either IOPRIO_CLASS_RT, IOPRIO_CLASS_BE, IOPRIO_CLASS_IDLE or
// 0. iodata goes from 0 to 7 depending on ioclass specified.
PyObject *
psutil_proc_ioprio_set(PyObject *self, PyObject *args) {
    pid_t pid;
    int ioprio, ioclass, iodata;
    int retval;

    if (! PyArg_ParseTuple(
            args, _Py_PARSE_PID "ii", &pid, &ioclass, &iodata)) {
        return NULL;
    }
    ioprio = IOPRIO_PRIO_VALUE(ioclass, iodata);
    retval = ioprio_set(IOPRIO_WHO_PROCESS, pid, ioprio);
    if (retval == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    Py_RETURN_NONE;
}
#endif  // PSUTIL_HAVE_IOPRIO


#ifdef PSUTIL_HAVE_CPU_AFFINITY

// Return process CPU affinity as a Python list.
PyObject *
psutil_proc_cpu_affinity_get(PyObject *self, PyObject *args) {
    int cpu, ncpus, count, cpucount_s;
    pid_t pid;
    size_t setsize;
    cpu_set_t *mask = NULL;
    PyObject *py_list = NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    // The minimum number of CPUs allocated in a cpu_set_t.
    ncpus = sizeof(unsigned long) * CHAR_BIT;
    while (1) {
        setsize = CPU_ALLOC_SIZE(ncpus);
        mask = CPU_ALLOC(ncpus);
        if (mask == NULL) {
            psutil_debug("CPU_ALLOC() failed");
            return PyErr_NoMemory();
        }
        if (sched_getaffinity(pid, setsize, mask) == 0)
            break;
        CPU_FREE(mask);
        if (errno != EINVAL)
            return PyErr_SetFromErrno(PyExc_OSError);
        if (ncpus > INT_MAX / 2) {
            PyErr_SetString(PyExc_OverflowError, "could not allocate "
                            "a large enough CPU set");
            return NULL;
        }
        ncpus = ncpus * 2;
    }

    py_list = PyList_New(0);
    if (py_list == NULL)
        goto error;

    cpucount_s = CPU_COUNT_S(setsize, mask);
    for (cpu = 0, count = cpucount_s; count; cpu++) {
        if (CPU_ISSET_S(cpu, setsize, mask)) {
#if PY_MAJOR_VERSION >= 3
            PyObject *cpu_num = PyLong_FromLong(cpu);
#else
            PyObject *cpu_num = PyInt_FromLong(cpu);
#endif
            if (cpu_num == NULL)
                goto error;
            if (PyList_Append(py_list, cpu_num)) {
                Py_DECREF(cpu_num);
                goto error;
            }
            Py_DECREF(cpu_num);
            --count;
        }
    }
    CPU_FREE(mask);
    return py_list;

error:
    if (mask)
        CPU_FREE(mask);
    Py_XDECREF(py_list);
    return NULL;
}


// Set process CPU affinity; expects a bitmask.
PyObject *
psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args) {
    cpu_set_t cpu_set;
    size_t len;
    pid_t pid;
    Py_ssize_t i, seq_len;
    PyObject *py_cpu_set;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "O", &pid, &py_cpu_set))
        return NULL;

    if (!PySequence_Check(py_cpu_set)) {
        return PyErr_Format(
            PyExc_TypeError,
#if PY_MAJOR_VERSION >= 3
            "sequence argument expected, got %R", Py_TYPE(py_cpu_set)
#else
            "sequence argument expected, got %s", Py_TYPE(py_cpu_set)->tp_name
#endif
        );
    }

    seq_len = PySequence_Size(py_cpu_set);
    if (seq_len < 0) {
        return NULL;
    }
    CPU_ZERO(&cpu_set);
    for (i = 0; i < seq_len; i++) {
        PyObject *item = PySequence_GetItem(py_cpu_set, i);
        if (!item) {
            return NULL;
        }
#if PY_MAJOR_VERSION >= 3
        long value = PyLong_AsLong(item);
#else
        long value = PyInt_AsLong(item);
#endif
        Py_XDECREF(item);
        if ((value == -1) || PyErr_Occurred()) {
            if (!PyErr_Occurred())
                PyErr_SetString(PyExc_ValueError, "invalid CPU value");
            return NULL;
        }
        CPU_SET(value, &cpu_set);
    }

    len = sizeof(cpu_set);
    if (sched_setaffinity(pid, len, &cpu_set)) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    Py_RETURN_NONE;
}
#endif  // PSUTIL_HAVE_CPU_AFFINITY
