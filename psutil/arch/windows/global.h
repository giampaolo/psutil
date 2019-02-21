/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <windows.h>

int psutil_loadlibs();
PVOID psutil_GetProcAddress(LPCSTR libname, LPCSTR procname);
PVOID psutil_GetProcAddressFromLib(LPCSTR libname, LPCSTR procname);
