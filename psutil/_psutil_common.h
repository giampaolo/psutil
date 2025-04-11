/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#ifdef PSUTIL_WINDOWS  // XXX - TEMPORARY
#include <windows.h>
#endif

#include "arch/all/init.h"

#ifdef PSUTIL_WINDOWS  // XXX - TEMPORARY
#include "arch/windows/init.h"
#endif

// ====================================================================
// --- Global utils
// ====================================================================

int psutil_setup(void);

// ====================================================================
// --- BSD
// ====================================================================

void convert_kvm_err(const char *syscall, char *errbuf);

// ====================================================================
// --- macOS
// ====================================================================

#ifdef PSUTIL_OSX
    #include <mach/mach_time.h>

    extern struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;
#endif

// ====================================================================
// --- Windows
// ====================================================================

#ifdef PSUTIL_WINDOWS
    // make it available to any file which includes this module
    #include "arch/windows/ntextapi.h"

    PVOID psutil_SetFromNTStatusErr(NTSTATUS Status, const char *syscall);
#endif
