/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdio.h>
#include <stdint.h>
#include <stdlib.h>

#include "../../_psutil_common.h"

#define MAX_INFO 512

uint64_t
parse_and_continue(char **start, char *end) {
    uint64_t val;

    while (**start != ' ')
        (*start)++;
    val = strtoull(*start, &end, 10);
    while (**start != '\n')
        (*start)++;
    return val;
}

PyObject *
psutil_gnu_meminfo(PyObject *self, PyObject *args) {
    uint64_t dummy __attribute__((unused));
    int32_t cnt;
    char info[MAX_INFO] = {0};
    char *p = &info[0];
    char *end = &info[MAX_INFO-1];
    FILE *meminfo = fopen("/proc/meminfo", "r");
    uint64_t totalram, freeram, bufferram, sharedram, totalswap, freeswap;
    cnt = fread(info, MAX_INFO, 1, meminfo);
    if (!cnt) {
        fclose(meminfo);
        return PyErr_SetFromErrno(PyExc_OSError);
    }
    fclose(meminfo);

    totalram = parse_and_continue(&p, end);	// MemTotal
    freeram = parse_and_continue(&p, end);	// MemFree
    bufferram = parse_and_continue(&p, end);	// Buffers
    sharedram = parse_and_continue(&p, end);	// Cached
    dummy = parse_and_continue(&p, end);	// Active
    dummy = parse_and_continue(&p, end);	// Inactive
    dummy = parse_and_continue(&p, end);	// Mlocked
    totalswap = parse_and_continue(&p, end);	// SwapTotal
    freeswap = parse_and_continue(&p, end);	// SwapFree

    return Py_BuildValue(
        "(kkkkkkI)",
        totalram,  // total
        freeram,   // free
        bufferram, // buffer
        sharedram, // shared
        totalswap, // swap tot
        freeswap,  // swap free
        1024  // multiplier (kB)
    );
}
