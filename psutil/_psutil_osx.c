/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * OS X platform-specific module methods for _psutil_osx
 */

#include <Python.h>
#include <assert.h>
#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <utmpx.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <libproc.h>
#include <sys/proc_info.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <net/if_dl.h>
#include <pwd.h>

#include <mach/mach.h>
#include <mach/task.h>
#include <mach/mach_init.h>
#include <mach/host_info.h>
#include <mach/mach_host.h>
#include <mach/mach_traps.h>
#include <mach/mach_vm.h>
#include <mach/shared_region.h>

#include <mach-o/loader.h>

#include <CoreFoundation/CoreFoundation.h>
#include <IOKit/IOKitLib.h>
#include <IOKit/storage/IOBlockStorageDriver.h>
#include <IOKit/storage/IOMedia.h>
#include <IOKit/IOBSD.h>

#include "_psutil_osx.h"
#include "_psutil_common.h"
#include "arch/osx/process_info.h"


/*
 * A wrapper around host_statistics() invoked with HOST_VM_INFO.
 */
int
psutil_sys_vminfo(vm_statistics_data_t *vmstat)
{
    kern_return_t ret;
    mach_msg_type_number_t count = sizeof(*vmstat) / sizeof(integer_t);
    mach_port_t mport = mach_host_self();

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)vmstat, &count);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError,
                     "host_statistics() failed: %s", mach_error_string(ret));
        return 0;
    }
    mach_port_deallocate(mach_task_self(), mport);
    return 1;
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
    PyObject *pid = NULL;
    PyObject *retlist = PyList_New(0);

    if (retlist == NULL)
        return NULL;

    if (psutil_get_proc_list(&proclist, &num_processes) != 0) {
        PyErr_SetString(PyExc_RuntimeError, "failed to retrieve process list.");
        goto error;
    }

    if (num_processes > 0) {
        // save the address of proclist so we can free it later
        orig_address = proclist;
        for (idx=0; idx < num_processes; idx++) {
            pid = Py_BuildValue("i", proclist->kp_proc.p_pid);
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
    if (orig_address != NULL)
        free(orig_address);
    return NULL;
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
    return Py_BuildValue("s", kp.kp_proc.p_comm);
}


/*
 * Return process current working directory.
 */
static PyObject*
get_process_cwd(PyObject* self, PyObject* args)
{
    long pid;
    struct proc_vnodepathinfo pathinfo;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    if (! psutil_proc_pidinfo(pid, PROC_PIDVNODEPATHINFO, &pathinfo,
                              sizeof(pathinfo)))
    {
        return NULL;
    }
    return Py_BuildValue("s", pathinfo.pvi_cdir.vip_path);
}


/*
 * Return path of the process executable.
 */
static PyObject*
get_process_exe(PyObject* self, PyObject* args)
{
    long pid;
    char buf[PATH_MAX];
    int ret;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    ret = proc_pidpath(pid, &buf, sizeof(buf));
    if (ret == 0) {
        if (! psutil_pid_exists(pid)) {
            return NoSuchProcess();
        }
        else {
            return AccessDenied();
        }
    }
    return Py_BuildValue("s", buf);
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

    // get the commandline, defined in arch/osx/process_info.c
    arglist = psutil_get_arg_list(pid);
    return arglist;
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
    return Py_BuildValue("l", (long)kp.kp_eproc.e_ppid);
}


/*
 * Return process real uid from kinfo_proc as a Python integer.
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
    return Py_BuildValue("lll", (long)kp.kp_eproc.e_pcred.p_ruid,
                                (long)kp.kp_eproc.e_ucred.cr_uid,
                                (long)kp.kp_eproc.e_pcred.p_svuid);
}


/*
 * Return process real group id from ki_comm as a Python integer.
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
    return Py_BuildValue("lll", (long)kp.kp_eproc.e_pcred.p_rgid,
                                (long)kp.kp_eproc.e_ucred.cr_groups[0],
                                (long)kp.kp_eproc.e_pcred.p_svgid);
}


/*
 * Return process controlling terminal number as an integer.
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
    return Py_BuildValue("i", kp.kp_eproc.e_tdev);
}


/*
 * Return a list of tuples for every process memory maps.
 * 'procstat' cmdline utility has been used as an example.
 */
static PyObject*
get_process_memory_maps(PyObject* self, PyObject* args)
{
    char buf[PATH_MAX];
    char addr_str[34];
    char perms[8];
    int pagesize = getpagesize();
    long pid;
    kern_return_t err = KERN_SUCCESS;
    mach_port_t task;
    uint32_t depth = 1;
    vm_address_t address = 0;
    vm_size_t size = 0;

    PyObject* py_tuple = NULL;
    PyObject* py_list = PyList_New(0);

    if (py_list == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        goto error;
    }

    err = task_for_pid(mach_task_self(), pid, &task);

    if (err != KERN_SUCCESS) {
        if (! psutil_pid_exists(pid)) {
            NoSuchProcess();
        }
        else {
            // pid exists, so return AccessDenied error since task_for_pid()
            // failed
            AccessDenied();
        }
        goto error;
    }

    while (1) {
        py_tuple = NULL;
        struct vm_region_submap_info_64 info;
        mach_msg_type_number_t count = VM_REGION_SUBMAP_INFO_COUNT_64;

        err = vm_region_recurse_64(task, &address, &size, &depth,
                                   (vm_region_info_64_t)&info, &count);

        if (err == KERN_INVALID_ADDRESS) {
            break;
        }

        if (info.is_submap) {
            depth++;
        }
        else {
            // Free/Reset the char[]s to avoid weird paths
            memset(buf, 0, sizeof(buf));
            memset(addr_str, 0, sizeof(addr_str));
            memset(perms, 0, sizeof(perms));

            sprintf(addr_str, "%016lx-%016lx", address, address + size);
            sprintf(perms, "%c%c%c/%c%c%c",
                    (info.protection & VM_PROT_READ) ? 'r' : '-',
                    (info.protection & VM_PROT_WRITE) ? 'w' : '-',
                    (info.protection & VM_PROT_EXECUTE) ? 'x' : '-',
                    (info.max_protection & VM_PROT_READ) ? 'r' : '-',
                    (info.max_protection & VM_PROT_WRITE) ? 'w' : '-',
                    (info.max_protection & VM_PROT_EXECUTE) ? 'x' : '-');

            address += size;

            err = proc_regionfilename(pid, address, buf, sizeof(buf));

            if (info.share_mode == SM_COW && info.ref_count == 1) {
                // Treat single reference SM_COW as SM_PRIVATE
                info.share_mode = SM_PRIVATE;
            }

            if (strlen(buf) == 0) {
                switch(info.share_mode) {
                /*
                case SM_LARGE_PAGE:
                    // Treat SM_LARGE_PAGE the same as SM_PRIVATE
                    // since they are not shareable and are wired.
                */
                case SM_COW:
                    strcpy(buf, "[cow]");
                    break;
                case SM_PRIVATE:
                    strcpy(buf, "[prv]");
                    break;
                case SM_EMPTY:
                    strcpy(buf, "[nul]");
                    break;
                case SM_SHARED:
                case SM_TRUESHARED:
                    strcpy(buf, "[shm]");
                    break;
                case SM_PRIVATE_ALIASED:
                    strcpy(buf, "[ali]");
                    break;
                case SM_SHARED_ALIASED:
                    strcpy(buf, "[s/a]");
                    break;
                default:
                    strcpy(buf, "[???]");
                }
            }

            py_tuple = Py_BuildValue("sssIIIIIH",
                addr_str,                                 // "start-end" address
                perms,                                    // "rwx" permissions
                buf,                                      // path
                info.pages_resident * pagesize,           // rss
                info.pages_shared_now_private * pagesize, // private
                info.pages_swapped_out * pagesize,        // swapped
                info.pages_dirtied * pagesize,            // dirtied
                info.ref_count,                           // ref count
                info.shadow_depth                         // shadow depth
            );
            if (!py_tuple)
                goto error;
            if (PyList_Append(py_list, py_tuple))
                goto error;
            Py_DECREF(py_tuple);
        }
    }

    if (task != MACH_PORT_NULL)
        mach_port_deallocate(mach_task_self(), task);

    return py_list;

error:
    if (task != MACH_PORT_NULL)
        mach_port_deallocate(mach_task_self(), task);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_list);
    return NULL;
}


/*
 * Return a Python integer indicating the number of CPUs on the system.
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


#define TV2DOUBLE(t)    ((t).tv_sec + (t).tv_usec / 1000000.0)

/*
 * Return a Python tuple (user_time, kernel_time)
 */
static PyObject*
get_process_cpu_times(PyObject* self, PyObject* args)
{
    long pid;
    struct proc_taskinfo pti;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, &pti, sizeof(pti))) {
        return NULL;
    }
    return Py_BuildValue("(dd)",
                         (float)pti.pti_total_user / 1000000000.0,
                         (float)pti.pti_total_system / 1000000000.0);
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
    return Py_BuildValue("d", TV2DOUBLE(kp.kp_proc.p_starttime));
}


/*
 * Return extended memory info about a process.
 */
static PyObject*
get_process_memory_info(PyObject* self, PyObject* args)
{
    long pid;
    struct proc_taskinfo pti;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, &pti, sizeof(pti))) {
        return NULL;
    }

    // Note: determining other memory stats on OSX is a mess:
    // http://www.opensource.apple.com/source/top/top-67/libtop.c?txt
    // I just give up...
    //struct proc_regioninfo pri;
    //psutil_proc_pidinfo(pid, PROC_PIDREGIONINFO, &pri, sizeof(pri))

    return Py_BuildValue("(KKkk)",
        pti.pti_resident_size,      // resident memory size (rss)
        pti.pti_virtual_size,       // virtual memory size (vms)
        pti.pti_faults,             // number of page faults (pages)
        pti.pti_pageins             // number of actual pageins (pages)
    );
}


/*
 * Return number of threads used by process as a Python integer.
 */
static PyObject*
get_process_num_threads(PyObject* self, PyObject* args)
{
    long pid;
    struct proc_taskinfo pti;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, &pti, sizeof(pti))) {
        return NULL;
    }
    return Py_BuildValue("k", pti.pti_threadnum);
}


/*
 * Return the number of context switches performed by process.
 */
static PyObject*
get_process_num_ctx_switches(PyObject* self, PyObject* args)
{
    long pid;
    struct proc_taskinfo pti;
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }
    if (! psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, &pti, sizeof(pti))) {
        return NULL;
    }
    // unvoluntary value seems not to be available;
    // pti.pti_csw probably refers to the sum of the two (getrusage()
    // numbers seems to confirm this theory).
    return Py_BuildValue("ki", pti.pti_csw, 0);
}


/*
 * Return system virtual memory stats
 */
static PyObject*
get_virtual_mem(PyObject* self, PyObject* args)
{

    int      mib[2];
    uint64_t total;
    size_t   len = sizeof(total);
    vm_statistics_data_t vm;
    int pagesize = getpagesize();

    // physical mem
    mib[0] = CTL_HW;
    mib[1] = HW_MEMSIZE;
    if (sysctl(mib, 2, &total, &len, NULL, 0)) {
        if (errno != 0)
            PyErr_SetFromErrno(0);
        else
            PyErr_Format(PyExc_RuntimeError, "sysctl(HW_MEMSIZE) failed");
        return NULL;
    }

    // vm
    if (!psutil_sys_vminfo(&vm)) {
        return NULL;
    }

    return Py_BuildValue("KKKKK",
        total,
        (unsigned long long) vm.active_count * pagesize,
        (unsigned long long) vm.inactive_count * pagesize,
        (unsigned long long) vm.wire_count * pagesize,
        (unsigned long long) vm.free_count * pagesize
    );
}


/*
 * Return stats about swap memory.
 */
static PyObject*
get_swap_mem(PyObject* self, PyObject* args)
{
    int mib[2];
    size_t size;
    struct xsw_usage totals;
    vm_statistics_data_t vmstat;
    int pagesize = getpagesize();

    mib[0] = CTL_VM;
    mib[1] = VM_SWAPUSAGE;
    size = sizeof(totals);
    if (sysctl(mib, 2, &totals, &size, NULL, 0) == -1) {
        if (errno != 0)
            PyErr_SetFromErrno(0);
        else
            PyErr_Format(PyExc_RuntimeError, "sysctl(VM_SWAPUSAGE) failed");
        return NULL;
    }
    if (!psutil_sys_vminfo(&vmstat)) {
        return NULL;
    }

    return Py_BuildValue("LLLKK",
                         totals.xsu_total,
                         totals.xsu_used,
                         totals.xsu_avail,
                         (unsigned long long)vmstat.pageins * pagesize,
                         (unsigned long long)vmstat.pageouts * pagesize);
}


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
static PyObject*
get_system_cpu_times(PyObject* self, PyObject* args)
{
    mach_msg_type_number_t  count = HOST_CPU_LOAD_INFO_COUNT;
    kern_return_t error;
    host_cpu_load_info_data_t r_load;

    mach_port_t host_port = mach_host_self();
    error = host_statistics(host_port, HOST_CPU_LOAD_INFO, (host_info_t)&r_load, &count);
    if (error != KERN_SUCCESS) {
        return PyErr_Format(PyExc_RuntimeError,
                "Error in host_statistics(): %s", mach_error_string(error));
    }
    mach_port_deallocate(mach_task_self(), host_port);

    return Py_BuildValue("(dddd)",
                         (double)r_load.cpu_ticks[CPU_STATE_USER] / CLK_TCK,
                         (double)r_load.cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
                         (double)r_load.cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
                         (double)r_load.cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
                         );
}


/*
 * Return a Python list of tuple representing per-cpu times
 */
static PyObject*
get_system_per_cpu_times(PyObject* self, PyObject* args)
{
    natural_t cpu_count;
    processor_info_array_t info_array;
    mach_msg_type_number_t info_count;
    kern_return_t error;
    processor_cpu_load_info_data_t* cpu_load_info = NULL;
    int i, ret;
    PyObject* py_retlist = PyList_New(0);
    PyObject* py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    mach_port_t host_port = mach_host_self();
    error = host_processor_info(host_port, PROCESSOR_CPU_LOAD_INFO,
                                &cpu_count, &info_array, &info_count);
    if (error != KERN_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "Error in host_processor_info(): %s",
                     mach_error_string(error));
        goto error;
    }
    mach_port_deallocate(mach_task_self(), host_port);

    cpu_load_info = (processor_cpu_load_info_data_t*) info_array;

    for (i = 0; i < cpu_count; i++) {
        py_cputime = Py_BuildValue("(dddd)",
               (double)cpu_load_info[i].cpu_ticks[CPU_STATE_USER] / CLK_TCK,
               (double)cpu_load_info[i].cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
               (double)cpu_load_info[i].cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
               (double)cpu_load_info[i].cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
              );
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_DECREF(py_cputime);
    }

    ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                        info_count * sizeof(int));
    if (ret != KERN_SUCCESS) {
        PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    }
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    if (cpu_load_info != NULL) {
        ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                            info_count * sizeof(int));
        if (ret != KERN_SUCCESS) {
            PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
        }
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
    char opts[400];
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
        if (flags & MNT_EXPORTED)
            strlcat(opts, ",exported", sizeof(opts));
        if (flags & MNT_QUARANTINE)
            strlcat(opts, ",quarantine", sizeof(opts));
        if (flags & MNT_LOCAL)
            strlcat(opts, ",local", sizeof(opts));
        if (flags & MNT_QUOTA)
            strlcat(opts, ",quota", sizeof(opts));
        if (flags & MNT_ROOTFS)
            strlcat(opts, ",rootfs", sizeof(opts));
        if (flags & MNT_DOVOLFS)
            strlcat(opts, ",dovolfs", sizeof(opts));
        if (flags & MNT_DONTBROWSE)
            strlcat(opts, ",dontbrowse", sizeof(opts));
        if (flags & MNT_IGNORE_OWNERSHIP)
            strlcat(opts, ",ignore-ownership", sizeof(opts));
        if (flags & MNT_AUTOMOUNTED)
            strlcat(opts, ",automounted", sizeof(opts));
        if (flags & MNT_JOURNALED)
            strlcat(opts, ",journaled", sizeof(opts));
        if (flags & MNT_NOUSERXATTR)
            strlcat(opts, ",nouserxattr", sizeof(opts));
        if (flags & MNT_DEFWRITE)
            strlcat(opts, ",defwrite", sizeof(opts));
        if (flags & MNT_MULTILABEL)
            strlcat(opts, ",multilabel", sizeof(opts));
        if (flags & MNT_NOATIME)
            strlcat(opts, ",noatime", sizeof(opts));
        if (flags & MNT_UPDATE)
            strlcat(opts, ",update", sizeof(opts));
        if (flags & MNT_RELOAD)
            strlcat(opts, ",reload", sizeof(opts));
        if (flags & MNT_FORCE)
            strlcat(opts, ",force", sizeof(opts));
        if (flags & MNT_CMDFLAGS)
            strlcat(opts, ",cmdflags", sizeof(opts));

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
    return Py_BuildValue("i", (int)kp.kp_proc.p_stat);
}


/*
 * Return process threads
 */
static PyObject*
get_process_threads(PyObject* self, PyObject* args)
{
    long pid;
    int err, j, ret;
    kern_return_t kr;
    unsigned int info_count = TASK_BASIC_INFO_COUNT;
    mach_port_t task;
    struct task_basic_info tasks_info;
    thread_act_port_array_t thread_list = NULL;
    thread_info_data_t thinfo;
    thread_basic_info_t basic_info_th;
    mach_msg_type_number_t thread_count, thread_info_count;

    PyObject* retList = PyList_New(0);
    PyObject* pyTuple = NULL;

    if (retList == NULL)
        return NULL;

    // the argument passed should be a process id
    if (! PyArg_ParseTuple(args, "l", &pid)) {
        goto error;
    }

    // task_for_pid() requires special privileges
    err = task_for_pid(mach_task_self(), pid, &task);
    if (err != KERN_SUCCESS) {
        if (! psutil_pid_exists(pid)) {
            NoSuchProcess();
        }
        else {
            AccessDenied();
        }
        goto error;
    }

    info_count = TASK_BASIC_INFO_COUNT;
    err = task_info(task, TASK_BASIC_INFO, (task_info_t)&tasks_info, &info_count);
    if (err != KERN_SUCCESS) {
        // errcode 4 is "invalid argument" (access denied)
        if (err == 4) {
            AccessDenied();
        }
        else {
            // otherwise throw a runtime error with appropriate error code
            PyErr_Format(PyExc_RuntimeError, "task_info(TASK_BASIC_INFO) failed");
        }
        goto error;
    }

    err = task_threads(task, &thread_list, &thread_count);
    if (err != KERN_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "task_threads() failed");
        goto error;
    }

    for (j = 0; j < thread_count; j++) {
        pyTuple = NULL;
        thread_info_count = THREAD_INFO_MAX;
        kr = thread_info(thread_list[j], THREAD_BASIC_INFO,
                         (thread_info_t)thinfo, &thread_info_count);
        if (kr != KERN_SUCCESS) {
            PyErr_Format(PyExc_RuntimeError, "thread_info() failed");
            goto error;
        }
        basic_info_th = (thread_basic_info_t)thinfo;
        // XXX - thread_info structure does not provide any process id;
        // the best we can do is assigning an incremental bogus value
        pyTuple = Py_BuildValue("Iff", j + 1,
                    (float)basic_info_th->user_time.microseconds / 1000000.0,
                    (float)basic_info_th->system_time.microseconds / 1000000.0
                  );
        if (!pyTuple)
            goto error;
        if (PyList_Append(retList, pyTuple))
            goto error;
        Py_DECREF(pyTuple);
    }

    ret = vm_deallocate(task, (vm_address_t)thread_list,
                        thread_count * sizeof(int));
    if (ret != KERN_SUCCESS) {
        PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    }

    mach_port_deallocate(mach_task_self(), task);

    return retList;

error:
    if (task != MACH_PORT_NULL)
        mach_port_deallocate(mach_task_self(), task);
    Py_XDECREF(pyTuple);
    Py_DECREF(retList);
    if (thread_list != NULL) {
        ret = vm_deallocate(task, (vm_address_t)thread_list,
                            thread_count * sizeof(int));
        if (ret != KERN_SUCCESS) {
            PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
        }
    }
    return NULL;
}


/*
 * Return process open files as a Python tuple.
 * References:
 * - lsof source code: http://goo.gl/SYW79 and http://goo.gl/m78fd
 * - /usr/include/sys/proc_info.h
 */
static PyObject*
get_process_open_files(PyObject* self, PyObject* args)
{
    long pid;
    int pidinfo_result;
    int iterations;
    int i;
    int nb;

    struct proc_fdinfo *fds_pointer = NULL;
    struct proc_fdinfo *fdp_pointer;
    struct vnode_fdinfowithpath vi;

    PyObject *retList = PyList_New(0);
    PyObject *tuple = NULL;

    if (retList == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        goto error;
    }

    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (pidinfo_result <= 0) {
        // may be be ignored later if errno != 0
        PyErr_Format(PyExc_RuntimeError, "proc_pidinfo(PROC_PIDLISTFDS) failed");
        goto error;
    }

    fds_pointer = malloc(pidinfo_result);
    if (fds_pointer == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fds_pointer,
                                  pidinfo_result);
    if (pidinfo_result <= 0) {
        // may be be ignored later if errno != 0
        PyErr_Format(PyExc_RuntimeError, "proc_pidinfo(PROC_PIDLISTFDS) failed");
        goto error;
    }

    iterations = (pidinfo_result / PROC_PIDLISTFD_SIZE);

    for (i = 0; i < iterations; i++) {
        tuple = NULL;
        fdp_pointer = &fds_pointer[i];

        if (fdp_pointer->proc_fdtype == PROX_FDTYPE_VNODE)
        {
            nb = proc_pidfdinfo(pid,
                                fdp_pointer->proc_fd,
                                PROC_PIDFDVNODEPATHINFO,
                                &vi,
                                sizeof(vi));

            // --- errors checking
            if (nb <= 0) {
                if ((errno == ENOENT) || (errno == EBADF)) {
                    // no such file or directory or bad file descriptor;
                    // let's assume the file has been closed or removed
                    continue;
                }
                // may be be ignored later if errno != 0
                PyErr_Format(PyExc_RuntimeError,
                            "proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed");
                goto error;
            }
            if (nb < sizeof(vi)) {
                PyErr_Format(PyExc_RuntimeError,
                 "proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed (buffer mismatch)");
                goto error;
            }
            // --- /errors checking

            // --- construct python list
            tuple = Py_BuildValue("(si)", vi.pvip.vip_path,
                                          (int)fdp_pointer->proc_fd);
            if (!tuple)
                goto error;
            if (PyList_Append(retList, tuple))
                goto error;
            Py_DECREF(tuple);
            // --- /construct python list
        }
    }

    free(fds_pointer);
    return retList;

error:
    Py_XDECREF(tuple);
    Py_DECREF(retList);
    if (fds_pointer != NULL) {
        free(fds_pointer);
    }
    if (errno != 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    else if (! psutil_pid_exists(pid)) {
        return NoSuchProcess();
    }
    else {
        // exception has already been set earlier
        return NULL;
    }
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
            return "";
    }
}


/*
 * Return process TCP and UDP connections as a list of tuples.
 * References:
 * - lsof source code: http://goo.gl/SYW79 and http://goo.gl/wNrC0
 * - /usr/include/sys/proc_info.h
 */
static PyObject*
get_process_connections(PyObject* self, PyObject* args)
{
    long pid;
    int pidinfo_result;
    int iterations;
    int i;
    int nb;

    struct proc_fdinfo *fds_pointer = NULL;
    struct proc_fdinfo *fdp_pointer;
    struct socket_fdinfo si;

    PyObject *retList = PyList_New(0);
    PyObject *tuple = NULL;
    PyObject *laddr = NULL;
    PyObject *raddr = NULL;
    PyObject *af_filter = NULL;
    PyObject *type_filter = NULL;

    if (retList == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, "lOO", &pid, &af_filter, &type_filter)) {
        goto error;
    }

    if (!PySequence_Check(af_filter) || !PySequence_Check(type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    if (pid == 0) {
        return retList;
    }

    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (pidinfo_result <= 0) {
        goto error;
    }

    fds_pointer = malloc(pidinfo_result);
    if (fds_pointer == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fds_pointer,
                                  pidinfo_result);

    if (pidinfo_result <= 0) {
        goto error;
    }

    iterations = (pidinfo_result / PROC_PIDLISTFD_SIZE);

    for (i = 0; i < iterations; i++) {
        tuple = NULL;
        laddr = NULL;
        raddr = NULL;
        errno = 0;
        fdp_pointer = &fds_pointer[i];

        if (fdp_pointer->proc_fdtype == PROX_FDTYPE_SOCKET)
        {
            nb = proc_pidfdinfo(pid, fdp_pointer->proc_fd, PROC_PIDFDSOCKETINFO,
                                &si, sizeof(si));

            // --- errors checking
            if (nb <= 0) {
                if (errno == EBADF) {
                    // let's assume socket has been closed
                    continue;
                }
                if (errno != 0) {
                    PyErr_SetFromErrno(PyExc_OSError);
                }
                else {
                    PyErr_Format(PyExc_RuntimeError,
                                 "proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed");
                }
                goto error;
            }
            if (nb < sizeof(si)) {
                PyErr_Format(PyExc_RuntimeError,
                 "proc_pidinfo(PROC_PIDFDVNODEPATHINFO) failed (buffer mismatch)");
                goto error;
            }
            // --- /errors checking

            //
            int fd, family, type, lport, rport;
            char lip[200], rip[200];
            char *state;
            int inseq;
            PyObject* _family;
            PyObject* _type;

            fd = (int)fdp_pointer->proc_fd;
            family = si.psi.soi_family;
            type = si.psi.soi_type;

            // apply filters
            _family = PyLong_FromLong((long)family);
            inseq = PySequence_Contains(af_filter, _family);
            Py_DECREF(_family);
            if (inseq == 0) {
                continue;
            }
            _type = PyLong_FromLong((long)type);
            inseq = PySequence_Contains(type_filter, _type);
            Py_DECREF(_type);
            if (inseq == 0) {
                continue;
            }

            if (errno != 0) {
                PyErr_SetFromErrno(PyExc_OSError);
                goto error;
            }

            if ((family == AF_INET) || (family == AF_INET6)) {
                if (family == AF_INET) {
                    inet_ntop(AF_INET,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_laddr.ina_46.i46a_addr4,
                              lip,
                              sizeof(lip));
                    inet_ntop(AF_INET,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_faddr.ina_46.i46a_addr4,
                              rip,
                              sizeof(rip));
                }
                else {
                    inet_ntop(AF_INET6,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_laddr.ina_6,
                              lip, sizeof(lip));
                    inet_ntop(AF_INET6,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_faddr.ina_6,
                              rip, sizeof(rip));
                }

                // check for inet_ntop failures
                if (errno != 0) {
                    PyErr_SetFromErrno(PyExc_OSError);
                    goto error;
                }

                lport = ntohs(si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_lport);
                rport = ntohs(si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_fport);
                if (type == SOCK_STREAM) {
                    state = get_connection_status((int)si.psi.soi_proto.pri_tcp.tcpsi_state);
                }

                else {
                    state = "";
                }

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

                // construct the python list
                tuple = Py_BuildValue("(iiiNNs)", fd, family, type, laddr, raddr,
                                                  state);
                if (!tuple)
                    goto error;
                if (PyList_Append(retList, tuple))
                    goto error;
                Py_DECREF(tuple);
            }
            else if (family == AF_UNIX) {
                // construct the python list
                tuple = Py_BuildValue("(iiisss)",
                    fd, family, type,
                    si.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path,
                    si.psi.soi_proto.pri_un.unsi_caddr.ua_sun.sun_path,
                    "");
                if (!tuple)
                    goto error;
                if (PyList_Append(retList, tuple))
                    goto error;
                Py_DECREF(tuple);
            }
        }
    }

    free(fds_pointer);
    return retList;

error:
    Py_XDECREF(tuple);
    Py_XDECREF(laddr);
    Py_XDECREF(raddr);
    Py_DECREF(retList);

    if (fds_pointer != NULL) {
        free(fds_pointer);
    }
    if (errno != 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    else if (! psutil_pid_exists(pid) ) {
        return NoSuchProcess();
    }
    else {
        return PyErr_Format(PyExc_RuntimeError,
                            "proc_pidinfo(PROC_PIDLISTFDS) failed");
    }
}


/*
 * Return number of file descriptors opened by process.
 */
static PyObject*
get_process_num_fds(PyObject* self, PyObject* args)
{
    long pid;
    int pidinfo_result;
    int num;
    struct proc_fdinfo *fds_pointer;

    if (! PyArg_ParseTuple(args, "l", &pid)) {
        return NULL;
    }

    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (pidinfo_result <= 0) {
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    fds_pointer = malloc(pidinfo_result);
    if (fds_pointer == NULL) {
        return PyErr_NoMemory();
    }
    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fds_pointer,
                                  pidinfo_result);
    if (pidinfo_result <= 0) {
        free(fds_pointer);
        return PyErr_SetFromErrno(PyExc_OSError);
    }

    num = (pidinfo_result / PROC_PIDLISTFD_SIZE);
    free(fds_pointer);
    return Py_BuildValue("i", num);
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
    mib[4] = NET_RT_IFLIST2;   // operation
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
        ifm = (struct if_msghdr *)next;
        next += ifm->ifm_msglen;

        if (ifm->ifm_type == RTM_IFINFO2) {
            py_ifc_info = NULL;
            struct if_msghdr2 *if2m = (struct if_msghdr2 *)ifm;
            struct sockaddr_dl *sdl = (struct sockaddr_dl *)(if2m + 1);
            char ifc_name[32];

            strncpy(ifc_name, sdl->sdl_data, sdl->sdl_nlen);
            ifc_name[sdl->sdl_nlen] = 0;

            py_ifc_info = Py_BuildValue("(KKKKKKKi)",
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
    CFDictionaryRef parent_dict;
    CFDictionaryRef props_dict;
    CFDictionaryRef stats_dict;
    io_registry_entry_t parent;
    io_registry_entry_t disk;
    io_iterator_t disk_list;
    PyObject* py_retdict = PyDict_New();
    PyObject* py_disk_info = NULL;

    if (py_retdict == NULL)
        return NULL;

    /* Get list of disks */
    if (IOServiceGetMatchingServices(kIOMasterPortDefault,
                                     IOServiceMatching(kIOMediaClass),
                                     &disk_list) != kIOReturnSuccess) {
        PyErr_SetString(PyExc_RuntimeError, "Unable to get the list of disks.");
        goto error;
    }

    /* Iterate over disks */
    while ((disk = IOIteratorNext(disk_list)) != 0) {
        py_disk_info = NULL;
        parent_dict = NULL;
        props_dict = NULL;
        stats_dict = NULL;

        if (IORegistryEntryGetParentEntry(disk, kIOServicePlane, &parent) != kIOReturnSuccess) {
            PyErr_SetString(PyExc_RuntimeError, "Unable to get the disk's parent.");
            IOObjectRelease(disk);
            goto error;
        }

        if (IOObjectConformsTo(parent, "IOBlockStorageDriver")) {
            if(IORegistryEntryCreateCFProperties(
                                     disk,
                                     (CFMutableDictionaryRef *) &parent_dict,
                                     kCFAllocatorDefault,
                                     kNilOptions) != kIOReturnSuccess)
            {
                PyErr_SetString(PyExc_RuntimeError,
                                "Unable to get the parent's properties.");
                IOObjectRelease(disk);
                IOObjectRelease(parent);
                goto error;
            }

            if (IORegistryEntryCreateCFProperties(parent,
                                          (CFMutableDictionaryRef *) &props_dict,
                                          kCFAllocatorDefault,
                                          kNilOptions) != kIOReturnSuccess)
            {
                PyErr_SetString(PyExc_RuntimeError,
                                "Unable to get the disk properties.");
                CFRelease(props_dict);
                IOObjectRelease(disk);
                IOObjectRelease(parent);
                goto error;
            }

            const int kMaxDiskNameSize = 64;
            CFStringRef disk_name_ref = (CFStringRef)CFDictionaryGetValue(
                                                    parent_dict,
                                                    CFSTR(kIOBSDNameKey));
            char disk_name[kMaxDiskNameSize];

            CFStringGetCString(disk_name_ref,
                               disk_name,
                               kMaxDiskNameSize,
                               CFStringGetSystemEncoding());

            stats_dict = (CFDictionaryRef)CFDictionaryGetValue(
                                    props_dict,
                                    CFSTR(kIOBlockStorageDriverStatisticsKey));

            if (stats_dict == NULL) {
                PyErr_SetString(PyExc_RuntimeError, "Unable to get disk stats.");
                goto error;
            }

            CFNumberRef number;
            int64_t reads, writes, read_bytes, write_bytes, read_time, write_time = 0;

            /* Get disk reads/writes */
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                            stats_dict,
                            CFSTR(kIOBlockStorageDriverStatisticsReadsKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &reads);
            }
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                            stats_dict,
                            CFSTR(kIOBlockStorageDriverStatisticsWritesKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &writes);
            }

            /* Get disk bytes read/written */
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                        stats_dict,
                        CFSTR(kIOBlockStorageDriverStatisticsBytesReadKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &read_bytes);
            }
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                stats_dict,
                CFSTR(kIOBlockStorageDriverStatisticsBytesWrittenKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &write_bytes);
            }

            /* Get disk time spent reading/writing (nanoseconds) */
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                    stats_dict,
                    CFSTR(kIOBlockStorageDriverStatisticsTotalReadTimeKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &read_time);
            }
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                    stats_dict,
                    CFSTR(kIOBlockStorageDriverStatisticsTotalWriteTimeKey)))) {
                CFNumberGetValue(number, kCFNumberSInt64Type, &write_time);
            }

            // Read/Write time on OS X comes back in nanoseconds and in psutil
            // we've standardized on milliseconds so do the conversion.
            py_disk_info = Py_BuildValue("(KKKKKK)",
                reads, writes,
                read_bytes, write_bytes,
                read_time / 1000 / 1000, write_time / 1000 / 1000
            );
            if (!py_disk_info)
                goto error;
            if (PyDict_SetItemString(py_retdict, disk_name, py_disk_info))
                goto error;
            Py_DECREF(py_disk_info);

            CFRelease(parent_dict);
            IOObjectRelease(parent);
            CFRelease(props_dict);
            IOObjectRelease(disk);
        }
    }

    IOObjectRelease (disk_list);

    return py_retdict;

error:
    Py_XDECREF(py_disk_info);
    Py_DECREF(py_retdict);
    return NULL;
}


/*
 * Return currently connected users as a list of tuples.
 */
static PyObject*
get_system_users(PyObject* self, PyObject* args)
{
    struct utmpx *utx;
    PyObject *ret_list = PyList_New(0);
    PyObject *tuple = NULL;

    if (ret_list == NULL)
        return NULL;
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
     {"get_process_cmdline", get_process_cmdline, METH_VARARGS,
        "Return process cmdline as a list of cmdline arguments"},
     {"get_process_exe", get_process_exe, METH_VARARGS,
        "Return path of the process executable"},
     {"get_process_cwd", get_process_cwd, METH_VARARGS,
        "Return process current working directory."},
     {"get_process_ppid", get_process_ppid, METH_VARARGS,
        "Return process ppid as an integer"},
     {"get_process_uids", get_process_uids, METH_VARARGS,
        "Return process real user id as an integer"},
     {"get_process_gids", get_process_gids, METH_VARARGS,
        "Return process real group id as an integer"},
     {"get_process_cpu_times", get_process_cpu_times, METH_VARARGS,
           "Return tuple of user/kern time for the given PID"},
     {"get_process_create_time", get_process_create_time, METH_VARARGS,
         "Return a float indicating the process create time expressed in "
         "seconds since the epoch"},
     {"get_process_memory_info", get_process_memory_info, METH_VARARGS,
         "Return memory information about a process"},
     {"get_process_num_threads", get_process_num_threads, METH_VARARGS,
         "Return number of threads used by process"},
     {"get_process_status", get_process_status, METH_VARARGS,
         "Return process status as an integer"},
     {"get_process_threads", get_process_threads, METH_VARARGS,
         "Return process threads as a list of tuples"},
     {"get_process_open_files", get_process_open_files, METH_VARARGS,
         "Return files opened by process as a list of tuples"},
     {"get_process_num_fds", get_process_num_fds, METH_VARARGS,
         "Return the number of fds opened by process."},
     {"get_process_num_ctx_switches", get_process_num_ctx_switches, METH_VARARGS,
         "Return the number of context switches performed by process"},
     {"get_process_connections", get_process_connections, METH_VARARGS,
         "Get process TCP and UDP connections as a list of tuples"},
     {"get_process_tty_nr", get_process_tty_nr, METH_VARARGS,
         "Return process tty number as an integer"},
     {"get_process_memory_maps", get_process_memory_maps, METH_VARARGS,
         "Return a list of tuples for every process's memory map"},

     // --- system-related functions

     {"get_pid_list", get_pid_list, METH_VARARGS,
         "Returns a list of PIDs currently running on the system"},
     {"get_num_cpus", get_num_cpus, METH_VARARGS,
           "Return number of CPUs on the system"},
     {"get_virtual_mem", get_virtual_mem, METH_VARARGS,
         "Return system virtual memory stats"},
     {"get_swap_mem", get_swap_mem, METH_VARARGS,
         "Return stats about swap memory, in bytes"},
     {"get_system_cpu_times", get_system_cpu_times, METH_VARARGS,
         "Return system cpu times as a tuple (user, system, nice, idle, irc)"},
     {"get_system_per_cpu_times", get_system_per_cpu_times, METH_VARARGS,
         "Return system per-cpu times as a list of tuples"},
     {"get_system_boot_time", get_system_boot_time, METH_VARARGS,
         "Return the system boot time expressed in seconds since the epoch."},
     {"get_disk_partitions", get_disk_partitions, METH_VARARGS,
         "Return a list of tuples including device, mount point and "
         "fs type for all partitions mounted on the system."},
     {"get_network_io_counters", get_network_io_counters, METH_VARARGS,
         "Return dict of tuples of networks I/O information."},
     {"get_disk_io_counters", get_disk_io_counters, METH_VARARGS,
         "Return dict of tuples of disks I/O information."},
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
psutil_osx_traverse(PyObject *m, visitproc visit, void *arg) {
    Py_VISIT(GETSTATE(m)->error);
    return 0;
}

static int
psutil_osx_clear(PyObject *m) {
    Py_CLEAR(GETSTATE(m)->error);
    return 0;
}


static struct PyModuleDef
moduledef = {
    PyModuleDef_HEAD_INIT,
    "psutil_osx",
    NULL,
    sizeof(struct module_state),
    PsutilMethods,
    NULL,
    psutil_osx_traverse,
    psutil_osx_clear,
    NULL
};

#define INITERROR return NULL

PyObject *
PyInit__psutil_osx(void)

#else
#define INITERROR return

void
init_psutil_osx(void)
#endif
{
#if PY_MAJOR_VERSION >= 3
    PyObject *module = PyModule_Create(&moduledef);
#else
    PyObject *module = Py_InitModule("_psutil_osx", PsutilMethods);
#endif
    // process status constants, defined in:
    // http://fxr.watson.org/fxr/source/bsd/sys/proc.h?v=xnu-792.6.70#L149
    PyModule_AddIntConstant(module, "SIDL", SIDL);
    PyModule_AddIntConstant(module, "SRUN", SRUN);
    PyModule_AddIntConstant(module, "SSLEEP", SSLEEP);
    PyModule_AddIntConstant(module, "SSTOP", SSTOP);
    PyModule_AddIntConstant(module, "SZOMB", SZOMB);

    if (module == NULL) {
        INITERROR;
    }
#if PY_MAJOR_VERSION >= 3
    return module;
#endif
}
