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
// https://github.com/satterly/zabbix-stats/blob/master/src/libs/zbxsysinfo/netbsd/memory.c
PyObject *
psutil_virtual_mem(PyObject *self, PyObject *args) {
    struct uvmexp_sysctl uv;
    int mib[] = {CTL_VM, VM_UVMEXP2};
    unsigned long long total, free, active, inactive, wired, cached;
    unsigned long long used, avail;
    double percent;
    PyObject *dict = PyDict_New();

    if (dict == NULL)
        return NULL;

    if (psutil_sysctl(mib, 2, &uv, sizeof(uv)) != 0)
        goto error;

    total = (unsigned long long)uv.npages << uv.pageshift;
    free = (unsigned long long)uv.free << uv.pageshift;
    active = (unsigned long long)uv.active << uv.pageshift;
    inactive = (unsigned long long)uv.inactive << uv.pageshift;
    wired = (unsigned long long)uv.wired << uv.pageshift;

    // Note: zabbix does not include anonpages, but that doesn't match
    // the "Cached" value in /proc/meminfo.
    // https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/
    //   zbxsysinfo/netbsd/memory.c#L182
    cached = (unsigned long long)(uv.filepages + uv.execpages + uv.anonpages)
             << uv.pageshift;

    // Before avail was calculated as (inactive + cached + free), same
    // as zabbix, but it turned out it could exceed total (see #2233),
    // so zabbix seems to be wrong. Htop calculates it differently, and
    // the used value seem more realistic, so let's match htop.
    // https://github.com/htop-dev/htop/blob/e7f447b/netbsd/NetBSDProcessList.c#L162
    // https://github.com/zabbix/zabbix/blob/af5e0f8/src/libs/zbxsysinfo/netbsd/memory.c#L135
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
          | pydict_add(dict, "wired", "K", wired)
          | pydict_add(dict, "cached", "K", cached)))
        goto error;

    return dict;

error:
    Py_DECREF(dict);
    return NULL;
}
