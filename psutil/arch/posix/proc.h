/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

int psutil_pid_exists(pid_t pid);
void psutil_raise_for_pid(pid_t pid, char *msg);

PyObject *psutil_posix_getpriority(PyObject *self, PyObject *args);
PyObject *psutil_posix_setpriority(PyObject *self, PyObject *args);
