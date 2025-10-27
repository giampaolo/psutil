/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

#include <utmpx.h>

#include "../../arch/all/init.h"


PyObject *
psutil_boot_time(PyObject *self, PyObject *args) {
    float boot_time = 0.0;
    struct utmpx *ut;

    UTXENT_MUTEX_LOCK();
    setutxent();
    while (NULL != (ut = getutxent())) {
        if (ut->ut_type == BOOT_TIME) {
            boot_time = (float)ut->ut_tv.tv_sec;
            break;
        }
    }
    endutxent();
    UTXENT_MUTEX_UNLOCK();
    if (fabs(boot_time) < 0.000001) {
        /* could not find BOOT_TIME in getutxent loop */
        psutil_runtime_error("can't determine boot time");
        return NULL;
    }
    return Py_BuildValue("f", boot_time);
}
