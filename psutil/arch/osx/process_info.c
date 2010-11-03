/*
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_osx
 * module methods.
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <limits.h>  /* for INT_MAX */
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/sysctl.h>

#include "process_info.h"

#define ARGS_ACCESS_DENIED -2



/*
 * Returns a list of all BSD processes on the system.  This routine
 * allocates the list and puts it in *procList and a count of the
 * number of entries in *procCount.  You are responsible for freeing
 * this list (use "free" from System framework).
 * On success, the function returns 0.
 * On error, the function returns a BSD errno value.
 */
int
get_proc_list(kinfo_proc **procList, size_t *procCount)
{
    /* Declaring mib as const requires use of a cast since the
     * sysctl prototype doesn't include the const modifier. */
    static const int mib3[3] = { CTL_KERN, KERN_PROC, KERN_PROC_ALL };
    size_t           size, size2;
    void            *ptr;
    int              err, lim = 8;  /* some limit */

    assert( procList != NULL);
    assert(*procList == NULL);
    assert(procCount != NULL);

    *procCount = 0;

    /* We start by calling sysctl with ptr == NULL and size == 0.
     * That will succeed, and set size to the appropriate length.
     * We then allocate a buffer of at least that size and call
     * sysctl with that buffer.  If that succeeds, we're done.
     * If that call fails with ENOMEM, we throw the buffer away
     * and try again.
     * Note that the loop calls sysctl with NULL again.  This is
     * is necessary because the ENOMEM failure case sets size to
     * the amount of data returned, not the amount of data that
     * could have been returned.
     */
    while (lim-- > 0) {
        size = 0;
        if (sysctl((int *)mib3, 3, NULL, &size, NULL, 0) == -1) {
            return errno;
        }

        size2 = size + (size >> 3);  /* add some */
        if (size2 > size) {
            ptr = malloc(size2);
            if (ptr == NULL) {
                ptr = malloc(size);
            } else {
                size = size2;
            }
        }
        else {
            ptr = malloc(size);
        }
        if (ptr == NULL) {
            return ENOMEM;
        }

        if (sysctl((int *)mib3, 3, ptr, &size, NULL, 0) == -1) {
            err = errno;
            free(ptr);
            if (err != ENOMEM) {
                return err;
            }

        } else {
            *procList = (kinfo_proc *)ptr;
            *procCount = size / sizeof(kinfo_proc);
            return 0;
        }
    }
    return ENOMEM;
}


/*
 * Modified from psi Python System Information project
 *
 * Get command path, arguments and environment variables.
 *
 * Based on code from ps.
 *
 * Returns:
 *       0 for success
 *       1 for sysctl error, errno exception raised
 *      -1 for failure, system or memory exception raised
 *      -2 rather ARGS_ACCESS_DENIED, for insufficient privileges
 */
int
getcmdargs(long pid, PyObject **exec_path, PyObject **envlist, PyObject **arglist)
{
    int nargs, mib[3];
    size_t size, argmax;
    char *curr_arg, *start_args, *iter_args, *end_args;
    char *procargs = NULL;
    char *err = NULL;
    PyObject *arg;

    *arglist = Py_BuildValue("[]");     /* empty list */
    if (*arglist == NULL) {
        err = "getcmdargs(): arglist exception";
        goto ERROR_RETURN;
    }

    /* Get the maximum process arguments size. */
    mib[0] = CTL_KERN;
    mib[1] = KERN_ARGMAX;

    size = sizeof(argmax);
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(NULL);
        return errno;
    }

    /* Allocate space for the arguments. */
    procargs = (char *)malloc(argmax);
    if (procargs == NULL) {
        PyErr_SetString(PyExc_MemoryError,
                        "getcmdargs(): insufficient memory for procargs");
        return ENOMEM;
    }

    /*
     * Make a sysctl() call to get the raw argument space of the process.
     */
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROCARGS2;
    mib[2] = (int)pid;

    size = argmax;
    if (sysctl(mib, 3, procargs, &size, NULL, 0) == -1) {
        if (EINVAL == errno) { // invalid == access denied for some reason
            free(procargs);
            return ARGS_ACCESS_DENIED;  /* Insufficient privileges */
        }

        PyErr_SetFromErrno(PyExc_OSError);
        free(procargs);
        return errno;
    }

    // copy the number of argument to nargs
    memcpy(&nargs, procargs, sizeof(nargs));
    iter_args =  procargs + sizeof(nargs);
    end_args = &procargs[size]; // end of the argument space
    if (iter_args >= end_args) {
        err = "getcmdargs(): argument length mismatch";
        goto ERROR_RETURN;
    }

    // Save the path
    if (NULL != exec_path) {
        *exec_path = Py_BuildValue("s", iter_args);
        if (*exec_path == NULL) {
            err = "getcmdargs(): exec_path exception";
            goto ERROR_RETURN;
        }
    }

    //TODO: save the environment variables to envlist as well
    // Skip over the exec_path and '\0' characters.
    while (iter_args < end_args && *iter_args != '\0') { iter_args++; }
    while (iter_args < end_args && *iter_args == '\0') { iter_args++; }

    /* Iterate through the '\0'-terminated strings and add each string
     * to the Python List arglist as a Python string.
     * Stop when nargs strings have been extracted.  That should be all
     * the arguments.  The rest of the strings will be environment
     * strings for the command.
     */
    curr_arg = iter_args;
    start_args = iter_args; //reset start position to beginning of cmdline
    while (iter_args < end_args && nargs > 0) {
        if (*iter_args++ == '\0') {
            /* Fetch next argument */
            arg = Py_BuildValue("s", curr_arg);
            if (arg == NULL) {
                err = "getcmdargs(): exception building argument string";
                goto ERROR_RETURN;
            }
            PyList_Append(*arglist, arg);
            Py_DECREF(arg);

            curr_arg = iter_args;
            nargs--;
        }
    }

    /*
     * curr_arg position should be further than the start of the argspace
     * and number of arguments should be 0 after iterating above. Otherwise
     * we had an empty argument space or a missing terminating \0 etc.
     */
    if (curr_arg == start_args || nargs > 0) {
        err = "getcmdargs(): argument parsing failed";
        goto ERROR_RETURN;
    }

ERROR_RETURN:
    // Clean up.
    if (NULL != procargs) {
        free(procargs);
    }
    if (NULL != err) {
        PyErr_SetString(PyExc_SystemError, err);
        return -1;
    }
    return 0;
}


/* return process args as a python list */
PyObject*
get_arg_list(long pid)
{
    int r;
    PyObject *argList;
    PyObject *env = NULL;
    PyObject *args = NULL;
    PyObject *exec_path = NULL;

    //special case for PID 0 (kernel_task) where cmdline cannot be fetched
    if (pid == 0) {
        return Py_BuildValue("[]");
    }

    /* Fetch the command-line arguments and environment variables */
    //printf("pid: %ld\n", pid);
    if (pid < 0 || pid > (long)INT_MAX) {
        return Py_BuildValue("");
    }

    r = getcmdargs(pid, &exec_path, &env, &args);
    if (r == 0) {
        //PySequence_Tuple(args);
        argList = PySequence_List(args);
    }
    else if (r == ARGS_ACCESS_DENIED) { //-2
        argList = Py_BuildValue("[]");
    }
    else {
        argList = Py_BuildValue("");
    }

    Py_XDECREF(args);
    Py_XDECREF(exec_path);
    Py_XDECREF(env);
    return argList;
}


int
get_kinfo_proc(pid_t pid, struct kinfo_proc *kp)
{
    int mib[4];
    size_t len;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    // fetch the info with sysctl()
    len = sizeof(struct kinfo_proc);

    // now read the data from sysctl
    if (sysctl(mib, 4, kp, &len, NULL, 0) == -1) {
        // raise an exception and throw errno as the error
        PyErr_SetFromErrno(PyExc_OSError);
    }

    /*
     * sysctl succeeds but len is zero, happens when process has gone away
     */
    if (len == 0) {
        errno = ESRCH;
        PyErr_SetFromErrno(PyExc_OSError);
        return -1;
    }
    return 0;
}
