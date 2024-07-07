/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
System-wide CPU related functions.
Original code was refactored and moved from psutil/arch/freebsd/specific.c
in 2020 (and was moved in there previously already) from cset.
a4c0a0eb0d2a872ab7a45e47fcf37ef1fde5b012
For reference, here's the git history with original(ish) implementations:
- CPU stats: fb0154ef164d0e5942ac85102ab660b8d2938fbb
- CPU freq: 459556dd1e2979cdee22177339ced0761caf4c83
- CPU cores: e0d6d7865df84dc9a1d123ae452fd311f79b1dde
*/


#include <Python.h>
#include <sys/sysctl.h>
#include <devstat.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int maxcpus;
    int mib[2];
    int ncpu;
    size_t len;
    size_t size;
    int i;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    // retrieve maxcpus value
    size = sizeof(maxcpus);
    if (sysctlbyname("kern.smp.maxcpus", &maxcpus, &size, NULL, 0) < 0) {
        Py_DECREF(py_retlist);
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('kern.smp.maxcpus')");
    }
    long cpu_time[maxcpus][CPUSTATES];

    // retrieve the number of cpus
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);
    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1) {
        PyErr_SetFromOSErrnoWithSyscall("sysctl(HW_NCPU)");
        goto error;
    }

    // per-cpu info
    size = sizeof(cpu_time);
    if (sysctlbyname("kern.cp_times", &cpu_time, &size, NULL, 0) == -1) {
        PyErr_SetFromOSErrnoWithSyscall("sysctlbyname('kern.smp.maxcpus')");
        goto error;
    }

    for (i = 0; i < ncpu; i++) {
        py_cputime = Py_BuildValue(
            "(ddddd)",
            (double)cpu_time[i][CP_USER] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_NICE] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_SYS] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_IDLE] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_INTR] / CLOCKS_PER_SEC);
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_DECREF(py_cputime);
    }

    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_cpu_topology(PyObject *self, PyObject *args) {
    void *topology = NULL;
    size_t size = 0;
    PyObject *py_str;

    if (sysctlbyname("kern.sched.topology_spec", NULL, &size, NULL, 0))
        goto error;

    topology = malloc(size);
    if (!topology) {
        PyErr_NoMemory();
        return NULL;
    }

    if (sysctlbyname("kern.sched.topology_spec", topology, &size, NULL, 0))
        goto error;

    py_str = Py_BuildValue("s", topology);
    free(topology);
    return py_str;

error:
    if (topology != NULL)
        free(topology);
    Py_RETURN_NONE;
}


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    unsigned int v_soft;
    unsigned int v_intr;
    unsigned int v_syscall;
    unsigned int v_trap;
    unsigned int v_swtch;
    size_t size = sizeof(v_soft);

    if (sysctlbyname("vm.stats.sys.v_soft", &v_soft, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.sys.v_soft')");
    }
    if (sysctlbyname("vm.stats.sys.v_intr", &v_intr, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.sys.v_intr')");
    }
    if (sysctlbyname("vm.stats.sys.v_syscall", &v_syscall, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.sys.v_syscall')");
    }
    if (sysctlbyname("vm.stats.sys.v_trap", &v_trap, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.sys.v_trap')");
    }
    if (sysctlbyname("vm.stats.sys.v_swtch", &v_swtch, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('vm.stats.sys.v_swtch')");
    }

    return Py_BuildValue(
        "IIIII",
        v_swtch,  // ctx switches
        v_intr,  // interrupts
        v_soft,  // software interrupts
        v_syscall,  // syscalls
        v_trap  // traps
    );
}


/*
 * Return frequency information of a given CPU.
 * As of Dec 2018 only CPU 0 appears to be supported and all other
 * cores match the frequency of CPU 0.
 */
PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    int current;
    int core;
    char sensor[26];
    char available_freq_levels[1000];
    size_t size = sizeof(current);

    if (! PyArg_ParseTuple(args, "i", &core))
        return NULL;
    // https://www.unix.com/man-page/FreeBSD/4/cpufreq/
    sprintf(sensor, "dev.cpu.%d.freq", core);
    if (sysctlbyname(sensor, &current, &size, NULL, 0))
        goto error;

    size = sizeof(available_freq_levels);
    // https://www.unix.com/man-page/FreeBSD/4/cpufreq/
    // In case of failure, an empty string is returned.
    sprintf(sensor, "dev.cpu.%d.freq_levels", core);
    sysctlbyname(sensor, &available_freq_levels, &size, NULL, 0);

    return Py_BuildValue("is", current, available_freq_levels);

error:
    if (errno == ENOENT)
        PyErr_SetString(PyExc_NotImplementedError, "unable to read frequency");
    else
        PyErr_SetFromErrno(PyExc_OSError);
    return NULL;
}
