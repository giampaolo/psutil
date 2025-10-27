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
#include <sys/swap.h>
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


PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    uint64_t swap_total, swap_free;
    struct swapent *swdev;
    int nswap, i;
    long pagesize = psutil_getpagesize();

    nswap = swapctl(SWAP_NSWAP, 0, 0);
    if (nswap == 0) {
        // This means there's no swap partition.
        return Py_BuildValue("(iiiii)", 0, 0, 0, 0, 0);
    }

    swdev = calloc(nswap, sizeof(*swdev));
    if (swdev == NULL) {
        psutil_oserror();
        return NULL;
    }

    if (swapctl(SWAP_STATS, swdev, nswap) == -1) {
        psutil_oserror();
        goto error;
    }

    // Total things up.
    swap_total = swap_free = 0;
    for (i = 0; i < nswap; i++) {
        if (swdev[i].se_flags & SWF_ENABLE) {
            swap_total += (uint64_t)swdev[i].se_nblks * DEV_BSIZE;
            swap_free += (uint64_t)(swdev[i].se_nblks - swdev[i].se_inuse)
                         * DEV_BSIZE;
        }
    }
    free(swdev);

    // Get swap in/out
    unsigned int total;
    size_t size = sizeof(total);
    struct uvmexp_sysctl uv;
    int mib[] = {CTL_VM, VM_UVMEXP2};
    if (psutil_sysctl(mib, 2, &uv, sizeof(uv)) != 0)
        goto error;

    return Py_BuildValue(
        "(LLLll)",
        swap_total,
        (swap_total - swap_free),
        swap_free,
        (long)uv.pgswapin * pagesize,  // swap in
        (long)uv.pgswapout * pagesize  // swap out
    );

error:
    free(swdev);
    return NULL;
}
