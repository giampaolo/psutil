/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * macOS platform-specific module methods.
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
#include <IOKit/ps/IOPowerSources.h>
#include <IOKit/ps/IOPSKeys.h>

#include "_psutil_common.h"
#include "_psutil_posix.h"
#include "arch/osx/process_info.h"


#define PSUTIL_TV2DOUBLE(t) ((t).tv_sec + (t).tv_usec / 1000000.0)

static PyObject *ZombieProcessError;


/*
 * A wrapper around host_statistics() invoked with HOST_VM_INFO.
 */
int
psutil_sys_vminfo(vm_statistics_data_t *vmstat) {
    kern_return_t ret;
    mach_msg_type_number_t count = sizeof(*vmstat) / sizeof(integer_t);
    mach_port_t mport = mach_host_self();

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)vmstat, &count);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_VM_INFO) syscall failed: %s",
            mach_error_string(ret));
        return 0;
    }
    mach_port_deallocate(mach_task_self(), mport);
    return 1;
}


/*
 * A wrapper around task_for_pid() which sucks big time:
 * - it's not documented
 * - errno is set only sometimes
 * - sometimes errno is ENOENT (?!?)
 * - for PIDs != getpid() or PIDs which are not members of the procmod
 *   it requires root
 * As such we can only guess what the heck went wrong and fail either
 * with NoSuchProcess, ZombieProcessError or giveup with AccessDenied.
 * Here's some history:
 * https://github.com/giampaolo/psutil/issues/1181
 * https://github.com/giampaolo/psutil/issues/1209
 * https://github.com/giampaolo/psutil/issues/1291#issuecomment-396062519
 */
int
psutil_task_for_pid(pid_t pid, mach_port_t *task)
{
    // See: https://github.com/giampaolo/psutil/issues/1181
    kern_return_t err = KERN_SUCCESS;

    err = task_for_pid(mach_task_self(), pid, task);
    if (err != KERN_SUCCESS) {
        if (psutil_pid_exists(pid) == 0)
            NoSuchProcess("task_for_pid");
        else if (psutil_is_zombie(pid) == 1)
            PyErr_SetString(ZombieProcessError, "task_for_pid() failed");
        else {
            psutil_debug(
                "task_for_pid() failed (pid=%ld, err=%i, errno=%i, msg='%s'); "
                "setting AccessDenied()",
                pid, err, errno, mach_error_string(err));
            AccessDenied("task_for_pid");
        }
        return 1;
    }
    return 0;
}


/*
 * Return a Python list of all the PIDs running on the system.
 */
static PyObject *
psutil_pids(PyObject *self, PyObject *args) {
    kinfo_proc *proclist = NULL;
    kinfo_proc *orig_address = NULL;
    size_t num_processes;
    size_t idx;
    PyObject *py_pid = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (psutil_get_proc_list(&proclist, &num_processes) != 0)
        goto error;

    // save the address of proclist so we can free it later
    orig_address = proclist;
    for (idx = 0; idx < num_processes; idx++) {
        py_pid = PyLong_FromPid(proclist->kp_proc.p_pid);
        if (! py_pid)
            goto error;
        if (PyList_Append(py_retlist, py_pid))
            goto error;
        Py_CLEAR(py_pid);
        proclist++;
    }
    free(orig_address);

    return py_retlist;

error:
    Py_XDECREF(py_pid);
    Py_DECREF(py_retlist);
    if (orig_address != NULL)
        free(orig_address);
    return NULL;
}


/*
 * Return multiple process info as a Python tuple in one shot by
 * using sysctl() and filling up a kinfo_proc struct.
 * It should be possible to do this for all processes without
 * incurring into permission (EPERM) errors.
 * This will also succeed for zombie processes returning correct
 * information.
 */
static PyObject *
psutil_proc_kinfo_oneshot(PyObject *self, PyObject *args) {
    pid_t pid;
    struct kinfo_proc kp;
    PyObject *py_name;
    PyObject *py_retlist;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_get_kinfo_proc(pid, &kp) == -1)
        return NULL;

    py_name = PyUnicode_DecodeFSDefault(kp.kp_proc.p_comm);
    if (! py_name) {
        // Likely a decoding error. We don't want to fail the whole
        // operation. The python module may retry with proc_name().
        PyErr_Clear();
        py_name = Py_None;
    }

    py_retlist = Py_BuildValue(
        _Py_PARSE_PID "llllllidiO",
        kp.kp_eproc.e_ppid,                        // (pid_t) ppid
        (long)kp.kp_eproc.e_pcred.p_ruid,          // (long) real uid
        (long)kp.kp_eproc.e_ucred.cr_uid,          // (long) effective uid
        (long)kp.kp_eproc.e_pcred.p_svuid,         // (long) saved uid
        (long)kp.kp_eproc.e_pcred.p_rgid,          // (long) real gid
        (long)kp.kp_eproc.e_ucred.cr_groups[0],    // (long) effective gid
        (long)kp.kp_eproc.e_pcred.p_svgid,         // (long) saved gid
        kp.kp_eproc.e_tdev,                        // (int) tty nr
        PSUTIL_TV2DOUBLE(kp.kp_proc.p_starttime),  // (double) create time
        (int)kp.kp_proc.p_stat,                    // (int) status
        py_name                                    // (pystr) name
    );

    if (py_retlist != NULL) {
        // XXX shall we decref() also in case of Py_BuildValue() error?
        Py_DECREF(py_name);
    }
    return py_retlist;
}


/*
 * Return multiple process info as a Python tuple in one shot by
 * using proc_pidinfo(PROC_PIDTASKINFO) and filling a proc_taskinfo
 * struct.
 * Contrarily from proc_kinfo above this function will fail with
 * EACCES for PIDs owned by another user and with ESRCH for zombie
 * processes.
 */
static PyObject *
psutil_proc_pidtaskinfo_oneshot(PyObject *self, PyObject *args) {
    pid_t pid;
    struct proc_taskinfo pti;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, 0, &pti, sizeof(pti)) <= 0)
        return NULL;

    return Py_BuildValue(
        "(ddKKkkkk)",
        (float)pti.pti_total_user / 1000000000.0,     // (float) cpu user time
        (float)pti.pti_total_system / 1000000000.0,   // (float) cpu sys time
        // Note about memory: determining other mem stats on macOS is a mess:
        // http://www.opensource.apple.com/source/top/top-67/libtop.c?txt
        // I just give up.
        // struct proc_regioninfo pri;
        // psutil_proc_pidinfo(pid, PROC_PIDREGIONINFO, 0, &pri, sizeof(pri))
        pti.pti_resident_size,  // (uns long long) rss
        pti.pti_virtual_size,   // (uns long long) vms
        pti.pti_faults,         // (uns long) number of page faults (pages)
        pti.pti_pageins,        // (uns long) number of actual pageins (pages)
        pti.pti_threadnum,      // (uns long) num threads
        // Unvoluntary value seems not to be available;
        // pti.pti_csw probably refers to the sum of the two;
        // getrusage() numbers seems to confirm this theory.
        pti.pti_csw             // (uns long) voluntary ctx switches
    );
}


/*
 * Return process name from kinfo_proc as a Python string.
 */
static PyObject *
psutil_proc_name(PyObject *self, PyObject *args) {
    pid_t pid;
    struct kinfo_proc kp;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_get_kinfo_proc(pid, &kp) == -1)
        return NULL;
    return PyUnicode_DecodeFSDefault(kp.kp_proc.p_comm);
}


/*
 * Return process current working directory.
 * Raises NSP in case of zombie process.
 */
static PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    pid_t pid;
    struct proc_vnodepathinfo pathinfo;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (psutil_proc_pidinfo(
            pid, PROC_PIDVNODEPATHINFO, 0, &pathinfo, sizeof(pathinfo)) <= 0)
    {
        return NULL;
    }

    return PyUnicode_DecodeFSDefault(pathinfo.pvi_cdir.vip_path);
}


/*
 * Return path of the process executable.
 */
static PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    pid_t pid;
    char buf[PATH_MAX];
    int ret;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    errno = 0;
    ret = proc_pidpath(pid, &buf, sizeof(buf));
    if (ret == 0) {
        if (pid == 0)
            AccessDenied("automatically set for PID 0");
        else
            psutil_raise_for_pid(pid, "proc_pidpath()");
        return NULL;
    }
    return PyUnicode_DecodeFSDefault(buf);
}


/*
 * Return process cmdline as a Python list of cmdline arguments.
 */
static PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    PyObject *py_retlist = NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    // get the commandline, defined in arch/osx/process_info.c
    py_retlist = psutil_get_cmdline(pid);
    return py_retlist;
}


/*
 * Return process environment as a Python string.
 */
static PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    pid_t pid;
    PyObject *py_retdict = NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    // get the environment block, defined in arch/osx/process_info.c
    py_retdict = psutil_get_environ(pid);
    return py_retdict;
}


/*
 * Return the number of logical CPUs in the system.
 * XXX this could be shared with BSD.
 */
static PyObject *
psutil_cpu_count_logical(PyObject *self, PyObject *args) {
    /*
    int mib[2];
    int ncpu;
    size_t len;
    mib[0] = CTL_HW;
    mib[1] = HW_NCPU;
    len = sizeof(ncpu);

    if (sysctl(mib, 2, &ncpu, &len, NULL, 0) == -1)
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", ncpu);
    */
    int num;
    size_t size = sizeof(int);

    if (sysctlbyname("hw.logicalcpu", &num, &size, NULL, 2))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


/*
 * Return the number of physical CPUs in the system.
 */
static PyObject *
psutil_cpu_count_phys(PyObject *self, PyObject *args) {
    int num;
    size_t size = sizeof(int);

    if (sysctlbyname("hw.physicalcpu", &num, &size, NULL, 0))
        Py_RETURN_NONE;  // mimic os.cpu_count()
    else
        return Py_BuildValue("i", num);
}


/*
 * Indicates if the given virtual address on the given architecture is in the
 * shared VM region.
 */
static bool
psutil_in_shared_region(mach_vm_address_t addr, cpu_type_t type) {
    mach_vm_address_t base;
    mach_vm_address_t size;

    switch (type) {
        case CPU_TYPE_ARM:
            base = SHARED_REGION_BASE_ARM;
            size = SHARED_REGION_SIZE_ARM;
            break;
        case CPU_TYPE_I386:
            base = SHARED_REGION_BASE_I386;
            size = SHARED_REGION_SIZE_I386;
            break;
        case CPU_TYPE_X86_64:
            base = SHARED_REGION_BASE_X86_64;
            size = SHARED_REGION_SIZE_X86_64;
            break;
        default:
            return false;
    }

    return base <= addr && addr < (base + size);
}


/*
 * Returns the USS (unique set size) of the process. Reference:
 * https://dxr.mozilla.org/mozilla-central/source/xpcom/base/
 *     nsMemoryReporterManager.cpp
 */
static PyObject *
psutil_proc_memory_uss(PyObject *self, PyObject *args) {
    pid_t pid;
    size_t len;
    cpu_type_t cpu_type;
    size_t private_pages = 0;
    mach_vm_size_t size = 0;
    mach_msg_type_number_t info_count = VM_REGION_TOP_INFO_COUNT;
    kern_return_t kr;
    vm_size_t page_size;
    mach_vm_address_t addr = MACH_VM_MIN_ADDRESS;
    mach_port_t task = MACH_PORT_NULL;
    vm_region_top_info_data_t info;
    mach_port_t object_name;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (psutil_task_for_pid(pid, &task) != 0)
        return NULL;

    len = sizeof(cpu_type);
    if (sysctlbyname("sysctl.proc_cputype", &cpu_type, &len, NULL, 0) != 0) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('sysctl.proc_cputype')");
    }

    // Roughly based on libtop_update_vm_regions in
    // http://www.opensource.apple.com/source/top/top-100.1.2/libtop.c
    for (addr = 0; ; addr += size) {
        kr = mach_vm_region(
            task, &addr, &size, VM_REGION_TOP_INFO, (vm_region_info_t)&info,
            &info_count, &object_name);
        if (kr == KERN_INVALID_ADDRESS) {
            // Done iterating VM regions.
            break;
        }
        else if (kr != KERN_SUCCESS) {
            PyErr_Format(
                PyExc_RuntimeError,
                "mach_vm_region(VM_REGION_TOP_INFO) syscall failed");
            return NULL;
        }

        if (psutil_in_shared_region(addr, cpu_type) &&
                info.share_mode != SM_PRIVATE) {
            continue;
        }

        switch (info.share_mode) {
#ifdef SM_LARGE_PAGE
            case SM_LARGE_PAGE:
                // NB: Large pages are not shareable and always resident.
#endif
            case SM_PRIVATE:
                private_pages += info.private_pages_resident;
                private_pages += info.shared_pages_resident;
                break;
            case SM_COW:
                private_pages += info.private_pages_resident;
                if (info.ref_count == 1) {
                    // Treat copy-on-write pages as private if they only
                    // have one reference.
                    private_pages += info.shared_pages_resident;
                }
                break;
            case SM_SHARED:
            default:
                break;
        }
    }

    mach_port_deallocate(mach_task_self(), task);

    if (host_page_size(mach_host_self(), &page_size) != KERN_SUCCESS)
        page_size = PAGE_SIZE;

    return Py_BuildValue("K", private_pages * page_size);
}


/*
 * Return system virtual memory stats.
 * See:
 * https://opensource.apple.com/source/system_cmds/system_cmds-790/
 *     vm_stat.tproj/vm_stat.c.auto.html
 */
static PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    int      mib[2];
    uint64_t total;
    size_t   len = sizeof(total);
    vm_statistics_data_t vm;
    int pagesize = getpagesize();
    // physical mem
    mib[0] = CTL_HW;
    mib[1] = HW_MEMSIZE;

    // This is also available as sysctlbyname("hw.memsize").
    if (sysctl(mib, 2, &total, &len, NULL, 0)) {
        if (errno != 0)
            PyErr_SetFromErrno(PyExc_OSError);
        else
            PyErr_Format(
                PyExc_RuntimeError, "sysctl(HW_MEMSIZE) syscall failed");
        return NULL;
    }

    // vm
    if (!psutil_sys_vminfo(&vm))
        return NULL;

    return Py_BuildValue(
        "KKKKKK",
        total,
        (unsigned long long) vm.active_count * pagesize,  // active
        (unsigned long long) vm.inactive_count * pagesize,  // inactive
        (unsigned long long) vm.wire_count * pagesize,  // wired
        (unsigned long long) vm.free_count * pagesize,  // free
        (unsigned long long) vm.speculative_count * pagesize  // speculative
    );
}


/*
 * Return stats about swap memory.
 */
static PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
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
            PyErr_SetFromErrno(PyExc_OSError);
        else
            PyErr_Format(
                PyExc_RuntimeError, "sysctl(VM_SWAPUSAGE) syscall failed");
        return NULL;
    }
    if (!psutil_sys_vminfo(&vmstat))
        return NULL;

    return Py_BuildValue(
        "LLLKK",
        totals.xsu_total,
        totals.xsu_used,
        totals.xsu_avail,
        (unsigned long long)vmstat.pageins * pagesize,
        (unsigned long long)vmstat.pageouts * pagesize);
}


/*
 * Return a Python tuple representing user, kernel and idle CPU times
 */
static PyObject *
psutil_cpu_times(PyObject *self, PyObject *args) {
    mach_msg_type_number_t count = HOST_CPU_LOAD_INFO_COUNT;
    kern_return_t error;
    host_cpu_load_info_data_t r_load;

    mach_port_t host_port = mach_host_self();
    error = host_statistics(host_port, HOST_CPU_LOAD_INFO,
                            (host_info_t)&r_load, &count);
    if (error != KERN_SUCCESS) {
        return PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_CPU_LOAD_INFO) syscall failed: %s",
            mach_error_string(error));
    }
    mach_port_deallocate(mach_task_self(), host_port);

    return Py_BuildValue(
        "(dddd)",
        (double)r_load.cpu_ticks[CPU_STATE_USER] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
        (double)r_load.cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
    );
}


/*
 * Return a Python list of tuple representing per-cpu times
 */
static PyObject *
psutil_per_cpu_times(PyObject *self, PyObject *args) {
    natural_t cpu_count;
    natural_t i;
    processor_info_array_t info_array;
    mach_msg_type_number_t info_count;
    kern_return_t error;
    processor_cpu_load_info_data_t *cpu_load_info = NULL;
    int ret;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_cputime = NULL;

    if (py_retlist == NULL)
        return NULL;

    mach_port_t host_port = mach_host_self();
    error = host_processor_info(host_port, PROCESSOR_CPU_LOAD_INFO,
                                &cpu_count, &info_array, &info_count);
    if (error != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_processor_info(PROCESSOR_CPU_LOAD_INFO) syscall failed: %s",
             mach_error_string(error));
        goto error;
    }
    mach_port_deallocate(mach_task_self(), host_port);

    cpu_load_info = (processor_cpu_load_info_data_t *) info_array;

    for (i = 0; i < cpu_count; i++) {
        py_cputime = Py_BuildValue(
            "(dddd)",
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_USER] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_NICE] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_SYSTEM] / CLK_TCK,
            (double)cpu_load_info[i].cpu_ticks[CPU_STATE_IDLE] / CLK_TCK
        );
        if (!py_cputime)
            goto error;
        if (PyList_Append(py_retlist, py_cputime))
            goto error;
        Py_CLEAR(py_cputime);
    }

    ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                        info_count * sizeof(int));
    if (ret != KERN_SUCCESS)
        PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    return py_retlist;

error:
    Py_XDECREF(py_cputime);
    Py_DECREF(py_retlist);
    if (cpu_load_info != NULL) {
        ret = vm_deallocate(mach_task_self(), (vm_address_t)info_array,
                            info_count * sizeof(int));
        if (ret != KERN_SUCCESS)
            PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    }
    return NULL;
}


/*
 * Retrieve CPU frequency.
 */
static PyObject *
psutil_cpu_freq(PyObject *self, PyObject *args) {
    int64_t curr;
    int64_t min;
    int64_t max;
    size_t size = sizeof(int64_t);

    if (sysctlbyname("hw.cpufrequency", &curr, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('hw.cpufrequency')");
    }
    if (sysctlbyname("hw.cpufrequency_min", &min, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('hw.cpufrequency_min')");
    }
    if (sysctlbyname("hw.cpufrequency_max", &max, &size, NULL, 0)) {
        return PyErr_SetFromOSErrnoWithSyscall(
            "sysctlbyname('hw.cpufrequency_max')");
    }

    return Py_BuildValue(
        "KKK",
        curr / 1000 / 1000,
        min / 1000 / 1000,
        max / 1000 / 1000);
}


/*
 * Return a Python float indicating the system boot time expressed in
 * seconds since the epoch.
 */
static PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    // fetch sysctl "kern.boottime"
    static int request[2] = { CTL_KERN, KERN_BOOTTIME };
    struct timeval result;
    size_t result_len = sizeof result;
    time_t boot_time = 0;

    if (sysctl(request, 2, &result, &result_len, NULL, 0) == -1)
        return PyErr_SetFromErrno(PyExc_OSError);
    boot_time = result.tv_sec;
    return Py_BuildValue("f", (float)boot_time);
}


/*
 * Return a list of tuples including device, mount point and fs type
 * for all partitions mounted on the system.
 */
static PyObject *
psutil_disk_partitions(PyObject *self, PyObject *args) {
    int num;
    int i;
    int len;
    uint64_t flags;
    char opts[400];
    struct statfs *fs = NULL;
    PyObject *py_dev = NULL;
    PyObject *py_mountp = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    // get the number of mount points
    Py_BEGIN_ALLOW_THREADS
    num = getfsstat(NULL, 0, MNT_NOWAIT);
    Py_END_ALLOW_THREADS
    if (num == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
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
        PyErr_SetFromErrno(PyExc_OSError);
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

        py_dev = PyUnicode_DecodeFSDefault(fs[i].f_mntfromname);
        if (! py_dev)
            goto error;
        py_mountp = PyUnicode_DecodeFSDefault(fs[i].f_mntonname);
        if (! py_mountp)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOss)",
            py_dev,               // device
            py_mountp,            // mount point
            fs[i].f_fstypename,   // fs type
            opts);                // options
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_dev);
        Py_CLEAR(py_mountp);
        Py_CLEAR(py_tuple);
    }

    free(fs);
    return py_retlist;

error:
    Py_XDECREF(py_dev);
    Py_XDECREF(py_mountp);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (fs != NULL)
        free(fs);
    return NULL;
}


/*
 * Return process threads
 */
static PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    pid_t pid;
    int err, ret;
    kern_return_t kr;
    unsigned int info_count = TASK_BASIC_INFO_COUNT;
    mach_port_t task = MACH_PORT_NULL;
    struct task_basic_info tasks_info;
    thread_act_port_array_t thread_list = NULL;
    thread_info_data_t thinfo_basic;
    thread_basic_info_t basic_info_th;
    mach_msg_type_number_t thread_count, thread_info_count, j;

    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    if (psutil_task_for_pid(pid, &task) != 0)
        goto error;

    info_count = TASK_BASIC_INFO_COUNT;
    err = task_info(task, TASK_BASIC_INFO, (task_info_t)&tasks_info,
                    &info_count);
    if (err != KERN_SUCCESS) {
        // errcode 4 is "invalid argument" (access denied)
        if (err == 4) {
            AccessDenied("task_info");
        }
        else {
            // otherwise throw a runtime error with appropriate error code
            PyErr_Format(PyExc_RuntimeError,
                         "task_info(TASK_BASIC_INFO) syscall failed");
        }
        goto error;
    }

    err = task_threads(task, &thread_list, &thread_count);
    if (err != KERN_SUCCESS) {
        PyErr_Format(PyExc_RuntimeError, "task_threads() syscall failed");
        goto error;
    }

    for (j = 0; j < thread_count; j++) {
        thread_info_count = THREAD_INFO_MAX;
        kr = thread_info(thread_list[j], THREAD_BASIC_INFO,
                         (thread_info_t)thinfo_basic, &thread_info_count);
        if (kr != KERN_SUCCESS) {
            PyErr_Format(PyExc_RuntimeError,
                         "thread_info(THREAD_BASIC_INFO) syscall failed");
            goto error;
        }

        basic_info_th = (thread_basic_info_t)thinfo_basic;
        py_tuple = Py_BuildValue(
            "Iff",
            j + 1,
            basic_info_th->user_time.seconds + \
                (float)basic_info_th->user_time.microseconds / 1000000.0,
            basic_info_th->system_time.seconds + \
                (float)basic_info_th->system_time.microseconds / 1000000.0
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
    }

    ret = vm_deallocate(task, (vm_address_t)thread_list,
                        thread_count * sizeof(int));
    if (ret != KERN_SUCCESS)
        PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);

    mach_port_deallocate(mach_task_self(), task);

    return py_retlist;

error:
    if (task != MACH_PORT_NULL)
        mach_port_deallocate(mach_task_self(), task);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    if (thread_list != NULL) {
        ret = vm_deallocate(task, (vm_address_t)thread_list,
                            thread_count * sizeof(int));
        if (ret != KERN_SUCCESS)
            PyErr_WarnEx(PyExc_RuntimeWarning, "vm_deallocate() failed", 2);
    }
    return NULL;
}


/*
 * Return process open files as a Python tuple.
 * References:
 * - lsof source code: http://goo.gl/SYW79 and http://goo.gl/m78fd
 * - /usr/include/sys/proc_info.h
 */
static PyObject *
psutil_proc_open_files(PyObject *self, PyObject *args) {
    pid_t pid;
    int pidinfo_result;
    int iterations;
    int i;
    unsigned long nb;

    struct proc_fdinfo *fds_pointer = NULL;
    struct proc_fdinfo *fdp_pointer;
    struct vnode_fdinfowithpath vi;

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_path = NULL;

    if (py_retlist == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    pidinfo_result = psutil_proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (pidinfo_result <= 0)
        goto error;

    fds_pointer = malloc(pidinfo_result);
    if (fds_pointer == NULL) {
        PyErr_NoMemory();
        goto error;
    }
    pidinfo_result = psutil_proc_pidinfo(
        pid, PROC_PIDLISTFDS, 0, fds_pointer, pidinfo_result);
    if (pidinfo_result <= 0)
        goto error;

    iterations = (pidinfo_result / PROC_PIDLISTFD_SIZE);

    for (i = 0; i < iterations; i++) {
        fdp_pointer = &fds_pointer[i];

        if (fdp_pointer->proc_fdtype == PROX_FDTYPE_VNODE) {
            errno = 0;
            nb = proc_pidfdinfo((pid_t)pid,
                                fdp_pointer->proc_fd,
                                PROC_PIDFDVNODEPATHINFO,
                                &vi,
                                sizeof(vi));

            // --- errors checking
            if ((nb <= 0) || nb < sizeof(vi)) {
                if ((errno == ENOENT) || (errno == EBADF)) {
                    // no such file or directory or bad file descriptor;
                    // let's assume the file has been closed or removed
                    continue;
                }
                else {
                    psutil_raise_for_pid(
                        pid, "proc_pidinfo(PROC_PIDFDVNODEPATHINFO)");
                    goto error;
                }
            }
            // --- /errors checking

            // --- construct python list
            py_path = PyUnicode_DecodeFSDefault(vi.pvip.vip_path);
            if (! py_path)
                goto error;
            py_tuple = Py_BuildValue(
                "(Oi)",
                py_path,
                (int)fdp_pointer->proc_fd);
            if (!py_tuple)
                goto error;
            if (PyList_Append(py_retlist, py_tuple))
                goto error;
            Py_CLEAR(py_tuple);
            Py_CLEAR(py_path);
            // --- /construct python list
        }
    }

    free(fds_pointer);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_path);
    Py_DECREF(py_retlist);
    if (fds_pointer != NULL)
        free(fds_pointer);
    return NULL;  // exception has already been set earlier
}


/*
 * Return process TCP and UDP connections as a list of tuples.
 * Raises NSP in case of zombie process.
 * References:
 * - lsof source code: http://goo.gl/SYW79 and http://goo.gl/wNrC0
 * - /usr/include/sys/proc_info.h
 */
static PyObject *
psutil_proc_connections(PyObject *self, PyObject *args) {
    pid_t pid;
    int pidinfo_result;
    int iterations;
    int i;
    unsigned long nb;

    struct proc_fdinfo *fds_pointer = NULL;
    struct proc_fdinfo *fdp_pointer;
    struct socket_fdinfo si;

    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;

    if (py_retlist == NULL)
        return NULL;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID "OO", &pid, &py_af_filter,
                           &py_type_filter)) {
        goto error;
    }

    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    if (pid == 0)
        return py_retlist;
    pidinfo_result = psutil_proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (pidinfo_result <= 0)
        goto error;

    fds_pointer = malloc(pidinfo_result);
    if (fds_pointer == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    pidinfo_result = psutil_proc_pidinfo(
        pid, PROC_PIDLISTFDS, 0, fds_pointer, pidinfo_result);
    if (pidinfo_result <= 0)
        goto error;

    iterations = (pidinfo_result / PROC_PIDLISTFD_SIZE);
    for (i = 0; i < iterations; i++) {
        py_tuple = NULL;
        py_laddr = NULL;
        py_raddr = NULL;
        fdp_pointer = &fds_pointer[i];

        if (fdp_pointer->proc_fdtype == PROX_FDTYPE_SOCKET) {
            errno = 0;
            nb = proc_pidfdinfo(pid, fdp_pointer->proc_fd,
                                PROC_PIDFDSOCKETINFO, &si, sizeof(si));

            // --- errors checking
            if ((nb <= 0) || (nb < sizeof(si))) {
                if (errno == EBADF) {
                    // let's assume socket has been closed
                    continue;
                }
                else {
                    psutil_raise_for_pid(
                        pid, "proc_pidinfo(PROC_PIDFDSOCKETINFO)");
                    goto error;
                }
            }
            // --- /errors checking

            //
            int fd, family, type, lport, rport, state;
            char lip[200], rip[200];
            int inseq;
            PyObject *py_family;
            PyObject *py_type;

            fd = (int)fdp_pointer->proc_fd;
            family = si.psi.soi_family;
            type = si.psi.soi_type;

            // apply filters
            py_family = PyLong_FromLong((long)family);
            inseq = PySequence_Contains(py_af_filter, py_family);
            Py_DECREF(py_family);
            if (inseq == 0)
                continue;
            py_type = PyLong_FromLong((long)type);
            inseq = PySequence_Contains(py_type_filter, py_type);
            Py_DECREF(py_type);
            if (inseq == 0)
                continue;

            if (errno != 0) {
                PyErr_SetFromErrno(PyExc_OSError);
                goto error;
            }

            if ((family == AF_INET) || (family == AF_INET6)) {
                if (family == AF_INET) {
                    inet_ntop(AF_INET,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini. \
                                  insi_laddr.ina_46.i46a_addr4,
                              lip,
                              sizeof(lip));
                    inet_ntop(AF_INET,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_faddr. \
                                  ina_46.i46a_addr4,
                              rip,
                              sizeof(rip));
                }
                else {
                    inet_ntop(AF_INET6,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini. \
                                  insi_laddr.ina_6,
                              lip, sizeof(lip));
                    inet_ntop(AF_INET6,
                              &si.psi.soi_proto.pri_tcp.tcpsi_ini. \
                                  insi_faddr.ina_6,
                              rip, sizeof(rip));
                }

                // check for inet_ntop failures
                if (errno != 0) {
                    PyErr_SetFromOSErrnoWithSyscall("inet_ntop()");
                    goto error;
                }

                lport = ntohs(si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_lport);
                rport = ntohs(si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_fport);
                if (type == SOCK_STREAM)
                    state = (int)si.psi.soi_proto.pri_tcp.tcpsi_state;
                else
                    state = PSUTIL_CONN_NONE;

                py_laddr = Py_BuildValue("(si)", lip, lport);
                if (!py_laddr)
                    goto error;
                if (rport != 0)
                    py_raddr = Py_BuildValue("(si)", rip, rport);
                else
                    py_raddr = Py_BuildValue("()");
                if (!py_raddr)
                    goto error;

                // construct the python list
                py_tuple = Py_BuildValue(
                    "(iiiNNi)", fd, family, type, py_laddr, py_raddr, state);
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
            }
            else if (family == AF_UNIX) {
                py_laddr = PyUnicode_DecodeFSDefault(
                    si.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path);
                if (!py_laddr)
                    goto error;
                py_raddr = PyUnicode_DecodeFSDefault(
                    si.psi.soi_proto.pri_un.unsi_caddr.ua_sun.sun_path);
                if (!py_raddr)
                    goto error;
                // construct the python list
                py_tuple = Py_BuildValue(
                    "(iiiOOi)",
                    fd, family, type,
                    py_laddr,
                    py_raddr,
                    PSUTIL_CONN_NONE);
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
                Py_CLEAR(py_laddr);
                Py_CLEAR(py_raddr);
            }
        }
    }

    free(fds_pointer);
    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_laddr);
    Py_XDECREF(py_raddr);
    Py_DECREF(py_retlist);
    if (fds_pointer != NULL)
        free(fds_pointer);
    return NULL;
}


/*
 * Return number of file descriptors opened by process.
 * Raises NSP in case of zombie process.
 */
static PyObject *
psutil_proc_num_fds(PyObject *self, PyObject *args) {
    pid_t pid;
    int pidinfo_result;
    int num;
    struct proc_fdinfo *fds_pointer;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    pidinfo_result = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (pidinfo_result <= 0)
        return PyErr_SetFromErrno(PyExc_OSError);

    fds_pointer = malloc(pidinfo_result);
    if (fds_pointer == NULL)
        return PyErr_NoMemory();
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
static PyObject *
psutil_net_io_counters(PyObject *self, PyObject *args) {
    char *buf = NULL, *lim, *next;
    struct if_msghdr *ifm;
    int mib[6];
    mib[0] = CTL_NET;          // networking subsystem
    mib[1] = PF_ROUTE;         // type of information
    mib[2] = 0;                // protocol (IPPROTO_xxx)
    mib[3] = 0;                // address family
    mib[4] = NET_RT_IFLIST2;   // operation
    mib[5] = 0;
    size_t len;
    PyObject *py_ifc_info = NULL;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    if (sysctl(mib, 6, NULL, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
        goto error;
    }

    buf = malloc(len);
    if (buf == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    if (sysctl(mib, 6, buf, &len, NULL, 0) < 0) {
        PyErr_SetFromErrno(PyExc_OSError);
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

            py_ifc_info = Py_BuildValue(
                "(KKKKKKKi)",
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
            Py_CLEAR(py_ifc_info);
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
static PyObject *
psutil_disk_io_counters(PyObject *self, PyObject *args) {
    CFDictionaryRef parent_dict;
    CFDictionaryRef props_dict;
    CFDictionaryRef stats_dict;
    io_registry_entry_t parent;
    io_registry_entry_t disk;
    io_iterator_t disk_list;
    PyObject *py_disk_info = NULL;
    PyObject *py_retdict = PyDict_New();

    if (py_retdict == NULL)
        return NULL;

    // Get list of disks
    if (IOServiceGetMatchingServices(kIOMasterPortDefault,
                                     IOServiceMatching(kIOMediaClass),
                                     &disk_list) != kIOReturnSuccess) {
        PyErr_SetString(
            PyExc_RuntimeError, "unable to get the list of disks.");
        goto error;
    }

    // Iterate over disks
    while ((disk = IOIteratorNext(disk_list)) != 0) {
        py_disk_info = NULL;
        parent_dict = NULL;
        props_dict = NULL;
        stats_dict = NULL;

        if (IORegistryEntryGetParentEntry(disk, kIOServicePlane, &parent)
                != kIOReturnSuccess) {
            PyErr_SetString(PyExc_RuntimeError,
                            "unable to get the disk's parent.");
            IOObjectRelease(disk);
            goto error;
        }

        if (IOObjectConformsTo(parent, "IOBlockStorageDriver")) {
            if (IORegistryEntryCreateCFProperties(
                    disk,
                    (CFMutableDictionaryRef *) &parent_dict,
                    kCFAllocatorDefault,
                    kNilOptions
                ) != kIOReturnSuccess)
            {
                PyErr_SetString(PyExc_RuntimeError,
                                "unable to get the parent's properties.");
                IOObjectRelease(disk);
                IOObjectRelease(parent);
                goto error;
            }

            if (IORegistryEntryCreateCFProperties(
                    parent,
                    (CFMutableDictionaryRef *) &props_dict,
                    kCFAllocatorDefault,
                    kNilOptions
                ) != kIOReturnSuccess)
            {
                PyErr_SetString(PyExc_RuntimeError,
                                "unable to get the disk properties.");
                CFRelease(props_dict);
                IOObjectRelease(disk);
                IOObjectRelease(parent);
                goto error;
            }

            const int kMaxDiskNameSize = 64;
            CFStringRef disk_name_ref = (CFStringRef)CFDictionaryGetValue(
                parent_dict, CFSTR(kIOBSDNameKey));
            char disk_name[kMaxDiskNameSize];

            CFStringGetCString(disk_name_ref,
                               disk_name,
                               kMaxDiskNameSize,
                               CFStringGetSystemEncoding());

            stats_dict = (CFDictionaryRef)CFDictionaryGetValue(
                props_dict, CFSTR(kIOBlockStorageDriverStatisticsKey));

            if (stats_dict == NULL) {
                PyErr_SetString(PyExc_RuntimeError,
                                "Unable to get disk stats.");
                goto error;
            }

            CFNumberRef number;
            int64_t reads = 0;
            int64_t writes = 0;
            int64_t read_bytes = 0;
            int64_t write_bytes = 0;
            int64_t read_time = 0;
            int64_t write_time = 0;

            // Get disk reads/writes
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

            // Get disk bytes read/written
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

            // Get disk time spent reading/writing (nanoseconds)
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                    stats_dict,
                    CFSTR(kIOBlockStorageDriverStatisticsTotalReadTimeKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &read_time);
            }
            if ((number = (CFNumberRef)CFDictionaryGetValue(
                    stats_dict,
                    CFSTR(kIOBlockStorageDriverStatisticsTotalWriteTimeKey))))
            {
                CFNumberGetValue(number, kCFNumberSInt64Type, &write_time);
            }

            // Read/Write time on macOS comes back in nanoseconds and in psutil
            // we've standardized on milliseconds so do the conversion.
            py_disk_info = Py_BuildValue(
                "(KKKKKK)",
                reads,
                writes,
                read_bytes,
                write_bytes,
                read_time / 1000 / 1000,
                write_time / 1000 / 1000);
           if (!py_disk_info)
                goto error;
            if (PyDict_SetItemString(py_retdict, disk_name, py_disk_info))
                goto error;
            Py_CLEAR(py_disk_info);

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
static PyObject *
psutil_users(PyObject *self, PyObject *args) {
    struct utmpx *utx;
    PyObject *py_username = NULL;
    PyObject *py_tty = NULL;
    PyObject *py_hostname = NULL;
    PyObject *py_tuple = NULL;
    PyObject *py_retlist = PyList_New(0);

    if (py_retlist == NULL)
        return NULL;
    while ((utx = getutxent()) != NULL) {
        if (utx->ut_type != USER_PROCESS)
            continue;
        py_username = PyUnicode_DecodeFSDefault(utx->ut_user);
        if (! py_username)
            goto error;
        py_tty = PyUnicode_DecodeFSDefault(utx->ut_line);
        if (! py_tty)
            goto error;
        py_hostname = PyUnicode_DecodeFSDefault(utx->ut_host);
        if (! py_hostname)
            goto error;
        py_tuple = Py_BuildValue(
            "(OOOfi)",
            py_username,              // username
            py_tty,                   // tty
            py_hostname,              // hostname
            (float)utx->ut_tv.tv_sec, // start time
            utx->ut_pid               // process id
        );
        if (!py_tuple) {
            endutxent();
            goto error;
        }
        if (PyList_Append(py_retlist, py_tuple)) {
            endutxent();
            goto error;
        }
        Py_CLEAR(py_username);
        Py_CLEAR(py_tty);
        Py_CLEAR(py_hostname);
        Py_CLEAR(py_tuple);
    }

    endutxent();
    return py_retlist;

error:
    Py_XDECREF(py_username);
    Py_XDECREF(py_tty);
    Py_XDECREF(py_hostname);
    Py_XDECREF(py_tuple);
    Py_DECREF(py_retlist);
    return NULL;
}


/*
 * Return CPU statistics.
 */
static PyObject *
psutil_cpu_stats(PyObject *self, PyObject *args) {
    struct vmmeter vmstat;
    kern_return_t ret;
    mach_msg_type_number_t count = sizeof(vmstat) / sizeof(integer_t);
    mach_port_t mport = mach_host_self();

    ret = host_statistics(mport, HOST_VM_INFO, (host_info_t)&vmstat, &count);
    if (ret != KERN_SUCCESS) {
        PyErr_Format(
            PyExc_RuntimeError,
            "host_statistics(HOST_VM_INFO) failed: %s",
            mach_error_string(ret));
        return NULL;
    }
    mach_port_deallocate(mach_task_self(), mport);

    return Py_BuildValue(
        "IIIII",
        vmstat.v_swtch,  // ctx switches
        vmstat.v_intr,  // interrupts
        vmstat.v_soft,  // software interrupts
        vmstat.v_syscall,  // syscalls
        vmstat.v_trap  // traps
    );
}


/*
 * Return battery information.
 */
static PyObject *
psutil_sensors_battery(PyObject *self, PyObject *args) {
    PyObject *py_tuple = NULL;
    CFTypeRef power_info = NULL;
    CFArrayRef power_sources_list = NULL;
    CFDictionaryRef power_sources_information = NULL;
    CFNumberRef capacity_ref = NULL;
    CFNumberRef time_to_empty_ref = NULL;
    CFStringRef ps_state_ref = NULL;
    uint32_t capacity;     /* units are percent */
    int time_to_empty;     /* units are minutes */
    int is_power_plugged;

    power_info = IOPSCopyPowerSourcesInfo();

    if (!power_info) {
        PyErr_SetString(PyExc_RuntimeError,
            "IOPSCopyPowerSourcesInfo() syscall failed");
        goto error;
    }

    power_sources_list = IOPSCopyPowerSourcesList(power_info);
    if (!power_sources_list) {
        PyErr_SetString(PyExc_RuntimeError,
            "IOPSCopyPowerSourcesList() syscall failed");
        goto error;
    }

    /* Should only get one source. But in practice, check for > 0 sources */
    if (!CFArrayGetCount(power_sources_list)) {
        PyErr_SetString(PyExc_NotImplementedError, "no battery");
        goto error;
    }

    power_sources_information = IOPSGetPowerSourceDescription(
        power_info, CFArrayGetValueAtIndex(power_sources_list, 0));

    capacity_ref = (CFNumberRef)  CFDictionaryGetValue(
        power_sources_information, CFSTR(kIOPSCurrentCapacityKey));
    if (!CFNumberGetValue(capacity_ref, kCFNumberSInt32Type, &capacity)) {
        PyErr_SetString(PyExc_RuntimeError,
            "No battery capacity infomration in power sources info");
        goto error;
    }

    ps_state_ref = (CFStringRef) CFDictionaryGetValue(
        power_sources_information, CFSTR(kIOPSPowerSourceStateKey));
    is_power_plugged = CFStringCompare(
        ps_state_ref, CFSTR(kIOPSACPowerValue), 0)
        == kCFCompareEqualTo;

    time_to_empty_ref = (CFNumberRef) CFDictionaryGetValue(
        power_sources_information, CFSTR(kIOPSTimeToEmptyKey));
    if (!CFNumberGetValue(time_to_empty_ref,
                          kCFNumberIntType, &time_to_empty)) {
        /* This value is recommended for non-Apple power sources, so it's not
         * an error if it doesn't exist. We'll return -1 for "unknown" */
        /* A value of -1 indicates "Still Calculating the Time" also for
         * apple power source */
        time_to_empty = -1;
    }

    py_tuple = Py_BuildValue("Iii",
        capacity, time_to_empty, is_power_plugged);
    if (!py_tuple) {
        goto error;
    }

    CFRelease(power_info);
    CFRelease(power_sources_list);
    /* Caller should NOT release power_sources_information */

    return py_tuple;

error:
    if (power_info)
        CFRelease(power_info);
    if (power_sources_list)
        CFRelease(power_sources_list);
    Py_XDECREF(py_tuple);
    return NULL;
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef mod_methods[] = {
    // --- per-process functions

    {"proc_kinfo_oneshot", psutil_proc_kinfo_oneshot, METH_VARARGS,
     "Return multiple process info."},
    {"proc_pidtaskinfo_oneshot", psutil_proc_pidtaskinfo_oneshot, METH_VARARGS,
     "Return multiple process info."},
    {"proc_name", psutil_proc_name, METH_VARARGS,
     "Return process name"},
    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS,
     "Return process cmdline as a list of cmdline arguments"},
    {"proc_environ", psutil_proc_environ, METH_VARARGS,
     "Return process environment data"},
    {"proc_exe", psutil_proc_exe, METH_VARARGS,
     "Return path of the process executable"},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS,
     "Return process current working directory."},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS,
     "Return process USS memory"},
    {"proc_threads", psutil_proc_threads, METH_VARARGS,
     "Return process threads as a list of tuples"},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS,
     "Return files opened by process as a list of tuples"},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS,
     "Return the number of fds opened by process."},
    {"proc_connections", psutil_proc_connections, METH_VARARGS,
     "Get process TCP and UDP connections as a list of tuples"},

    // --- system-related functions

    {"pids", psutil_pids, METH_VARARGS,
     "Returns a list of PIDs currently running on the system"},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS,
     "Return number of logical CPUs on the system"},
    {"cpu_count_phys", psutil_cpu_count_phys, METH_VARARGS,
     "Return number of physical CPUs on the system"},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS,
     "Return system virtual memory stats"},
    {"swap_mem", psutil_swap_mem, METH_VARARGS,
     "Return stats about swap memory, in bytes"},
    {"cpu_times", psutil_cpu_times, METH_VARARGS,
     "Return system cpu times as a tuple (user, system, nice, idle, irc)"},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS,
     "Return system per-cpu times as a list of tuples"},
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS,
     "Return cpu current frequency"},
    {"boot_time", psutil_boot_time, METH_VARARGS,
     "Return the system boot time expressed in seconds since the epoch."},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS,
     "Return a list of tuples including device, mount point and "
     "fs type for all partitions mounted on the system."},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS,
     "Return dict of tuples of networks I/O information."},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS,
     "Return dict of tuples of disks I/O information."},
    {"users", psutil_users, METH_VARARGS,
     "Return currently connected users as a list of tuples"},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS,
     "Return CPU statistics"},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS,
     "Return battery information."},

    // --- others
    {"set_testing", psutil_set_testing, METH_NOARGS,
     "Set psutil in testing mode"},

    {NULL, NULL, 0, NULL}
};


#if PY_MAJOR_VERSION >= 3
    #define INITERR return NULL

    static struct PyModuleDef moduledef = {
        PyModuleDef_HEAD_INIT,
        "_psutil_osx",
        NULL,
        -1,
        mod_methods,
        NULL,
        NULL,
        NULL,
        NULL
    };

    PyObject *PyInit__psutil_osx(void)
#else  /* PY_MAJOR_VERSION */
    #define INITERR return

    void init_psutil_osx(void)
#endif  /* PY_MAJOR_VERSION */
{
#if PY_MAJOR_VERSION >= 3
    PyObject *mod = PyModule_Create(&moduledef);
#else
    PyObject *mod = Py_InitModule("_psutil_osx", mod_methods);
#endif
    if (mod == NULL)
        INITERR;

    if (psutil_setup() != 0)
        INITERR;

    if (PyModule_AddIntConstant(mod, "version", PSUTIL_VERSION))
        INITERR;
    // process status constants, defined in:
    // http://fxr.watson.org/fxr/source/bsd/sys/proc.h?v=xnu-792.6.70#L149
    if (PyModule_AddIntConstant(mod, "SIDL", SIDL))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SRUN", SRUN))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SSLEEP", SSLEEP))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SSTOP", SSTOP))
        INITERR;
    if (PyModule_AddIntConstant(mod, "SZOMB", SZOMB))
        INITERR;
    // connection status constants
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSED", TCPS_CLOSED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSING", TCPS_CLOSING))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_CLOSE_WAIT", TCPS_CLOSE_WAIT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_LISTEN", TCPS_LISTEN))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_ESTABLISHED", TCPS_ESTABLISHED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_SENT", TCPS_SYN_SENT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_SYN_RECEIVED", TCPS_SYN_RECEIVED))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_1", TCPS_FIN_WAIT_1))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_FIN_WAIT_2", TCPS_FIN_WAIT_2))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_LAST_ACK", TCPS_LAST_ACK))
        INITERR;
    if (PyModule_AddIntConstant(mod, "TCPS_TIME_WAIT", TCPS_TIME_WAIT))
        INITERR;
    if (PyModule_AddIntConstant(mod, "PSUTIL_CONN_NONE", PSUTIL_CONN_NONE))
        INITERR;

    // Exception.
    ZombieProcessError = PyErr_NewException(
        "_psutil_osx.ZombieProcessError", NULL, NULL);
    if (ZombieProcessError == NULL)
        INITERR;
    Py_INCREF(ZombieProcessError);
    if (PyModule_AddObject(mod, "ZombieProcessError", ZombieProcessError)) {
        Py_DECREF(ZombieProcessError);
        INITERR;
    }

    if (mod == NULL)
        INITERR;
#if PY_MAJOR_VERSION >= 3
    return mod;
#endif
}
