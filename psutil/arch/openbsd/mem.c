/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <sys/mount.h>
#include <sys/param.h>

#include "../../arch/all/init.h"


PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    int64_t _total;
    unsigned long long free, active, inactive, wired, cached, shared;
    unsigned long long total, avail, used;
    double percent;
    int uvmexp_mib[] = {CTL_VM, VM_UVMEXP};
    int bcstats_mib[] = {CTL_VFS, VFS_GENERIC, VFS_BCACHESTAT};
    int physmem_mib[] = {CTL_HW, HW_PHYSMEM64};
    int vmmeter_mib[] = {CTL_VM, VM_METER};
    struct uvmexp uvmexp;
    struct bcachestats bcstats;
    struct vmtotal vmdata;
    long pagesize = psutil_getpagesize();
    PyObject *dict = PyDict_New();

    if (dict == NULL)
        return NULL;

    // Note: many programs calculate total memory as "uvmexp.npages *
    // pagesize" but this is incorrect and does not match "sysctl |
    // grep hw.physmem".
    if (psutil_sysctl(physmem_mib, 2, &_total, sizeof(_total)) != 0)
        goto error;
    if (psutil_sysctl(uvmexp_mib, 2, &uvmexp, sizeof(uvmexp)) != 0)
        goto error;
    if (psutil_sysctl(bcstats_mib, 3, &bcstats, sizeof(bcstats)) != 0)
        goto error;
    if (psutil_sysctl(vmmeter_mib, 2, &vmdata, sizeof(vmdata)) != 0)
        goto error;

    total = (unsigned long long)_total;
    free = (unsigned long long)uvmexp.free * pagesize;
    active = (unsigned long long)uvmexp.active * pagesize;
    inactive = (unsigned long long)uvmexp.inactive * pagesize;
    wired = (unsigned long long)uvmexp.wired * pagesize;
    shared = (unsigned long long)(vmdata.t_vmshr + vmdata.t_rmshr) * pagesize;

    // this is how "top" determines cached mem
    cached = (unsigned long long)bcstats.numbufpages * pagesize;

    // matches freebsd-memory CLI:
    // * https://people.freebsd.org/~rse/dist/freebsd-memory
    // * https://www.cyberciti.biz/files/scripts/freebsd-memory.pl.txt
    // matches zabbix:
    // * https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/zbxsysinfo/freebsd/memory.c#L143
    avail = inactive + cached + free;
    used = active + wired + cached;
    percent = psutil_usage_percent((double)(total - avail), (double)total, 1);

    if (!(pydict_add(dict, "total", "K", total)
          | pydict_add(dict, "available", "K", avail)
          | pydict_add(dict, "percent", "d", percent)
          | pydict_add(dict, "used", "K", used)
          | pydict_add(dict, "free", "K", free)
          | pydict_add(dict, "active", "K", active)
          | pydict_add(dict, "inactive", "K", inactive)
          | pydict_add(dict, "buffers", "K", 0ULL)
          | pydict_add(dict, "cached", "K", cached)
          | pydict_add(dict, "shared", "K", shared)
          | pydict_add(dict, "wired", "K", wired)))
        goto error;

    return dict;

error:
    Py_DECREF(dict);
    return NULL;
}
