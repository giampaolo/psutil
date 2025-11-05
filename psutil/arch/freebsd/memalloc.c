/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <stdlib.h>
#include <malloc_np.h>

#include "../../arch/all/init.h"


// Purges unused pages.
PyObject *
psutil_malloc_release(PyObject *self, PyObject *args) {
    if (mallctl("arena.0.purge", NULL, NULL, NULL, 0) != 0)
        return psutil_oserror();
    Py_RETURN_NONE;
}
