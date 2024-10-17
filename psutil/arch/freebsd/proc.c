/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
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
#include <fcntl.h>
#include <devstat.h>
#include <libutil.h>  // process open files, shared libs (kinfo_getvmmap), cwd
#include <sys/cpuset.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"


#define PSUTIL_TV2DOUBLE(t)    ((t).tv_sec + (t).tv_usec / 1000000.0)


// ============================================================================
// Utility functions
// ============================================================================


int
psutil_kinfo_proc(pid_t pid, struct kinfo_proc *proc) {
    // Fills a kinfo_proc struct based on process pid.
    int mib[4];
    size_t size;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    size = sizeof(struct kinfo_proc);
    if (sysctl((int *)mib, 4, proc, &size, NULL, 0) == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_PID)");
        return -1;
    }

    // sysctl stores 0 in the size if we can't find the process information.
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        return -1;
    }
    return 0;
}


// remove spaces from string
static void psutil_remove_spaces(char *str) {
    char *p1 = str;
    char *p2 = str;
    do
        while (*p2 == ' ')
            p2++;
    while ((*p1++ = *p2++));
}


// ============================================================================
// APIS
// ============================================================================

int
psutil_get_proc_list(struct kinfo_proc **procList, size_t *procCount) {
    // Returns a list of all BSD processes on the system.  This routine
    // allocates the list and puts it in *procList and a count of the
    // number of entries in *procCount.  You are responsible for freeing
    // this list. On success returns 0, else 1 with exception set.
    int err;
    struct kinfo_proc *buf = NULL;
    int name[] = { CTL_KERN, KERN_PROC, KERN_PROC_PROC, 0 };
    size_t length = 0;
    size_t max_length = 12 * 1024 * 1024;  // 12MB

    assert(procList != NULL);
    assert(*procList == NULL);
    assert(procCount != NULL);

    // Call sysctl with a NULL buffer in order to get buffer length.
    err = sysctl(name, 3, NULL, &length, NULL, 0);
    if (err == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl (null buffer)");
        return 1;
    }

    while (1) {
        // Allocate an appropriately sized buffer based on the results
        // from the previous call.
        buf = malloc(length);
        if (buf == NULL) {
            PyErr_NoMemory();
            return 1;
        }

        // Call sysctl again with the new buffer.
        err = sysctl(name, 3, buf, &length, NULL, 0);
        if (err == -1) {
            free(buf);
            if (errno == ENOMEM) {
                // Sometimes the first sysctl() suggested size is not enough,
                // so we dynamically increase it until it's big enough :
                // https://github.com/giampaolo/psutil/issues/2093
                psutil_debug("errno=ENOMEM, length=%zu; retrying", length);
                length *= 2;
                if (length < max_length) {
                    continue;
                }
            }

            psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl()");
            return 1;
        }
        else {
            break;
        }
    }

    *procList = buf;
    *procCount = length / sizeof(struct kinfo_proc);
    return 0;
}


/*
 * Borrowed from psi Python System Information project
 * Based on code from ps.
 */
PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    int mib[4];
    int argmax;
    size_t size = sizeof(argmax);
    char *procargs = NULL;
    size_t pos = 0;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    // Get the maximum process arguments size.
    mib[0] = CTL_KERN;
    mib[1] = KERN_ARGMAX;

    size = sizeof(argmax);
    if (sysctl(mib, 2, &argmax, &size, NULL, 0) == -1)
        goto error;

    // Allocate space for the arguments.
    procargs = (char *)malloc(argmax);
    if (procargs == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    // Make a sysctl() call to get the raw argument space of the process.
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_ARGS;
    mib[3] = pid;

    size = argmax;
    if (sysctl(mib, 4, procargs, &size, NULL, 0) == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_ARGS)");
        goto error;
    }

    // args are returned as a flattened string with \0 separators between
    // arguments add each string to the list then step forward to the next
    // separator
    if (size > 0) {
        while (pos < size) {
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


/*
 * Return process pathname executable.
 * Thanks to Robert N. M. Watson:
 * http://fxr.googlebit.com/source/usr.bin/procstat/procstat_bin.c?v=8-CURRENT
 */
PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    pid_t pid;
    char pathname[PATH_MAX];
    int error;
    int mib[4];
    int ret;
    size_t size;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PATHNAME;
    mib[3] = pid;

    size = sizeof(pathname);
    error = sysctl(mib, 4, pathname, &size, NULL, 0);
    if (error == -1) {
        // see: https://github.com/giampaolo/psutil/issues/907
        if (errno == ENOENT) {
            return PyUnicode_DecodeFSDefault("");
        }
        else {
            return psutil_PyErr_SetFromOSErrnoWithSyscall(
                "sysctl(KERN_PROC_PATHNAME)"
            );
        }
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
}


PyObject *
psutil_proc_num_threads(PyObject *self, PyObject *args) {
    // Return number of threads used by process as a Python integer.
    pid_t pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        return NULL;
    return Py_BuildValue("l", (long)kp.ki_numthreads);
}


PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    // Retrieves all threads used by process returning a list of tuples
    // including thread id, user time and system time.
    // Thanks to Robert N. M. Watson:
    // http://code.metager.de/source/xref/freebsd/usr.bin/procstat/
    //     procstat_threads.c
    pid_t pid;
    int mib[4];
    struct kinfo_proc *kip = NULL;
    struct kinfo_proc *kipp = NULL;
    int error;
    unsigned int i;
    size_t size;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    // we need to re-query for thread information, so don't use *kipp
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID | KERN_PROC_INC_THREAD;
    mib[3] = pid;

    size = 0;
    error = sysctl(mib, 4, NULL, &size, NULL, 0);
    if (error == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_INC_THREAD)");
        goto error;
    }
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        goto error;
    }

    kip = malloc(size);
    if (kip == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    error = sysctl(mib, 4, kip, &size, NULL, 0);
    if (error == -1) {
        psutil_PyErr_SetFromOSErrnoWithSyscall("sysctl(KERN_PROC_INC_THREAD)");
        goto error;
    }
    if (size == 0) {
        NoSuchProcess("sysctl (size = 0)");
        goto error;
    }

    for (i = 0; i < size / sizeof(*kipp); i++) {
        kipp = &kip[i];
        py_tuple = Py_BuildValue("Idd",
                                 kipp->ki_tid,
                                 PSUTIL_TV2DOUBLE(kipp->ki_rusage.ru_utime),
                                 PSUTIL_TV2DOUBLE(kipp->ki_rusage.ru_stime));
        if (py_tuple == NULL)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }
    free(kip);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (kip != NULL)
        free(kip);
    return NULL;
}


#if defined(__FreeBSD_version) && __FreeBSD_version >= 701000
PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    pid_t pid;
    struct kinfo_file *freep = NULL;
    struct kinfo_file *kif;
    struct kinfo_proc kipp;
    PyObject *py_path = NULL;

    int i, cnt;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    if (psutil_kinfo_proc(pid, &kipp) == -1)
        goto error;

    errno = 0;
    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_for_pid(pid, "kinfo_getfile()");
        goto error;
    }

    for (i = 0; i < cnt; i++) {
        kif = &freep[i];
        if (kif->kf_fd == KF_FD_TYPE_CWD) {
            py_path = PyUnicode_DecodeFSDefault(kif->kf_path);
            if (!py_path)
                goto error;
            break;
        }
    }
    /*
     * For lower pids it seems we can't retrieve any information
     * (lsof can't do that it either).  Since this happens even
     * as root we return an empty string instead of AccessDenied.
     */
    if (py_path == NULL)
        py_path = PyUnicode_DecodeFSDefault("");
    free(freep);
    return py_path;

error:
    Py_XDECREF(py_path);
    if (freep != NULL)
        free(freep);
    return NULL;
}
#endif


#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
PyObject *
psutil_proc_num_fds(PyObject *self, PyObject *args) {
    pid_t pid;
    int cnt;

    struct kinfo_file *freep;
    struct kinfo_proc kipp;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kipp) == -1)
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
#endif


PyObject *
psutil_proc_memory_maps(PyObject *self, PyObject *args) {
    // Return a list of tuples for every process memory maps.
    // 'procstat' cmdline utility has been used as an example.
    pid_t pid;
    int ptrwidth;
    int i, cnt;
    char addr[1000];
    char perms[4];
    char *path;
    struct kinfo_proc kp;
    struct kinfo_vmentry *freep = NULL;
    struct kinfo_vmentry *kve;
    ptrwidth = 2 * sizeof(void *);
    PyObject *py_tuple = NULL;
    PyObject *py_path = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        goto error;

    errno = 0;
    freep = kinfo_getvmmap(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_for_pid(pid, "kinfo_getvmmap()");
        goto error;
    }
    for (i = 0; i < cnt; i++) {
        py_tuple = NULL;
        kve = &freep[i];
        addr[0] = '\0';
        perms[0] = '\0';
        sprintf(addr, "%#*jx-%#*jx", ptrwidth, (uintmax_t)kve->kve_start,
                ptrwidth, (uintmax_t)kve->kve_end);
        psutil_remove_spaces(addr);
        strlcat(perms, kve->kve_protection & KVME_PROT_READ ? "r" : "-",
                sizeof(perms));
        strlcat(perms, kve->kve_protection & KVME_PROT_WRITE ? "w" : "-",
                sizeof(perms));
        strlcat(perms, kve->kve_protection & KVME_PROT_EXEC ? "x" : "-",
                sizeof(perms));

        if (strlen(kve->kve_path) == 0) {
            switch (kve->kve_type) {
                case KVME_TYPE_NONE:
                    path = "[none]";
                    break;
                case KVME_TYPE_DEFAULT:
                    path = "[default]";
                    break;
                case KVME_TYPE_VNODE:
                    path = "[vnode]";
                    break;
                case KVME_TYPE_SWAP:
                    path = "[swap]";
                    break;
                case KVME_TYPE_DEVICE:
                    path = "[device]";
                    break;
                case KVME_TYPE_PHYS:
                    path = "[phys]";
                    break;
                case KVME_TYPE_DEAD:
                    path = "[dead]";
                    break;
#ifdef KVME_TYPE_SG
                case KVME_TYPE_SG:
                    path = "[sg]";
                    break;
#endif
                case KVME_TYPE_UNKNOWN:
                    path = "[unknown]";
                    break;
                default:
                    path = "[?]";
                    break;
            }
        }
        else {
            path = kve->kve_path;
        }

        py_path = PyUnicode_DecodeFSDefault(path);
        if (! py_path)
            goto error;
        py_tuple = Py_BuildValue("ssOiiii",
            addr,                       // "start-end" address
            perms,                      // "rwx" permissions
            py_path,                    // path
            kve->kve_resident,          // rss
            kve->kve_private_resident,  // private
            kve->kve_ref_count,         // ref count
            kve->kve_shadow_count);     // shadow count
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_path);
        Py_DECREF(py_tuple);
    }
    free(freep);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_path);
    Py_DECREF(py_retlist);
    if (freep != NULL)
        free(freep);
    return NULL;
}


PyObject*
psutil_proc_cpu_affinity_get(PyObject* self, PyObject* args) {
    // Get process CPU affinity.
    // Reference:
    // http://sources.freebsd.org/RELENG_9/src/usr.bin/cpuset/cpuset.c
    pid_t pid;
    int ret;
    int i;
    cpuset_t mask;
    PyObject* py_retlist;
    PyObject* py_cpu_num;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    ret = cpuset_getaffinity(CPU_LEVEL_WHICH, CPU_WHICH_PID, pid,
                             sizeof(mask), &mask);
    if (ret != 0)
        return PyErr_SetFromErrno(PyExc_OSError);

    py_retlist = PyList_New(0);
    if (py_retlist == NULL)
        return NULL;

    for (i = 0; i < CPU_SETSIZE; i++) {
        if (CPU_ISSET(i, &mask)) {
            py_cpu_num = Py_BuildValue("i", i);
            if (py_cpu_num == NULL)
                goto error;
            if (PyList_Append(py_retlist, py_cpu_num))
                goto error;
        }
    }

    return py_retlist;

error:
    Py_XDECREF(py_cpu_num);
    Py_DECREF(py_retlist);
    return NULL;
}


PyObject *
psutil_proc_cpu_affinity_set(PyObject *self, PyObject *args) {
    // Set process CPU affinity.
    // Reference:
    // http://sources.freebsd.org/RELENG_9/src/usr.bin/cpuset/cpuset.c
    pid_t pid;
    int i;
    int seq_len;
    int ret;
    cpuset_t cpu_set;
    PyObject *py_cpu_set;
    PyObject *py_cpu_seq = NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID "O", &pid, &py_cpu_set))
        return NULL;

    py_cpu_seq = PySequence_Fast(py_cpu_set, "expected a sequence or integer");
    if (!py_cpu_seq)
        return NULL;
    seq_len = PySequence_Fast_GET_SIZE(py_cpu_seq);

    // calculate the mask
    CPU_ZERO(&cpu_set);
    for (i = 0; i < seq_len; i++) {
        PyObject *item = PySequence_Fast_GET_ITEM(py_cpu_seq, i);
#if PY_MAJOR_VERSION >= 3
        long value = PyLong_AsLong(item);
#else
        long value = PyInt_AsLong(item);
#endif
        if (value == -1 || PyErr_Occurred())
            goto error;
        CPU_SET(value, &cpu_set);
    }

    // set affinity
    ret = cpuset_setaffinity(CPU_LEVEL_WHICH, CPU_WHICH_PID, pid,
                             sizeof(cpu_set), &cpu_set);
    if (ret != 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    Py_DECREF(py_cpu_seq);
    Py_RETURN_NONE;

error:
    if (py_cpu_seq != NULL)
        Py_DECREF(py_cpu_seq);
    return NULL;
}


/*
 * An emulation of Linux prlimit(). Returns a (soft, hard) tuple.
 */
PyObject *
psutil_proc_getrlimit(PyObject *self, PyObject *args) {
    pid_t pid;
    int ret;
    int resource;
    size_t len;
    int name[5];
    struct rlimit rlp;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "i", &pid, &resource))
        return NULL;

    name[0] = CTL_KERN;
    name[1] = KERN_PROC;
    name[2] = KERN_PROC_RLIMIT;
    name[3] = pid;
    name[4] = resource;
    len = sizeof(rlp);

    ret = sysctl(name, 5, &rlp, &len, NULL, 0);
    if (ret == -1)
        return PyErr_SetFromErrno(PyExc_OSError);

#if defined(HAVE_LONG_LONG)
    return Py_BuildValue("LL",
                         (PY_LONG_LONG) rlp.rlim_cur,
                         (PY_LONG_LONG) rlp.rlim_max);
#else
    return Py_BuildValue("ll",
                         (long) rlp.rlim_cur,
                         (long) rlp.rlim_max);
#endif
}


/*
 * An emulation of Linux prlimit() (set).
 */
PyObject *
psutil_proc_setrlimit(PyObject *self, PyObject *args) {
    pid_t pid;
    int ret;
    int resource;
    int name[5];
    struct rlimit new;
    struct rlimit *newp = NULL;
    PyObject *py_soft = NULL;
    PyObject *py_hard = NULL;

    if (! PyArg_ParseTuple(
            args, _Py_PARSE_PID "iOO", &pid, &resource, &py_soft, &py_hard))
        return NULL;

    name[0] = CTL_KERN;
    name[1] = KERN_PROC;
    name[2] = KERN_PROC_RLIMIT;
    name[3] = pid;
    name[4] = resource;

#if defined(HAVE_LONG_LONG)
    new.rlim_cur = PyLong_AsLongLong(py_soft);
    if (new.rlim_cur == (rlim_t) - 1 && PyErr_Occurred())
        return NULL;
    new.rlim_max = PyLong_AsLongLong(py_hard);
    if (new.rlim_max == (rlim_t) - 1 && PyErr_Occurred())
        return NULL;
#else
    new.rlim_cur = PyLong_AsLong(py_soft);
    if (new.rlim_cur == (rlim_t) - 1 && PyErr_Occurred())
        return NULL;
    new.rlim_max = PyLong_AsLong(py_hard);
    if (new.rlim_max == (rlim_t) - 1 && PyErr_Occurred())
        return NULL;
#endif
    newp = &new;
    ret = sysctl(name, 5, NULL, 0, newp, sizeof(*newp));
    if (ret == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    Py_RETURN_NONE;
}
