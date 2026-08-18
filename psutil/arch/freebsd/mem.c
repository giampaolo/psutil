/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <kvm.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <vm/vm_param.h>
#include <paths.h>
#include <fcntl.h>

#include "../../arch/all/init.h"

#ifndef _PATH_DEVNULL
#define _PATH_DEVNULL "/dev/null"
#endif


// shorter alias for psutil_sysctlbyname()
static inline int
sbn(const char *name, void *oldp, size_t oldlen) {
    return psutil_sysctlbyname(name, oldp, oldlen);
}


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    unsigned long _total;
    long _buffers;
    unsigned int _active, _inactive, _wired, _cached, _free;
    unsigned long long total, buffers, active, inactive, wired, cached, free;
    unsigned long long avail, used, shared;
    double percent;
    struct vmtotal vm;
    int mib[] = {CTL_VM, VM_METER};
    long pagesize = psutil_getpagesize();
    PyObject *dict = PyDict_New();

    if (dict == NULL)
        return NULL;

    if (sbn("hw.physmem", &_total, sizeof(_total)) != 0)
        goto error;
    if (sbn("vm.stats.vm.v_active_count", &_active, sizeof(_active)) != 0)
        goto error;
    if (sbn("vm.stats.vm.v_inactive_count", &_inactive, sizeof(_inactive))
        != 0)
        goto error;
    if (sbn("vm.stats.vm.v_wire_count", &_wired, sizeof(_wired)) != 0)
        goto error;
    if (sbn("vm.stats.vm.v_free_count", &_free, sizeof(_free)) != 0)
        goto error;
    if (sbn("vfs.bufspace", &_buffers, sizeof(_buffers)) != 0)
        goto error;

    // Optional; ignore error if not avail
    if (sbn("vm.stats.vm.v_cache_count", &_cached, sizeof(_cached)) != 0) {
        PyErr_Clear();
        _cached = 0;
    }

    if (psutil_sysctl(mib, 2, &vm, sizeof(vm)) != 0)
        goto error;

    total = (unsigned long long)_total;
    buffers = (unsigned long long)_buffers;
    free = (unsigned long long)_free * pagesize;
    active = (unsigned long long)_active * pagesize;
    inactive = (unsigned long long)_inactive * pagesize;
    wired = (unsigned long long)_wired * pagesize;
    cached = (unsigned long long)_cached * pagesize;
    shared = (unsigned long long)(vm.t_vmshr + vm.t_rmshr) * pagesize;

    // matches freebsd-memory CLI:
    // * https://people.freebsd.org/~rse/dist/freebsd-memory
    // * https://www.cyberciti.biz/files/scripts/freebsd-memory.pl.txt
    // matches zabbix:
    // * https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/zbxsysinfo/freebsd/memory.c#L143
    avail = (inactive + cached + free);
    used = (active + wired + cached);
    percent = psutil_usage_percent((double)(total - avail), (double)total, 1);

    if (!(pydict_add(dict, "total", "K", total)
          | pydict_add(dict, "available", "K", avail)
          | pydict_add(dict, "percent", "d", percent)
          | pydict_add(dict, "used", "K", used)
          | pydict_add(dict, "free", "K", free)
          | pydict_add(dict, "active", "K", active)
          | pydict_add(dict, "inactive", "K", inactive)
          | pydict_add(dict, "buffers", "K", buffers)
          | pydict_add(dict, "cached", "K", cached)
          | pydict_add(dict, "shared", "K", shared)
          | pydict_add(dict, "wired", "K", wired)))
        goto error;

    return dict;

error:
    Py_DECREF(dict);
    return NULL;
}


PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    // Return swap memory stats (see 'swapinfo' cmdline tool)
    kvm_t *kd;
    struct kvm_swap kvmsw[1];
    unsigned long long total, used, free;
    unsigned int swapin, swapout, nodein, nodeout;
    long pagesize = psutil_getpagesize();
    double percent;
    PyObject *dict = PyDict_New();

    if (dict == NULL)
        return NULL;

    kd = kvm_open(NULL, _PATH_DEVNULL, NULL, O_RDONLY, "kvm_open failed");
    if (kd == NULL) {
        psutil_runtime_error("kvm_open() syscall failed");
        goto error;
    }

    if (kvm_getswapinfo(kd, kvmsw, 1, 0) < 0) {
        kvm_close(kd);
        psutil_runtime_error("kvm_getswapinfo() syscall failed");
        goto error;
    }

    kvm_close(kd);

    if (sbn("vm.stats.vm.v_swapin", &swapin, sizeof(swapin)) != 0)
        goto error;
    if (sbn("vm.stats.vm.v_swapout", &swapout, sizeof(swapout)) != 0)
        goto error;
    if (sbn("vm.stats.vm.v_vnodein", &nodein, sizeof(nodein)) != 0)
        goto error;
    if (sbn("vm.stats.vm.v_vnodeout", &nodeout, sizeof(nodeout)) != 0)
        goto error;

    total = (unsigned long long)kvmsw[0].ksw_total * pagesize;
    used = (unsigned long long)kvmsw[0].ksw_used * pagesize;
    free = (unsigned long long)(kvmsw[0].ksw_total - kvmsw[0].ksw_used)
           * pagesize;
    percent = psutil_usage_percent((double)used, (double)total, 1);

    if (!(pydict_add(dict, "total", "K", total)
          | pydict_add(dict, "used", "K", used)
          | pydict_add(dict, "free", "K", free)
          | pydict_add(dict, "percent", "d", percent)
          | pydict_add(dict, "sin", "I", swapin + swapout)
          | pydict_add(dict, "sout", "I", nodein + nodeout)))
        goto error;

    return dict;

error:
    Py_DECREF(dict);
    return NULL;
}
