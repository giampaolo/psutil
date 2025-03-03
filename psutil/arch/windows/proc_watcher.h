/*
 * Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
 * Use of this source code is governed by a BSD-style license that can be
 * found in the LICENSE file.
 */

#include <Python.h>

extern unsigned int PROC_EVENT_FORK;
extern unsigned int PROC_EVENT_EXIT;

PyType_Spec ProcessWatcher_spec;
