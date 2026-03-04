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
    int64_t total_physmem;
    int uvmexp_mib[] = {CTL_VM, VM_UVMEXP};
    int bcstats_mib[] = {CTL_VFS, VFS_GENERIC, VFS_BCACHESTAT};
    int physmem_mib[] = {CTL_HW, HW_PHYSMEM64};
    int vmmeter_mib[] = {CTL_VM, VM_METER};
    size_t size;
    struct uvmexp uvmexp;
    struct bcachestats bcstats;
    struct vmtotal vmdata;
    long pagesize = psutil_getpagesize();

    size = sizeof(total_physmem);
    if (psutil_sysctl(physmem_mib, 2, &total_physmem, size) != 0)
        return NULL;

    size = sizeof(uvmexp);
    if (psutil_sysctl(uvmexp_mib, 2, &uvmexp, size) != 0)
        return NULL;

    size = sizeof(bcstats);
    if (psutil_sysctl(bcstats_mib, 3, &bcstats, size) != 0)
        return NULL;

    size = sizeof(vmdata);
    if (psutil_sysctl(vmmeter_mib, 2, &vmdata, size) != 0)
        return NULL;

    return Py_BuildValue(
        "KKKKKKKK",
        // Note: many programs calculate total memory as
        // "uvmexp.npages * pagesize" but this is incorrect and does not
        // match "sysctl | grep hw.physmem".
        (unsigned long long)total_physmem,
        (unsigned long long)uvmexp.free * pagesize,
        (unsigned long long)uvmexp.active * pagesize,
        (unsigned long long)uvmexp.inactive * pagesize,
        (unsigned long long)uvmexp.wired * pagesize,
        // this is how "top" determines it
        (unsigned long long)bcstats.numbufpages * pagesize,  // cached
        (unsigned long long)0,  // buffers
        (unsigned long long)vmdata.t_vmshr + vmdata.t_rmshr  // shared
    );
}
