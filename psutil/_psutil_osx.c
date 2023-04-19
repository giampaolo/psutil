/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
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
#include <sys/sysctl.h>
#include <libproc.h>
#include <sys/proc_info.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <pwd.h>
#include <unistd.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/shared_region.h>
#include <mach-o/loader.h>

#include "_psutil_common.h"
#include "_psutil_posix.h"
#include "arch/osx/cpu.h"
#include "arch/osx/disk.h"
#include "arch/osx/net.h"
#include "arch/osx/mem.h"
#include "arch/osx/process_info.h"
#include "arch/osx/sensors.h"
#include "arch/osx/sys.h"


#define PSUTIL_TV2DOUBLE(t) ((t).tv_sec + (t).tv_usec / 1000000.0)

static PyObject *ZombieProcessError;


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
            PyErr_SetString(ZombieProcessError,
                            "task_for_pid -> psutil_is_zombie -> 1");
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
 * A wrapper around proc_pidinfo(PROC_PIDLISTFDS), which dynamically sets
 * the buffer size.
 */
static struct proc_fdinfo*
psutil_proc_list_fds(pid_t pid, int *num_fds) {
    int ret;
    int fds_size = 0;
    int max_size = 24 * 1024 * 1024;  // 24M
    struct proc_fdinfo *fds_pointer = NULL;

    errno = 0;
    ret = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, NULL, 0);
    if (ret <= 0) {
        psutil_raise_for_pid(pid, "proc_pidinfo(PROC_PIDLISTFDS) 1/2");
        goto error;
    }

    while (1) {
        if (ret > fds_size) {
            while (ret > fds_size) {
                fds_size += PROC_PIDLISTFD_SIZE * 32;
                if (fds_size > max_size) {
                    PyErr_Format(PyExc_RuntimeError,
                                 "prevent malloc() to allocate > 24M");
                    goto error;
                }
            }

            if (fds_pointer != NULL) {
                free(fds_pointer);
            }
            fds_pointer = malloc(fds_size);

            if (fds_pointer == NULL) {
                PyErr_NoMemory();
                goto error;
            }
        }

        errno = 0;
        ret = proc_pidinfo(pid, PROC_PIDLISTFDS, 0, fds_pointer, fds_size);
        if (ret <= 0) {
            psutil_raise_for_pid(pid, "proc_pidinfo(PROC_PIDLISTFDS) 2/2");
            goto error;
        }

        if (ret + (int)PROC_PIDLISTFD_SIZE >= fds_size) {
            psutil_debug("PROC_PIDLISTFDS: make room for 1 extra fd");
            ret = fds_size + (int)PROC_PIDLISTFD_SIZE;
            continue;
        }

        break;
    }

    *num_fds = (ret / (int)PROC_PIDLISTFD_SIZE);
    return fds_pointer;

error:
    if (fds_pointer != NULL)
        free(fds_pointer);
    return NULL;
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
    uint64_t total_user;
    uint64_t total_system;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, 0, &pti, sizeof(pti)) <= 0)
        return NULL;

    total_user = pti.pti_total_user * PSUTIL_MACH_TIMEBASE_INFO.numer;
    total_user /= PSUTIL_MACH_TIMEBASE_INFO.denom;
    total_system = pti.pti_total_system * PSUTIL_MACH_TIMEBASE_INFO.numer;
    total_system /= PSUTIL_MACH_TIMEBASE_INFO.denom;

    return Py_BuildValue(
        "(ddKKkkkk)",
        (float)total_user / 1000000000.0,     // (float) cpu user time
        (float)total_system / 1000000000.0,   // (float) cpu sys time
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
        if (pid == 0) {
            AccessDenied("automatically set for PID 0");
            return NULL;
        }
        else if (errno == ENOENT) {
            // It may happen (file not found error) if the process is
            // still alive but the executable which launched it got
            // deleted, see:
            // https://github.com/giampaolo/psutil/issues/1738
            return Py_BuildValue("s", "");
        }
        else {
            psutil_raise_for_pid(pid, "proc_pidpath()");
            return NULL;
        }
    }
    return PyUnicode_DecodeFSDefault(buf);
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
    long pagesize = psutil_getpagesize();
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
    return Py_BuildValue("K", private_pages * pagesize);
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
            AccessDenied("task_info(TASK_BASIC_INFO)");
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
    int num_fds;
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

    // see: https://github.com/giampaolo/psutil/issues/2116
    if (pid == 0)
        return py_retlist;

    fds_pointer = psutil_proc_list_fds(pid, &num_fds);
    if (fds_pointer == NULL)
        goto error;

    for (i = 0; i < num_fds; i++) {
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
    int num_fds;
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

    // see: https://github.com/giampaolo/psutil/issues/2116
    if (pid == 0)
        return py_retlist;

    if (!PySequence_Check(py_af_filter) || !PySequence_Check(py_type_filter)) {
        PyErr_SetString(PyExc_TypeError, "arg 2 or 3 is not a sequence");
        goto error;
    }

    fds_pointer = psutil_proc_list_fds(pid, &num_fds);
    if (fds_pointer == NULL)
        goto error;

    for (i = 0; i < num_fds; i++) {
        py_tuple = NULL;
        py_laddr = NULL;
        py_raddr = NULL;
        fdp_pointer = &fds_pointer[i];

        if (fdp_pointer->proc_fdtype == PROX_FDTYPE_SOCKET) {
            errno = 0;
            nb = proc_pidfdinfo(pid, fdp_pointer->proc_fd,
                                PROC_PIDFDSOCKETINFO, &si, sizeof(si));

            // --- errors checking
            if ((nb <= 0) || (nb < sizeof(si)) || (errno != 0)) {
                if (errno == EBADF) {
                    // let's assume socket has been closed
                    psutil_debug("proc_pidfdinfo(PROC_PIDFDSOCKETINFO) -> "
                                 "EBADF (ignored)");
                    continue;
                }
                else if (errno == EOPNOTSUPP) {
                    // may happen sometimes, see:
                    // https://github.com/giampaolo/psutil/issues/1512
                    psutil_debug("proc_pidfdinfo(PROC_PIDFDSOCKETINFO) -> "
                                 "EOPNOTSUPP (ignored)");
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
            // TODO: use INET6_ADDRSTRLEN instead of 200
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
    int num_fds;
    struct proc_fdinfo *fds_pointer;

    if (! PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    fds_pointer = psutil_proc_list_fds(pid, &num_fds);
    if (fds_pointer == NULL)
        return NULL;

    free(fds_pointer);
    return Py_BuildValue("i", num_fds);
}


/*
 * define the psutil C module methods and initialize the module.
 */
static PyMethodDef mod_methods[] = {
    // --- per-process functions
    {"proc_cmdline", psutil_proc_cmdline, METH_VARARGS},
    {"proc_connections", psutil_proc_connections, METH_VARARGS},
    {"proc_cwd", psutil_proc_cwd, METH_VARARGS},
    {"proc_environ", psutil_proc_environ, METH_VARARGS},
    {"proc_exe", psutil_proc_exe, METH_VARARGS},
    {"proc_kinfo_oneshot", psutil_proc_kinfo_oneshot, METH_VARARGS},
    {"proc_memory_uss", psutil_proc_memory_uss, METH_VARARGS},
    {"proc_name", psutil_proc_name, METH_VARARGS},
    {"proc_num_fds", psutil_proc_num_fds, METH_VARARGS},
    {"proc_open_files", psutil_proc_open_files, METH_VARARGS},
    {"proc_pidtaskinfo_oneshot", psutil_proc_pidtaskinfo_oneshot, METH_VARARGS},
    {"proc_threads", psutil_proc_threads, METH_VARARGS},

    // --- system-related functions
    {"boot_time", psutil_boot_time, METH_VARARGS},
    {"cpu_count_cores", psutil_cpu_count_cores, METH_VARARGS},
    {"cpu_count_logical", psutil_cpu_count_logical, METH_VARARGS},
    {"cpu_freq", psutil_cpu_freq, METH_VARARGS},
    {"cpu_stats", psutil_cpu_stats, METH_VARARGS},
    {"cpu_times", psutil_cpu_times, METH_VARARGS},
    {"disk_io_counters", psutil_disk_io_counters, METH_VARARGS},
    {"disk_partitions", psutil_disk_partitions, METH_VARARGS},
    {"disk_usage_used", psutil_disk_usage_used, METH_VARARGS},
    {"net_io_counters", psutil_net_io_counters, METH_VARARGS},
    {"per_cpu_times", psutil_per_cpu_times, METH_VARARGS},
    {"pids", psutil_pids, METH_VARARGS},
    {"sensors_battery", psutil_sensors_battery, METH_VARARGS},
    {"swap_mem", psutil_swap_mem, METH_VARARGS},
    {"users", psutil_users, METH_VARARGS},
    {"virtual_mem", psutil_virtual_mem, METH_VARARGS},

    // --- others
    {"set_debug", psutil_set_debug, METH_VARARGS},

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
