/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Routines common to all platforms.
 */

#include <Python.h>

#include "arch/all/init.h"
#include "_psutil_common.h"


// ============================================================================
// Utility functions (BSD)
// ============================================================================

#if defined(PSUTIL_FREEBSD) || defined(PSUTIL_OPENBSD) || defined(PSUTIL_NETBSD)
void
convert_kvm_err(const char *syscall, char *errbuf) {
    char fullmsg[8192];

    sprintf(fullmsg, "(originated from %s: %s)", syscall, errbuf);
    if (strstr(errbuf, "Permission denied") != NULL)
        AccessDenied(fullmsg);
    else if (strstr(errbuf, "Operation not permitted") != NULL)
        AccessDenied(fullmsg);
    else
        PyErr_Format(PyExc_RuntimeError, fullmsg);
}
#endif
