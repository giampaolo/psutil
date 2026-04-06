/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

// Memory related functions. Original code was refactored and moved from
// psutil/arch/netbsd/specific.c in 2023 (and was moved in there previously
// already) from cset 84219ad. For reference, here's the git history with
// original(ish) implementations:
// - virtual memory: 0749a69c01b374ca3e2180aaafc3c95e3b2d91b9 (Oct 2016)
// - swap memory: 312442ad2a5b5d0c608476c5ab3e267735c3bc59 (Jan 2016)

#include <Python.h>
#include <stdio.h>
#include <string.h>
#include <sys/sysctl.h>
#include <sys/vmmeter.h>
#include <uvm/uvm_extern.h>

#include "../../arch/all/init.h"


/*
 * Virtual memory stats for NetBSD using VM_UVMEXP2 and VM_METER.
 *
 * Sources:
 *   cached  = (filepages + execpages + anonpages) << pageshift  [btop]
 *   buffers = filepages << pageshift  [file cache * excl. exec]
 *   shared  = (t_vmshr + t_rmshr) * pagesize [vmtotal]
 *   used    =  (active + wired) << pageshift [top/btop]
 *   avail   = total - used [htop/btop]
 */
PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    struct uvmexp_sysctl uv;
    struct vmtotal vmdata;
    int uvmexp_mib[] = {CTL_VM, VM_UVMEXP2};
    int vmmeter_mib[] = {CTL_VM, VM_METER};
    unsigned long long total, free, active, inactive, wired, cached;
    unsigned long long buffers, shared, used, avail;
    double percent;
    long pagesize = psutil_getpagesize();
    PyObject *dict = PyDict_New();

    if (dict == NULL)
        return NULL;

    if (psutil_sysctl(uvmexp_mib, 2, &uv, sizeof(uv)) != 0)
        goto error;
    if (psutil_sysctl(vmmeter_mib, 2, &vmdata, sizeof(vmdata)) != 0)
        goto error;

    // https://github.com/aristocratos/btop/blob/main/src/netbsd/btop_collect.cpp#L723
    total = (unsigned long long)uv.npages << uv.pageshift;
    free = (unsigned long long)uv.free << uv.pageshift;
    active = (unsigned long long)uv.active << uv.pageshift;
    inactive = (unsigned long long)uv.inactive << uv.pageshift;
    wired = (unsigned long long)uv.wired << uv.pageshift;
    shared = (unsigned long long)(vmdata.t_vmshr + vmdata.t_rmshr) * pagesize;
    cached = (unsigned long long)(uv.filepages + uv.execpages + uv.anonpages)
             << uv.pageshift;

    /*
     * buffers: file-backed pages excluding executable mappings.
     *
     * The source is uvmexp_sysctl.filepages
     * This matches what btop uses on NetBSD:
     *   cached = (filepages + execpages + anonpages) * pagesize
     * and filepages alone is the file cache excluding exec mappings,
     * which is the closest accurate equivalent to Linux "Buffers".
     */
    buffers = (unsigned long long)uv.filepages << uv.pageshift;

    used = active + wired;
    avail = total - used;
    percent = psutil_usage_percent((double)(total - avail), (double)total, 1);

    if (!(pydict_add(dict, "total", "K", total)
          | pydict_add(dict, "available", "K", avail)
          | pydict_add(dict, "percent", "d", percent)
          | pydict_add(dict, "used", "K", used)
          | pydict_add(dict, "free", "K", free)
          | pydict_add(dict, "active", "K", active)
          | pydict_add(dict, "inactive", "K", inactive)
          | pydict_add(dict, "buffers", "K", buffers)
          | pydict_add(dict, "wired", "K", wired)
          | pydict_add(dict, "cached", "K", cached)
          | pydict_add(dict, "shared", "K", shared)))
        goto error;

    return dict;

error:
    Py_DECREF(dict);
    return NULL;
}
