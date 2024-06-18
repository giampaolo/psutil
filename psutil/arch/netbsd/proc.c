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

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"
#include "proc.h"


#define PSUTIL_KPT2DOUBLE(t) (t ## _sec + t ## _usec / 1000000.0)
#define PSUTIL_TV2DOUBLE(t) ((t).tv_sec + (t).tv_usec / 1000000.0)


// ============================================================================
// Utility functions
// ============================================================================


int
psutil_kinfo_proc(pid_t pid, kinfo_proc *proc) {
    // Fills a kinfo_proc struct based on process pid.
    int ret;
    int mib[6];
    size_t size = sizeof(kinfo_proc);

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC2;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;
    mib[4] = size;
    mib[5] = 1;

    ret = sysctl((int*)mib, 6, proc, &size, NULL, 0);
    if (ret == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return -1;
    }
    // sysctl stores 0 in the size if we can't find the process information.
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        return -1;
    }
    return 0;
}


struct kinfo_file *
kinfo_getfile(pid_t pid, int* cnt) {
    // Mimic's FreeBSD kinfo_file call, taking a pid and a ptr to an
    // int as arg and returns an array with cnt struct kinfo_file.
    int mib[6];
    size_t len;
    struct kinfo_file* kf;
    mib[0] = CTL_KERN;
    mib[1] = KERN_FILE2;
    mib[2] = KERN_FILE_BYPID;
    mib[3] = (int) pid;
    mib[4] = sizeof(struct kinfo_file);
    mib[5] = 0;

    // get the size of what would be returned
    if (sysctl(mib, 6, NULL, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if ((kf = malloc(len)) == NULL) {
        PyErr_NoMemory();
        return NULL;
    }
    mib[5] = (int)(len / sizeof(struct kinfo_file));
    if (sysctl(mib, 6, kf, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    *cnt = (int)(len / sizeof(struct kinfo_file));
    return kf;
}

PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    long pid;

    char path[MAXPATHLEN];
    size_t pathlen = sizeof path;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

#ifdef KERN_PROC_CWD
    int name[] = { CTL_KERN, KERN_PROC_ARGS, pid, KERN_PROC_CWD};
    if (sysctl(name, 4, path, &pathlen, NULL, 0) != 0) {
        if (errno == ENOENT)
            NoSuchProcess("sysctl -> ENOENT");
        else
            PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
#else
    char *buf;
    if (asprintf(&buf, "/proc/%d/cwd", (int)pid) < 0) {
        PyErr_NoMemory();
        return NULL;
    }

    ssize_t len = readlink(buf, path, sizeof(path) - 1);
    free(buf);
    if (len == -1) {
        if (errno == ENOENT)
            NoSuchProcess("readlink -> ENOENT");
        else
            PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    path[len] = '\0';
#endif

    return PyUnicode_DecodeFSDefault(path);
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
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    error = sysctl(mib, 4, pathname, &size, NULL, 0);
    if (error == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (size == 0 || strlen(pathname) == 0) {
        ret = psutil_pid_exists(pid);
        if (ret == -1)
            return NULL;
        else if (ret == 0)
            return NoSuchProcess("psutil_pid_exists -> 0");
        else
            strcpy(pathname, "");
    }

    return PyUnicode_DecodeFSDefault(pathname);
#else
    return Py_BuildValue("s", "");
#endif
}
*/


PyObject *
psutil_proc_num_threads(PyObject *self, PyObject *args) {
    // Return number of threads used by process as a Python integer.
    long pid;
    kinfo_proc kp;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
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
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    mib[0] = CTL_KERN;
    mib[1] = KERN_LWP;
    mib[2] = pid;
    mib[3] = sizeof(struct kinfo_lwp);
    mib[4] = 0;

    st = sysctl(mib, 5, NULL, &size, NULL, 0);
    if (st == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        goto error;
    }

    mib[4] = size / sizeof(size_t);
    kl = malloc(size);
    if (kl == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    st = sysctl(mib, 5, kl, &size, NULL, 0);
    if (st == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        goto error;
    }

    nlwps = (int)(size / sizeof(struct kinfo_lwp));
    for (i = 0; i < nlwps; i++) {
        if ((&kl[i])->l_stat == LSIDL || (&kl[i])->l_stat == LSZOMB)
            continue;
        // XXX: we return 2 "user" times because the struct does not provide
        // any "system" time.
        py_tuple = Py_BuildValue("idd",
                                 (&kl[i])->l_lid,
                                 PSUTIL_KPT2DOUBLE((&kl[i])->l_rtime),
                                 PSUTIL_KPT2DOUBLE((&kl[i])->l_rtime));
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


int
psutil_get_proc_list(kinfo_proc **procList, size_t *procCount) {
    // Returns a list of all BSD processes on the system.  This routine
    // allocates the list and puts it in *procList and a count of the
    // number of entries in *procCount.  You are responsible for freeing
    // this list (use "free" from System framework).
    // On success, the function returns 0.
    // On error, the function returns a BSD errno value.
    kinfo_proc *result;
    // Declaring name as const requires us to cast it when passing it to
    // sysctl because the prototype doesn't include the const modifier.
    char errbuf[_POSIX2_LINE_MAX];
    int cnt;
    kvm_t *kd;

    assert( procList != NULL);
    assert(*procList == NULL);
    assert(procCount != NULL);

    kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);

    if (kd == NULL) {
        PyErr_Format(
            PyExc_RuntimeError, "kvm_openfiles() syscall failed: %s", errbuf);
        return 1;
    }

    result = kvm_getproc2(kd, KERN_PROC_ALL, 0, sizeof(kinfo_proc), &cnt);
    if (result == NULL) {
        PyErr_Format(PyExc_RuntimeError, "kvm_getproc2() syscall failed");
        kvm_close(kd);
        return 1;
    }

    *procCount = (size_t)cnt;

    size_t mlen = cnt * sizeof(kinfo_proc);

    if ((*procList = malloc(mlen)) == NULL) {
        PyErr_NoMemory();
        kvm_close(kd);
        return 1;
    }

    memcpy(*procList, result, mlen);
    assert(*procList != NULL);
    kvm_close(kd);

    return 0;
}


PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    int mib[4];
    int st;
    int attempt;
    int max_attempts = 50;
    size_t len = 0;
    size_t pos = 0;
    char *procargs = NULL;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC_ARGS;
    mib[2] = pid;
    mib[3] = KERN_PROC_ARGV;

    st = sysctl(mib, __arraycount(mib), NULL, &len, NULL, 0);
    if (st == -1) {
        PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_ARGV) get size");
        goto error;
    }

    procargs = (char *)malloc(len);
    if (procargs == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    while (1) {
        st = sysctl(mib, __arraycount(mib), procargs, &len, NULL, 0);
        if (st == -1) {
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
                    free(procargs);
                    return py_retlist;
                }
            }
            else {
                PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_ARGV)");
                goto error;
            }
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

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
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
