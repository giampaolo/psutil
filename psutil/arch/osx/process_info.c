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
int GetBSDProcessList(kinfo_proc **procList, size_t *procCount)
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
        } else {
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
 * Borrowed from psi Python System Information project
 *
 * Get command arguments and environment variables.
 *
 * Based on code from ps.
 *
 * Returns:
 *       0 for success
 *       1 for sysctl error, errno exception raised
 *      -1 for failure, system or memory exception raised
 *      -2 rather ARGS_ACCESS_DENIED, for insufficient privileges
 */
int getcmdargs(long pid, PyObject **exec_path, PyObject **arglist)
{
    int       mib[3], nargs;
    size_t    size, argmax;
    PyObject  *arg;
    char      *ap, *sp, *cp, *ep;
    char      *procargs = NULL, *err = NULL;

    *arglist = Py_BuildValue("[]");     /* empty list */
    if (*arglist == NULL) {
        err = "getcmdargs(): arglist exception";
        goto erroreturn;
    }

    /* Get the maximum process arguments size. */
    mib[0] = CTL_KERN;
    mib[1] = KERN_ARGMAX;

    size = sizeof(argmax);
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(NULL);
        return 1;
    }

    /* Allocate space for the arguments. */
    procargs = (char *)malloc(argmax);
    if (procargs == NULL) {
        PyErr_SetString(PyExc_MemoryError,
                        "getcmdargs(): insufficient memory for procargs");
        return -1;
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
        return 1;
    }

    memcpy(&nargs, procargs, sizeof(nargs));
    cp =  procargs + sizeof(nargs);
    ep = &procargs[size];
    if (cp >= ep) {
        err = "getcmdargs(): path parsing";
        goto erroreturn;
    }

    if (NULL != exec_path) {  /* Save the path */
        *exec_path = Py_BuildValue("s", cp);
        if (*exec_path == NULL) {
            err = "getcmdargs(): path exception";
            goto erroreturn;
        }
    }

    /* Skip over the exec_path and '\0' characters. */
    while (cp < ep && *cp != '\0') cp++;
    while (cp < ep && *cp == '\0') cp++;

    /* Iterate through the '\0'-terminated strings and add each string
     * to the Python List arglist as a Python string.
     * Stop when nargs strings have been extracted.  That should be all
     * the arguments.  The rest of the strings will be environment
     * strings for the command.
     */
    ap = sp = cp;
    while (cp < ep && nargs > 0) {
        if (*cp++ == '\0') {
            /* Fetch next argument */
            arg = Py_BuildValue("s", ap);
            if (arg == NULL) {
                err = "getcmdargs(): args exception";
                goto erroreturn;
            }
            PyList_Append(*arglist, arg);
            Py_DECREF(arg);

            ap = cp;
            nargs--;
        }
    }

    /* sp points to the beginning of the arguments/environment string,
     * and ap should point past the '\0' terminator for the string.
     */
    if (ap == sp || nargs > 0) {
        err = "getcmdargs(): args parsing";  // empty or unterminated
        goto erroreturn;
    }

    // Make a copy of the string.
    // asprintf(args, "%s", sp);

erroreturn:
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
PyObject* get_arg_list(long pid)
{
    int r;
    PyObject *argList;
    PyObject *args = NULL;

    //special case for PID 0 (kernel_task) where cmdline cannot be fetched
    if (pid == 0) {
        return Py_BuildValue("[]");
    }

    /* Fetch the command-line arguments and environment variables */
    //printf("pid: %ld\n", pid);
    if (pid < 0 || pid > (long)INT_MAX) {
        return Py_BuildValue("");
    }

    r = getcmdargs(pid, NULL, &args);
    if (r == 0) {
        //PySequence_Tuple(args);
        argList = PySequence_List(args);
    } else if (r == ARGS_ACCESS_DENIED) { //-2
        argList = Py_BuildValue("[]");
    } else {
        argList = Py_BuildValue("");
    }

    Py_XDECREF(args);
    return argList;
}

