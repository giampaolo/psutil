# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import ctypes
import gc
import sys

import psutil
from psutil import MACOS

from . import PsutilTestCase
from . import skipif

SIZE = 64 * 1024


class Stats(ctypes.Structure):
    _fields_ = [
        ("blocks_in_use", ctypes.c_uint),
        ("size_in_use", ctypes.c_size_t),
        ("max_size_in_use", ctypes.c_size_t),
        ("size_allocated", ctypes.c_size_t),
    ]


def setup():
    libc = ctypes.CDLL(None)
    libc.malloc.argtypes = [ctypes.c_size_t]
    libc.malloc.restype = ctypes.c_void_p
    libc.free.argtypes = [ctypes.c_void_p]
    libc.malloc_get_zone_name.argtypes = [ctypes.c_void_p]
    libc.malloc_get_zone_name.restype = ctypes.c_char_p
    libc.malloc_zone_from_ptr.argtypes = [ctypes.c_void_p]
    libc.malloc_zone_from_ptr.restype = ctypes.c_void_p
    libc.malloc_zone_statistics.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(Stats),
    ]
    return libc


def zone_stats(libc):
    task = ctypes.c_uint.in_dll(libc, "mach_task_self_")
    addrs = ctypes.POINTER(ctypes.c_size_t)()
    count = ctypes.c_uint()
    kr = libc.malloc_get_all_zones(
        task, None, ctypes.byref(addrs), ctypes.byref(count)
    )
    out = {}
    for i in range(count.value):
        z = addrs[i]
        st = Stats()
        libc.malloc_zone_statistics(z, ctypes.byref(st))
        name = libc.malloc_get_zone_name(z)
        out[(z, name)] = (st.blocks_in_use, st.size_in_use)
    return kr, out


def log(*args):
    print("HEAPDBG", *args, file=sys.stderr)  # noqa: T201


@skipif(not MACOS, reason="MACOS only")
class TestHeapDebug(PsutilTestCase):
    def test_debug(self):
        libc = setup()
        for trim in (True, False):
            for i in range(15):
                if trim:
                    gc.collect()
                    psutil.heap_trim()
                m1 = psutil.heap_info().heap_used
                kr, z1 = zone_stats(libc)
                p = libc.malloc(SIZE)
                m2 = psutil.heap_info().heap_used
                _, z2 = zone_stats(libc)
                zone = libc.malloc_zone_from_ptr(p)
                libc.free(p)
                deltas = {
                    k[1]: (z2[k][0] - z1[k][0], z2[k][1] - z1[k][1])
                    for k in z1
                    if k in z2 and z1[k] != z2[k]
                }
                log(
                    f"trim={trim} i={i} kr={kr} nzones={len(z1)}"
                    f" delta={m2 - m1}"
                    f" zone={libc.malloc_get_zone_name(zone)}"
                    f" zdeltas={deltas}"
                )
        _, z = zone_stats(libc)
        log(f"zones={z}")
