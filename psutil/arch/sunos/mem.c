/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <kstat.h>
#include <sys/sysinfo.h>

#include "../../arch/all/init.h"


PyObject *
psutil_swap_mem(PyObject *self, PyObject *args) {
    // XXX (arghhh!)
    // total/free swap mem: commented out as for some reason I can't
    // manage to get the same results shown by "swap -l", despite the
    // code below is exactly the same as:
    // http://cvs.opensolaris.org/source/xref/onnv/onnv-gate/usr/src/
    //    cmd/swap/swap.c
    // We're going to parse "swap -l" output from Python (sigh!)

    /*
        struct swaptable     *st;
        struct swapent    *swapent;
        int    i;
        struct stat64 statbuf;
        char *path;
        char fullpath[MAXPATHLEN+1];
        int    num;

        if ((num = swapctl(SC_GETNSWP, NULL)) == -1) {
            psutil_oserror();
            return NULL;
        }
        if (num == 0) {
            psutil_runtime_error("no swap devices configured");
            return NULL;
        }
        if ((st = malloc(num * sizeof(swapent_t) + sizeof (int))) == NULL) {
            psutil_runtime_error("malloc failed");
            return NULL;
        }
        if ((path = malloc(num * MAXPATHLEN)) == NULL) {
            psutil_runtime_error("malloc failed");
            return NULL;
        }
        swapent = st->swt_ent;
        for (i = 0; i < num; i++, swapent++) {
            swapent->ste_path = path;
            path += MAXPATHLEN;
        }
        st->swt_n = num;
        if ((num = swapctl(SC_LIST, st)) == -1) {
            psutil_oserror();
            return NULL;
        }

        swapent = st->swt_ent;
        long t = 0, f = 0;
        for (i = 0; i < num; i++, swapent++) {
            int diskblks_per_page =(int)(sysconf(_SC_PAGESIZE) >> DEV_BSHIFT);
            t += (long)swapent->ste_pages;
            f += (long)swapent->ste_free;
        }

        free(st);
        return Py_BuildValue("(kk)", t, f);
    */

    kstat_ctl_t *kc;
    kstat_t *k;
    cpu_stat_t *cpu;
    int cpu_count = 0;
    int flag = 0;
    uint_t sin = 0;
    uint_t sout = 0;

    kc = kstat_open();
    if (kc == NULL)
        return psutil_oserror();
    ;

    k = kc->kc_chain;
    while (k != NULL) {
        if ((strncmp(k->ks_name, "cpu_stat", 8) == 0)
            && (kstat_read(kc, k, NULL) != -1))
        {
            flag = 1;
            cpu = (cpu_stat_t *)k->ks_data;
            sin += cpu->cpu_vminfo.pgswapin;  // num pages swapped in
            sout += cpu->cpu_vminfo.pgswapout;  // num pages swapped out
        }
        cpu_count += 1;
        k = k->ks_next;
    }
    kstat_close(kc);
    if (!flag) {
        psutil_runtime_error("no swap device was found");
        return NULL;
    }
    return Py_BuildValue("(II)", sin, sout);
}
