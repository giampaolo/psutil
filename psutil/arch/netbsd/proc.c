/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Platform-specific module methods for NetBSD.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <kvm.h>

#include "../../arch/all/init.h"


PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    long pid;
    char path[MAXPATHLEN];

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

#ifdef KERN_PROC_CWD  // available since NetBSD 99.43
    int name[] = {CTL_KERN, KERN_PROC_ARGS, pid, KERN_PROC_CWD};
    size_t pathlen = sizeof(path);

    if (sysctl(name, 4, path, &pathlen, NULL, 0) != 0)
        goto error;
#else
    char buf[32];
    ssize_t len;

    str_format(buf, sizeof(buf), "/proc/%d/cwd", (int)pid);
    len = readlink(buf, path, sizeof(path) - 1);
    if (len == -1)
        goto error;
    path[len] = '\0';
#endif

    return PyUnicode_DecodeFSDefault(path);

error:
    if (errno == ENOENT)
        psutil_oserror_nsp("sysctl -> ENOENT");
    else
        psutil_oserror();
    return NULL;
}


// XXX: This is no longer used as per
// https://github.com/giampaolo/psutil/pull/557#issuecomment-171912820
// Current implementation uses /proc instead.
// Left here just in case.
/*
PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
#if __NetBSD_Version__ >= 799000000
    pid_t pid;
    char pathname[MAXPATHLEN];
    int error;
    int mib[4];
    int ret;
    size_t size;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (pid == 0) {
        // else returns ENOENT
        return Py_BuildValue("s", "");
    }

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC_ARGS;
    mib[2] = pid;
    mib[3] = KERN_PROC_PATHNAME;

    size = sizeof(pathname);
    error = sysctl(mib, 4, NULL, &size, NULL, 0);
    if (error == -1) {
        psutil_oserror();
        return NULL;
    }

    error = sysctl(mib, 4, pathname, &size, NULL, 0);
    if (error == -1) {
        psutil_oserror();
        return NULL;
    }
    if (size == 0 || strlen(pathname) == 0) {
        ret = psutil_pid_exists(pid);
        if (ret == -1)
            return NULL;
        else if (ret == 0)
            return psutil_oserror_nsp("psutil_pid_exists -> 0");
        else
            str_copy(pathname, sizeof(pathname), "");
    }

    return PyUnicode_DecodeFSDefault(pathname);
#else
    return Py_BuildValue("s", "");
#endif
}
*/


PyObject *
psutil_proc_num_threads(PyObject *self, PyObject *args) {
    long pid;
    struct kinfo_proc2 kp;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        return NULL;
    return Py_BuildValue("l", (long)kp.p_nlwps);
}


PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    pid_t pid;
    int mib[5];
    int i, nlwps;
    ssize_t st;
    size_t size;
    struct kinfo_lwp *kl = NULL;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    mib[0] = CTL_KERN;
    mib[1] = KERN_LWP;
    mib[2] = pid;
    mib[3] = sizeof(struct kinfo_lwp);
    mib[4] = 0;

    // first query size
    st = sysctl(mib, 5, NULL, &size, NULL, 0);
    if (st == -1) {
        psutil_oserror();
        goto error;
    }
    if (size == 0) {
        psutil_oserror_nsp("sysctl (size = 0)");
        goto error;
    }

    // set slot count for NetBSD KERN_LWP
    mib[4] = size / sizeof(size_t);

    if (psutil_sysctl_malloc(mib, __arraycount(mib), (char **)&kl, &size) != 0)
    {
        goto error;
    }
    if (size == 0) {
        psutil_oserror_nsp("sysctl (size = 0)");
        goto error;
    }

    nlwps = (int)(size / sizeof(struct kinfo_lwp));
    for (i = 0; i < nlwps; i++) {
        if (kl[i].l_stat == LSIDL || kl[i].l_stat == LSZOMB)
            continue;
        // XXX: return 2 "user" times, no "system" time available
        py_tuple = Py_BuildValue(
            "idd",
            kl[i].l_lid,
            PSUTIL_KPT2DOUBLE(kl[i].l_rtime),
            PSUTIL_KPT2DOUBLE(kl[i].l_rtime)
        );
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }

    free(kl);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (kl != NULL)
        free(kl);
    return NULL;
}


PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    int mib[4];
    int st;
    int attempt = 0;
    int max_attempts = 50;
    size_t len = 0;
    size_t pos = 0;
    char *procargs = NULL;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC_ARGS;
    mib[2] = pid;
    mib[3] = KERN_PROC_ARGV;

    while (1) {
        if (psutil_sysctl_malloc(
                mib, __arraycount(mib), (char **)&procargs, &len
            )
            != 0)
        {
            if (errno == EBUSY) {
                // Usually happens with TestProcess.test_long_cmdline. See:
                // https://github.com/giampaolo/psutil/issues/2250
                attempt += 1;
                if (attempt < max_attempts) {
                    psutil_debug("proc %zu cmdline(): retry on EBUSY", pid);
                    continue;
                }
                else {
                    psutil_debug(
                        "proc %zu cmdline(): return [] due to EBUSY", pid
                    );
                    return py_retlist;
                }
            }
            goto error;
        }
        break;
    }

    if (len > 0) {
        while (pos < len) {
            py_arg = PyUnicode_DecodeFSDefault(&procargs[pos]);
            if (!py_arg)
                goto error;
            if (PyList_Append(py_retlist, py_arg))
                goto error;
            Py_DECREF(py_arg);
            pos = pos + strlen(&procargs[pos]) + 1;
        }
    }

    free(procargs);
    return py_retlist;

error:
    Py_XDECREF(py_arg);
    Py_DECREF(py_retlist);
    if (procargs != NULL)
        free(procargs);
    return NULL;
}


PyObject *
psutil_proc_num_fds(PyObject *self, PyObject *args) {
    long pid;
    int cnt;

    struct kinfo_file *freep;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    errno = 0;
    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_for_pid(pid, "kinfo_getfile()");
        return NULL;
    }
    free(freep);

    return Py_BuildValue("i", cnt);
}
