/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */


#include <signal.h>
#include <sys/resource.h>

#include "../../arch/all/init.h"

// Check if PID exists. Return values:
// 1: exists
// 0: does not exist
// -1: error (Python exception is set)
int
psutil_pid_exists(pid_t pid) {
    int ret;

    // No negative PID exists, plus -1 is an alias for sending signal
    // too all processes except system ones. Not what we want.
    if (pid < 0)
        return 0;

    // As per "man 2 kill" PID 0 is an alias for sending the signal to
    // every process in the process group of the calling process.
    // Not what we want. Some platforms have PID 0, some do not.
    // We decide that at runtime.
    if (pid == 0) {
#if defined(PSUTIL_LINUX) || defined(PSUTIL_FREEBSD)
        return 0;
#else
        return 1;
#endif
    }

    ret = kill(pid , 0);
    if (ret == 0)
        return 1;
    else {
        if (errno == ESRCH) {
            // ESRCH == No such process
            return 0;
        }
        else if (errno == EPERM) {
            // EPERM clearly indicates there's a process to deny
            // access to.
            return 1;
        }
        else {
            // According to "man 2 kill" possible error values are
            // (EINVAL, EPERM, ESRCH) therefore we should never get
            // here. If we do let's be explicit in considering this
            // an error.
            PyErr_SetFromErrno(PyExc_OSError);
            return -1;
        }
    }
}


// Utility used for those syscalls which do not return a meaningful
// error that we can translate into an exception which makes sense. As
// such, we'll have to guess. On UNIX, if errno is set, we return that
// one (OSError). Else, if PID does not exist we assume the syscall
// failed because of that so we raise NoSuchProcess. If none of this is
// true we giveup and raise RuntimeError(msg). This will always set a
// Python exception and return NULL.
void
psutil_raise_for_pid(pid_t pid, char *syscall) {
    if (errno != 0)
        psutil_PyErr_SetFromOSErrnoWithSyscall(syscall);
    else if (psutil_pid_exists(pid) == 0)
        NoSuchProcess(syscall);
    else
        PyErr_Format(PyExc_RuntimeError, "%s syscall failed", syscall);
}


// Get PID priority.
PyObject *
psutil_proc_priority_get(PyObject *self, PyObject *args) {
    pid_t pid;
    int priority;
    errno = 0;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

#ifdef PSUTIL_OSX
    priority = getpriority(PRIO_PROCESS, (id_t)pid);
#else
    priority = getpriority(PRIO_PROCESS, pid);
#endif
    if (errno != 0)
        return PyErr_SetFromErrno(PyExc_OSError);
    return Py_BuildValue("i", priority);
}


// Set PID priority.
PyObject *
psutil_proc_priority_set(PyObject *self, PyObject *args) {
    pid_t pid;
    int priority;
    int retval;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &priority))
        return NULL;

#ifdef PSUTIL_OSX
    retval = setpriority(PRIO_PROCESS, (id_t)pid, priority);
#else
    retval = setpriority(PRIO_PROCESS, pid, priority);
#endif
    if (retval == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    Py_RETURN_NONE;
}
