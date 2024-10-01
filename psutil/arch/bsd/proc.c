/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <kvm.h>
#include <sys/proc.h>
#include <sys/sysctl.h>
#include <sys/types.h>
#include <sys/file.h>
#include <sys/vnode.h>  // VREG
#ifdef PSUTIL_FREEBSD
    #include <sys/user.h>  // kinfo_proc, kinfo_file, KF_*
    #include <libutil.h>  // kinfo_getfile()
#endif

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"
#ifdef PSUTIL_FREEBSD
    #include "../../arch/freebsd/proc.h"
#elif PSUTIL_OPENBSD
    #include "../../arch/openbsd/proc.h"
#elif PSUTIL_NETBSD
    #include "../../arch/netbsd/proc.h"
#endif


// convert a timeval struct to a double
#define PSUTIL_TV2DOUBLE(t) ((t).tv_sec + (t).tv_usec / 1000000.0)

#if defined(PSUTIL_OPENBSD) || defined (PSUTIL_NETBSD)
    #define PSUTIL_KPT2DOUBLE(t) (t ## _sec + t ## _usec / 1000000.0)
#endif


/*
 * Return a Python list of all the PIDs running on the system.
 */
PyObject *
psutil_pids(PyObject *self, PyObject *args) {
    kinfo_proc *proclist = NULL;
    kinfo_proc *orig_address = NULL;
    size_t num_processes;
    size_t idx;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_pid = NULL;

    if (py_retlist == NULL)
        return NULL;

    if (psutil_get_proc_list(&proclist, &num_processes) != 0)
        goto error;

    if (num_processes > 0) {
        orig_address = proclist; // save so we can free it after we're done
        for (idx = 0; idx < num_processes; idx++) {
#ifdef PSUTIL_FREEBSD
            py_pid = PyLong_FromPid(proclist->ki_pid);
#elif defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
            py_pid = PyLong_FromPid(proclist->p_pid);
#endif
            if (!py_pid)
                goto error;
            if (PyList_Append(py_retlist, py_pid))
                goto error;
            Py_CLEAR(py_pid);
            proclist++;
        }
        free(orig_address);
    }

    return py_retlist;

error:
    Py_XDECREF(py_pid);
    Py_DECREF(py_retlist);
    if (orig_address != NULL)
        free(orig_address);
    return NULL;
}


/*
 * Collect different info about a process in one shot and return
 * them as a big Python tuple.
 */
PyObject *
psutil_proc_oneshot_info(PyObject *self, PyObject *args) {
    pid_t pid;
    long rss;
    long vms;
    long memtext;
    long memdata;
    long memstack;
    int oncpu;
    kinfo_proc kp;
    long pagesize = psutil_getpagesize();
    char str[1000];
    PyObject *py_name;
    PyObject *py_ppid;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        return NULL;

    // Process
#ifdef PSUTIL_FREEBSD
    sprintf(str, "%s", kp.ki_comm);
#elif defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
    sprintf(str, "%s", kp.p_comm);
#endif
    py_name = PyUnicode_DecodeFSDefault(str);
    if (! py_name) {
        // Likely a decoding error. We don't want to fail the whole
        // operation. The python module may retry with proc_name().
        PyErr_Clear();
        py_name = Py_None;
    }
    // Py_INCREF(py_name);

    // Calculate memory.
#ifdef PSUTIL_FREEBSD
    rss = (long)kp.ki_rssize * pagesize;
    vms = (long)kp.ki_size;
    memtext = (long)kp.ki_tsize * pagesize;
    memdata = (long)kp.ki_dsize * pagesize;
    memstack = (long)kp.ki_ssize * pagesize;
#else
    rss = (long)kp.p_vm_rssize * pagesize;
    #ifdef PSUTIL_OPENBSD
        // VMS, this is how ps determines it on OpenBSD:
        // https://github.com/openbsd/src/blob/
        //     588f7f8c69786211f2d16865c552afb91b1c7cba/bin/ps/print.c#L505
        vms = (long)(kp.p_vm_dsize + kp.p_vm_ssize + kp.p_vm_tsize) * pagesize;
    #elif PSUTIL_NETBSD
        // VMS, this is how top determines it on NetBSD:
        // https://github.com/IIJ-NetBSD/netbsd-src/blob/master/external/
        //     bsd/top/dist/machine/m_netbsd.c
        vms = (long)kp.p_vm_msize * pagesize;
    #endif
        memtext = (long)kp.p_vm_tsize * pagesize;
        memdata = (long)kp.p_vm_dsize * pagesize;
        memstack = (long)kp.p_vm_ssize * pagesize;
#endif

#ifdef PSUTIL_FREEBSD
    // what CPU we're on; top was used as an example:
    // https://svnweb.freebsd.org/base/head/usr.bin/top/machine.c?
    //     view=markup&pathrev=273835
    // XXX - note: for "intr" PID this is -1.
    if (kp.ki_stat == SRUN && kp.ki_oncpu != NOCPU)
        oncpu = kp.ki_oncpu;
    else
        oncpu = kp.ki_lastcpu;
#else
    // On Net/OpenBSD we have kp.p_cpuid but it appears it's always
    // set to KI_NOCPU. Even if it's not, ki_lastcpu does not exist
    // so there's no way to determine where "sleeping" processes
    // were. Not supported.
    oncpu = -1;
#endif

#ifdef PSUTIL_FREEBSD
    py_ppid = PyLong_FromPid(kp.ki_ppid);
#elif defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
    py_ppid = PyLong_FromPid(kp.p_ppid);
#else
    py_ppid = Py_BuildfValue(-1);
#endif
    if (! py_ppid)
        return NULL;

    // Return a single big tuple with all process info.
    py_retlist = Py_BuildValue(
#if defined(__FreeBSD_version) && __FreeBSD_version >= 1200031
        "(OillllllLdllllddddlllllbO)",
#else
        "(OillllllidllllddddlllllbO)",
#endif
#ifdef PSUTIL_FREEBSD
        py_ppid,                         // (pid_t) ppid
        (int)kp.ki_stat,                 // (int) status
        // UIDs
        (long)kp.ki_ruid,                // (long) real uid
        (long)kp.ki_uid,                 // (long) effective uid
        (long)kp.ki_svuid,               // (long) saved uid
        // GIDs
        (long)kp.ki_rgid,                // (long) real gid
        (long)kp.ki_groups[0],           // (long) effective gid
        (long)kp.ki_svuid,               // (long) saved gid
        //
        kp.ki_tdev,                      // (int or long long) tty nr
        PSUTIL_TV2DOUBLE(kp.ki_start),   // (double) create time
        // ctx switches
        kp.ki_rusage.ru_nvcsw,           // (long) ctx switches (voluntary)
        kp.ki_rusage.ru_nivcsw,          // (long) ctx switches (unvoluntary)
        // IO count
        kp.ki_rusage.ru_inblock,         // (long) read io count
        kp.ki_rusage.ru_oublock,         // (long) write io count
        // CPU times: convert from micro seconds to seconds.
        PSUTIL_TV2DOUBLE(kp.ki_rusage.ru_utime),     // (double) user time
        PSUTIL_TV2DOUBLE(kp.ki_rusage.ru_stime),     // (double) sys time
        PSUTIL_TV2DOUBLE(kp.ki_rusage_ch.ru_utime),  // (double) children utime
        PSUTIL_TV2DOUBLE(kp.ki_rusage_ch.ru_stime),  // (double) children stime
        // memory
        rss,                              // (long) rss
        vms,                              // (long) vms
        memtext,                          // (long) mem text
        memdata,                          // (long) mem data
        memstack,                         // (long) mem stack
        // others
        oncpu,                            // (int) the CPU we are on
#elif defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
        py_ppid,                         // (pid_t) ppid
        (int)kp.p_stat,                  // (int) status
        // UIDs
        (long)kp.p_ruid,                 // (long) real uid
        (long)kp.p_uid,                  // (long) effective uid
        (long)kp.p_svuid,                // (long) saved uid
        // GIDs
        (long)kp.p_rgid,                 // (long) real gid
        (long)kp.p_groups[0],            // (long) effective gid
        (long)kp.p_svuid,                // (long) saved gid
        //
        kp.p_tdev,                       // (int) tty nr
        PSUTIL_KPT2DOUBLE(kp.p_ustart),  // (double) create time
        // ctx switches
        kp.p_uru_nvcsw,                  // (long) ctx switches (voluntary)
        kp.p_uru_nivcsw,                 // (long) ctx switches (unvoluntary)
        // IO count
        kp.p_uru_inblock,                // (long) read io count
        kp.p_uru_oublock,                // (long) write io count
        // CPU times: convert from micro seconds to seconds.
        PSUTIL_KPT2DOUBLE(kp.p_uutime),  // (double) user time
        PSUTIL_KPT2DOUBLE(kp.p_ustime),  // (double) sys time
        // OpenBSD and NetBSD provide children user + system times summed
        // together (no distinction).
        kp.p_uctime_sec + kp.p_uctime_usec / 1000000.0,  // (double) ch utime
        kp.p_uctime_sec + kp.p_uctime_usec / 1000000.0,  // (double) ch stime
        // memory
        rss,                              // (long) rss
        vms,                              // (long) vms
        memtext,                          // (long) mem text
        memdata,                          // (long) mem data
        memstack,                         // (long) mem stack
        // others
        oncpu,                            // (int) the CPU we are on
#endif
        py_name                           // (pystr) name
    );

    Py_DECREF(py_name);
    Py_DECREF(py_ppid);
    return py_retlist;
}


PyObject *
psutil_proc_name(PyObject *self, PyObject *args) {
    pid_t pid;
    kinfo_proc kp;
    char str[1000];

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_kinfo_proc(pid, &kp) == -1)
        return NULL;

#ifdef PSUTIL_FREEBSD
    sprintf(str, "%s", kp.ki_comm);
#elif defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
    sprintf(str, "%s", kp.p_comm);
#endif
    return PyUnicode_DecodeFSDefault(str);
}


PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    int i, cnt = -1;
    long pid;
    char *s, **envs, errbuf[_POSIX2_LINE_MAX];
    PyObject *py_value=NULL, *py_retdict=NULL;
    kvm_t *kd;
#ifdef PSUTIL_NETBSD
    struct kinfo_proc2 *p;
#else
    struct kinfo_proc *p;
#endif

    if (!PyArg_ParseTuple(args, "l", &pid))
        return NULL;

#if defined(PSUTIL_FREEBSD)
    kd = kvm_openfiles(NULL, "/dev/null", NULL, 0, errbuf);
#else
    kd = kvm_openfiles(NULL, NULL, NULL, KVM_NO_FILES, errbuf);
#endif
    if (!kd) {
        convert_kvm_err("kvm_openfiles", errbuf);
        return NULL;
    }

    py_retdict = PyDict_New();
    if (!py_retdict)
        goto error;

#if defined(PSUTIL_FREEBSD)
    p = kvm_getprocs(kd, KERN_PROC_PID, pid, &cnt);
#elif defined(PSUTIL_OPENBSD)
    p = kvm_getprocs(kd, KERN_PROC_PID, pid, sizeof(*p), &cnt);
#elif defined(PSUTIL_NETBSD)
    p = kvm_getproc2(kd, KERN_PROC_PID, pid, sizeof(*p), &cnt);
#endif
    if (!p) {
        NoSuchProcess("kvm_getprocs");
        goto error;
    }
    if (cnt <= 0) {
        NoSuchProcess(cnt < 0 ? kvm_geterr(kd) : "kvm_getprocs: cnt==0");
        goto error;
    }

    // On *BSD kernels there are a few kernel-only system processes without an
    // environment (See e.g. "procstat -e 0 | 1 | 2 ..." on FreeBSD.)
    // Some system process have no stats attached at all
    // (they are marked with P_SYSTEM.)
    // On FreeBSD, it's possible that the process is swapped or paged out,
    // then there no access to the environ stored in the process' user area.
    // On NetBSD, we cannot call kvm_getenvv2() for a zombie process.
    // To make unittest suite happy, return an empty environment.
#if defined(PSUTIL_FREEBSD)
#if (defined(__FreeBSD_version) && __FreeBSD_version >= 700000)
    if (!((p)->ki_flag & P_INMEM) || ((p)->ki_flag & P_SYSTEM)) {
#else
    if ((p)->ki_flag & P_SYSTEM) {
#endif
#elif defined(PSUTIL_NETBSD)
    if ((p)->p_stat == SZOMB) {
#elif defined(PSUTIL_OPENBSD)
    if ((p)->p_flag & P_SYSTEM) {
#endif
        kvm_close(kd);
        return py_retdict;
    }

#if defined(PSUTIL_NETBSD)
    envs = kvm_getenvv2(kd, p, 0);
#else
    envs = kvm_getenvv(kd, p, 0);
#endif
    if (!envs) {
        // Map to "psutil" general high-level exceptions
        switch (errno) {
            case 0:
                // Process has cleared it's environment, return empty one
                kvm_close(kd);
                return py_retdict;
            case EPERM:
                AccessDenied("kvm_getenvv -> EPERM");
                break;
            case ESRCH:
                NoSuchProcess("kvm_getenvv -> ESRCH");
                break;
#if defined(PSUTIL_FREEBSD)
            case ENOMEM:
                // Unfortunately, under FreeBSD kvm_getenvv() returns
                // failure for certain processes ( e.g. try
                // "sudo procstat -e <pid of your XOrg server>".)
                // Map the error condition to 'AccessDenied'.
                sprintf(errbuf,
                        "kvm_getenvv(pid=%ld, ki_uid=%d) -> ENOMEM",
                        pid, p->ki_uid);
                AccessDenied(errbuf);
                break;
#endif
            default:
                sprintf(errbuf, "kvm_getenvv(pid=%ld)", pid);
                psutil_PyErr_SetFromOSErrnoWithSyscall(errbuf);
                break;
        }
        goto error;
    }

    for (i = 0; envs[i] != NULL; i++) {
        s = strchr(envs[i], '=');
        if (!s)
            continue;
        *s++ = 0;
        py_value = PyUnicode_DecodeFSDefault(s);
        if (!py_value)
            goto error;
        if (PyDict_SetItemString(py_retdict, envs[i], py_value)) {
            goto error;
        }
        Py_DECREF(py_value);
    }

    kvm_close(kd);
    return py_retdict;

error:
    Py_XDECREF(py_value);
    Py_XDECREF(py_retdict);
    kvm_close(kd);
    return NULL;
}


 /*
 * Return files opened by process as a list of (path, fd) tuples.
 * TODO: this is broken as it may report empty paths. 'procstat'
 * utility has the same problem see:
 * https://github.com/giampaolo/psutil/issues/595
 */
#if (defined(__FreeBSD_version) && __FreeBSD_version >= 800000) || PSUTIL_OPENBSD || defined(PSUTIL_NETBSD)
PyObject *
psutil_proc_open_files(PyObject *self, PyObject *args) {
    pid_t pid;
    int i;
    int cnt;
    int regular;
    int fd;
    char *path;
    struct kinfo_file *freep = NULL;
    struct kinfo_file *kif;
    kinfo_proc kipp;
    PyObject *py_tuple = NULL;
    PyObject *py_path = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;
    if (psutil_kinfo_proc(pid, &kipp) == -1)
        goto error;

    errno = 0;
    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
#if !defined(PSUTIL_OPENBSD)
        psutil_raise_for_pid(pid, "kinfo_getfile()");
#endif
        goto error;
    }

    for (i = 0; i < cnt; i++) {
        kif = &freep[i];

#ifdef PSUTIL_FREEBSD
        regular = (kif->kf_type == KF_TYPE_VNODE) && \
            (kif->kf_vnode_type == KF_VTYPE_VREG);
        fd = kif->kf_fd;
        path = kif->kf_path;
#elif PSUTIL_OPENBSD
        regular = (kif->f_type == DTYPE_VNODE) && (kif->v_type == VREG);
        fd = kif->fd_fd;
        // XXX - it appears path is not exposed in the kinfo_file struct.
        path = "";
#elif PSUTIL_NETBSD
        regular = (kif->ki_ftype == DTYPE_VNODE) && (kif->ki_vtype == VREG);
        fd = kif->ki_fd;
        // XXX - it appears path is not exposed in the kinfo_file struct.
        path = "";
#endif
        if (regular == 1) {
            py_path = PyUnicode_DecodeFSDefault(path);
            if (! py_path)
                goto error;
            py_tuple = Py_BuildValue("(Oi)", py_path, fd);
            if (py_tuple == NULL)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_CLEAR(py_path);
            Py_CLEAR(py_tuple);
        }
    }
    free(freep);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (freep != NULL)
        free(freep);
    return NULL;
}
#endif
