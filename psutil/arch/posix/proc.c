/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */


#include <signal.h>
#include <sys/resource.h>

#include "../../arch/all/init.h"


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
        psutil_oserror_wsyscall(syscall);
    else if (psutil_pid_exists(pid) == 0)
        psutil_oserror_nsp(syscall);
    else
        psutil_runtime_error("%s syscall failed", syscall);
}


// Get PID priority.
PyObject *
psutil_proc_priority_get(PyObject *self, PyObject *args) {
    pid_t pid;
    int priority;
    errno = 0;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

#ifdef PSUTIL_OSX
    priority = getpriority(PRIO_PROCESS, (id_t)pid);
#else
    priority = getpriority(PRIO_PROCESS, pid);
#endif
    if (errno != 0)
        return psutil_oserror();
    return Py_BuildValue("i", priority);
}


// Set PID priority.
PyObject *
psutil_proc_priority_set(PyObject *self, PyObject *args) {
    pid_t pid;
    int priority;
    int retval;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &priority))
        return NULL;

#ifdef PSUTIL_OSX
    retval = setpriority(PRIO_PROCESS, (id_t)pid, priority);
#else
    retval = setpriority(PRIO_PROCESS, pid, priority);
#endif
    if (retval == -1)
        return psutil_oserror();
    Py_RETURN_NONE;
}
