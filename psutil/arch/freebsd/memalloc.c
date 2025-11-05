/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdlib.h>
#include <malloc_np.h>

#include "../../arch/all/init.h"

#define _STRINGIFY(x) #x
#define STRINGIFY(x) _STRINGIFY(x)


// Purges unused pages.
PyObject *
psutil_malloc_release(PyObject *self, PyObject *args) {
    int ret = mallctl(
        "arena." STRINGIFY(MALLCTL_ARENAS_ALL) ".purge", NULL, NULL, NULL, 0
    );
    if (ret != 0)
        return psutil_oserror();
    Py_RETURN_NONE;
}
