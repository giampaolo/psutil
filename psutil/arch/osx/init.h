/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <mach/mach_time.h>

extern struct mach_timebase_info PSUTIL_MACH_TIMEBASE_INFO;

int psutil_setup_osx(void);
