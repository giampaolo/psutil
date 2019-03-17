/*
 * Copyright (c) 2017, Arnon Yaari
 * All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/core.h>
#include <stdlib.h>
#include "common.h"

/* psutil_kread() - read from kernel memory */
int
psutil_kread(
    int Kd,             /* kernel memory file descriptor */
    KA_T addr,          /* kernel memory address */
    char *buf,          /* buffer to receive data */
    size_t len) {       /* length to read */
    int br;

    if (lseek64(Kd, (off64_t)addr, L_SET) == (off64_t)-1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return 1;
    }
    br = read(Kd, buf, len);
    if (br == -1) {
        PyErr_SetFromErrno(PyExc_OSError);
        return 1;
    }
    if (br != len) {
        PyErr_SetString(PyExc_RuntimeError,
                        "size mismatch when reading kernel memory fd");
        return 1;
    }
    return 0;
}

struct procentry64 *
psutil_read_process_table(int * num) {
    size_t msz;
    pid32_t pid = 0;
    struct procentry64 *processes = (struct procentry64 *)NULL;
    struct procentry64 *p;
    int Np = 0;          /* number of processes allocated in 'processes' */
    int np = 0;          /* number of processes read into 'processes' */
    int i;               /* number of processes read in current iteration */

    msz = (size_t)(PROCSIZE * PROCINFO_INCR);
    processes = (struct procentry64 *)malloc(msz);
    if (!processes) {
        PyErr_NoMemory();
        return NULL;
    }
    Np = PROCINFO_INCR;
    p = processes;
    while ((i = getprocs64(p, PROCSIZE, (struct fdsinfo64 *)NULL, 0, &pid,
                 PROCINFO_INCR))
    == PROCINFO_INCR) {
        np += PROCINFO_INCR;
        if (np >= Np) {
            msz = (size_t)(PROCSIZE * (Np + PROCINFO_INCR));
            processes = (struct procentry64 *)realloc((char *)processes, msz);
            if (!processes) {
                PyErr_NoMemory();
                return NULL;
            }
            Np += PROCINFO_INCR;
        }
        p = (struct procentry64 *)((char *)processes + (np * PROCSIZE));
    }

    /* add the number of processes read in the last iteration */
    if (i > 0)
        np += i;

    *num = np;
    return processes;
}