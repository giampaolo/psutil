/*
 * $Id$
 *
 * Helper functions related to fetching process information. Used by _psutil_osx
 * module methods.
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
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
 *      0 for success;
 *      -1 for failure (Exception raised);
 *      1 for insufficient privileges.
 */
int getcmdargs(long pid, PyObject **exec_path, PyObject **arglist)
{
    char        *arg_start;
    int         mib[3], argmax, nargs, c = 0;
    size_t      size;
    char        *procargs, *sp, *np, *cp;
    PyObject    *arg;
    PyObject    *val;
    char        *val_start;

    *arglist = Py_BuildValue("[]");     /* empty list */
    if (*arglist == NULL) {
        PyErr_SetString(PyExc_SystemError,
                        "getcmdargs(): failed to build empty list");
        return -1;
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
                           "getcmdargs(): Cannot allocate memory for procargs");
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
        if (22 == errno) { // invalid parameter == access denied for some reason
            free(procargs);
            return -2;       /* Insufficient privileges */
        }

        PyErr_SetFromErrno(PyExc_OSError);
        free(procargs);
        return -1;
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
            // End of exec_path reached.
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
            Py_DECREF(arg);

            arg_start = cp + 1;
        }
    }

    /*
     * sp points to the beginning of the arguments/environment string, and
     * np should point to the '\0' terminator for the string.
     */

    if (np == NULL || np == sp) {
        // Empty or unterminated string.
        goto ERROR_B;
    }

    // Make a copy of the string.
    // asprintf(args, "%s", sp);

    // Clean up.
    free(procargs);
    return 0;

    ERROR_B:
    PyErr_SetString(PyExc_MemoryError, "getcmdargs() failure to allocate memory.");

    ERROR_C:
    PyErr_SetString(PyExc_SystemError, "getcmdargs(): failed to parse string values.");

    if (NULL != procargs) {
        free(procargs);
    }
    return -1;
}


/* return process args as a python list */
PyObject* get_arg_list(long pid)
{
    int r;
    PyObject *cmd_args = NULL;
    PyObject *command_path = NULL;
    PyObject *argList = Py_BuildValue("");

    //special case for PID 0 (kernel_task) where cmdline cannot be fetched
    if (pid == 0) {
        Py_DECREF(argList);
        return Py_BuildValue("[]");
    }

    /* Fetch the command-line arguments and environment variables */
    //printf("pid: %ld\n", pid);
    if (pid < 0) {
        return argList;
    }

    r = getcmdargs(pid, &command_path, &cmd_args);
    if (r == 0) {
        //PySequence_Tuple(args);
        argList = PySequence_List(cmd_args);
        Py_XDECREF(cmd_args);
        Py_XDECREF(command_path);
    }

    if (r == ARGS_ACCESS_DENIED) { //-2
        Py_XDECREF(cmd_args);
        Py_XDECREF(command_path);
        Py_DECREF(argList);
        return Py_BuildValue("[]");
    }

    return argList;
}

