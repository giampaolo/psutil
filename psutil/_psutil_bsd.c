/*
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
#include <paths.h>
#include <sys/types.h>
#include <sys/sysctl.h>
#include <sys/param.h>
#include <sys/user.h>
#include <sys/proc.h>
#include <sys/file.h>
#include <net/route.h>

#include <sys/socket.h>
#include <sys/socketvar.h>    /* for struct xsocket */
/* for xinpcb struct */
#include <netinet/in.h>
#include <netinet/in_systm.h>
#include <netinet/ip.h>
#include <netinet/in_pcb.h>
#include <netinet/tcp_var.h>   /* for struct xtcpcb */
#include <netinet/tcp_fsm.h>   /* for TCP connection states */
#include <arpa/inet.h>         /* for inet_ntop() */

#if __FreeBSD_version < 900000
    #include <utmp.h>         /* system users */
#else
    #include <utmpx.h>
#endif
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
psutil_get_kinfo_proc(const pid_t pid, struct kinfo_proc *proc)
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
    PyObject* pid = NULL;

    if (retlist == NULL) {
        return NULL;
    }
    if (psutil_get_proc_list(&proclist, &num_processes) != 0) {
        PyErr_SetString(PyExc_RuntimeError, "failed to retrieve process list.");
        goto error;
    }

    if (num_processes > 0) {
        orig_address = proclist; // save so we can free it after we're done
        for (idx=0; idx < num_processes; idx++) {
            pid = Py_BuildValue("i", proclist->ki_pid);
            if (!pid)
                goto error;
            if (PyList_Append(retlist, pid))
                goto error;
            Py_DECREF(pid);
            proclist++;
        }
        free(orig_address);
    }

    return retlist;

error:
    Py_XDECREF(pid);
    Py_DECREF(retlist);
    if (orig_address != NULL) {
        free(orig_address);
    }
    return NULL;
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
    struct timeval boottime;
    size_t len = sizeof(boottime);

    if (sysctl(request, 2, &boottime, &len, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        return NULL;
    }
    return Py_BuildValue("d", (double)boottime.tv_sec);
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
        if (psutil_pid_exists(pid) == 0) {
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
    arglist = psutil_get_arg_list(pid);

    // psutil_get_arg_list() returns NULL only if psutil_get_cmd_args failed with ESRCH
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("i", kp.ki_tdev);
}


/*
 * Return the number of context switches performed by process as a tuple.
 */
static PyObject*
get_process_num_ctx_switches(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("(ll)", kp.ki_rusage.ru_nvcsw,
                                 kp.ki_rusage.ru_nivcsw);
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    struct kinfo_proc *kip = NULL;
    struct kinfo_proc *kipp;
    int error;
    unsigned int i;
    size_t size;
    PyObject* retList = PyList_New(0);
    PyObject* pyTuple = NULL;

    if (retList == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;

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
        goto error;
    }
    if (size == 0) {
        NoSuchProcess();
        goto error;
    }

    kip = malloc(size);
    if (kip == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    error = sysctl(mib, 4, kip, &size, NULL, 0);
    if (error == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }
    if (size == 0) {
        NoSuchProcess();
        goto error;
    }

    for (i = 0; i < size / sizeof(*kipp); i++) {
        kipp = &kip[i];
        pyTuple = Py_BuildValue("Idd", kipp->ki_tid,
                                       TV2DOUBLE(kipp->ki_rusage.ru_utime),
                                       TV2DOUBLE(kipp->ki_rusage.ru_stime)
                                );
        if (pyTuple == NULL)
            goto error;
        if (PyList_Append(retList, pyTuple))
            goto error;
        Py_DECREF(pyTuple);
    }
    free(kip);
    return retList;

error:
    Py_XDECREF(pyTuple);
    Py_DECREF(retList);
    if (kip != NULL) {
        free(kip);
    }
    return NULL;
}


/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject*
get_process_cpu_times(PyObject* self, PyObject* args)
{
    long pid;
    double user_t, sys_t;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
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
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    // there's apparently no way to determine bytes count, hence return -1.
    return Py_BuildValue("(llll)", kp.ki_rusage.ru_inblock,
                                   kp.ki_rusage.ru_oublock,
                                   -1, -1);
}


/*
 * Return extended memory info for a process as a Python tuple.
 */
static PyObject*
get_process_memory_info(PyObject* self, PyObject* args)
{
    long pid;
    struct kinfo_proc kp;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
        return NULL;
    }
    return Py_BuildValue("(lllll)", ptoa(kp.ki_rssize),    // rss
                                    (long)kp.ki_size,      // vms
                                    ptoa(kp.ki_tsize),     // text
                                    ptoa(kp.ki_dsize),     // data
                                    ptoa(kp.ki_ssize));    // stack
}


/*
 * Return virtual memory usage statistics.
 */
static PyObject*
get_virtual_mem(PyObject* self, PyObject* args)
{
    unsigned int   total, active, inactive, wired, cached, free;
    size_t         size = sizeof(total);
    struct vmtotal vm;
    int            mib[] = {CTL_VM, VM_METER};
    long           pagesize = getpagesize();
#if __FreeBSD_version > 702101
    long buffers;
#else
    int buffers;
#endif
    size_t buffers_size = sizeof(buffers);

    if (sysctlbyname("vm.stats.vm.v_page_count", &total, &size, NULL, 0))
        goto error;
    if (sysctlbyname("vm.stats.vm.v_active_count", &active, &size, NULL, 0))
        goto error;
    if (sysctlbyname("vm.stats.vm.v_inactive_count", &inactive, &size, NULL, 0))
        goto error;
    if (sysctlbyname("vm.stats.vm.v_wire_count", &wired, &size, NULL, 0))
        goto error;
    if (sysctlbyname("vm.stats.vm.v_cache_count", &cached, &size, NULL, 0))
        goto error;
    if (sysctlbyname("vm.stats.vm.v_free_count", &free, &size, NULL, 0))
        goto error;
    if (sysctlbyname("vfs.bufspace", &buffers, &buffers_size, NULL, 0))
        goto error;

    size = sizeof(vm);
    if (sysctl(mib, 2, &vm, &size, NULL, 0) != 0)
        goto error;

    return Py_BuildValue("KKKKKKKK",
        (unsigned long long) total    * pagesize,
        (unsigned long long) free     * pagesize,
        (unsigned long long) active   * pagesize,
        (unsigned long long) inactive * pagesize,
        (unsigned long long) wired    * pagesize,
        (unsigned long long) cached   * pagesize,
        (unsigned long long) buffers,
        (unsigned long long) (vm.t_vmshr + vm.t_rmshr) * pagesize  // shared
    );

error:
    PyErr_SetFromErrno(0);
    return NULL;
}


#ifndef _PATH_DEVNULL
#define _PATH_DEVNULL "/dev/null"
#endif

/*
 * Return swap memory stats (see 'swapinfo' cmdline tool)
 */
static PyObject*
get_swap_mem(PyObject* self, PyObject* args)
{
    kvm_t *kd;
    struct kvm_swap kvmsw[1];
    unsigned int swapin, swapout, nodein, nodeout;
    size_t size = sizeof(unsigned int);

    kd = kvm_open(NULL, _PATH_DEVNULL, NULL, O_RDONLY, "kvm_open failed");
    if (kd == NULL) {
        PyErr_SetString(PyExc_RuntimeError, "kvm_open failed");
        return NULL;
    }

    if (kvm_getswapinfo(kd, kvmsw, 1, 0) < 0) {
        kvm_close(kd);
        PyErr_SetString(PyExc_RuntimeError, "kvm_getswapinfo failed");
        return NULL;
    }

    kvm_close(kd);

    if (sysctlbyname("vm.stats.vm.v_swapin", &swapin, &size, NULL, 0) == -1)
        goto sbn_error;
    if (sysctlbyname("vm.stats.vm.v_swapout", &swapout, &size, NULL, 0) == -1)
        goto sbn_error;
    if (sysctlbyname("vm.stats.vm.v_vnodein", &nodein, &size, NULL, 0) == -1)
        goto sbn_error;
    if (sysctlbyname("vm.stats.vm.v_vnodeout", &nodeout, &size, NULL, 0) == -1)
        goto sbn_error;

    return Py_BuildValue("(iiiII)",
                            kvmsw[0].ksw_total,                     // total
                            kvmsw[0].ksw_used,                      // used
                            kvmsw[0].ksw_total - kvmsw[0].ksw_used, // free
                            swapin + swapout,                       // swap in
                            nodein + nodeout);                      // swap out

sbn_error:
    PyErr_SetFromErrno(0);
    return NULL;
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
    struct kinfo_file *freep = NULL;
    struct kinfo_file *kif;
    struct kinfo_proc kipp;
    PyObject *retList = PyList_New(0);
    PyObject *tuple = NULL;

    if (retList == NULL)
        return NULL;
    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;
    if (psutil_get_kinfo_proc(pid, &kipp) == -1)
        goto error;

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_ad_or_nsp(pid);
        goto error;
    }

    for (i = 0; i < cnt; i++) {
        kif = &freep[i];
        if ((kif->kf_type == KF_TYPE_VNODE) &&
            (kif->kf_vnode_type == KF_VTYPE_VREG))
        {
            tuple = Py_BuildValue("(si)", kif->kf_path, kif->kf_fd);
            if (tuple == NULL)
                goto error;
            if (PyList_Append(retList, tuple))
                goto error;
            Py_DECREF(tuple);
        }
    }
    free(freep);
    return retList;

error:
    Py_XDECREF(tuple);
    Py_DECREF(retList);
    if (freep != NULL)
        free(freep);
    return NULL;
}


/*
 * Return files opened by process as a list of (path, fd) tuples
 */
static PyObject*
get_process_num_fds(PyObject* self, PyObject* args)
{
    long pid;
    int cnt;

    struct kinfo_file *freep;
    struct kinfo_proc kipp;

    if (! PyArg_ParseTuple(args, "l", &pid))
        return NULL;
    if (psutil_get_kinfo_proc(pid, &kipp) == -1)
        return NULL;

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_ad_or_nsp(pid);
        return NULL;
    }
    free(freep);

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
    struct kinfo_file *freep = NULL;
    struct kinfo_file *kif;
    struct kinfo_proc kipp;

    int i, cnt;

    if (! PyArg_ParseTuple(args, "l", &pid))
        goto error;
    if (psutil_get_kinfo_proc(pid, &kipp) == -1)
        goto error;

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_ad_or_nsp(pid);
        goto error;
    }

    for (i = 0; i < cnt; i++) {
        kif = &freep[i];
        if (kif->kf_fd == KF_FD_TYPE_CWD) {
            path = Py_BuildValue("s", kif->kf_path);
            if (!path)
                goto error;
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

error:
    Py_XDECREF(path);
    if (freep != NULL)
        free(freep);
    return NULL;
}


/*
 * mathes Linux net/tcp_states.h:
 * http://students.mimuw.edu.pl/lxr/source/include/net/tcp_states.h
 */
static char *
get_connection_status(int st) {
    switch (st) {
        case TCPS_CLOSED:
            return "CLOSE";
        case TCPS_CLOSING:
            return "CLOSING";
        case TCPS_CLOSE_WAIT:
            return "CLOSE_WAIT";
        case TCPS_LISTEN:
            return "LISTEN";
        case TCPS_ESTABLISHED:
            return "ESTABLISHED";
        case TCPS_SYN_SENT:
            return "SYN_SENT";
        case TCPS_SYN_RECEIVED:
            return "SYN_RECV";
        case TCPS_FIN_WAIT_1:
            return "FIN_WAIT_1";
        case TCPS_FIN_WAIT_2:
            return "FIN_WAIT_2";
        case TCPS_LAST_ACK:
            return "LAST_ACK";
        case TCPS_TIME_WAIT:
            return "TIME_WAIT";
        default:
            return "?";
    }
}

/* The tcplist fetching and walking is borrowed from netstat/inet.c. */
static char *
psutil_fetch_tcplist(void)
{
    char *buf;
    size_t len;
    int error;

    for (;;) {
        if (sysctlbyname("net.inet.tcp.pcblist", NULL, &len, NULL, 0) < 0) {
            PyErr_SetFromErrno(0);
            return NULL;
        }
        buf = malloc(len);
        if (buf == NULL) {
            PyErr_NoMemory();
            return NULL;
        }
        if (sysctlbyname("net.inet.tcp.pcblist", buf, &len, NULL, 0) < 0) {
            free(buf);
            PyErr_SetFromErrno(0);
            return NULL;
        }
        return buf;
    }
}

static int
psutil_sockaddr_port(int family, struct sockaddr_storage *ss)
{
    struct sockaddr_in6 *sin6;
    struct sockaddr_in *sin;

    if (family == AF_INET) {
        sin = (struct sockaddr_in *)ss;
        return (sin->sin_port);
    } else {
        sin6 = (struct sockaddr_in6 *)ss;
        return (sin6->sin6_port);
    }
}

static void *
psutil_sockaddr_addr(int family, struct sockaddr_storage *ss)
{
    struct sockaddr_in6 *sin6;
    struct sockaddr_in *sin;

    if (family == AF_INET) {
        sin = (struct sockaddr_in *)ss;
        return (&sin->sin_addr);
    } else {
        sin6 = (struct sockaddr_in6 *)ss;
        return (&sin6->sin6_addr);
    }
}

static socklen_t
psutil_sockaddr_addrlen(int family)
{
    if (family == AF_INET)
        return (sizeof(struct in_addr));
    else
        return (sizeof(struct in6_addr));
}

static int
psutil_sockaddr_matches(int family, int port, void *pcb_addr,
                        struct sockaddr_storage *ss)
{
    if (psutil_sockaddr_port(family, ss) != port)
        return (0);
    return (memcmp(psutil_sockaddr_addr(family, ss), pcb_addr,
        psutil_sockaddr_addrlen(family)) == 0);
}

static struct tcpcb *
psutil_search_tcplist(char *buf, struct kinfo_file *kif)
{
    struct tcpcb *tp;
    struct inpcb *inp;
    struct xinpgen *xig, *oxig;
    struct xsocket *so;

    oxig = xig = (struct xinpgen *)buf;
    for (xig = (struct xinpgen *)((char *)xig + xig->xig_len);
         xig->xig_len > sizeof(struct xinpgen);
         xig = (struct xinpgen *)((char *)xig + xig->xig_len)) {
        tp = &((struct xtcpcb *)xig)->xt_tp;
        inp = &((struct xtcpcb *)xig)->xt_inp;
        so = &((struct xtcpcb *)xig)->xt_socket;

        if (so->so_type != kif->kf_sock_type ||
            so->xso_family != kif->kf_sock_domain ||
            so->xso_protocol != kif->kf_sock_protocol)
                continue;

        if (kif->kf_sock_domain == AF_INET) {
            if (!psutil_sockaddr_matches(AF_INET, inp->inp_lport, &inp->inp_laddr,
                &kif->kf_sa_local))
                continue;
            if (!psutil_sockaddr_matches(AF_INET, inp->inp_fport, &inp->inp_faddr,
                &kif->kf_sa_peer))
                continue;
        } else {
            if (!psutil_sockaddr_matches(AF_INET6, inp->inp_lport, &inp->in6p_laddr,
                &kif->kf_sa_local))
                continue;
            if (!psutil_sockaddr_matches(AF_INET6, inp->inp_fport, &inp->in6p_faddr,
                &kif->kf_sa_peer))
                continue;
        }

        return (tp);
    }
    return NULL;
}

/*
 * Return connections opened by process.
 */
static PyObject*
get_process_connections(PyObject* self, PyObject* args)
{
    long pid;
    int i, cnt;

    struct kinfo_file *freep = NULL;
    struct kinfo_file *kif;
    struct kinfo_proc kipp;
    char *tcplist = NULL;
    struct tcpcb *tcp;

    PyObject *retList = PyList_New(0);
    PyObject *tuple = NULL;
    PyObject *laddr = NULL;
    PyObject *raddr = NULL;
    PyObject *af_filter = NULL;
    PyObject *type_filter = NULL;
    PyObject* _family = NULL;
    PyObject* _type = NULL;

    if (retList == NULL) {
        return NULL;
    }
    if (! PyArg_ParseTuple(args, "lOO", &pid, &af_filter, &type_filter)) {
        goto error;
    }
    if (!PySequence_Check(af_filter) || !PySequence_Check(type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    if (psutil_get_kinfo_proc(pid, &kipp) == -1) {
        goto error;
    }

    freep = kinfo_getfile(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_ad_or_nsp(pid);
        goto error;
    }

    tcplist = psutil_fetch_tcplist();
    if (tcplist == NULL) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    for (i = 0; i < cnt; i++) {
        int lport, rport;
        char lip[200], rip[200];
        char path[PATH_MAX];
        char *state;
        int inseq;
        tuple = NULL;
        laddr = NULL;
        raddr = NULL;

        kif = &freep[i];
        if (kif->kf_type == KF_TYPE_SOCKET)
        {
            // apply filters
            _family = PyLong_FromLong((long)kif->kf_sock_domain);
            inseq = PySequence_Contains(af_filter, _family);
            Py_DECREF(_family);
            if (inseq == 0) {
                continue;
            }
            _type = PyLong_FromLong((long)kif->kf_sock_type);
            inseq = PySequence_Contains(type_filter, _type);
            Py_DECREF(_type);
            if (inseq == 0) {
                continue;
            }

            // IPv4 / IPv6 socket
            if ((kif->kf_sock_domain == AF_INET) ||
                (kif->kf_sock_domain == AF_INET6)) {
                // fill status
                state = "";
                if (kif->kf_sock_type == SOCK_STREAM) {
                    tcp = psutil_search_tcplist(tcplist, kif);
                    if (tcp != NULL)
                        state = get_connection_status((int)tcp->t_state);
                }

                // build addr and port
                inet_ntop(kif->kf_sock_domain,
                    psutil_sockaddr_addr(kif->kf_sock_domain, &kif->kf_sa_local),
                    lip, sizeof(lip));
                inet_ntop(kif->kf_sock_domain,
                    psutil_sockaddr_addr(kif->kf_sock_domain, &kif->kf_sa_peer),
                    rip, sizeof(rip));
                lport = htons(psutil_sockaddr_port(kif->kf_sock_domain,
                                                   &kif->kf_sa_local));
                rport = htons(psutil_sockaddr_port(kif->kf_sock_domain,
                                                   &kif->kf_sa_peer));

                // construct python tuple/list
                laddr = Py_BuildValue("(si)", lip, lport);
                if (!laddr)
                    goto error;
                if (rport != 0) {
                    raddr = Py_BuildValue("(si)", rip, rport);
                }
                else {
                    raddr = Py_BuildValue("()");
                }
                if (!raddr)
                    goto error;
                tuple = Py_BuildValue("(iiiNNs)", kif->kf_fd,
                                                  kif->kf_sock_domain,
                                                  kif->kf_sock_type,
                                                  laddr,
                                                  raddr,
                                                  state);
                if (!tuple)
                    goto error;
                if (PyList_Append(retList, tuple))
                    goto error;
                Py_DECREF(tuple);
            }
            // UNIX socket
            else if (kif->kf_sock_domain == AF_UNIX) {
                struct sockaddr_un *sun;

                sun = (struct sockaddr_un *)&kif->kf_sa_local;
                snprintf(path, sizeof(path), "%.*s",
                        (sun->sun_len - (sizeof(*sun) - sizeof(sun->sun_path))),
                         sun->sun_path);

                tuple = Py_BuildValue("(iiisOs)", kif->kf_fd,
                                                  kif->kf_sock_domain,
                                                  kif->kf_sock_type,
                                                  path,
                                                  Py_None,
                                                  "");
                if (!tuple)
                    goto error;
                if (PyList_Append(retList, tuple))
                    goto error;
                Py_DECREF(tuple);
                Py_INCREF(Py_None);
            }
        }
    }
    free(freep);
    free(tcplist);
    return retList;

error:
    Py_XDECREF(tuple);
    Py_XDECREF(laddr);
    Py_XDECREF(raddr);
    Py_DECREF(retList);
    if (freep != NULL)
        free(freep);
    if (tcplist != NULL)
        free(tcplist);
    return NULL;
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
    PyObject* py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    // retrieve maxcpus value
    size = sizeof(maxcpus);
    if (sysctlbyname("kern.smp.maxcpus", &maxcpus, &size, NULL, 0) < 0) {
        Py_DECREF(py_retlist);
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
        goto error;
    }

    // per-cpu info
    size = sizeof(cpu_time);
    if (sysctlbyname("kern.cp_times", &cpu_time, &size, NULL, 0) == -1) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    for (i = 0; i < ncpu; i++) {
        py_cputime = Py_BuildValue("(ddddd)",
                               (double)cpu_time[i][CP_USER] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_NICE] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_SYS] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_IDLE] / CLOCKS_PER_SEC,
                               (double)cpu_time[i][CP_INTR] / CLOCKS_PER_SEC
                               );
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_DECREF(py_cputime);
    }

    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    return NULL;
}


// remove spaces from string
void remove_spaces(char *str) {
    char *p1 = str;
    char *p2 = str;
    do
        while (*p2 == ' ')
            p2++;
    while (*p1++ = *p2++);
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
    char perms[4];
    const char *path;
    struct kinfo_proc kp;
    struct kinfo_vmentry *freep = NULL;
    struct kinfo_vmentry *kve;
    ptrwidth = 2*sizeof(void *);
    PyObject* pytuple = NULL;
    PyObject* retlist = PyList_New(0);

    if (retlist == NULL) {
        return NULL;
    }
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        goto error;
    }
    if (psutil_get_kinfo_proc(pid, &kp) == -1) {
        goto error;
    }

    freep = kinfo_getvmmap(pid, &cnt);
    if (freep == NULL) {
        psutil_raise_ad_or_nsp(pid);
        goto error;
    }
    for (i = 0; i < cnt; i++) {
        pytuple = NULL;
        kve = &freep[i];
        addr[0] = '\0';
        perms[0] = '\0';
        sprintf(addr, "%#*jx-%#*jx", ptrwidth, (uintmax_t)kve->kve_start,
                                     ptrwidth, (uintmax_t)kve->kve_end);
        remove_spaces(addr);
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
        if (!pytuple)
            goto error;
        if (PyList_Append(retlist, pytuple))
            goto error;
        Py_DECREF(pytuple);
    }
    free(freep);
    return retlist;

error:
    Py_XDECREF(pytuple);
    Py_DECREF(retlist);
    if (freep != NULL)
        free(freep);
    return NULL;
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
    struct statfs *fs = NULL;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_tuple = NULL;

    if (py_retlist == NULL)
        return NULL;

    // get the number of mount points
    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(NULL, 0, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    len = sizeof(*fs) * num;
    fs = malloc(len);
    if (fs == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(fs, len, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    for (i = 0; i < num; i++) {
        py_tuple = NULL;
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
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_DECREF(py_tuple);
    }

    free(fs);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (fs != NULL)
        free(fs);
    return NULL;
}


/*
 * Return a Python list of named tuples with overall network I/O information
 */
static PyObject*
get_network_io_counters(PyObject* self, PyObject* args)
{
    char *buf = NULL, *lim, *next;
    struct if_msghdr *ifm;
    int mib[6];
    size_t len;
    PyObject* py_retdict = PyDict_New();
    PyObject* py_ifc_info = NULL;
    if (py_retdict == NULL)
        return NULL;

    mib[0] = CTL_NET;          // networking subsystem
    mib[1] = PF_ROUTE;         // type of information
    mib[2] = 0;                // protocol (IPPROTO_xxx)
    mib[3] = 0;                // address family
    mib[4] = NET_RT_IFLIST;   // operation
    mib[5] = 0;

    if (sysctl(mib, 6, NULL, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    buf = malloc(len);
    if (buf == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    if (sysctl(mib, 6, buf, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    lim = buf + len;

    for (next = buf; next < lim; ) {
        py_ifc_info = NULL;
        ifm = (struct if_msghdr *)next;
        next += ifm->ifm_msglen;

        if (ifm->ifm_type == RTM_IFINFO) {
            struct if_msghdr *if2m = (struct if_msghdr *)ifm;
            struct sockaddr_dl *sdl = (struct sockaddr_dl *)(if2m + 1);
            char ifc_name[32];

            strncpy(ifc_name, sdl->sdl_data, sdl->sdl_nlen);
            ifc_name[sdl->sdl_nlen] = 0;
            // XXX: ignore usbus interfaces:
            // http://lists.freebsd.org/pipermail/freebsd-current/2011-October/028752.html
            // 'ifconfig -a' doesn't show them, nor do we.
            if (strncmp(ifc_name, "usbus", 5) == 0) {
                continue;
            }

            py_ifc_info = Py_BuildValue("(kkkkkkki)",
                                        if2m->ifm_data.ifi_obytes,
                                        if2m->ifm_data.ifi_ibytes,
                                        if2m->ifm_data.ifi_opackets,
                                        if2m->ifm_data.ifi_ipackets,
                                        if2m->ifm_data.ifi_ierrors,
                                        if2m->ifm_data.ifi_oerrors,
                                        if2m->ifm_data.ifi_iqdrops,
                                        0);  // dropout not supported
            if (!py_ifc_info)
                goto error;
            if (PyDict_SetItemString(py_retdict, ifc_name, py_ifc_info))
                goto error;
            Py_DECREF(py_ifc_info);
        }
        else {
            continue;
        }
    }

    free(buf);
    return py_retdict;

error:
    Py_XDECREF(py_ifc_info);
    Py_DECREF(py_retdict);
    if (buf != NULL)
        free(buf);
    return NULL;
}


/*
 * Return a Python dict of tuples for disk I/O information
 */
static PyObject*
get_disk_io_counters(PyObject* self, PyObject* args)
{
    int i;
    struct statinfo stats;

    PyObject* py_retdict = PyDict_New();
    PyObject* py_disk_info = NULL;
    if (py_retdict == NULL)
        return NULL;

    if (devstat_checkversion(NULL) < 0) {
        PyErr_Format(PyExc_RuntimeError, "devstat_checkversion() failed");
        goto error;
    }

    stats.dinfo = (struct devinfo *)malloc(sizeof(struct devinfo));
    if (stats.dinfo == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    bzero(stats.dinfo, sizeof(struct devinfo));

    if (devstat_getdevs(NULL, &stats) == -1) {
        PyErr_Format(PyExc_RuntimeError, "devstat_getdevs() failed");
        goto error;
    }

    for (i = 0; i < stats.dinfo->numdevs; i++) {
        py_disk_info = NULL;
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
        if (!py_disk_info)
            goto error;
        if (PyDict_SetItemString(py_retdict, disk_name, py_disk_info))
            goto error;
        Py_DECREF(py_disk_info);
    }

    if (stats.dinfo->mem_ptr) {
        free(stats.dinfo->mem_ptr);
    }
    free(stats.dinfo);
    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    if (stats.dinfo != NULL)
        free(stats.dinfo);
    return NULL;
}


/*
 * Return currently connected users as a list of tuples.
 */
static PyObject*
get_system_users(PyObject* self, PyObject* args)
{
    PyObject *ret_list = PyList_New(0);
    PyObject *tuple = NULL;

    if (ret_list == NULL)
        return NULL;

#if __FreeBSD_version < 900000
    struct utmp ut;
    FILE *fp;

    fp = fopen(_PATH_UTMP, "r");
    if (fp == NULL) {
        PyErr_SetFromErrno(0);
        goto error;
    }

    while (fread(&ut, sizeof(ut), 1, fp) == 1) {
        if (*ut.ut_name == '\0')
            continue;
        tuple = Py_BuildValue("(sssf)",
            ut.ut_name,              // username
            ut.ut_line,              // tty
            ut.ut_host,              // hostname
            (float)ut.ut_time        // start time
        );
        if (!tuple) {
            fclose(fp);
            goto error;
        }
        if (PyList_Append(ret_list, tuple)) {
            fclose(fp);
            goto error;
        }
        Py_DECREF(tuple);
    }

    fclose(fp);
#else
    struct utmpx *utx;

    while ((utx = getutxent()) != NULL) {
        if (utx->ut_type != USER_PROCESS)
            continue;
        tuple = Py_BuildValue("(sssf)",
            utx->ut_user,             // username
            utx->ut_line,             // tty
            utx->ut_host,             // hostname
            (float)utx->ut_tv.tv_sec  // start time
        );
        if (!tuple) {
            endutxent();
            goto error;
        }
        if (PyList_Append(ret_list, tuple)) {
            endutxent();
            goto error;
        }
        Py_DECREF(tuple);
    }

    endutxent();
#endif
    return ret_list;

error:
    Py_XDECREF(tuple);
    Py_DECREF(ret_list);
    return NULL;
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
     {"get_process_connections", get_process_connections, METH_VARARGS,
        "Return connections opened by process"},
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
     {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
           "Return tuple of user/kern time for the given PID"},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return a float indicating the process create time expressed in "
         "seconds since the epoch"},
     {"get_process_memory_info", get_process_memory_info, METH_VARARGS,
         "Return extended memory info for a process as a Python tuple."},
     {"get_process_num_threads", get_process_num_threads, METH_VARARGS,
         "Return number of threads used by process"},
     {"get_process_num_ctx_switches", get_process_num_ctx_switches, METH_VARARGS,
         "Return the number of context switches performed by process"},
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
     {"get_virtual_mem", get_virtual_mem, METH_VARARGS,
         "Return system virtual memory usage statistics"},
     {"get_swap_mem", get_swap_mem, METH_VARARGS,
         "Return swap mem stats"},
     {"get_system_cpu_times", get_system_cpu_times, METH_VARARGS,
         "Return system cpu times as a tuple (user, system, nice, idle, irc)"},
#if defined(__FreeBSD_version) && __FreeBSD_version >= 800000
     {"get_system_per_cpu_times", get_system_per_cpu_times, METH_VARARGS,
         "Return system per-cpu times as a list of tuples"},
#endif
     {"get_system_boot_time", get_system_boot_time, METH_VARARGS,
         "Return the system boot time expressed in seconds since the epoch."},
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
