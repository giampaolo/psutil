/*
 * $Id$
 *
 * OS X platform-specific module methods for _psutil_osx
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <sys/sysctl.h>

#include <mach/task.h>
#include <mach/mach_init.h>
#include <mach/mach_traps.h>
#include <mach/shared_memory_server.h>

#include "_psutil_osx.h"
#include "arch/osx/process_info.h"


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef PsutilMethods[] =
{
     {"get_pid_list", get_pid_list, METH_VARARGS,
     	"Returns a python list of PIDs currently running on the host system"},
     {"get_process_info", get_process_info, METH_VARARGS,
       	"Returns a psutil.ProcessInfo object for the given PID"},
     {"get_num_cpus", get_num_cpus, METH_VARARGS,
       	"Returns the number of CPUs on the system"},
     {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
         "Return process CPU kernel/user times."},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return process creation time."},
     {"get_memory_info", get_memory_info, METH_VARARGS,
         "Return a tuple of RSS/VMS memory information"},
     {"get_total_phymem", get_total_phymem, METH_VARARGS,
         "Return the total amount of physical memory, in bytes"},
     {"get_total_virtmem", get_total_virtmem, METH_VARARGS,
         "Return the total amount of virtual memory, in bytes"},
     {NULL, NULL, 0, NULL}
};


static PyObject *NoSuchProcessException;
static PyObject *AccessDeniedException;

PyMODINIT_FUNC
init_psutil_osx(void)
{
     PyObject *m;
     m = Py_InitModule("_psutil_osx", PsutilMethods);
     NoSuchProcessException = PyErr_NewException("_psutil_osx.NoSuchProcess", NULL, NULL);
     Py_INCREF(NoSuchProcessException);
     PyModule_AddObject(m, "NoSuchProcess", NoSuchProcessException);
     AccessDeniedException = PyErr_NewException("_psutil_osx.AccessDenied", NULL, NULL);
     Py_INCREF(AccessDeniedException);
     PyModule_AddObject(m, "AccessDenied", AccessDeniedException);
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
    PyObject *pid;
    PyObject *retlist = PyList_New(0);

    if (GetBSDProcessList(&proclist, &num_processes) != 0) {
        Py_DECREF(retlist);
        PyErr_SetString(PyExc_RuntimeError, "failed to retrieve process list.");
        return NULL;
    }

    if (num_processes > 0) {
        //save the address of proclist so we can free it later
        orig_address = proclist;
        for (idx=0; idx < num_processes; idx++) {
            //printf("%i: %s\n", proclist->kp_proc.p_pid, proclist->kp_proc.p_comm);
            pid = Py_BuildValue("i", proclist->kp_proc.p_pid);
            PyList_Append(retlist, pid);
            Py_XDECREF(pid);
            proclist++;
        }
    }

    free(orig_address);
    return retlist;
}


static int pid_exists(long pid) {
    kinfo_proc *procList = NULL;
    size_t num_processes;
    size_t idx;
    int kill_ret;

    //save some time if it's an invalid PID
    if (pid < 0) {
        return 0;
    }

    //if kill returns success of permission denied we know it's a valid PID
    kill_ret = kill(pid , 0);
    if ( (0 == kill_ret) || (EPERM == errno) ) {
        return 1;
    }

    return 0;
}


static PyObject* get_process_info(PyObject* self, PyObject* args)
{
    int mib[4];
    size_t len;
    struct kinfo_proc kp;
	long pid;
    PyObject* arglist = NULL;

	//the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}

    /* Fill out the first three components of the mib */
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    //now the PID we want
    mib[3] = pid;

    //fetch the info with sysctl()
    len = sizeof(kp);

    //now read the data from sysctl
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        // raise an exception and throw errno as the error
        if (ESRCH == errno) { //no such process
            return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
        }
        return PyErr_SetFromErrno(NULL);
    }

    if (len > 0) {
        arglist = get_arg_list(pid);
        if (Py_None == arglist) {
            return NULL; //exception should already be set from getcmdargs()
        }

        return Py_BuildValue("llssNll", pid, kp.kp_eproc.e_ppid, kp.kp_proc.p_comm, "", arglist, kp.kp_eproc.e_pcred.p_ruid, kp.kp_eproc.e_pcred.p_rgid);
    }

    /*
     * if sysctl succeeds but len is zero, raise NoSuchProcess as this only
     * appears to happen when the process has gone away.
     */
    else {
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
    }

    //something went wrong if we get to this, so throw an exception
	return PyErr_Format(PyExc_RuntimeError, "Failed to retrieve process information.");
}


// returns he number of CPUs on the system, needed for CPU utilization % calc
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


#define TV2DOUBLE(t)    ((t).tv_sec + (t).tv_usec / 1000000.0)

static PyObject* get_process_cpu_times(PyObject* self, PyObject* args)
{
    long pid;
    int t_utime, t_utime_ms;
    int t_stime, t_stime_ms;
    int t_cpu;
    unsigned int thread_count;
    thread_array_t thread_list = NULL;
    unsigned int info_count = TASK_BASIC_INFO_COUNT;
    task_port_t task = (task_port_t)NULL;
    time_value_t user_time, system_time;
    struct task_basic_info tasks_info;
    struct task_thread_times_info task_times;


    //the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}


    /* task_for_pid() requires special privileges
     * "This function can be called only if the process is owned by the
     * procmod group or if the caller is root."
     * - http://developer.apple.com/documentation/MacOSX/Conceptual/universal_binary/universal_binary_tips/chapter_5_section_19.html
     */
    if (task_for_pid(mach_task_self(), pid, &task) == KERN_SUCCESS) {
        info_count = TASK_BASIC_INFO_COUNT;
        if (task_info(task, TASK_BASIC_INFO, (task_info_t)&tasks_info, &info_count) != KERN_SUCCESS) {
            return PyErr_Format(PyExc_RuntimeError, "task_info(TASK_BASIC_INFO) failed for pid %lu\n", pid);
        }

        info_count = TASK_THREAD_TIMES_INFO_COUNT;
        if (task_info(task, TASK_THREAD_TIMES_INFO, (task_info_t)&task_times, &info_count) != KERN_SUCCESS) {
            return PyErr_Format(PyExc_RuntimeError, "task_info(TASK_THREAD_TIMES_INFO) failed for pid %lu\n", pid);
        }
    }

    /* Some stats need to be fetched from all the threads for the process
    */
    if (task) {
        if (task_threads(task, &thread_list, &(thread_count)) != KERN_SUCCESS) {
            return PyErr_Format(PyExc_RuntimeError, "task_threads() failed for pid %lu\n", pid);
        }

        else {
            /* sum the stats from each thread */
            int i;
            t_utime = 0;
            t_utime_ms = 0;
            t_stime = 0;
            t_stime_ms = 0;
            t_cpu = 0;

            for(i = 0; i < thread_count; i++) {
                struct thread_basic_info t_info;
                unsigned int icount = THREAD_BASIC_INFO_COUNT;

                if(thread_info(thread_list[i], THREAD_BASIC_INFO, (thread_info_t)&t_info, &icount) != KERN_SUCCESS) {
                    return PyErr_Format(PyExc_RuntimeError, "thread_info() failed for pid %lu\n", pid);
                }

                else {
                    t_utime += t_info.user_time.seconds;
                    t_utime_ms += t_info.user_time.microseconds;
                    t_stime += t_info.system_time.seconds;
                    t_stime_ms += t_info.system_time.microseconds;
                    t_cpu += t_info.cpu_usage;
                }
            }
        }
    }

    /*
    //XXX: throwing false access denied errors so we'll ignore this for now
    else {
        //return PyErr_Format(AccessDeniedException, "Access denied to CPU times for PID %lu", pid);
    }
    */

    float user_t = -1.0;
    float sys_t = -1.0;
    user_time = tasks_info.user_time;
    system_time = tasks_info.system_time;

    time_value_add(&user_time, &task_times.user_time);
    time_value_add(&system_time, &task_times.system_time);

    user_t = (float)user_time.seconds + ((float)user_time.microseconds / 1000000.0);
    sys_t = (float)system_time.seconds + ((float)system_time.microseconds / 1000000.0);
    return Py_BuildValue("(dd)", user_t, sys_t);
}


static PyObject* get_process_create_time(PyObject* self, PyObject* args)
{

    int mib[4];
    long pid;
    size_t len;
    struct kinfo_proc kp;

	//the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
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
        return Py_BuildValue("d", TV2DOUBLE(kp.kp_proc.p_starttime));
    }

    return PyErr_Format(PyExc_RuntimeError, "Unable to read process start time.");
}


/*
 * Returns a tuple of RSS and VMS memory usage
 */
static PyObject* get_memory_info(PyObject* self, PyObject* args)
{
    long pid;
    unsigned int info_count = TASK_BASIC_INFO_COUNT;
    task_port_t task = (task_port_t)NULL;
    time_value_t user_time, system_time;
    struct task_basic_info tasks_info;

    //the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}


    /* task_for_pid() requires special privileges
     * "This function can be called only if the process is owned by the
     * procmod group or if the caller is root."
     * - http://developer.apple.com/documentation/MacOSX/Conceptual/universal_binary/universal_binary_tips/chapter_5_section_19.html
     */
    if (task_for_pid(mach_task_self(), pid, &task) == KERN_SUCCESS) {
        info_count = TASK_BASIC_INFO_COUNT;
        if (task_info(task, TASK_BASIC_INFO, (task_info_t)&tasks_info, &info_count) != KERN_SUCCESS) {
            return PyErr_Format(PyExc_RuntimeError, "task_info(TASK_BASIC_INFO) failed for pid %lu\n", pid);
        }
    }

    else {
        return PyErr_Format(PyExc_RuntimeError, "task_for_pid() failed for pid %lu\n", pid);
    }

    return Py_BuildValue("(ll)", tasks_info.resident_size, tasks_info.virtual_size);
}


static PyObject* get_total_phymem(PyObject* self, PyObject* args)
{
    int mib[2];
    uint64_t total_phymem;
    size_t len;

    mib[0] = CTL_HW;
    mib[1] = HW_MEMSIZE;
    len = sizeof(total_phymem);

    if (sysctl(mib, 2, &total_phymem, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("L", total_phymem);
}


static PyObject* get_total_virtmem(PyObject* self, PyObject* args)
{
    //FIXME: write a real function here to retrieve total virtual memory
    return Py_BuildValue("L", 0);
}
