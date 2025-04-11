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

#ifdef PSUTIL_OSX  // XXX - TEMPORARY
#include "arch/osx/init.h"
#endif

// ====================================================================
// --- Global utils
// ====================================================================

int psutil_setup(void);

// ====================================================================
// --- BSD
// ====================================================================

void convert_kvm_err(const char *syscall, char *errbuf);
