/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <sys/sysctl.h>

#include "../../arch/all/init.h"
#include "init.h"


uint64_t PSUTIL_HW_TBFREQUENCY;

// Called on module import.
int
psutil_setup_osx(void) {
    size_t size = sizeof(PSUTIL_HW_TBFREQUENCY);

    // hw.tbfrequency gives the real hardware timer frequency regardless of
    // whether we are running under Rosetta 2 (x86_64 on Apple Silicon).
    // mach_timebase_info() is intercepted by Rosetta and returns numer=1,
    // denom=1 for x86_64 processes, but proc_pidinfo() returns raw ARM Mach
    // ticks, so mach_timebase_info gives a wrong conversion factor there.
    if (sysctlbyname("hw.tbfrequency", &PSUTIL_HW_TBFREQUENCY, &size, NULL, 0)
        != 0)
    {
        psutil_oserror_wsyscall("sysctlbyname('hw.tbfrequency')");
        return -1;
    }
    return 0;
}
