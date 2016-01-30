/* -*- Mode: C++; tab-width: 8; indent-tabs-mode: nil; c-basic-offset: 2 -*- */
/* vim: set ts=8 sts=2 et sw=2 tw=80: */
/* This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at http://mozilla.org/MPL/2.0/. */

#include "_psutil_windows_uss.h"
#include <psapi.h>

BOOL
calc_uss(DWORD target, unsigned long long* aN)
{
  BOOL result = FALSE;
  HANDLE proc;
  PSAPI_WORKING_SET_INFORMATION tmp;
  DWORD tmpSize = sizeof(tmp);
  size_t entries, privatePages, i;
  DWORD infoArraySize;
  PSAPI_WORKING_SET_INFORMATION* infoArray;
  SYSTEM_INFO si;

  proc = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ,
                     FALSE, target);

  if (!proc) {
    goto done;
  }

  /* Determine how many entries we need. */
  memset(&tmp, 0, tmpSize);
  QueryWorkingSet(proc, &tmp, tmpSize);

  /* Fudge the size in case new entries are added between calls. */
  entries = tmp.NumberOfEntries * 2;

  if (!entries) {
    goto done;
  }

  infoArraySize = tmpSize + (entries * sizeof(PSAPI_WORKING_SET_BLOCK));
  infoArray = (PSAPI_WORKING_SET_INFORMATION*)malloc(infoArraySize);

  if (!infoArray || !QueryWorkingSet(proc, infoArray, infoArraySize)) {
    goto done;
  }

  /* At this point the working set has been successfully queried. */
  result = TRUE;

  entries = (size_t)infoArray->NumberOfEntries;
  privatePages = 0;
  for (i = 0; i < entries; i++) {
    /* Count shared pages that only one process is using as private. */
    if (!infoArray->WorkingSetInfo[i].Shared ||
        infoArray->WorkingSetInfo[i].ShareCount <= 1) {
      privatePages++;
    }
  }

  GetSystemInfo(&si);
  *aN = privatePages * si.dwPageSize;

done:
  if (proc) {
    CloseHandle(proc);
  }

  if (infoArray) {
    free(infoArray);
  }

  return result;
}
