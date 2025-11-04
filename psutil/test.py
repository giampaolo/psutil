# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import functools
import gc
import os
import sys
import unittest

import psutil

from ._common import POSIX
from ._common import bytes2human
from ._common import print_color

__all__ = ["MemoryLeakTestCase"]


class MemoryLeakTestCase(unittest.TestCase):
    """Test framework class for detecting function memory leaks,
    typically functions implemented in C which forgot to free() memory
    from the heap. It does so by checking whether the process memory
    usage increased before and after calling the function many times.

    Note that this is hard (probably impossible) to do reliably, due
    to how the OS handles memory, the GC and so on (memory can even
    decrease!). In order to avoid false positives, in case of failure
    (mem > 0) we retry the test for up to 5 times, increasing call
    repetitions each time. If the memory keeps increasing then it's a
    failure.

    We currently check RSS, VMS and USS [1] memory. mallinfo() on Linux
    and _heapwalk() on Windows should give even more precision [2], but
    at the moment they are not implemented.

    PyPy appears to be completely unstable for this framework, probably
    because of its JIT, so tests on PYPY are skipped.

    Usage:

        import psutil.test import MemoryLeakTestCase

        class TestLeaks(MemoryLeakTestCase):
            def test_fun(self):
                self.execute(some_function)

    [1] https://gmpy.dev/blog/2016/real-process-memory-and-environ-in-python
    [2] https://github.com/giampaolo/psutil/issues/1275
    """

    # Configurable class attrs.
    times = 200
    warmup_times = 10
    tolerance = 0  # memory
    retries = 10
    verbose = True

    _thisproc = psutil.Process()
    _psutil_debug_orig = bool(os.getenv('PSUTIL_DEBUG'))

    @classmethod
    def setUpClass(cls):
        psutil._set_debug(False)  # avoid spamming to stderr

    @classmethod
    def tearDownClass(cls):
        psutil._set_debug(cls._psutil_debug_orig)

    def _log(self, msg):
        if self.verbose:
            print_color(msg, color="yellow", file=sys.stderr)

    # --- getters

    def _get_mem(self):
        mem = self._thisproc.memory_full_info()
        return {
            "rss": mem.rss,
            "vms": mem.vms,
            "uss": getattr(mem, "uss", 0),
        }

    def _get_num_fds(self):
        if POSIX:
            return self._thisproc.num_fds()
        else:
            return self._thisproc.num_handles()

    # --- checkers

    def _check_fds(self, fun):
        """Makes sure num_fds() (POSIX) or num_handles() (Windows) does
        not increase after calling a function.  Used to discover forgotten
        close(2) and CloseHandle syscalls.
        """
        before = self._get_num_fds()
        self.call(fun)
        after = self._get_num_fds()
        diff = after - before
        if diff < 0:
            msg = (
                f"negative diff {diff!r} (gc probably collected a"
                " resource from a previous test)"
            )
            return self.fail(msg)
        if diff > 0:
            type_ = "fd" if POSIX else "handle"
            if diff > 1:
                type_ += "s"
            msg = f"{diff} unclosed {type_} after calling {fun!r}"
            return self.fail(msg)

    def _call_ntimes(self, fun, times):
        """Get memory samples (rss, vms, uss) before and after calling
        fun repeatedly, and return the diffs as a dict.
        """
        gc.collect(generation=1)
        mem1 = self._get_mem()
        for x in range(times):
            ret = self.call(fun)
            del x, ret
        gc.collect(generation=1)
        mem2 = self._get_mem()
        assert gc.garbage == []
        diffs = {k: mem2[k] - mem1[k] for k in mem1}
        return diffs

    def _check_mem(self, fun, times, retries, tolerance):
        messages = []
        prev_mem = {}
        increase = times
        b2h = functools.partial(bytes2human, format="%(value)i%(symbol)s")

        for idx in range(1, retries + 1):
            diffs = self._call_ntimes(fun, times)

            # Filter only metrics with positive diffs (possible leaks).
            positive_diffs = {k: v for k, v in diffs.items() if v > 0}

            # Build message only for those metrics.
            if positive_diffs:
                msg_parts = [
                    f"{k}=+{b2h(v)}" for k, v in positive_diffs.items()
                ]
                msg = "Run #{}: {} (ncalls={}, avg-per-call=+{})".format(
                    idx,
                    ", ".join(msg_parts),
                    times,
                    b2h(sum(positive_diffs.values()) / times),
                )
                if idx == 1:
                    msg = "\n" + msg
                messages.append(msg)
                self._log(msg)

            # Determine if memory stabilized or decreased.
            success = all(
                diffs.get(k, 0) <= tolerance
                or diffs.get(k, 0) <= prev_mem.get(k, 0)
                for k in diffs
            )
            if success:
                if idx > 1 and positive_diffs:
                    self._log("Memory stabilized (no further growth detected)")
                return None

            times += increase
            prev_mem = diffs

        msg = "\n" + "\n".join(messages)
        return self.fail(msg)

    # ---

    def call(self, fun):
        return fun()

    def execute(
        self, fun, times=None, warmup_times=None, retries=None, tolerance=None
    ):
        """Test a callable."""
        times = times if times is not None else self.times
        warmup_times = (
            warmup_times if warmup_times is not None else self.warmup_times
        )
        retries = retries if retries is not None else self.retries
        tolerance = tolerance if tolerance is not None else self.tolerance

        if times < 1:
            msg = f"times must be >= 1 (got {times})"
            raise ValueError(msg)
        if warmup_times < 0:
            msg = f"warmup_times must be >= 0 (got {warmup_times})"
            raise ValueError(msg)
        if retries < 0:
            msg = f"retries must be >= 0 (got {retries})"
            raise ValueError(msg)
        if tolerance < 0:
            msg = f"tolerance must be >= 0 (got {tolerance})"
            raise ValueError(msg)

        self._call_ntimes(fun, warmup_times)  # warm up

        self._check_fds(fun)
        self._check_mem(fun, times=times, retries=retries, tolerance=tolerance)

    def execute_w_exc(self, exc, fun, **kwargs):
        """Convenience method to test a callable while making sure it
        raises an exception on every call.
        """

        def call():
            try:
                fun()
            except exc:
                pass
            else:
                return self.fail(f"{fun} did not raise {exc}")

        self.execute(call, **kwargs)
