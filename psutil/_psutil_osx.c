/*
 * $Id
 *
 * OS X platform-specific module methods for _psutil_osx
 */

#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/sysctl.h>

#include <Python.h>
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
     {NULL, NULL, 0, NULL}
};


static PyObject *NoSuchProcessException;
 
PyMODINIT_FUNC
init_psutil_osx(void)
{
     PyObject *m;
     m = Py_InitModule("_psutil_osx", PsutilMethods);
     NoSuchProcessException = PyErr_NewException("_psutil_osx.NoSuchProcess", NULL, NULL);
     Py_INCREF(NoSuchProcessException);
     PyModule_AddObject(m, "NoSuchProcess", NoSuchProcessException);
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject* get_pid_list(PyObject* self, PyObject* args)
{
    kinfo_proc *procList = NULL;
    size_t num_processes;
    size_t idx;
    PyObject* retlist = PyList_New(0);

    GetBSDProcessList(&procList, &num_processes);

    //printf("%i\n", procList->kp_proc.p_pid);
    for (idx=0; idx < num_processes; idx++) {
        //printf("%i: %s\n", procList->kp_proc.p_pid, procList->kp_proc.p_comm);
        PyList_Append(retlist, Py_BuildValue("i", procList->kp_proc.p_pid));
        procList++;
    }
   
    return retlist;
}


static int pid_exists(pid) {
    kinfo_proc *procList = NULL;
    size_t num_processes;
    size_t idx;

    GetBSDProcessList(&procList, &num_processes);

    for (idx=0; idx < num_processes; idx++) {
        if (pid == procList->kp_proc.p_pid) {
            return 1;
        }
        procList++;
    }
    
    return 0;
}


static PyObject* get_process_info(PyObject* self, PyObject* args)
{

    int mib[4];
    size_t len;
    struct kinfo_proc kp;
	long pid;
    PyObject* arglist = Py_BuildValue("");

	//the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		return PyErr_Format(PyExc_RuntimeError, "Invalid argument - no PID provided.");
	}

    /* Fill out the first three components of the mib */
    len = 4;
    sysctlnametomib("kern.proc.pid", mib, &len);
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    //now the PID we want
    mib[3] = pid;
    
    //fetch the info with sysctl()
    len = sizeof(kp);

    if (! pid_exists(pid) ){
        return PyErr_Format(NoSuchProcessException, "No process found with pid %lu", pid);
    } 

    // now read the data from sysctl
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        // raise an exception and throw errno as the error
        return PyErr_SetFromErrno(NULL);
    } 
    
    if (len > 0) {
        arglist = get_arg_list(pid);
        if (Py_None == arglist) {
            return NULL; //exception should already be set from getcmdargs()
        }

        return Py_BuildValue("llssNll", pid, kp.kp_eproc.e_ppid, kp.kp_proc.p_comm, "", arglist, kp.kp_eproc.e_pcred.p_ruid, kp.kp_eproc.e_pcred.p_rgid);
    }

	return PyErr_Format(PyExc_SystemError, "Failed to retrieve process information.");
}

