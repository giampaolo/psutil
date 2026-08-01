/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/types.h>


#define PSUTIL_KPT2DOUBLE(t) (t##_sec + t##_usec / 1000000.0)

#ifdef PSUTIL_NETBSD
// Same states as the kernel's P_ZOMBIE(), which we can't use here:
// it reads p_stat, which in kinfo_proc2 is the LWP status. The
// process one is p_realstat.
#define PSUTIL_KINFO_ZOMBIE(kp)                            \
    ((kp).p_realstat == SZOMB || (kp).p_realstat == SDYING \
     || (kp).p_realstat == SDEAD)
#elif defined(PSUTIL_OPENBSD)
// According to /usr/include/sys/proc.h SZOMB is unused.
// test_zombie_process() shows that SDEAD is the right equivalent.
#define PSUTIL_KINFO_ZOMBIE(kp) ((kp).p_stat == SZOMB || (kp).p_stat == SDEAD)
#endif

#if defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
#define PSUTIL_HASNT_KINFO_GETFILE
struct kinfo_file *kinfo_getfile(pid_t pid, int *cnt);
#endif

int psutil_kinfo_proc(pid_t pid, void *proc);
void convert_kvm_err(const char *syscall, char *errbuf);
int is_zombie(size_t pid);

PyObject *psutil_boot_time(PyObject *self, PyObject *args);
PyObject *psutil_cpu_count_logical(PyObject *self, PyObject *args);
PyObject *psutil_cpu_times(PyObject *self, PyObject *args);
PyObject *psutil_disk_partitions(PyObject *self, PyObject *args);
PyObject *psutil_heap_info(PyObject *self, PyObject *args);
PyObject *psutil_heap_trim(PyObject *self, PyObject *args);
PyObject *psutil_net_io_counters(PyObject *self, PyObject *args);
PyObject *psutil_proc_environ(PyObject *self, PyObject *args);
PyObject *psutil_proc_name(PyObject *self, PyObject *args);
PyObject *psutil_proc_oneshot_kinfo(PyObject *self, PyObject *args);
PyObject *psutil_proc_open_files(PyObject *self, PyObject *args);
#if defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
PyObject *psutil_swap_mem(PyObject *self, PyObject *args);
#endif
