/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Process related functions. Original code was moved in here from
// psutil/_psutil_osx.c and psutil/arc/osx/process_info.c in 2023.
// For reference, here's the GIT blame history before the move:
// https://github.com/giampaolo/psutil/blame/59504a5/psutil/_psutil_osx.c
// https://github.com/giampaolo/psutil/blame/efd7ed3/psutil/arch/osx/process_info.c

#include <Python.h>
#include <errno.h>
#include <stdbool.h>
#include <stdlib.h>
#include <stdio.h>
#include <sys/sysctl.h>
#include <libproc.h>
#include <sys/proc_info.h>
#include <sys/sysctl.h>
#include <netinet/tcp_fsm.h>
#include <arpa/inet.h>
#include <pwd.h>
#include <unistd.h>
#include <mach/mach.h>
#include <mach/mach_vm.h>
#include <mach/shared_region.h>
#include <mach-o/loader.h>

#include "../../arch/all/init.h"


// macOS is apparently the only UNIX where the process "base" status
// (running, idle, etc.) is unreliable and must be guessed from flags:
// https://github.com/giampaolo/psutil/issues/2675
static int
convert_status(struct extern_proc *p, struct eproc *e) {
    int flag = p->p_flag;
    int eflag = e->e_flag;

    // zombies and stopped
    if (p->p_stat == SZOMB)
        return SZOMB;
    if (p->p_stat == SSTOP)
        return SSTOP;

    if (flag & P_SYSTEM)
        return SIDL;  // system idle
    if (flag & P_WEXIT)
        return SIDL;  // waiting to exit
    if (flag & P_PPWAIT)
        return SIDL;  // parent waiting
    if (eflag & EPROC_SLEADER)
        return SSLEEP;  // session leader treated as sleeping

    // Default: 99% is SRUN (running)
    return p->p_stat;
}


/*
 * Return multiple process info as a Python tuple in one shot by
 * using sysctl() and filling up a kinfo_proc struct.
 * It should be possible to do this for all processes without
 * incurring into permission (EPERM) errors.
 * This will also succeed for zombie processes returning correct
 * information.
 */
PyObject *
psutil_proc_kinfo_oneshot(PyObject *self, PyObject *args) {
    pid_t pid;
    int status;
    struct kinfo_proc kp;
    PyObject *py_name = NULL;
    PyObject *py_retlist = NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_get_kinfo_proc(pid, &kp) == -1)
        return NULL;

    py_name = PyUnicode_DecodeFSDefault(kp.kp_proc.p_comm);
    if (!py_name) {
        // Likely a decoding error. We don't want to fail the whole
        // operation. The python module may retry with proc_name().
        PyErr_Clear();
        Py_INCREF(Py_None);
        py_name = Py_None;
    }

    status = convert_status(&kp.kp_proc, &kp.kp_eproc);

    py_retlist = Py_BuildValue(
        _Py_PARSE_PID "llllllldiO",
        kp.kp_eproc.e_ppid,  // (pid_t) ppid
        (long)kp.kp_eproc.e_pcred.p_ruid,  // (long) real uid
        (long)kp.kp_eproc.e_ucred.cr_uid,  // (long) effective uid
        (long)kp.kp_eproc.e_pcred.p_svuid,  // (long) saved uid
        (long)kp.kp_eproc.e_pcred.p_rgid,  // (long) real gid
        (long)kp.kp_eproc.e_ucred.cr_groups[0],  // (long) effective gid
        (long)kp.kp_eproc.e_pcred.p_svgid,  // (long) saved gid
        (long long)kp.kp_eproc.e_tdev,  // (long long) tty nr
        PSUTIL_TV2DOUBLE(kp.kp_proc.p_starttime),  // (double) create time
        status,  // (int) status
        py_name  // (pystr) name
    );

    Py_DECREF(py_name);
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
PyObject *
psutil_proc_pidtaskinfo_oneshot(PyObject *self, PyObject *args) {
    pid_t pid;
    struct proc_taskinfo pti;
    uint64_t total_user;
    uint64_t total_system;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_proc_pidinfo(pid, PROC_PIDTASKINFO, 0, &pti, sizeof(pti)) != 0)
        return NULL;

    total_user = pti.pti_total_user * PSUTIL_MACH_TIMEBASE_INFO.numer;
    total_user /= PSUTIL_MACH_TIMEBASE_INFO.denom;
    total_system = pti.pti_total_system * PSUTIL_MACH_TIMEBASE_INFO.numer;
    total_system /= PSUTIL_MACH_TIMEBASE_INFO.denom;

    return Py_BuildValue(
        "(ddKKkkkk)",
        (float)total_user / 1000000000.0,  // (float) cpu user time
        (float)total_system / 1000000000.0,  // (float) cpu sys time
        // Note about memory: determining other mem stats on macOS is a mess:
        // http://www.opensource.apple.com/source/top/top-67/libtop.c?txt
        // I just give up.
        // struct proc_regioninfo pri;
        // psutil_proc_pidinfo(pid, PROC_PIDREGIONINFO, 0, &pri, sizeof(pri))
        pti.pti_resident_size,  // (uns long long) rss
        pti.pti_virtual_size,  // (uns long long) vms
        pti.pti_faults,  // (uns long) number of page faults (pages)
        pti.pti_pageins,  // (uns long) number of actual pageins (pages)
        pti.pti_threadnum,  // (uns long) num threads
        // Unvoluntary value seems not to be available;
        // pti.pti_csw probably refers to the sum of the two;
        // getrusage() numbers seems to confirm this theory.
        pti.pti_csw  // (uns long) voluntary ctx switches
    );
}


/*
 * Return process name from kinfo_proc as a Python string.
 */
PyObject *
psutil_proc_name(PyObject *self, PyObject *args) {
    pid_t pid;
    struct kinfo_proc kp;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    if (psutil_get_kinfo_proc(pid, &kp) == -1)
        return NULL;

    return PyUnicode_DecodeFSDefault(kp.kp_proc.p_comm);
}

/*
 * Return process current working directory.
 * Raises NSP in case of zombie process.
 */
PyObject *
psutil_proc_cwd(PyObject *self, PyObject *args) {
    pid_t pid;
    struct proc_vnodepathinfo pathinfo;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (psutil_proc_pidinfo(
            pid, PROC_PIDVNODEPATHINFO, 0, &pathinfo, sizeof(pathinfo)
        )
        != 0)
    {
        return NULL;
    }

    return PyUnicode_DecodeFSDefault(pathinfo.pvi_cdir.vip_path);
}


/*
 * Return path of the process executable.
 */
PyObject *
psutil_proc_exe(PyObject *self, PyObject *args) {
    pid_t pid;
    char buf[PATH_MAX];
    int ret;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;
    errno = 0;
    ret = proc_pidpath(pid, &buf, sizeof(buf));
    if (ret == 0) {
        if (pid == 0) {
            psutil_oserror_ad("automatically set for PID 0");
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
PyObject *
psutil_proc_memory_uss(PyObject *self, PyObject *args) {
    pid_t pid;
    cpu_type_t cpu_type;
    size_t private_pages = 0;
    mach_vm_size_t size = 0;
    mach_msg_type_number_t info_count;
    kern_return_t kr;
    long pagesize = psutil_getpagesize();
    mach_vm_address_t addr;
    mach_port_t task = MACH_PORT_NULL;
    vm_region_top_info_data_t info;
    mach_port_t object_name;
    mach_vm_address_t prev_addr;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    if (psutil_task_for_pid(pid, &task) != 0)
        return NULL;

    if (psutil_sysctlbyname("sysctl.proc_cputype", &cpu_type, sizeof(cpu_type))
        != 0)
    {
        return NULL;
    }

    // Roughly based on libtop_update_vm_regions in
    // http://www.opensource.apple.com/source/top/top-100.1.2/libtop.c
    for (addr = MACH_VM_MIN_ADDRESS;; addr += size) {
        prev_addr = addr;
        info_count = VM_REGION_TOP_INFO_COUNT;  // reset before each call

        kr = mach_vm_region(
            task,
            &addr,
            &size,
            VM_REGION_TOP_INFO,
            (vm_region_info_t)&info,
            &info_count,
            &object_name
        );
        if (kr == KERN_INVALID_ADDRESS) {
            // Done iterating VM regions.
            break;
        }
        else if (kr != KERN_SUCCESS) {
            psutil_runtime_error(
                "mach_vm_region(VM_REGION_TOP_INFO) syscall failed"
            );
            mach_port_deallocate(mach_task_self(), task);
            return NULL;
        }

        if (size == 0 || addr < prev_addr) {
            psutil_debug("prevent infinite loop");
            break;
        }

        if (psutil_in_shared_region(addr, cpu_type)
            && info.share_mode != SM_PRIVATE)
        {
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
PyObject *
psutil_proc_threads(PyObject *self, PyObject *args) {
    pid_t pid;
    kern_return_t kr;
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

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    if (psutil_task_for_pid(pid, &task) != 0)
        goto error;

    // Get basic task info (optional, ignored if access denied)
    mach_msg_type_number_t info_count = TASK_BASIC_INFO_COUNT;
    kr = task_info(
        task, TASK_BASIC_INFO, (task_info_t)&tasks_info, &info_count
    );
    if (kr != KERN_SUCCESS) {
        if (kr == KERN_INVALID_ARGUMENT) {
            psutil_oserror_ad("task_info(TASK_BASIC_INFO)");
        }
        else {
            // otherwise throw a runtime error with appropriate error code
            psutil_runtime_error("task_info(TASK_BASIC_INFO) syscall failed");
        }
        goto error;
    }

    kr = task_threads(task, &thread_list, &thread_count);
    if (kr != KERN_SUCCESS) {
        psutil_runtime_error("task_threads() syscall failed");
        goto error;
    }

    for (j = 0; j < thread_count; j++) {
        thread_info_count = THREAD_INFO_MAX;
        kr = thread_info(
            thread_list[j],
            THREAD_BASIC_INFO,
            (thread_info_t)thinfo_basic,
            &thread_info_count
        );
        if (kr != KERN_SUCCESS) {
            psutil_runtime_error(
                "thread_info(THREAD_BASIC_INFO) syscall failed"
            );
            goto error;
        }

        basic_info_th = (thread_basic_info_t)thinfo_basic;
        py_tuple = Py_BuildValue(
            "Iff",
            j + 1,
            basic_info_th->user_time.seconds
                + (float)basic_info_th->user_time.microseconds / 1000000.0,
            basic_info_th->system_time.seconds
                + (float)basic_info_th->system_time.microseconds / 1000000.0
        );
        if (!py_tuple)
            goto error;
        if (PyList_Append(py_retlist, py_tuple))
            goto error;
        Py_CLEAR(py_tuple);
    }

    if (thread_list != NULL) {
        vm_deallocate(
            mach_task_self(),
            (vm_address_t)thread_list,
            thread_count * sizeof(thread_act_t)
        );
    }
    if (task != MACH_PORT_NULL) {
        mach_port_deallocate(mach_task_self(), task);
    }

    return py_retlist;

error:
    Py_XDECREF(py_tuple);
    Py_XDECREF(py_retlist);

    if (thread_list != NULL) {
        vm_deallocate(
            mach_task_self(),
            (vm_address_t)thread_list,
            thread_count * sizeof(thread_act_t)
        );
    }
    if (task != MACH_PORT_NULL) {
        mach_port_deallocate(mach_task_self(), task);
    }

    return NULL;
}


/*
 * Return process open files as a Python tuple.
 * See lsof source code:
 * https://github.com/apple-opensource/lsof/blob/28/lsof/dialects/darwin/libproc/dproc.c#L342
 * ...and /usr/include/sys/proc_info.h
 */
PyObject *
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

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
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
            nb = proc_pidfdinfo(
                (pid_t)pid,
                fdp_pointer->proc_fd,
                PROC_PIDFDVNODEPATHINFO,
                &vi,
                sizeof(vi)
            );

            // --- errors checking
            if ((nb <= 0) || nb < sizeof(vi)) {
                if ((errno == ENOENT) || (errno == EBADF)) {
                    // no such file or directory or bad file descriptor;
                    // let's assume the file has been closed or removed
                    continue;
                }
                else {
                    psutil_raise_for_pid(
                        pid, "proc_pidinfo(PROC_PIDFDVNODEPATHINFO)"
                    );
                    goto error;
                }
            }
            // --- /errors checking

            // --- construct python list
            py_path = PyUnicode_DecodeFSDefault(vi.pvip.vip_path);
            if (!py_path)
                goto error;
            py_tuple = Py_BuildValue(
                "(Oi)", py_path, (int)fdp_pointer->proc_fd
            );
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
 * See lsof source code:
 * https://github.com/apple-opensource/lsof/blob/28/lsof/dialects/darwin/libproc/dproc.c#L342
 * ...and /usr/include/sys/proc_info.h
 */
PyObject *
psutil_proc_net_connections(PyObject *self, PyObject *args) {
    pid_t pid;
    int num_fds;
    int i;
    unsigned long nb;
    struct proc_fdinfo *fds_pointer = NULL;
    struct proc_fdinfo *fdp_pointer;
    struct socket_fdinfo si;
    const char *ntopret;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_tuple = NULL;
    PyObject *py_laddr = NULL;
    PyObject *py_raddr = NULL;
    PyObject *py_af_filter = NULL;
    PyObject *py_type_filter = NULL;

    if (py_retlist == NULL)
        return NULL;

    if (!PyArg_ParseTuple(
            args, _Py_PARSE_PID "OO", &pid, &py_af_filter, &py_type_filter
        ))
    {
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
            nb = proc_pidfdinfo(
                pid,
                fdp_pointer->proc_fd,
                PROC_PIDFDSOCKETINFO,
                &si,
                sizeof(si)
            );

            // --- errors checking
            if ((nb <= 0) || (nb < sizeof(si))) {
                if (errno == EBADF) {
                    // let's assume socket has been closed
                    psutil_debug(
                        "proc_pidfdinfo(PROC_PIDFDSOCKETINFO) -> "
                        "EBADF (ignored)"
                    );
                    continue;
                }
                else if (errno == EOPNOTSUPP) {
                    // may happen sometimes, see:
                    // https://github.com/giampaolo/psutil/issues/1512
                    psutil_debug(
                        "proc_pidfdinfo(PROC_PIDFDSOCKETINFO) -> "
                        "EOPNOTSUPP (ignored)"
                    );
                    continue;
                }
                else {
                    psutil_raise_for_pid(
                        pid, "proc_pidinfo(PROC_PIDFDSOCKETINFO)"
                    );
                    goto error;
                }
            }
            // --- /errors checking

            //
            int fd, family, type, lport, rport, state;
            char lip[INET6_ADDRSTRLEN], rip[INET6_ADDRSTRLEN];
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
            if (inseq == -1)
                goto error;
            if (inseq == 0)
                continue;

            py_type = PyLong_FromLong((long)type);
            inseq = PySequence_Contains(py_type_filter, py_type);
            Py_DECREF(py_type);
            if (inseq == -1)
                goto error;
            if (inseq == 0)
                continue;

            if ((family == AF_INET) || (family == AF_INET6)) {
                if (family == AF_INET) {
                    ntopret = inet_ntop(
                        AF_INET,
                        &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_laddr.ina_46
                             .i46a_addr4,
                        lip,
                        sizeof(lip)
                    );
                    if (!ntopret) {
                        psutil_oserror_wsyscall("inet_ntop()");
                        goto error;
                    }
                    ntopret = inet_ntop(
                        AF_INET,
                        &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_faddr.ina_46
                             .i46a_addr4,
                        rip,
                        sizeof(rip)
                    );
                    if (!ntopret) {
                        psutil_oserror_wsyscall("inet_ntop()");
                        goto error;
                    }
                }
                else {
                    ntopret = inet_ntop(
                        AF_INET6,
                        &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_laddr.ina_6,
                        lip,
                        sizeof(lip)
                    );
                    if (!ntopret) {
                        psutil_oserror_wsyscall("inet_ntop()");
                        goto error;
                    }
                    ntopret = inet_ntop(
                        AF_INET6,
                        &si.psi.soi_proto.pri_tcp.tcpsi_ini.insi_faddr.ina_6,
                        rip,
                        sizeof(rip)
                    );
                    if (!ntopret) {
                        psutil_oserror_wsyscall("inet_ntop()");
                        goto error;
                    }
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

                py_tuple = Py_BuildValue(
                    "(iiiNNi)", fd, family, type, py_laddr, py_raddr, state
                );
                if (!py_tuple)
                    goto error;
                if (PyList_Append(py_retlist, py_tuple))
                    goto error;
                Py_CLEAR(py_tuple);
            }
            else if (family == AF_UNIX) {
                py_laddr = PyUnicode_DecodeFSDefault(
                    si.psi.soi_proto.pri_un.unsi_addr.ua_sun.sun_path
                );
                if (!py_laddr)
                    goto error;
                py_raddr = PyUnicode_DecodeFSDefault(
                    si.psi.soi_proto.pri_un.unsi_caddr.ua_sun.sun_path
                );
                if (!py_raddr)
                    goto error;

                py_tuple = Py_BuildValue(
                    "(iiiOOi)",
                    fd,
                    family,
                    type,
                    py_laddr,
                    py_raddr,
                    PSUTIL_CONN_NONE
                );
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
PyObject *
psutil_proc_num_fds(PyObject *self, PyObject *args) {
    pid_t pid;
    int num_fds;
    struct proc_fdinfo *fds_pointer;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    fds_pointer = psutil_proc_list_fds(pid, &num_fds);
    if (fds_pointer == NULL)
        return NULL;

    free(fds_pointer);
    return Py_BuildValue("i", num_fds);
}


// return process args as a python list
PyObject *
psutil_proc_cmdline(PyObject *self, PyObject *args) {
    pid_t pid;
    int nargs;
    size_t len;
    char *procargs = NULL;
    char *arg_ptr;
    char *arg_end;
    char *curr_arg;
    size_t argmax;
    PyObject *py_retlist = PyList_New(0);
    PyObject *py_arg = NULL;

    if (py_retlist == NULL)
        return NULL;
    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        goto error;

    // special case for PID 0 (kernel_task) where cmdline cannot be fetched
    if (pid == 0)
        return py_retlist;

    // read argmax and allocate memory for argument space.
    argmax = psutil_sysctl_argmax();
    if (argmax == 0)
        goto error;

    procargs = (char *)malloc(argmax);
    if (NULL == procargs) {
        PyErr_NoMemory();
        goto error;
    }

    if (psutil_sysctl_procargs(pid, procargs, &argmax) != 0)
        goto error;

    arg_end = &procargs[argmax];
    // copy the number of arguments to nargs
    memcpy(&nargs, procargs, sizeof(nargs));

    arg_ptr = procargs + sizeof(nargs);
    len = strlen(arg_ptr);
    arg_ptr += len + 1;

    if (arg_ptr == arg_end) {
        free(procargs);
        return py_retlist;
    }

    // skip ahead to the first argument
    for (; arg_ptr < arg_end; arg_ptr++) {
        if (*arg_ptr != '\0')
            break;
    }

    // iterate through arguments
    curr_arg = arg_ptr;
    while (arg_ptr < arg_end && nargs > 0) {
        if (*arg_ptr++ == '\0') {
            py_arg = PyUnicode_DecodeFSDefault(curr_arg);
            if (!py_arg)
                goto error;
            if (PyList_Append(py_retlist, py_arg))
                goto error;
            Py_DECREF(py_arg);
            // iterate to next arg and decrement # of args
            curr_arg = arg_ptr;
            nargs--;
        }
    }

    free(procargs);
    return py_retlist;

error:
    Py_XDECREF(py_arg);
    Py_XDECREF(py_retlist);
    if (procargs != NULL)
        free(procargs);
    return NULL;
}


// Return process environment as a python string.
// On Big Sur this function returns an empty string unless:
// * kernel is DEVELOPMENT || DEBUG
// * target process is same as current_proc()
// * target process is not cs_restricted
// * SIP is off
// * caller has an entitlement
// See:
// https://github.com/apple/darwin-xnu/blob/2ff845c2e033bd0ff64b5b6aa6063a1f8f65aa32/bsd/kern/kern_sysctl.c#L1315-L1321
PyObject *
psutil_proc_environ(PyObject *self, PyObject *args) {
    pid_t pid;
    int nargs;
    char *procargs = NULL;
    char *procenv = NULL;
    char *arg_ptr;
    char *arg_end;
    char *env_start;
    size_t argmax;
    size_t env_len;
    PyObject *py_ret = NULL;

    if (!PyArg_ParseTuple(args, _Py_PARSE_PID, &pid))
        return NULL;

    // PID 0 (kernel_task) has no cmdline.
    if (pid == 0)
        goto empty;

    // Allocate buffer for process args.
    argmax = psutil_sysctl_argmax();
    if (argmax == 0)
        goto error;

    procargs = (char *)malloc(argmax);
    if (procargs == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    if (psutil_sysctl_procargs(pid, procargs, &argmax) != 0)
        goto error;

    arg_end = procargs + argmax;

    // Copy nargs.
    memcpy(&nargs, procargs, sizeof(nargs));

    // skip executable path
    arg_ptr = procargs + sizeof(nargs);
    arg_ptr = memchr(arg_ptr, '\0', arg_end - arg_ptr);
    if (arg_ptr == NULL || arg_ptr >= arg_end)
        goto empty;

    // Skip null bytes until first argument.
    while (arg_ptr < arg_end && *arg_ptr == '\0')
        arg_ptr++;

    // Skip arguments.
    while (arg_ptr < arg_end && nargs > 0) {
        if (*arg_ptr++ == '\0')
            nargs--;
    }

    if (arg_ptr >= arg_end)
        goto empty;

    env_start = arg_ptr;

    // Compute maximum possible environment length.
    env_len = (size_t)(arg_end - env_start);
    if (env_len == 0)
        goto empty;

    procenv = (char *)calloc(1, env_len);
    if (procenv == NULL) {
        PyErr_NoMemory();
        goto error;
    }

    while (arg_ptr < arg_end && *arg_ptr != '\0') {
        // Find the next NUL terminator.
        size_t rem = (size_t)(arg_end - arg_ptr);
        char *s = memchr(arg_ptr, '\0', rem);
        if (s == NULL)
            break;

        size_t copy_len = (size_t)(s - arg_ptr);
        size_t offset = (size_t)(arg_ptr - env_start);
        if (offset + copy_len >= env_len)
            break;  // prevent overflow.

        memcpy(procenv + offset, arg_ptr, copy_len);
        arg_ptr = s + 1;
    }

    size_t used = (size_t)(arg_ptr - env_start);
    if (used >= env_len)
        used = env_len - 1;

    py_ret = PyUnicode_DecodeFSDefaultAndSize(procenv, (Py_ssize_t)used);
    if (py_ret == NULL) {
        procargs = NULL;  // don't double free; see psutil issue #926.
        goto error;
    }

    free(procargs);
    free(procenv);
    return py_ret;

empty:
    psutil_debug("set environ to empty");
    if (procargs != NULL)
        free(procargs);
    return Py_BuildValue("s", "");

error:
    Py_XDECREF(py_ret);
    if (procargs != NULL)
        free(procargs);
    if (procenv != NULL)
        free(procenv);
    return NULL;
}
