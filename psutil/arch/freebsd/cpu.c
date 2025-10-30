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

#include "../../arch/all/init.h"


PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    int maxcpus;
    int mib[2];
    int ncpu;
    size_t size;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    // retrieve the number of CPUs currently online
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    if (psutil_sysctl(mib, 2, &ncpu, sizeof(ncpu)) != 0) {
        goto error;
    }

    // allocate buffer dynamically based on actual CPU count
    long(*cpu_time)[CPUSTATES] = malloc(ncpu * sizeof(*cpu_time));
    if (!cpu_time) {
        PyErr_NoMemory();
        goto error;
    }

    // get per-cpu times using ncpu count
    size = ncpu * sizeof(*cpu_time);
    if (psutil_sysctlbyname("kern.cp_times", cpu_time, size) == -1) {
        free(cpu_time);
        goto error;
    }

    for (int i = 0; i < ncpu; i++) {
        py_cputime = Py_BuildValue(
            "(ddddd)",
            (double)cpu_time[i][CP_USER] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_NICE] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_SYS] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_IDLE] / CLOCKS_PER_SEC,
            (double)cpu_time[i][CP_INTR] / CLOCKS_PER_SEC
        );
        if (!py_cputime) {
            free(cpu_time);
            goto error;
        }
        if (PyList_Append(py_retlist, py_cputime)) {
            Py_DECREF(py_cputime);
            free(cpu_time);
            goto error;
        }
        Py_DECREF(py_cputime);
    }

    free(cpu_time);
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_cpu_topology(PyObject *self, PyObject *args) {
    char *topology = NULL;
    size_t size = 0;
    PyObject *py_str;

    if (psutil_sysctlbyname_malloc(
            "kern.sched.topology_spec", &topology, &size
        )
        != 0)
    {
        psutil_debug("ignore sysctlbyname('kern.sched.topology_spec') error");
        Py_RETURN_NONE;
    }

    py_str = Py_BuildValue("s", topology);
    free(topology);
    return py_str;
}


PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    unsigned int v_soft;
    unsigned int v_intr;
    unsigned int v_syscall;
    unsigned int v_trap;
    unsigned int v_swtch;
    size_t size = sizeof(v_soft);

    if (psutil_sysctlbyname("vm.stats.sys.v_soft", &v_soft, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.sys.v_intr", &v_intr, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.sys.v_syscall", &v_syscall, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.sys.v_trap", &v_trap, size) != 0)
        return NULL;
    if (psutil_sysctlbyname("vm.stats.sys.v_swtch", &v_swtch, size) != 0)
        return NULL;

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
    size_t size;

    if (!PyArg_ParseTuple(args, "i", &core))
        return NULL;

    // https://www.unix.com/man-page/FreeBSD/4/cpufreq/
    size = sizeof(current);
    str_format(sensor, sizeof(sensor), "dev.cpu.%d.freq", core);
    if (psutil_sysctlbyname(sensor, &current, size) != 0)
        goto error;

    // In case of failure, an empty string is returned.
    size = sizeof(available_freq_levels);
    str_format(sensor, sizeof(sensor), "dev.cpu.%d.freq_levels", core);
    if (psutil_sysctlbyname(sensor, &available_freq_levels, size) != 0)
        psutil_debug("cpu freq levels failed (ignored)");

    return Py_BuildValue("is", current, available_freq_levels);

error:
    if (errno == ENOENT)
        PyErr_SetString(PyExc_NotImplementedError, "unable to read frequency");
    else
        psutil_oserror();
    return NULL;
}
