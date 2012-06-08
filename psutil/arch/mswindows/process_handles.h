/*
 * $Id: process_info.h 1060 2011-07-02 18:05:26Z g.rodola $
 *
 * Copyright (c) 2009, Jay Loden, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <windows.h>

PyObject* psutil_get_open_files(long pid, HANDLE processHandle);
