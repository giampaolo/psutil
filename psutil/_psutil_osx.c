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


typedef struct kinfo_proc kinfo_proc;

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


static PyObject* get_process_info(PyObject* self, PyObject* args)
{

    int mib[4];
    size_t len;
    struct kinfo_proc kp;
	long pid;
    PyObject* infoTuple;

	//the argument passed should be a process id
	if (! PyArg_ParseTuple(args, "l", &pid)) {
		PyErr_SetString(PyExc_RuntimeError, "get_process_info(): Invalid argument");
        //return Py_BuildValue("");
	}
	
    infoTuple = Py_BuildValue("lNssNNN", pid, Py_BuildValue(""), "<unknown>", "<unknown>", PyList_New(0), Py_BuildValue(""), Py_BuildValue(""));

	//get the process information that we need
	//(name, path, arguments)
 
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
    if (sysctl(mib, 4, &kp, &len, NULL, 0) == -1) {
        /* perror("sysctl"); */
        // will be set to <unknown> in case this errors
    } else if (len > 0) {
        infoTuple = Py_BuildValue("llssNll", pid, kp.kp_eproc.e_ppid, kp.kp_proc.p_comm, "<unknown>", get_arg_list(pid), kp.kp_eproc.e_pcred.p_ruid, kp.kp_eproc.e_pcred.p_rgid);
    }

	return infoTuple;
}


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
 
PyMODINIT_FUNC
 
init_psutil_osx(void)
{
     (void) Py_InitModule("_psutil_osx", PsutilMethods);
}
