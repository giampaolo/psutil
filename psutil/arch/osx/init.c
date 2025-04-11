/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <mach/mach_time.h>

#include "../../arch/all/init.h"
#include "init.h"

struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;


// Called on module import.
int
psutil_setup_osx(void) {
    mach_timebase_info(&PSUTIL_MACH_TIMEBASE_INFO);
    return 0;
}
