/*
 * $Id$
 *
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * FreeBSD platform-specific module methods for _psutil_bsd
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdlib.h>
#include <stdio.h>
#include <signal.h>
#include <fcntl.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/param.h>
#include <sys/user.h>
#include <sys/proc.h>
#include <sys/socket.h>
#include <utmp.h>         /* system users */
#include <devstat.h>      /* get io counters */
#include <sys/vmmeter.h>  /* needed for vmtotal struct */
#include <libutil.h>      /* process open files, shared libs (kinfo_getvmmap) */
#include <sys/mount.h>

#include <net/if.h>       /* net io counters */
#include <net/if_dl.h>
#include <net/route.h>

#include <netinet/in.h>   /* process open files/connections */
#include <sys/un.h>

#include "_psutil_bsd.h"
#include "_psutil_common.h"
#include "arch/bsd/process_info.h"


// convert a timeval struct to a double
#define TV2DOUBLE(t)    ((t).tv_sec + (t).tv_usec / 1000000.0)


/*
 * Utility function which fills a kinfo_proc struct based on process pid
 */
static int
get_kinfo_proc(const pid_t pid, struct kinfo_proc *proc)
{
    int mib[4];
    size_t size;
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID;
    mib[3] = pid;

    size = sizeof(struct kinfo_proc);

    if (sysctl((int*)mib, 4, proc, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return -1;
    }

    /*
     * sysctl stores 0 in the size if we can't find the process information.
     */
    if (size == 0) {
        NoSuchProcess();
        return -1;
    }
    return 0;
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject*
get_pid_list(PyObject* self, PyObject* args)
{
    kinfo_proc *proclist = NULL;
    kinfo_proc *orig_address = NULL;
    size_t num_processes;
    size_t idx;
    PyObject* retlist = PyList_New(0);
    PyObject* pid;

    if (get_proc_list(&proclist, &num_processes) != 0) {
        Py_DECREF(retlist);
        PyErr_SetString(PyExc_RuntimeError, "failed to retrieve process list.");
        return NULL;
    }

    if (num_processes > 0) {
        orig_address = proclist; // save so we can free it after we're done
        for (idx=0; idx < num_processes; idx++) {
            pid = Py_BuildValue("i", proclist->ki_pid);
            PyList_Append(retlist, pid);
            Py_XDECREF(pid);
            proclist++;
        }
        free(orig_address);
    }

    return retlist;
}


/*
 * Return a Python float indicating the system boot time expressed in
 * seconds since the epoch.
 */
static PyObject*
get_system_boot_time(PyObject* self, PyObject* args)
{
    /* fetch sysctl "kern.boottime" */
    static int request[2] = { CTL_KERN, KERN_BOOTTIME };
    struct timeval result;
    size_t result_len = sizeof result;
    time_t boot_time = 0;

    if (sysctl(request, 2, &result, &result_len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }
    boot_time = result.tv_sec;
    return Py_BuildValue("f", (float)boot_time);
}


/*
 * Return process name from kinfo_proc as a Python string.
 */
static PyObject*
get_process_name(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("s", kp.ki_comm);
}


/*
 * Return process pathname executable.
 * Thanks to Robert N. M. Watson:
 * http://fxr.googlebit.com/source/usr.bin/procstat/procstat_bin.c?v=8-CURRENT
 */
static PyObject*
get_process_exe(PyObject* self, PyObject* args)
{
    long pid;
    char pathname[PATH_MAX];
    int error;
    int mib[4];
    size_t size;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PATHNAME;
    mib[3] = pid;

    size = sizeof(pathname);
    error = sysctl(mib, 4, pathname, &size, NULL, 0);
    if (error == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (size == 0 || strlen(pathname) == 0) {
        if (pid_exists(pid) == 0) {
            return NoSuchProcess();
        }
        else {
            strcpy(pathname, "");
        }
    }
    return Py_BuildValue("s", pathname);
}


/*
 * Return process cmdline as a Python list of cmdline arguments.
 */
static PyObject*
get_process_cmdline(PyObject* self, PyObject* args)
{
    long pid;
    PyObject* arglist = NULL;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    // get the commandline, defined in arch/bsd/process_info.c
    arglist = get_arg_list(pid);

    // get_arg_list() returns NULL only if getcmdargs failed with ESRCH
    // (no process with that PID)
    if (NULL == arglist) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    return Py_BuildValue("N", arglist);
}


/*
 * Return process parent pid from kinfo_proc as a Python integer.
 */
static PyObject*
get_process_ppid(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("l", (long)kp.ki_ppid);
}


/*
 * Return process status as a Python integer.
 */
static PyObject*
get_process_status(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("i", (int)kp.ki_stat);
}


/*
 * Return process real, effective and saved user ids from kinfo_proc
 * as a Python tuple.
 */
static PyObject*
get_process_uids(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("lll", (long)kp.ki_ruid,
                                (long)kp.ki_uid,
                                (long)kp.ki_svuid);
}


/*
 * Return process real, effective and saved group ids from kinfo_proc
 * as a Python tuple.
 */
static PyObject*
get_process_gids(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("lll", (long)kp.ki_rgid,
                                (long)kp.ki_groups[0],
                                (long)kp.ki_svuid);
}


/*
 * Return process real, effective and saved group ids from kinfo_proc
 * as a Python tuple.
 */
static PyObject*
get_process_tty_nr(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("i", kp.ki_tdev);
}


/*
 * Return number of threads used by process as a Python integer.
 */
static PyObject*
get_process_num_threads(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("l", (long)kp.ki_numthreads);
}


/*
 * Retrieves all threads used by process returning a list of tuples
 * including thread id, user time and system time.
 * Thanks to Robert N. M. Watson:
 * http://fxr.googlebit.com/source/usr.bin/procstat/procstat_threads.c?v=8-CURRENT
 */
static PyObject*
get_process_threads(PyObject* self, PyObject* args)
{
    long pid;
    int mib[4];
    struct kinfo_proc *kip;
    struct kinfo_proc *kipp;
    int error;
    unsigned int i;
    size_t size;
    PyObject* retList = PyList_New(0);
    PyObject* pyTuple = NULL;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    /*
     * We need to re-query for thread information, so don't use *kipp.
     */
    mib[0] = CTL_KERN;
    mib[1] = KERN_PROC;
    mib[2] = KERN_PROC_PID | KERN_PROC_INC_THREAD;
    mib[3] = pid;

    size = 0;
    error = sysctl(mib, 4, NULL, &size, NULL, 0);
    if (error == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (size == 0) {
        return NoSuchProcess();
    }

    kip = malloc(size);
    if (kip == NULL) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }

    error = sysctl(mib, 4, kip, &size, NULL, 0);
    if (error == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return NULL;
    }
    if (size == 0) {
        return NoSuchProcess();
    }

    for (i = 0; i < size / sizeof(*kipp); i++) {
        kipp = &kip[i];
        pyTuple = Py_BuildValue("Idd", kipp->ki_tid,
                                       TV2DOUBLE(kipp->ki_rusage.ru_utime),
                                       TV2DOUBLE(kipp->ki_rusage.ru_stime)
                                );
        PyList_Append(retList, pyTuple);
        Py_XDECREF(pyTuple);
    }
    free(kip);
    return retList;
}


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject*
get_cpu_times(PyObject* self, PyObject* args)
{
    long pid;
    double user_t, sys_t;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    // convert from microseconds to seconds
    user_t = TV2DOUBLE(kp.ki_rusage.ru_utime);
    sys_t = TV2DOUBLE(kp.ki_rusage.ru_stime);
    return Py_BuildValue("(dd)", user_t, sys_t);
}


/*
 * Return a Python integer indicating the number of CPUs on the system
 */
static PyObject*
get_num_cpus(PyObject* self, PyObject* args)
{
    int mib[2];
    int ncpu;
    size_t len;

    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);

    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("i", ncpu);
}


/*
 * Return a Python float indicating the process create time expressed in
 * seconds since the epoch.
 */
static PyObject*
get_process_create_time(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("d", TV2DOUBLE(kp.ki_start));
}


/*
 * Return a Python float indicating the process create time expressed in
 * seconds since the epoch.
 */
static PyObject*
get_process_io_counters(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    // there's apparently no way to determine bytes count, hence return -1.
    return Py_BuildValue("(llll)", kp.ki_rusage.ru_inblock,
                                   kp.ki_rusage.ru_oublock,
                                   -1, -1);
}



/*
 * Return the RSS and VMS as a Python tuple.
 */
static PyObject*
get_memory_info(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("(ll)", ptoa(kp.ki_rssize), (long)kp.ki_size);
}


/*
 * Return a Python integer indicating the total amount of physical memory
 * in bytes.
 */
static PyObject*
get_total_phymem(PyObject* self, PyObject* args)
{
    long total_phymem;
    int mib[2];
    size_t len;

    mib[0] = CTL_HW;
    mib[1] = HW_PHYSMEM;
    len = sizeof(total_phymem);

    if (sysctl(mib, 2, &total_phymem, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("l", total_phymem);
}


/*
 * Return a Python long indicating the amount of available physical memory in
 * bytes.
 */
static PyObject*
get_avail_phymem(PyObject* self, PyObject* args)
{
    unsigned long v_inactive_count = 0;
    unsigned long v_cache_count = 0;
    unsigned long v_free_count = 0;
    long total_mem = 0;
    long long avail_mem = 0;
    size_t size = sizeof(unsigned long);
    size_t psize = sizeof(total_mem);
    int pagesize = getpagesize();

    if (sysctlbyname("hw.physmem", &total_mem, &psize, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    if (sysctlbyname("vm.stats.vm.v_inactive_count", &v_inactive_count,
                     &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    if (sysctlbyname("vm.stats.vm.v_cache_count",
                     &v_cache_count, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    if (sysctlbyname("vm.stats.vm.v_free_count",
                     &v_free_count, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    avail_mem = (v_inactive_count + v_cache_count + v_free_count) * pagesize;
    // used_mem = total_mem - avail_mem;

    return Py_BuildValue("L", avail_mem);
}


/*
 * Return a Python long indicating the total amount of virtual memory
 * in bytes.
 */
static PyObject*
get_total_virtmem(PyObject* self, PyObject* args)
{
    int mib[2];
    struct vmtotal vm;
    size_t size;
    long long total_vmem;

    mib[0] = CTL_VM;
    mib[1] = VM_METER;
    size = sizeof(vm);
    sysctl(mib, 2, &vm, &size, NULL, 0);

    // vmtotal struct:
    // http://fxr.watson.org/fxr/source/sys/vmmeter.h?v=FREEBSD54
    // note: value is returned in page, so we must multiply by size of a page
    total_vmem = (long long)vm.t_vm * (long long)getpagesize();
    return Py_BuildValue("L", total_vmem);
}


/*
 * Return a Python long indicating the avail amount of virtual memory
 * in bytes.
 */
static PyObject*
get_avail_virtmem(PyObject* self, PyObject* args)
{
    int mib[2];
    struct vmtotal vm;
    size_t size;
    long long total_vmem;
    long long avail_vmem;

    mib[0] = CTL_VM;
    mib[1] = VM_METER;
    size = sizeof(vm);
    sysctl(mib, 2, &vm, &size, NULL, 0);

    // vmtotal struct:
    // http://fxr.watson.org/fxr/source/sys/vmmeter.h?v=FREEBSD54
    // note: value is returned in page, so we must multiply by size of a page
    total_vmem = (long long)vm.t_vm * (long long)getpagesize();
    avail_vmem = total_vmem - ((long long)vm.t_avm * (long long)getpagesize());
    return Py_BuildValue("L", avail_vmem);
}


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
static PyObject*
get_system_cpu_times(PyObject* self, PyObject* args)
{
    long cpu_time[CPUSTATES];
    size_t size;

    size = sizeof(cpu_time);

    if (sysctlbyname("kern.cp_time", &cpu_time, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("(ddddd)",
                         (double)cpu_time[CP_USER] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_NICE] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_SYS] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_IDLE] / CLOCKS_PER_SEC,
                         (double)cpu_time[CP_INTR] / CLOCKS_PER_SEC
    );
}

/*
 * XXX
 * These functions are available on FreeBSD 8 only.
 * In the upper python layer we do various tricks to avoid crashing
 * and/or to provide alternatives where possible.
 */


#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
/*
 * Return files opened by process as a list of (path, fd) tuples
 */
static PyObject*
get_process_open_files(PyObject* self, PyObject* args)
{
    long pid;
    int i, cnt;
    PyObject *retList = PyList_New(0);
    PyObject *tuple = NULL;

    struct kinfo_file *freep, *kif;
    struct kinfo_proc kipp;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    if (get_kinfo_proc(pid, &kipp) == -1)
        return NULL;

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    for (i = 0; i < cnt; i++) {
        kif = &freep[i];
        if ((kif->kf_type == KF_TYPE_VNODE) &&
            (kif->kf_vnode_type == KF_VTYPE_VREG))
        {
            tuple = Py_BuildValue("(si)", kif->kf_path, kif->kf_fd);
            PyList_Append(retList, tuple);
            Py_DECREF(tuple);
        }
    }
    free(freep);

    return retList;
}


/*
 * Return files opened by process as a list of (path, fd) tuples
 */
static PyObject*
get_process_num_fds(PyObject* self, PyObject* args)
{
    long pid;
    int cnt;

    struct kinfo_file *freep, *kif;
    struct kinfo_proc kipp;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    if (get_kinfo_proc(pid, &kipp) == -1)
        return NULL;

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    return Py_BuildValue("i", cnt);
}


/*
 * Return process current working directory.
 */
static PyObject*
get_process_cwd(PyObject* self, PyObject* args)
{
    long pid;
    PyObject *path = NULL;
    struct kinfo_file *freep, *kif;
    struct kinfo_proc kipp;

    int i, cnt;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    if (get_kinfo_proc(pid, &kipp) == -1)
        return NULL;

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    for (i = 0; i < cnt; i++) {
        kif = &freep[i];
        if (kif->kf_fd == KF_FD_TYPE_CWD) {
            path = Py_BuildValue("s", kif->kf_path);
            break;
        }
    }
    /*
     * For lower pids it seems we can't retrieve any information
     * (lsof can't do that it either).  Since this happens even
     * as root we return an empty string instead of AccessDenied.
     */
    if (path == NULL) {
        path = Py_BuildValue("s", "");
    }
    free(freep);
    return path;
}


/*
 * Return a Python list of tuple representing per-cpu times
 */
static PyObject*
get_system_per_cpu_times(PyObject* self, PyObject* args)
{
    static int maxcpus;
    int mib[2];
    int ncpu;
    size_t len;
    size_t size;
    int i;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_cputime;

    // retrieve maxcpus value
    size = sizeof(maxcpus);
    if (sysctlbyname("kern.smp.maxcpus", &maxcpus, &size, NULL, 0) < 0) {
        PyErr_SetFromErrno(0);
        return NULL;
    }
    long cpu_time[maxcpus][CPUSTATES];

    // retrieve the number of cpus
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);
    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    // per-cpu info
    size = sizeof(cpu_time);
    if (sysctlbyname("kern.cp_times", &cpu_time, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    for (i = 0; i < ncpu; i++) {
        py_cputime = Py_BuildValue("(ddddd)",
                               (double)cpu_time[i][CP_USER] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_NICE] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_SYS] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_IDLE] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_INTR] / CLOCKS_PER_SEC
                               );
        PyList_Append(py_retlist, py_cputime);
        Py_XDECREF(py_cputime);
    }

    return py_retlist;
}


/*
 * Return a list of tuples for every process memory maps.
 * 'procstat' cmdline utility has been used as an example.
 */
static PyObject*
get_process_memory_maps(PyObject* self, PyObject* args)
{
    long pid;
    int ptrwidth;
    int i, cnt;
    char addr[30];
    char perms[10];
    const char *path;
    struct kinfo_proc kp;
    struct kinfo_vmentry *freep, *kve;
    PyObject* pytuple = NULL;
    PyObject* retlist = PyList_New(0);

    ptrwidth = 2*sizeof(void *);

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }

    freep = kinfo_getvmmap(pid, &cnt);
    if (freep == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "kinfo_getvmmap() failed");
        return NULL;
    }
    for (i = 0; i < cnt; i++) {
        kve = &freep[i];
        addr[0] = '\0';
        perms[0] = '\0';
        sprintf(addr, "%#*jx-%#*jx", ptrwidth, (uintmax_t)kve->kve_start,
                                     ptrwidth, (uintmax_t)kve->kve_end);
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
            case KVME_TYPE_SG:
                path = "[sg]";
                break;
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

        pytuple = Py_BuildValue("sssiiii",
            addr,                       // "start-end" address
            perms,                      // "rwx" permissions
            path,                       // path
            kve->kve_resident,          // rss
            kve->kve_private_resident,  // private
            kve->kve_ref_count,         // ref count
            kve->kve_shadow_count       // shadow count
        );
        PyList_Append(retlist, pytuple);
        Py_XDECREF(pytuple);
    }
    free(freep);
    return retlist;
}
#endif


/*
 * Return a list of tuples including device, mount point and fs type
 * for all partitions mounted on the system.
 */
static PyObject*
get_disk_partitions(PyObject* self, PyObject* args)
{
    int num;
    int i;
    long len;
    uint64_t flags;
    char opts[200];
    struct statfs *fs;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_tuple;

    // get the number of mount points
    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(NULL, 0, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }

    len = sizeof(*fs) * num;
    fs = malloc(len);

    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(fs, len, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        free(fs);
        PyErr_SetFromErrno(0);
        return NULL;
    }

    for (i = 0; i < num; i++) {
        opts[0] = 0;
        flags = fs[i].f_flags;

        // see sys/mount.h
        if (flags & MNT_RDONLY)
            strlcat(opts, "ro", sizeof(opts));
        else
            strlcat(opts, "rw", sizeof(opts));
        if (flags & MNT_SYNCHRONOUS)
            strlcat(opts, ",sync", sizeof(opts));
        if (flags & MNT_NOEXEC)
            strlcat(opts, ",noexec", sizeof(opts));
        if (flags & MNT_NOSUID)
            strlcat(opts, ",nosuid", sizeof(opts));
        if (flags & MNT_UNION)
            strlcat(opts, ",union", sizeof(opts));
        if (flags & MNT_ASYNC)
            strlcat(opts, ",async", sizeof(opts));
        if (flags & MNT_SUIDDIR)
            strlcat(opts, ",suiddir", sizeof(opts));
        if (flags & MNT_SOFTDEP)
            strlcat(opts, ",softdep", sizeof(opts));
        if (flags & MNT_NOSYMFOLLOW)
            strlcat(opts, ",nosymfollow", sizeof(opts));
        if (flags & MNT_GJOURNAL)
            strlcat(opts, ",gjournal", sizeof(opts));
        if (flags & MNT_MULTILABEL)
            strlcat(opts, ",multilabel", sizeof(opts));
        if (flags & MNT_ACLS)
            strlcat(opts, ",acls", sizeof(opts));
        if (flags & MNT_NOATIME)
            strlcat(opts, ",noatime", sizeof(opts));
        if (flags & MNT_NOCLUSTERR)
            strlcat(opts, ",noclusterr", sizeof(opts));
        if (flags & MNT_NOCLUSTERW)
            strlcat(opts, ",noclusterw", sizeof(opts));
        if (flags & MNT_NFS4ACLS)
            strlcat(opts, ",nfs4acls", sizeof(opts));

        py_tuple = Py_BuildValue("(ssss)", fs[i].f_mntfromname,  // device
                                           fs[i].f_mntonname,    // mount point
                                           fs[i].f_fstypename,   // fs type
                                           opts);                // options
        PyList_Append(py_retlist, py_tuple);
        Py_XDECREF(py_tuple);
    }

    free(fs);
    return py_retlist;
}


/*
 * Return a Python list of named tuples with overall network I/O information
 */
static PyObject*
get_network_io_counters(PyObject* self, PyObject* args)
{
    PyObject* py_retdict = PyDict_New();
    PyObject* py_ifc_info;

    char *buf = NULL, *lim, *next;
    struct if_msghdr *ifm;
    int mib[6];
    size_t len;

    mib[0] = CTL_NET;          // networking subsystem
    mib[1] = PF_ROUTE;         // type of information
    mib[2] = 0;                // protocol (IPPROTO_xxx)
    mib[3] = 0;                // address family
    mib[4] = NET_RT_IFLIST;   // operation
    mib[5] = 0;

    if (sysctl(mib, 6, NULL, &len, NULL, 0) < 0) {
        Py_DECREF(py_retdict);
        PyErr_SetFromErrno(0);
        return NULL;
    }


    buf = malloc(len);

    if (sysctl(mib, 6, buf, &len, NULL, 0) < 0) {
        if (buf) {
            free(buf);
        }
        Py_DECREF(py_retdict);
        PyErr_SetFromErrno(0);
        return NULL;
    }

    lim = buf + len;

    for (next = buf; next < lim; ) {
        ifm = (struct if_msghdr *)next;
        next += ifm->ifm_msglen;

        if (ifm->ifm_type == RTM_IFINFO) {
            struct if_msghdr *if2m = (struct if_msghdr *)ifm;
            struct sockaddr_dl *sdl = (struct sockaddr_dl *)(if2m + 1);
            char ifc_name[32];

            strncpy(ifc_name, sdl->sdl_data, sdl->sdl_nlen);
            ifc_name[sdl->sdl_nlen] = 0;

            py_ifc_info = Py_BuildValue("(KKKK)",
                                        if2m->ifm_data.ifi_obytes,
                                        if2m->ifm_data.ifi_ibytes,
                                        if2m->ifm_data.ifi_opackets,
                                        if2m->ifm_data.ifi_ipackets);
            PyDict_SetItemString(py_retdict, ifc_name, py_ifc_info);
            Py_XDECREF(py_ifc_info);
        }
        else {
            continue;
        }
    }

    free(buf);
    return py_retdict;
}


/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject*
get_disk_io_counters(PyObject* self, PyObject* args)
{
    PyObject* py_retdict = PyDict_New();
    PyObject* py_disk_info;

    int i;
    struct statinfo stats;

    if (devstat_checkversion(NULL) < 0) {
        Py_DECREF(py_retdict);
        return PyErr_Format(PyExc_RuntimeError,
                           "devstat_checkversion() failed");
    }

    stats.dinfo = (struct devinfo *)malloc(sizeof(struct devinfo));
    bzero(stats.dinfo, sizeof(struct devinfo));

    if (devstat_getdevs(NULL, &stats) == -1) {
        Py_DECREF(py_retdict);
        return PyErr_Format(PyExc_RuntimeError,
                           "devstat_getdevs() failed");
    }

    for (i = 0; i < stats.dinfo->numdevs; i++) {
        struct devstat current;
        char disk_name[128];
        current = stats.dinfo->devices[i];
        snprintf(disk_name, sizeof(disk_name), "%s%d",
                                current.device_name,
                                current.unit_number);


        py_disk_info = Py_BuildValue("(KKKKLL)",
            current.operations[DEVSTAT_READ],   // no reads
            current.operations[DEVSTAT_WRITE],  // no writes
            current.bytes[DEVSTAT_READ],        // bytes read
            current.bytes[DEVSTAT_WRITE],       // bytes written
            (long long)devstat_compute_etime(
                &current.duration[DEVSTAT_READ], NULL),  // r time
            (long long)devstat_compute_etime(
                &current.duration[DEVSTAT_WRITE], NULL)  // w time
       );
        PyDict_SetItemString(py_retdict, disk_name, py_disk_info);
        Py_XDECREF(py_disk_info);
    }

    if (stats.dinfo->mem_ptr) {
        free(stats.dinfo->mem_ptr);
    }
    free(stats.dinfo);

    return py_retdict;
}


/*
 * Return currently connected users as a list of tuples.
 */
static PyObject*
get_system_users(PyObject* self, PyObject* args)
{
    PyObject *ret_list = PyList_New(0);
    PyObject *tuple = NULL;
    struct utmp ut;
    FILE *fp;


    fp = fopen(_PATH_UTMP, "r");
    if (fp == NULL) {
        return PyErr_SetFromErrno(0);
    }

    while (fread(&ut, sizeof(ut), 1, fp) == 1) {
        if (*ut.ut_name == '\0')
            continue;
        tuple = Py_BuildValue("(sssf)",
            ut.ut_name,              // username
            ut.ut_line,              // tty
            ut.ut_host,              // hostname
            (float)ut.ut_time        // tstamp
        );
        PyList_Append(ret_list, tuple);
        Py_DECREF(tuple);
    }

    fclose(fp);
    return ret_list;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef
PsutilMethods[] =
{
     // --- per-process functions

     {"get_process_name", get_process_name, METH_VARARGS,
        "Return process name"},
     {"get_process_exe", get_process_exe, METH_VARARGS,
        "Return process pathname executable"},
     {"get_process_cmdline", get_process_cmdline, METH_VARARGS,
        "Return process cmdline as a list of cmdline arguments"},
     {"get_process_ppid", get_process_ppid, METH_VARARGS,
        "Return process ppid as an integer"},
     {"get_process_uids", get_process_uids, METH_VARARGS,
        "Return process real effective and saved user ids as a Python tuple"},
     {"get_process_gids", get_process_gids, METH_VARARGS,
        "Return process real effective and saved group ids as a Python tuple"},
     {"get_cpu_times", get_cpu_times, METH_VARARGS,
           "Return tuple of user/kern time for the given PID"},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return a float indicating the process create time expressed in "
         "seconds since the epoch"},
     {"get_memory_info", get_memory_info, METH_VARARGS,
         "Return a tuple of RSS/VMS memory information"},
     {"get_process_num_threads", get_process_num_threads, METH_VARARGS,
         "Return number of threads used by process"},
     {"get_process_threads", get_process_threads, METH_VARARGS,
         "Return process threads"},
     {"get_process_status", get_process_status, METH_VARARGS,
         "Return process status as an integer"},
     {"get_process_io_counters", get_process_io_counters, METH_VARARGS,
         "Return process IO counters"},
     {"get_process_tty_nr", get_process_tty_nr, METH_VARARGS,
         "Return process tty (terminal) number"},
#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
     {"get_process_open_files", get_process_open_files, METH_VARARGS,
         "Return files opened by process as a list of (path, fd) tuples"},
     {"get_process_cwd", get_process_cwd, METH_VARARGS,
         "Return process current working directory."},
     {"get_process_memory_maps", get_process_memory_maps, METH_VARARGS,
         "Return a list of tuples for every process's memory map"},
     {"get_process_num_fds", get_process_num_fds, METH_VARARGS,
         "Return the number of file descriptors opened by this process"},
#endif

     // --- system-related functions

     {"get_pid_list", get_pid_list, METH_VARARGS,
         "Returns a list of PIDs currently running on the system"},
     {"get_num_cpus", get_num_cpus, METH_VARARGS,
           "Return number of CPUs on the system"},
     {"get_total_phymem", get_total_phymem, METH_VARARGS,
         "Return the total amount of physical memory, in bytes"},
     {"get_avail_phymem", get_avail_phymem, METH_VARARGS,
         "Return the amount of available physical memory, in bytes"},
     {"get_total_virtmem", get_total_virtmem, METH_VARARGS,
         "Return the total amount of virtual memory, in bytes"},
     {"get_avail_virtmem", get_avail_virtmem, METH_VARARGS,
         "Return the amount of available virtual memory, in bytes"},
     {"get_system_cpu_times", get_system_cpu_times, METH_VARARGS,
         "Return system cpu times as a tuple (user, system, nice, idle, irc)"},
#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
     {"get_system_per_cpu_times", get_system_per_cpu_times, METH_VARARGS,
         "Return system per-cpu times as a list of tuples"},
#endif
     {"get_system_boot_time", get_system_boot_time, METH_VARARGS,
         "Return a float indicating the system boot time expressed in "
         "seconds since the epoch"},
     {"get_disk_partitions", get_disk_partitions, METH_VARARGS,
         "Return a list of tuples including device, mount point and "
         "fs type for all partitions mounted on the system."},
     {"get_network_io_counters", get_network_io_counters, METH_VARARGS,
         "Return dict of tuples of networks I/O information."},
     {"get_disk_io_counters", get_disk_io_counters, METH_VARARGS,
         "Return a Python dict of tuples for disk I/O information"},
     {"get_system_users", get_system_users, METH_VARARGS,
        "Return currently connected users as a list of tuples"},

     {NULL, NULL, 0, NULL}
};

struct module_state {
    PyObject *error;
};

#if PY_MAJOR_VERSION >= 3
#define GETSTATE(m) ((struct module_state*)PyModule_GetState(m))
#else
#define GETSTATE(m) (&_state)
#endif

#if PY_MAJOR_VERSION >= 3

static int
psutil_bsd_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_bsd_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}

static struct PyModuleDef
moduledef = {
        PyModuleDef_HEAD_INIT,
        "psutil_bsd",
        NULL,
        sizeof(struct module_state),
        PsutilMethods,
        NULL,
        psutil_bsd_traverse,
        psutil_bsd_clear,
        NULL
};

#define INITERROR return NULL

PyObject *
PyInit__psutil_bsd(void)

#else
#define INITERROR return

void init_psutil_bsd(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_bsd", PsutilMethods);
#endif
    PyModule_AddIntConstant(module, "SSTOP", SSTOP);
    PyModule_AddIntConstant(module, "SSLEEP", SSLEEP);
    PyModule_AddIntConstant(module, "SRUN", SRUN);
    PyModule_AddIntConstant(module, "SIDL", SIDL);
    PyModule_AddIntConstant(module, "SWAIT", SWAIT);
    PyModule_AddIntConstant(module, "SLOCK", SLOCK);
    PyModule_AddIntConstant(module, "SZOMB", SZOMB);

    if (module == NULL) {
        INITERROR;
    }
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
