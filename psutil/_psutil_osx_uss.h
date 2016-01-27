/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=8 sts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

#ifndef _psutil_osx_uss_h
#define _psutil_osx_uss_h

#include <stdbool.h>
#include <stdint.h>
#include <mach/port.h>

bool calc_uss(mach_port_t target, int64_t* aN);

#endif
