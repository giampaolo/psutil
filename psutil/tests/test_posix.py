#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""POSIX specific tests."""

import datetime
import errno
import os
import re
import subprocess
import sys
import time

import psutil
from psutil import BSD
from psutil import CYGWIN
from psutil import LINUX
from psutil import OSX
from psutil import POSIX
from psutil import SUNOS
from psutil._compat import callable
from psutil._compat import PY3
from psutil.tests import APPVEYOR
from psutil.tests import get_kernel_version
from psutil.tests import get_test_subprocess
from psutil.tests import mock
from psutil.tests import PYTHON
from psutil.tests import reap_children
from psutil.tests import retry_before_failing
from psutil.tests import run_test_module_by_name
from psutil.tests import sh
from psutil.tests import skip_on_access_denied
from psutil.tests import TRAVIS
from psutil.tests import unittest
from psutil.tests import wait_for_pid


def run(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE)
    output = p.communicate()[0].strip()

    if PY3:
        output = str(output, sys.stdout.encoding)

    return output


def ps(fmt, pid=None):
    """
    Wrapper for calling the ps command with a little bit of cross-platform
    support for a narrow range of features.
    """

    # The ps on Cygwin bears only small resemblance to the *nix ps, and
    # probably shouldn't even be used for these tests; this tries as
    # best as possible to emulate it as used currently by these tests
    cmd = ['ps']

    if LINUX:
        cmd.append('--no-headers')

    if pid is not None:
        cmd.extend(['-p', str(pid)])
    else:
        if SUNOS:
            cmd.append('-A')
        elif CYGWIN:
            cmd.append('-a')
        else:
            cmd.append('ax')

    if SUNOS:
        fmt_map = {'command', 'comm',
                   'start', 'stime'}
        fmt = fmt_map.get(fmt, fmt)

    if not CYGWIN:
        cmd.extend(['-o', fmt])
    else:
        cmd.append('-l')

    output = run(cmd)

    if LINUX:
        output = output.splitlines()
    else:
        output = output.splitlines()[1:]

    if CYGWIN:
        cygwin_ps_re = re.compile(r'I?\s*(?P<pid>\d+)\s*(?P<ppid>\d+)\s*'
                                  '(?P<pgid>\d+)\s*(?P<winpid>\d+)\s*'
                                  '(?P<tty>[a-z0-9?]+)\s*(?P<uid>\d+)\s*'
                                  '(?:(?P<stime>\d{2}:\d{2}:\d{2})|'
                                  '   (?P<sdate>[A-Za-z]+\s+\d+))\s*'
                                  '(?P<command>/.+)')

        def cygwin_output(line, fmt):
            # NOTE: Cygwin's ps is very limited in what it outputs, so we work
            # around that by looking to various other sources for some
            # information
            fmt_map = {'start': 'stime'}
            fmt = fmt_map.get(fmt, fmt)

            m = cygwin_ps_re.match(line)
            if not m:
                return ''

            if fmt in cygwin_ps_re.groupindex:
                output = m.group(fmt)
                if output is None:
                    output = ''
            elif fmt == 'rgid':
                pid = m.group('pid')
                output = open('/proc/{0}/gid'.format(pid)).readline().strip()
            elif fmt == 'user':
                # Cygwin's ps only returns UID
                uid = m.group('uid')
                output = run(['getent', 'passwd', uid])
                output = output.splitlines()[0].split(':')[0]
            elif fmt == 'rss':
                winpid = m.group('winpid')
                output = run(['wmic', 'process', winpid, 'get',
                              'WorkingSetSize'])
                output = int(output.split('\n')[-1].strip()) / 1024
            elif fmt == 'vsz':
                winpid = m.group('winpid')
                output = run(['wmic', 'process', winpid, 'get',
                              'PrivatePageCount'])
                output = int(output.split('\n')[-1].strip()) / 1024
            else:
                raise ValueError('format %s not supported on Cygwin' % fmt)

            return output

    all_output = []
    for line in output:
        if CYGWIN:
            output = cygwin_output(line, fmt)

            if not output:
                continue

        try:
            output = int(output)
        except ValueError:
            pass

        all_output.append(output)

    if pid is None:
        return all_output
    else:
        return all_output[0]


@unittest.skipUnless(POSIX, "POSIX only")
class TestProcess(unittest.TestCase):
    """Compare psutil results against 'ps' command line utility (mainly)."""

    @classmethod
    def setUpClass(cls):
        cls.pid = get_test_subprocess([PYTHON, "-E", "-O"],
                                      stdin=subprocess.PIPE).pid
        wait_for_pid(cls.pid)

    @classmethod
    def tearDownClass(cls):
        reap_children()

    # for ps -o arguments see: http://unixhelp.ed.ac.uk/CGI/man-cgi?ps

    def test_ppid(self):
        ppid_ps = ps('ppid', self.pid)
        ppid_psutil = psutil.Process(self.pid).ppid()
        self.assertEqual(ppid_ps, ppid_psutil)

    def test_uid(self):
        uid_ps = ps('uid', self.pid)
        uid_psutil = psutil.Process(self.pid).uids().real
        self.assertEqual(uid_ps, uid_psutil)

    def test_gid(self):
        gid_ps = ps('rgid', self.pid)
        gid_psutil = psutil.Process(self.pid).gids().real
        self.assertEqual(gid_ps, gid_psutil)

    def test_username(self):
        username_ps = ps('user', self.pid)
        username_psutil = psutil.Process(self.pid).username()
        self.assertEqual(username_ps, username_psutil)

    @skip_on_access_denied()
    @retry_before_failing()
    def test_rss_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        rss_ps = ps('rss', self.pid)
        rss_psutil = psutil.Process(self.pid).memory_info()[0] / 1024
        self.assertEqual(rss_ps, rss_psutil)

    @skip_on_access_denied()
    @retry_before_failing()
    def test_vsz_memory(self):
        # give python interpreter some time to properly initialize
        # so that the results are the same
        time.sleep(0.1)
        vsz_ps = ps('vsz', self.pid)
        vsz_psutil = psutil.Process(self.pid).memory_info()[1] / 1024
        self.assertEqual(vsz_ps, vsz_psutil)

    def test_name(self):
        # use command + arg since "comm" keyword not supported on all platforms
        name_ps = ps('command', self.pid).split(' ')[0]
        # remove path if there is any, from the command
        name_ps = os.path.basename(name_ps).lower()
        name_psutil = psutil.Process(self.pid).name().lower()
        self.assertEqual(name_ps, name_psutil)

    @unittest.skipIf(OSX or BSD, 'ps -o start not available')
    def test_create_time(self):
        time_ps = ps('start', self.pid)
        time_psutil = psutil.Process(self.pid).create_time()
        time_psutil_tstamp = datetime.datetime.fromtimestamp(
            time_psutil).strftime("%H:%M:%S")
        # sometimes ps shows the time rounded up instead of down, so we check
        # for both possible values
        round_time_psutil = round(time_psutil)
        round_time_psutil_tstamp = datetime.datetime.fromtimestamp(
            round_time_psutil).strftime("%H:%M:%S")
        self.assertIn(time_ps, [time_psutil_tstamp, round_time_psutil_tstamp])

    def test_exe(self):
        ps_pathname = ps('command', self.pid).split(' ')[0]
        psutil_pathname = psutil.Process(self.pid).exe()
        try:
            self.assertEqual(ps_pathname, psutil_pathname)
        except AssertionError:
            # certain platforms such as BSD are more accurate returning:
            # "/usr/local/bin/python2.7"
            # ...instead of:
            # "/usr/local/bin/python"
            # We do not want to consider this difference in accuracy
            # an error.
            adjusted_ps_pathname = ps_pathname[:len(ps_pathname)]
            self.assertEqual(ps_pathname, adjusted_ps_pathname)

    def test_cmdline(self):
        ps_cmdline = ps('command', self.pid)
        psutil_cmdline = " ".join(psutil.Process(self.pid).cmdline())
        if SUNOS or CYGWIN:
            # ps on Solaris and Cygwin only shows the first part of the cmdline
            psutil_cmdline = psutil_cmdline.split(" ")[0]
        self.assertEqual(ps_cmdline, psutil_cmdline)

    # To be more specific, process priorities are complicated in Windows and
    # there's no simple way, from the command line, to get the information
    # needed to reproduce the way Cygwin maps Windows process priorties to
    # 'nice' values (not even through Cygwin's /proc API, which only returns
    # the "base priority" which actually is not sufficient because what we
    # really need is the process's "priority class" which is different
    @unittest.skipIf(CYGWIN, "this is not supported by Cygwin")
    def test_nice(self):
        ps_nice = ps('nice', self.pid)
        psutil_nice = psutil.Process().nice()
        self.assertEqual(ps_nice, psutil_nice)

    def test_num_fds(self):
        # Note: this fails from time to time; I'm keen on thinking
        # it doesn't mean something is broken
        def call(p, attr):
            args = ()
            attr = getattr(p, name, None)
            if attr is not None and callable(attr):
                if name == 'rlimit':
                    args = (psutil.RLIMIT_NOFILE,)
                attr(*args)
            else:
                attr

        p = psutil.Process(os.getpid())
        failures = []
        ignored_names = ['terminate', 'kill', 'suspend', 'resume', 'nice',
                         'send_signal', 'wait', 'children', 'as_dict']
        if LINUX and get_kernel_version() < (2, 6, 36):
            ignored_names.append('rlimit')
        if LINUX and get_kernel_version() < (2, 6, 23):
            ignored_names.append('num_ctx_switches')
        for name in dir(psutil.Process):
            if (name.startswith('_') or name in ignored_names):
                continue
            else:
                try:
                    num1 = p.num_fds()
                    for x in range(2):
                        call(p, name)
                    num2 = p.num_fds()
                except psutil.AccessDenied:
                    pass
                else:
                    if abs(num2 - num1) > 1:
                        fail = "failure while processing Process.%s method " \
                               "(before=%s, after=%s)" % (name, num1, num2)
                        failures.append(fail)
        if failures:
            self.fail('\n' + '\n'.join(failures))

    @unittest.skipUnless(os.path.islink("/proc/%s/cwd" % os.getpid()),
                         "/proc fs not available")
    def test_cwd(self):
        self.assertEqual(os.readlink("/proc/%s/cwd" % os.getpid()),
                         psutil.Process().cwd())


@unittest.skipUnless(POSIX, "POSIX only")
class TestSystemAPIs(unittest.TestCase):
    """Test some system APIs."""

    @retry_before_failing()
    def test_pids(self):
        # Note: this test might fail if the OS is starting/killing
        # other processes in the meantime
        pids_ps = ps('pid')
        pids_psutil = psutil.pids()
        pids_ps.sort()
        pids_psutil.sort()

        # on OSX ps doesn't show pid 0
        if OSX and 0 not in pids_ps:
            pids_ps.insert(0, 0)

        if pids_ps != pids_psutil:
            difference = [x for x in pids_psutil if x not in pids_ps] + \
                         [x for x in pids_ps if x not in pids_psutil]
            self.fail("difference: " + str(difference))

    # for some reason ifconfig -a does not report all interfaces
    # returned by psutil
    @unittest.skipIf(SUNOS, "unreliable on SUNOS")
    @unittest.skipIf(TRAVIS, "unreliable on TRAVIS")
    def test_nic_names(self):
        p = subprocess.Popen("ifconfig -a", shell=1, stdout=subprocess.PIPE)
        output = p.communicate()[0].strip()
        if p.returncode != 0:
            raise unittest.SkipTest('ifconfig returned no output')
        if PY3:
            output = str(output, sys.stdout.encoding)
        for nic in psutil.net_io_counters(pernic=True).keys():
            for line in output.split():
                if line.startswith(nic):
                    break
            else:
                self.fail(
                    "couldn't find %s nic in 'ifconfig -a' output\n%s" % (
                        nic, output))

    # can't find users on APPVEYOR or TRAVIS
    @unittest.skipIf(APPVEYOR or TRAVIS and not psutil.users(),
                     "unreliable on APPVEYOR or TRAVIS")
    @retry_before_failing()
    def test_users(self):
        out = sh("who")
        lines = [x.strip() for x in out.split('\n')]
        users = [x.split()[0] for x in lines if x]
        self.assertEqual(len(users), len(psutil.users()))
        terminals = [x.split()[1] for x in lines if x]
        for u in psutil.users():
            self.assertTrue(u.name in users, u.name)
            self.assertTrue(u.terminal in terminals, u.terminal)

    def test_pid_exists_let_raise(self):
        # According to "man 2 kill" possible error values for kill
        # are (EINVAL, EPERM, ESRCH). Test that any other errno
        # results in an exception.
        with mock.patch("psutil._psposix.os.kill",
                        side_effect=OSError(errno.EBADF, "")) as m:
            self.assertRaises(OSError, psutil._psposix.pid_exists, os.getpid())
            assert m.called

    def test_os_waitpid_let_raise(self):
        # os.waitpid() is supposed to catch EINTR and ECHILD only.
        # Test that any other errno results in an exception.
        with mock.patch("psutil._psposix.os.waitpid",
                        side_effect=OSError(errno.EBADF, "")) as m:
            self.assertRaises(OSError, psutil._psposix.wait_pid, os.getpid())
            assert m.called

    def test_os_waitpid_eintr(self):
        # os.waitpid() is supposed to "retry" on EINTR.
        with mock.patch("psutil._psposix.os.waitpid",
                        side_effect=OSError(errno.EINTR, "")) as m:
            self.assertRaises(
                psutil._psposix.TimeoutExpired,
                psutil._psposix.wait_pid, os.getpid(), timeout=0.01)
            assert m.called

    def test_os_waitpid_bad_ret_status(self):
        # Simulate os.waitpid() returning a bad status.
        with mock.patch("psutil._psposix.os.waitpid",
                        return_value=(1, -1)) as m:
            self.assertRaises(ValueError,
                              psutil._psposix.wait_pid, os.getpid())
            assert m.called

    def test_disk_usage(self):
        def df(device):
            out = sh("df -k %s" % device).strip()
            line = out.split('\n')[1]
            fields = line.split()
            total = int(fields[1]) * 1024
            used = int(fields[2]) * 1024
            free = int(fields[3]) * 1024
            percent = float(fields[4].replace('%', ''))
            return (total, used, free, percent)

        tolerance = 4 * 1024 * 1024  # 4MB
        for part in psutil.disk_partitions(all=False):
            if not os.path.exists(part.mountpoint):
                continue

            usage = psutil.disk_usage(part.mountpoint)
            try:
                total, used, free, percent = df(part.device)
            except RuntimeError as err:
                # see:
                # https://travis-ci.org/giampaolo/psutil/jobs/138338464
                # https://travis-ci.org/giampaolo/psutil/jobs/138343361
                if "no such file or directory" in str(err).lower() or \
                        "raw devices not supported" in str(err).lower():
                    continue
                else:
                    raise
            else:
                self.assertAlmostEqual(usage.total, total, delta=tolerance)
                self.assertAlmostEqual(usage.used, used, delta=tolerance)
                self.assertAlmostEqual(usage.free, free, delta=tolerance)
                self.assertAlmostEqual(usage.percent, percent, delta=1)


if __name__ == '__main__':
    run_test_module_by_name(__file__)
