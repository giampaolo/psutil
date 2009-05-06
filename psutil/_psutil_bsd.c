/*
 * $Id$
 *
 * FreeBSD platform-specific module methods for _psutil_bsd
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/user.h>
#include <sys/proc.h>
#include <sys/vmmeter.h>  /* needed for vmtotal struct */

#include "_psutil_bsd.h"
#include "arch/bsd/process_info.h"


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef PsutilMethods[] =
{
     {"get_pid_list", get_pid_list, METH_VARARGS,
     	"Returns a list of PIDs currently running on the system"},
     {"get_process_info", get_process_info, METH_VARARGS,
        "Return a tuple containing a set of information about the "
        "process (pid, ppid, name, path, cmdline)"},
     {"get_cpu_times", get_cpu_times, METH_VARARGS,
       	"Return tuple of user/kern time for the given PID"},
     {"get_num_cpus", get_num_cpus, METH_VARARGS,
       	"Return number of CPUs on the system"},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return a float indicating the process create time expressed in "
         "seconds since the epoch"},
     {"get_memory_info", get_memory_info, METH_VARARGS,
         "Return a tuple of RSS/VMS memory information"},
     {"get_total_phymem", get_total_phymem, METH_VARARGS,
         "Return the total amount of physical memory, in bytes"},
     {"get_avail_phymem", get_avail_phymem, METH_VARARGS,
         "Return the amount of available physical memory, in bytes"},
     {"get_total_virtmem", get_total_virtmem, METH_VARARGS,
         "Return the total amount of virtual memory, in bytes"},
     {"get_avail_virtmem", get_avail_virtmem, METH_VARARGS,
         "Return the amount of available virtual memory, in bytes"},
     {"get_system_cpu_times", get_system_cpu_times, METH_VARARGS,
         "Return system cpu times as a tuple (user, system, nice, idle, irc)"},
     {NULL, NULL, 0, NULL}
};


static PyObject *NoSuchProcessException;

PyMODINIT_FUNC
init_psutil_bsd(void)
{
     PyObject *m;
     m = Py_InitModule("_psutil_bsd", PsutilMethods);
     NoSuchProcessException = PyErr_NewException("_psutil_bsd.NoSuchProcess", NULL, NULL);
     Py_INCREF(NoSuchProcessException);
     PyModule_AddObject(m, "NoSuchProcess", NoSuchProcessException);
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject* get_pid_list(PyObject* self, PyObject* args)
{
    kinfo_proc *proclist = NULL;
    kinfo_proc *orig_address = NULL;
    size_t num_processes;
    size_t idx;
    PyObject* retlist = PyList_New(0);
    PyObject* pid;

    if (get_proc_list(&proclist, &num_processes) != 0) {
        Py_DECREF(retlist);
        PyErr_SetString(PyExc_RuntimeError, "failed to retrieve process list.");
        return NULL;
    }

    if (num_processes > 0) {
        orig_address = proclist; // save so we can free it after we're done
        for (idx=0; idx < num_processes; idx++) {
            pid = Py_BuildValue("i", proclist->ki_pid);
            PyList_Append(retlist, pid);
            Py_XDECREF(pid);
            proclist++;
        }
        free(orig_address);
    }

    return retlist;
}


/*
 * Return a Python tuple containing a set of information about the process:
 * (pid, ppid, name, path, cmdline).
 */
static PyObject* get_process_info(PyObject* self, PyObject* args)
{

    int mib[4];
    size_t len;
    struct kinfo_proc kp;
	long pid;
    PyObject* infoTuple = NULL;
    PyObject* arglist = NULL;

	// the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}

    if (0 == pid) {
        // USER   PID %CPU %MEM   VSZ   RSS  TT  STAT STARTED      TIME COMMAND
        // root     0  0.0  0.0     0     0  ??  DLs  12:22AM   0:00.13 [swapper]
        return Py_BuildValue("llssNll", pid, 0, "swapper", "", Py_BuildValue("[]"), 0, 0);
    }

    // build the mib to pass to sysctl to tell it what PID and what info we want
    len = 4;
    sysctlnametomib("kern.proc.pid", mib, &len);
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    // fetch the info with sysctl()
    len = sizeof(kp);
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        // raise an exception if it failed, since we won't get any data
        if (ESRCH == errno) {
            return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
        }
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    if (len > 0) { // if 0 then no data was retrieved

        // get the commandline, since we got everything else
        arglist = get_arg_list(pid);

        // get_arg_list() returns NULL only if getcmdargs failed with ESRCH
        // (no process with that PID)
        if (NULL == arglist) {
            return PyErr_Format(NoSuchProcessException,
                                "No such process found with pid %lu", pid);
        }

        // hooray, we got all the data, so return it as a tuple to be passed to
        // ProcessInfo() constructor
        infoTuple = Py_BuildValue("llssNll", pid, kp.ki_ppid, kp.ki_comm, "",
                                  arglist, kp.ki_ruid, kp.ki_rgid);
        if (NULL == infoTuple) {
            PyErr_SetString(PyExc_RuntimeError,
                            "Failed to build process information tuple!");
        }
        return infoTuple;
    }

    // something went wrong, throw an error
	return PyErr_Format(PyExc_RuntimeError,
                        "Failed to retrieve process information.");
}

// convert a timeval struct to a double
#define TV2DOUBLE(t)    ((t).tv_sec + (t).tv_usec / 1000000.0)


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject* get_cpu_times(PyObject* self, PyObject* args)
{

    int mib[4];
    size_t len;
    struct kinfo_proc kp;
	long pid;
    double user_t, sys_t;
    PyObject* timeTuple = NULL;

	// the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError,
                            "Invalid argument - no PID provided.");
	}

    // build the mib to pass to sysctl to tell it what PID and what info we want
    len = 4;
    sysctlnametomib("kern.proc.pid", mib, &len);
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    // fetch the info with sysctl()
    len = sizeof(kp);
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        // raise an exception if it failed, since we won't get any data
        if (ESRCH == errno) {
            return PyErr_Format(NoSuchProcessException,
                                "No process found with pid %lu", pid);
        }
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    if (len > 0) { // if 0 then no data was retrieved
        user_t = TV2DOUBLE(kp.ki_rusage.ru_utime);
        sys_t = TV2DOUBLE(kp.ki_rusage.ru_stime);

        // convert from microseconds to seconds
        timeTuple = Py_BuildValue("(dd)", user_t, sys_t);
        if (NULL == timeTuple) {
            PyErr_SetString(PyExc_RuntimeError,
                            "Failed to build process CPU times tuple!");
        }
        return timeTuple;
    }

    // something went wrong, throw an error
	return PyErr_Format(PyExc_RuntimeError,
                        "Failed to retrieve process CPU times.");
}


/*
 * Return a Python integer indicating the number of CPUs on the system
 */
static PyObject* get_num_cpus(PyObject* self, PyObject* args)
{

    int mib[2];
    int ncpu;
    size_t len;

    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);

    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("i", ncpu);
}


/*
 * Return a Python float indicating the process create time expressed in
 * seconds since the epoch.
 */
static PyObject* get_process_create_time(PyObject* self, PyObject* args)
{
    int mib[4];
    long pid;
    size_t len;
    struct kinfo_proc kp;

	// the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError,
                            "Invalid argument - no PID provided.");
	}

    len = 4;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;
    len = sizeof(kp);
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    if (len > 0) {
        return Py_BuildValue("d", TV2DOUBLE(kp.ki_start));
    }

    return PyErr_Format(PyExc_RuntimeError, "Unable to read process start time.");
}


/*
 * Return the RSS and VMS as a Python tuple.
 */
static PyObject* get_memory_info(PyObject* self, PyObject* args)
{
    int mib[4];
    long pid;
    size_t len;
    struct kinfo_proc kp;

    // the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError,
                            "Invalid argument - no PID provided.");
	}

    len = 4;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;
    len = sizeof(kp);
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    if (len > 0) {
        return Py_BuildValue("(ll)", ptoa(kp.ki_rssize), (long)kp.ki_size);
    }

    return PyErr_Format(PyExc_RuntimeError, "Unable to read process start time.");
}


/*
 * Return a Python integer indicating the total amount of physical memory
 * in bytes.
 */
static PyObject* get_total_phymem(PyObject* self, PyObject* args)
{
    int mib[2];
    int total_phymem;
    size_t len;

    mib[0] = CTL_HW;
    mib[1] = HW_PHYSMEM;
    len = sizeof(total_phymem);

    if (sysctl(mib, 2, &total_phymem, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("i", total_phymem);
}


/*
 * Return a Python long indicating the amount of available physical memory in
 * bytes.
 */
static PyObject* get_avail_phymem(PyObject* self, PyObject* args)
{
    unsigned int v_inactive_count;
    unsigned int v_cache_count;
    unsigned int v_free_count;
    int total_mem;
    long long avail_mem;
    size_t size = sizeof(unsigned int);
    size_t psize = sizeof(int);
    int pagesize = getpagesize();

    if (sysctlbyname("hw.physmem", &total_mem, &psize, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    if (sysctlbyname("vm.stats.vm.v_inactive_count", &v_inactive_count,
                     &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    if (sysctlbyname("vm.stats.vm.v_cache_count",
                     &v_cache_count, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    if (sysctlbyname("vm.stats.vm.v_free_count",
                     &v_free_count, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    avail_mem = (v_inactive_count + v_cache_count + v_free_count) * pagesize;
    // used_mem = total_mem - avail_mem;

    return Py_BuildValue("L", avail_mem);
}


/*
 * Return a Python long indicating the total amount of virtual memory
 * in bytes.
 */
static PyObject* get_total_virtmem(PyObject* self, PyObject* args)
{
    int mib[2];
    struct vmtotal vm;
    size_t size;
    long long total_vmem;

    mib[0] = CTL_VM;
    mib[1] = VM_METER;
    size = sizeof(vm);
    sysctl(mib, 2, &vm, &size, NULL, 0);

    // vmtotal struct:
    // http://fxr.watson.org/fxr/source/sys/vmmeter.h?v=FREEBSD54
    // note: value is returned in page, so we must multiply by size of a page
    total_vmem = (long long)vm.t_vm * (long long)getpagesize();
    return Py_BuildValue("L", total_vmem);
}


/*
 * Return a Python long indicating the avail amount of virtual memory
 * in bytes.
 */
static PyObject* get_avail_virtmem(PyObject* self, PyObject* args)
{
    int mib[2];
    struct vmtotal vm;
    size_t size;
    long long total_vmem;
    long long avail_vmem;

    mib[0] = CTL_VM;
    mib[1] = VM_METER;
    size = sizeof(vm);
    sysctl(mib, 2, &vm, &size, NULL, 0);

    // vmtotal struct:
    // http://fxr.watson.org/fxr/source/sys/vmmeter.h?v=FREEBSD54
    // note: value is returned in page, so we must multiply by size of a page
    total_vmem = (long long)vm.t_vm * (long long)getpagesize();
    avail_vmem = total_vmem - ((long long)vm.t_avm * (long long)getpagesize());
    return Py_BuildValue("L", avail_vmem);
}


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
static PyObject* get_system_cpu_times(PyObject* self, PyObject* args)
{
    long cpu_time[CPUSTATES];
    size_t size;

    size = sizeof(cpu_time);

    if (sysctlbyname("kern.cp_time", &cpu_time, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    /*
        #define CP_USER     0
        #define CP_NICE     1
        #define CP_SYS      2
        #define CP_INTR     3
        #define CP_IDLE     4
        #define CPUSTATES   5
    */
    //user, nice, system, idle, iowait, irqm, softirq
    return Py_BuildValue("(ddddd)",
                         (double)cpu_time[CP_USER] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_NICE] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_SYS] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_IDLE] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_INTR] / CLOCKS_PER_SEC
    );
}
