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

