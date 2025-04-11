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

// ====================================================================
// --- macOS
// ====================================================================

#ifdef PSUTIL_OSX
#include <mach/mach_time.h>

struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;
#endif

// ====================================================================
// --- Windows
// ====================================================================



// Called on module import on all platforms.
int
psutil_setup(void) {
    if (getenv("PSUTIL_DEBUG") != NULL)
        PSUTIL_DEBUG = 1;

#ifdef PSUTIL_OSX
    mach_timebase_info(&PSUTIL_MACH_TIMEBASE_INFO);
#endif
    return 0;
}
