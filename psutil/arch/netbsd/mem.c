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
    uint64_t swap_total = 0;
    uint64_t swap_free = 0;
    uint64_t swap_used = 0;
    uint64_t sin = 0;
    uint64_t sout = 0;
    double percent = 0.0;
    struct swapent *swdev = NULL;
    int nswap, i;
    long pagesize = psutil_getpagesize();
    PyObject *dict = PyDict_New();

    if (dict == NULL)
        return NULL;

    nswap = swapctl(SWAP_NSWAP, 0, 0);
    if (nswap == 0)  // this means there's no swap partition
        goto done;

    swdev = calloc(nswap, sizeof(*swdev));
    if (swdev == NULL) {
        psutil_oserror();
        goto error;
    }

    if (swapctl(SWAP_STATS, swdev, nswap) == -1) {
        psutil_oserror();
        goto error;
    }

    // Total things up.
    for (i = 0; i < nswap; i++) {
        if (swdev[i].se_flags & SWF_ENABLE) {
            swap_total += (uint64_t)swdev[i].se_nblks * DEV_BSIZE;
            swap_free += (uint64_t)(swdev[i].se_nblks - swdev[i].se_inuse)
                         * DEV_BSIZE;
        }
    }

    // Get swap in/out
    struct uvmexp_sysctl uv;
    int mib[] = {CTL_VM, VM_UVMEXP2};
    if (psutil_sysctl(mib, 2, &uv, sizeof(uv)) != 0)
        goto error;

    free(swdev);

    sin = (uint64_t)uv.pgswapin * pagesize;
    sout = (uint64_t)uv.pgswapout * pagesize;
    swap_used = swap_total - swap_free;
    percent = psutil_usage_percent((double)swap_used, (double)swap_total, 1);

done:
    if (!(pydict_add(dict, "total", "K", swap_total)
          | pydict_add(dict, "used", "K", swap_used)
          | pydict_add(dict, "free", "K", swap_free)
          | pydict_add(dict, "percent", "d", percent)
          | pydict_add(dict, "sin", "K", sin)
          | pydict_add(dict, "sout", "K", sout)))
        goto error;

    return dict;

error:
    Py_DECREF(dict);
    free(swdev);
    return NULL;
}
