/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysinfo.h>

#include "../../_psutil_common.h"


PyObject *
psutil_linux_sysinfo(PyObject *self, PyObject *args) {
    struct sysinfo info;

    if (sysinfo(&info) != 0)
        return PyErr_SetFromErrno(PyExc_OSError);
    // note: boot time might also be determined from here
    return Py_BuildValue(
        "(kkkkkkI)",
        info.totalram,  // total
        info.freeram,  // free
        info.bufferram, // buffer
        info.sharedram, // shared
        info.totalswap, // swap tot
        info.freeswap,  // swap free
        info.mem_unit  // multiplier
    );
}
