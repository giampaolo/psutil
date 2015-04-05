/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information.
 * Used by _psutil_bsd module methods.
 */


#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/param.h>
#include <sys/user.h>
#include <sys/proc.h>
#include <signal.h>

#include "process_info.h"


/*
 * Returns a list of all BSD processes on the system.  This routine
 * allocates the list and puts it in *procList and a count of the
 * number of entries in *procCount.  You are responsible for freeing
 * this list (use "free" from System framework).
 * On success, the function returns 0.
 * On error, the function returns a BSD errno value.
 */
int
psutil_get_proc_list(struct kinfo_proc **procList, size_t *procCount)
{
    int err;
    struct kinfo_proc *result;
    int done;
    static const int name[] = { CTL_KERN, KERN_PROC, KERN_PROC_PROC, 0 };
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
    done = 0;
    do {
        assert(result == NULL);
        // Call sysctl with a NULL buffer.
        length = 0;
        err = sysctl((int *)name, (sizeof(name) / sizeof(*name)) - 1,
                     NULL, &length, NULL, 0);
        if (err == -1)
            err = errno;

        // Allocate an appropriately sized buffer based on the results
        // from the previous call.
        if (err == 0) {
            result = malloc(length);
            if (result == NULL)
                err = ENOMEM;
        }

        // Call sysctl again with the new buffer.  If we get an ENOMEM
        // error, toss away our buffer and start again.
        if (err == 0) {
            err = sysctl((int *) name, (sizeof(name) / sizeof(*name)) - 1,
                         result, &length, NULL, 0);
            if (err == -1)
                err = errno;
            if (err == 0) {
                done = 1;
            }
            else if (err == ENOMEM) {
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
    *procCount = length / sizeof(struct kinfo_proc);

    assert((err == 0) == (*procList != NULL));
    return err;
}


char
*psutil_get_cmd_path(long pid, size_t *pathsize)
{
    int mib[4];
    char *path;
    size_t size = 0;

    /*
     * Make a sysctl() call to get the raw argument space of the process.
     */
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PATHNAME;
    mib[3] = pid;

    // call with a null buffer first to determine if we need a buffer
    if (sysctl(mib, 4, NULL, &size, NULL, 0) == -1)
        return NULL;

    path = malloc(size);
    if (path == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    *pathsize = size;
    if (sysctl(mib, 4, path, &size, NULL, 0) == -1) {
        free(path);
        return NULL;       // Insufficient privileges
    }

    return path;
}


/*
 * XXX no longer used; it probably makese sense to remove it.
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
char
*psutil_get_cmd_args(long pid, size_t *argsize)
{
    int mib[4], argmax;
    size_t size = sizeof(argmax);
    char *procargs = NULL;

    // Get the maximum process arguments size.
    mib[0] = CTL_KERN;
    mib[1] = KERN_ARGMAX;

    size = sizeof(argmax);
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) == -1)
        return NULL;

    // Allocate space for the arguments.
    procargs = (char *)malloc(argmax);
    if (procargs == NULL) {
        PyErr_NoMemory();
        return NULL;
    }

    /*
     * Make a sysctl() call to get the raw argument space of the process.
     */
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_ARGS;
    mib[3] = pid;

    size = argmax;
    if (sysctl(mib, 4, procargs, &size, NULL, 0) == -1) {
        free(procargs);
        return NULL;       // Insufficient privileges
    }

    // return string and set the length of arguments
    *argsize = size;
    return procargs;
}


// returns the command line as a python list object
PyObject *
psutil_get_arg_list(long pid)
{
    char *argstr = NULL;
    int pos = 0;
    size_t argsize = 0;
    PyObject *retlist = Py_BuildValue("[]");
    PyObject *item = NULL;

    if (pid < 0)
        return retlist;
    argstr = psutil_get_cmd_args(pid, &argsize);
    if (argstr == NULL)
        goto error;

    // args are returned as a flattened string with \0 separators between
    // arguments add each string to the list then step forward to the next
    // separator
    if (argsize > 0) {
        while (pos < argsize) {
            item = Py_BuildValue("s", &argstr[pos]);
            if (!item)
                goto error;
            if (PyList_Append(retlist, item))
                goto error;
            Py_DECREF(item);
            pos = pos + strlen(&argstr[pos]) + 1;
        }
    }

    free(argstr);
    return retlist;

error:
    Py_XDECREF(item);
    Py_DECREF(retlist);
    if (argstr != NULL)
        free(argstr);
    return NULL;
}


/*
 * Return 1 if PID exists in the current process list, else 0.
 */
int
psutil_pid_exists(long pid)
{
    int kill_ret;

    if (pid < 0)
        return 0;
    // if kill returns success of permission denied we know it's a valid PID
    kill_ret = kill(pid , 0);
    if ((0 == kill_ret) || (EPERM == errno))
        return 1;
    // otherwise return 0 for PID not found
    return 0;
}

