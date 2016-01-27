/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=8 sts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

#include <mach/mach_init.h>
#include <mach/mach_vm.h>
#include <mach/shared_region.h>
#include <mach/task.h>
#include <sys/sysctl.h>

#include "_psutil_osx_uss.h"

bool
InSharedRegion(mach_vm_address_t aAddr, cpu_type_t aType)
{
  mach_vm_address_t base;
  mach_vm_address_t size;

  switch (aType) {
    case CPU_TYPE_ARM:
      base = SHARED_REGION_BASE_ARM;
      size = SHARED_REGION_SIZE_ARM;
      break;
    case CPU_TYPE_I386:
      base = SHARED_REGION_BASE_I386;
      size = SHARED_REGION_SIZE_I386;
      break;
    case CPU_TYPE_X86_64:
      base = SHARED_REGION_BASE_X86_64;
      size = SHARED_REGION_SIZE_X86_64;
      break;
    default:
      return false;
  }

  return base <= aAddr && aAddr < (base + size);
}

bool
calc_uss(mach_port_t target, int64_t* aN)
{
  if (!aN) {
    return false;
  }

  cpu_type_t cpu_type;
  size_t len = sizeof(cpu_type);
  if (sysctlbyname("sysctl.proc_cputype", &cpu_type, &len, NULL, 0) != 0) {
    return false;
  }

  /* Roughly based on libtop_update_vm_regions in
    http://www.opensource.apple.com/source/top/top-100.1.2/libtop.c */
  size_t privatePages = 0;
  mach_vm_size_t size = 0;
  for (mach_vm_address_t addr = MACH_VM_MIN_ADDRESS; ; addr += size) {
    vm_region_top_info_data_t info;
    mach_msg_type_number_t infoCount = VM_REGION_TOP_INFO_COUNT;
    mach_port_t objectName;

    kern_return_t kr =
        mach_vm_region(target, &addr, &size, VM_REGION_TOP_INFO,
                       (vm_region_info_t)&info,
                       &infoCount, &objectName);
    if (kr == KERN_INVALID_ADDRESS) {
      /* Done iterating VM regions. */
      break;
    } else if (kr != KERN_SUCCESS) {
      return false;
    }

    if (InSharedRegion(addr, cpu_type) && info.share_mode != SM_PRIVATE) {
        continue;
    }

    switch (info.share_mode) {
      case SM_LARGE_PAGE:
        /* NB: Large pages are not shareable and always resident. */
      case SM_PRIVATE:
        privatePages += info.private_pages_resident;
        privatePages += info.shared_pages_resident;
        break;
      case SM_COW:
        privatePages += info.private_pages_resident;
        if (info.ref_count == 1) {
          /* Treat copy-on-write pages as private if they only have one reference. */
          privatePages += info.shared_pages_resident;
        }
        break;
      case SM_SHARED:
      default:
        break;
    }
  }

  vm_size_t pageSize;
  if (host_page_size(mach_host_self(), &pageSize) != KERN_SUCCESS) {
    pageSize = PAGE_SIZE;
  }

  *aN = privatePages * pageSize;
  return true;
}
