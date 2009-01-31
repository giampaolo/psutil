#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/sysctl.h>

#include <Python.h>


/*
 * Returns a list of all BSD processes on the system.  This routine
 * allocates the list and puts it in *procList and a count of the
 * number of entries in *procCount.  You are responsible for freeing
 * this list (use "free" from System framework).
 * On success, the function returns 0.
 * On error, the function returns a BSD errno value.
 */
typedef struct kinfo_proc kinfo_proc;
static int GetBSDProcessList(kinfo_proc **procList, size_t *procCount) 
{
    int                 err;
    kinfo_proc *        result;
    bool                done;
    static const int    name[] = { CTL_KERN, KERN_PROC, KERN_PROC_ALL, 0 };
    // Declaring name as const requires us to cast it when passing it to
    // sysctl because the prototype doesn't include the const modifier.
    size_t              length;

    assert( procList != NULL);
    assert(*procList == NULL);
    assert(procCount != NULL);

    *procCount = 0;

    /*
     * We start by calling sysctl with result == NULL and length == 0.
     * That will succeed, and set length to the appropriate length.
     * We then allocate a buffer of that size and call sysctl again
     * with that buffer.  If that succeeds, we're done.  If that fails
     * with ENOMEM, we have to throw away our buffer and loop.  Note
     * that the loop causes use to call sysctl with NULL again; this
     * is necessary because the ENOMEM failure case sets length to
     * the amount of data returned, not the amount of data that
     * could have been returned.
     */
    result = NULL;
    done = false;
    do {
        assert(result == NULL);
        // Call sysctl with a NULL buffer.
        length = 0;
        err = sysctl( (int *) name, (sizeof(name) / sizeof(*name)) - 1,
                      NULL, &length,
                      NULL, 0);
        if (err == -1) {
            err = errno;
        }

        // Allocate an appropriately sized buffer based on the results
        // from the previous call.
        if (err == 0) {
            result = malloc(length);
            if (result == NULL) {
                err = ENOMEM;
            }
        }

        // Call sysctl again with the new buffer.  If we get an ENOMEM
        // error, toss away our buffer and start again.
        if (err == 0) {
            err = sysctl( (int *) name, (sizeof(name) / sizeof(*name)) - 1,
                          result, &length,
                          NULL, 0);
            if (err == -1) {
                err = errno;
            }
            if (err == 0) {
                done = true;
            } else if (err == ENOMEM) {
                assert(result != NULL);
                free(result);
                result = NULL;
                err = 0;
            }
        }
    } while (err == 0 && ! done);

    // Clean up and establish post conditions.
    if (err != 0 && result != NULL) {
        free(result);
        result = NULL;
    }
    *procList = result;
    if (err == 0) {
        *procCount = length / sizeof(kinfo_proc);
    }

    assert( (err == 0) == (*procList != NULL) );

    return err;
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



/*
 * Borrowed from psi Python System Information project
 * 
 * Get command arguments and environment variables.
 *
 * Based on code from ps.
 *
 * Returns:
 *      0 for success;
 *      -1 for failure (Exception raised);
 *      1 for insufficient privileges.
 */
static int getcmdargs(long pid, PyObject **exec_path, PyObject **arglist, PyObject **envdict)
{
    PyObject    *arg;
    char        *arg_start;
    int         mib[3], argmax, nargs, c = 0;
    size_t      size;
    char        *procargs, *sp, *np, *cp;
    PyObject    *val;
    char        *val_start;

    *arglist = Py_BuildValue("[]");     /* empty list */
    if (*arglist == NULL)
        return -1;

    *envdict = Py_BuildValue("{}");     /* empty dict */
    if (*envdict == NULL)
        return -1;

    /* Get the maximum process arguments size. */
    mib[0] = CTL_KERN;
    mib[1] = KERN_ARGMAX;

    size = sizeof(argmax);
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) == -1) {
        return 1;
    }

    /* Allocate space for the arguments. */
    procargs = (char *)malloc(argmax);
    if (procargs == NULL) {
        PyErr_Format(PyExc_MemoryError, "Cannot allocate memory for procargs");
        return -1;
    }

    /*
     * Make a sysctl() call to get the raw argument space of the process.
     */
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROCARGS2;
    mib[2] = pid;

    size = (size_t)argmax;
    if (sysctl(mib, 3, procargs, &size, NULL, 0) == -1) {
        //perror(NULL);
        // goto ERROR_B;
        free(procargs);
        return 1;       /* Insufficient privileges */
    }

    memcpy(&nargs, procargs, sizeof(nargs));
    cp = procargs + sizeof(nargs);

    /* Save the exec_path */
    *exec_path = Py_BuildValue("s", cp);
    if (*exec_path == NULL)
        goto ERROR_C;   /* Exception */

    /* Skip over the exec_path. */
    for (; cp < &procargs[size]; cp++) {
        if (*cp == '\0') {
            /* End of exec_path reached. */
            break;
        }
    }
    if (cp == &procargs[size]) {
        goto ERROR_B;
    }

    /* Skip trailing '\0' characters. */
    for (; cp < &procargs[size]; cp++) {
        if (*cp != '\0') {
            /* Beginning of first argument reached. */
            break;
        }
    }
    if (cp == &procargs[size]) {
        goto ERROR_B;
    }
    /* Save where the argv[0] string starts. */
    sp = cp;

    /*
     * Iterate through the '\0'-terminated strings and add each string
     * to the Python List arglist as a Python string.
     * Stop when nargs strings have been extracted.  That should be all
     * the arguments.  The rest of the strings will be environment
     * strings for the command.
     */
    for (arg_start = cp; c < nargs && cp < &procargs[size]; cp++) {
        if (*cp == '\0') {
            /* Fetch next argument */
            c++;
            arg = Py_BuildValue("s", arg_start);
            if (arg == NULL)
                goto ERROR_C;   /* Exception */
            PyList_Append(*arglist, arg);
            
            arg_start = cp + 1;
        }
    }

    /*
     * Continue extracting '\0'-terminated strings and save in Python
     * dictionary of environment settings.
     */
    np = cp;
    val_start = NULL;
    for (arg_start = cp; cp < &procargs[size]; cp++) {
        if (*cp == '\0') {
            if (np != NULL) {
                if (&np[1] == cp || val_start == NULL) {
                    /*
                     * Two '\0' characters in a row.
                     * This should normally only
                     * happen after all the strings
                     * have been seen, but in any
                     * case, stop parsing.
                     */
                    break;
                }
                /* Fetch next environment string. */
                arg = Py_BuildValue("s", arg_start);
                if (arg == NULL)
                    goto ERROR_C;   /* Exception */
             
                val = Py_BuildValue("s", val_start);
                if (val == NULL)
                    goto ERROR_C;   /* Exception */

                PyDict_SetItem(*envdict, arg, val);
            }
            /* Note location of current '\0'. */
            np = cp;
            arg_start = cp + 1;
            val_start = NULL;
        } else if (val_start == NULL && *cp == '=') {
            /* start of environment value */
            *cp = '\0';     /* terminate the environment variable name */
            val_start = cp + 1;
        }
    }

    /*
     * sp points to the beginning of the arguments/environment string, and
     * np should point to the '\0' terminator for the string.
     */
    if (np == NULL || np == sp) {
        /* Empty or unterminated string. */
        goto ERROR_B;
    }

    /* Make a copy of the string. */
/*    asprintf(args, "%s", sp);*/

    /* Clean up. */
    free(procargs);
    return 0;

    ERROR_B:
    PyErr_Format(PyExc_SystemError, "getcmdargs() failure.");
    ERROR_C:
    free(procargs);
    return -1;
}


/* return process args as a python list */
static PyObject* get_arg_list(long pid)
{
    int r;
    PyObject *cmd_args = NULL;
    PyObject *command_path = NULL;
    PyObject *env = NULL;
    PyObject *argList = PyList_New(0);

    /* Fetch the command-line arguments and environment variables */
    //printf("pid: %ld\n", pid);
    if (pid < 0) {
        return argList;
    } 

    r = getcmdargs(pid, &command_path, &cmd_args, &env);
    if (r == 0) {
        //PySequence_Tuple(args);
        argList = PySequence_List(cmd_args);
    }

    //printf("r = %i\n", r);
    return argList;
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
	
    infoTuple = Py_BuildValue("lssNNN", pid, "<unknown>", "<unknown>", PyList_New(0), Py_BuildValue(""), Py_BuildValue(""));

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
        infoTuple = Py_BuildValue("lssNll", pid, kp.kp_proc.p_comm, "<unknown>", get_arg_list(pid), kp.kp_eproc.e_pcred.p_ruid, kp.kp_eproc.e_pcred.p_rgid);
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
