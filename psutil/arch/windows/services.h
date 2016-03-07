/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>
#include <Winsvc.h>

SC_HANDLE psutil_get_service_handle(char service_name);
PyObject *psutil_winservice_enumerate();
PyObject *psutil_winservice_get_srv_descr();
