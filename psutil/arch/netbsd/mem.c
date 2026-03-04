/*
 * Copyright (c) 2009, Giampaolo Rodola', Landry Breuil.
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

/*
Memory related functions. Original code was refactored and moved from
psutil/arch/netbsd/specific.c in 2023 (and was moved in there previously
already) from cset 84219ad. For reference, here's the git history with
original(ish) implementations:
- virtual memory: 0749a69c01b374ca3e2180aaafc3c95e3b2d91b9 (Oct 2016)
- swap memory: 312442ad2a5b5d0c608476c5ab3e267735c3bc59 (Jan 2016)
*/

#include <Python.h>
#include <sys/sysctl.h>
#include <uvm/uvm_extern.h>

#include "../../arch/all/init.h"


// Virtual memory stats, taken from:
// https://github.com/satterly/zabbix-stats/blob/master/src/libs/zbxsysinfo/
//     netbsd/memory.c
PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    size_t size;
    struct uvmexp_sysctl uv;
    int mib[] = {CTL_VM, VM_UVMEXP2};
    long long cached;

    if (psutil_sysctl(mib, 2, &uv, sizeof(uv)) != 0)
        return NULL;

    // Note: zabbix does not include anonpages, but that doesn't match the
    // "Cached" value in /proc/meminfo.
    // https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/zbxsysinfo/netbsd/memory.c#L182
    cached = (uv.filepages + uv.execpages + uv.anonpages) << uv.pageshift;
    return Py_BuildValue(
        "LLLLLL",
        (long long)uv.npages << uv.pageshift,  // total
        (long long)uv.free << uv.pageshift,  // free
        (long long)uv.active << uv.pageshift,  // active
        (long long)uv.inactive << uv.pageshift,  // inactive
        (long long)uv.wired << uv.pageshift,  // wired
        cached  // cached
    );
}
