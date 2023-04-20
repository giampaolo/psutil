/*
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 *
 * Helper functions related to fetching process information.
 * Used by _psutil_osx module methods.
 */

#include <Python.h>
#include <errno.h>
#include <sys/sysctl.h>
#include <libproc.h>

#include "../../_psutil_common.h"
#include "../../_psutil_posix.h"
#include "process_info.h"
