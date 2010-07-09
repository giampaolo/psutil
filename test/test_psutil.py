#!/usr/bin/env python
#
# $Id$
#

import unittest
import os
import sys
import subprocess
import time
import signal
import types
import errno
import platform
import traceback
import socket

import psutil


PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')

POSIX = os.name == 'posix'
LINUX = sys.platform.lower().startswith("linux")
WINDOWS = sys.platform.lower().startswith("win32")
OSX = sys.platform.lower().startswith("darwin")
BSD = sys.platform.lower().startswith("freebsd")


def wait_for_pid(pid, timeout=1):
    """Wait for pid to show up in the process list then return.
    Used in the test suite to give time the sub process to initialize.
    """
    raise_at = time.time() + timeout
    while 1:
        if pid in psutil.get_pid_list():
            # give it one more iteration to allow full initialization
            time.sleep(0.01)
            return
        time.sleep(0.0001)
        if time.time() >= raise_at:
            raise RuntimeError("Timed out")

def kill(pid):
    """Kill a process given its PID."""
    if hasattr(os, 'kill'):
        os.kill(pid, signal.SIGKILL)
    else:
        psutil.Process(pid).kill()

def reap_children():
    """Kill any subprocess started by this test suite and ensure that
    no zombies stick around to hog resources and create problems when
    looking for refleaks.
    """
    if POSIX:
        def waitpid(process):
            # on posix we are free to wait for any pending process by
            # passing -1 to os.waitpid()
            while True:
                try:
                    any_process = -1
                    pid, status = os.waitpid(any_process, os.WNOHANG)
                    if pid == 0 and not process.is_running():
                        break
                except OSError:
                    if not process.is_running():
                        break
    else:
        def waitpid(process):
            # on non-posix systems we just wait for the given process
            # to go away
            while process.is_running():
                time.sleep(0.01)

    this_process = psutil.Process(os.getpid())
    for child in this_process.get_children():
        child.kill()
        waitpid(child)


class TestCase(unittest.TestCase):

    def setUp(self):
        # supposed to always be a subprocess.Popen instance
        self.proc = None

    def tearDown(self):
        reap_children()

    def test_get_process_list(self):
        pids = [x.pid for x in psutil.get_process_list()]
        if hasattr(os, 'getpid'):
            self.assertTrue(os.getpid() in pids)

    def test_process_iter(self):
        pids = [x.pid for x in psutil.process_iter()]
        if hasattr(os, 'getpid'):
            self.assertTrue(os.getpid() in pids)

    def test_kill(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        test_pid = self.proc.pid
        wait_for_pid(test_pid)
        p = psutil.Process(test_pid)
        name = p.name
        p.kill()
        self.proc.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_terminate(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        test_pid = self.proc.pid
        wait_for_pid(test_pid)
        p = psutil.Process(test_pid)
        name = p.name
        p.terminate()
        self.proc.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_send_signal(self):
        if POSIX:
            sig = signal.SIGKILL
        else:
            sig = signal.SIGTERM
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        test_pid = self.proc.pid
        p = psutil.Process(test_pid)
        name = p.name
        p.send_signal(sig)
        self.proc.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_TOTAL_PHYMEM(self):
        x = psutil.TOTAL_PHYMEM
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x > 0)

    def test_used_phymem(self):
        x = psutil.used_phymem()
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x > 0)

    def test_avail_phymem(self):
        x = psutil.avail_phymem()
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x > 0)

    def test_total_virtmem(self):
        x = psutil.total_virtmem()
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x >= 0)

    def test_used_virtmem(self):
        x = psutil.used_virtmem()
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x >= 0)

    def test_avail_virtmem(self):
        x = psutil.avail_virtmem()
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x >= 0)

    def test_cached_mem(self):
        x = psutil.cached_mem()
        self.assertTrue(isinstance(x, int) or isinstance(x, long))
        self.assertTrue(x >= 0)

    def test_system_cpu_times(self):
        total = 0
        times = psutil.cpu_times()
        self.assertTrue(isinstance(times, psutil.CPUTimes))
        sum(times)
        for cp_time in times:
            self.assertTrue(isinstance(cp_time, float))
            self.assertTrue(cp_time >= 0.0)
            total += cp_time
        # test CPUTimes's __iter__ and __str__ implementation
        self.assertEqual(total, sum(times))
        str(times)

    def test_system_cpu_percent(self):
        percent = psutil.cpu_percent()
        self.assertTrue(isinstance(percent, float))
        for x in xrange(1000):
            percent = psutil.cpu_percent()
            self.assertTrue(isinstance(percent, float))
            self.assertTrue(percent >= 0.0)
            self.assertTrue(percent <= 100.0)

    # os.times() is broken on OS X and *BSD because, see:
    # http://bugs.python.org/issue1040026
    # It's also broken on Windows on Python 2.5 (not 2.6)
    # Disabled since we can't rely on it

##    def test_get_cpu_times(self):
##        user_time, kernel_time = psutil.Process(os.getpid()).get_cpu_times()
##        utime, ktime = os.times()[:2]
##
##        # Use os.times()[:2] as base values to compare our results
##        # using a tolerance  of +/- 0.1 seconds.
##        # It will fail if the difference between the values is > 0.1s.
##        if (max([user_time, utime]) - min([user_time, utime])) > 0.1:
##            self.fail("expected: %s, found: %s" %(utime, user_time))
##
##        if (max([kernel_time, ktime]) - min([kernel_time, ktime])) > 0.1:
##            self.fail("expected: %s, found: %s" %(ktime, kernel_time))
##
##        # make sure returned values can be pretty printed with strftime
##        time.strftime("%H:%M:%S", time.localtime(user_time))
##        time.strftime("%H:%M:%S", time.localtime(kernel_time))

    def test_get_cpu_times(self):
        times = psutil.Process(os.getpid()).get_cpu_times()
        self.assertTrue((times.user > 0.0) or (times.kernel > 0.0))

    def test_create_time(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        now = time.time()
        wait_for_pid(self.proc.pid)
        p = psutil.Process(self.proc.pid)
        create_time = p.create_time

        # Use time.time() as base value to compare our result using a
        # tolerance of +/- 1 second.
        # It will fail if the difference between the values is > 2s.
        difference = abs(create_time - now)
        if difference > 2:
            self.fail("expected: %s, found: %s, difference: %s" %(now, create_time, difference))

        # make sure returned value can be pretty printed with strftime
        time.strftime("%Y %m %d %H:%M:%S", time.localtime(p.create_time))

    def test_get_memory_info(self):
        p = psutil.Process(os.getpid())

        # step 1 - get a base value to compare our results
        rss1, vms1 = p.get_memory_info()
        percent1 = p.get_memory_percent()
        self.assertTrue(rss1 > 0)
        self.assertTrue(vms1 > 0)

        # step 2 - allocate some memory
        memarr = [None] * 1500000

        rss2, vms2 = p.get_memory_info()
        percent2 = p.get_memory_percent()
        # make sure that the memory usage bumped up
        self.assertTrue(rss2 > rss1)
        self.assertTrue(vms2 >= vms1)  # vms might be equal
        self.assertTrue(percent2 > percent1)
        del memarr

    def test_get_memory_percent(self):
        p = psutil.Process(os.getpid())
        self.assertTrue(p.get_memory_percent() > 0.0)

    def test_pid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        self.assertEqual(psutil.Process(self.proc.pid).pid, self.proc.pid)

    def test_eq(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        self.assertTrue(psutil.Process(self.proc.pid) == psutil.Process(self.proc.pid))

    def test_is_running(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        p = psutil.Process(self.proc.pid)
        self.assertTrue(p.is_running())
        psutil.Process(self.proc.pid).kill()
        self.proc.wait()
        self.assertFalse(p.is_running())

    def test_pid_exists(self):
        if hasattr(os, 'getpid'):
            self.assertTrue(psutil.pid_exists(os.getpid()))
        self.assertFalse(psutil.pid_exists(-1))

    def test_path(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        self.assertEqual(psutil.Process(self.proc.pid).path, os.path.dirname(PYTHON))

    def test_cmdline(self):
        self.proc = subprocess.Popen([PYTHON, "-E"], stdout=DEVNULL, stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        self.assertEqual(psutil.Process(self.proc.pid).cmdline, [PYTHON, "-E"])

    def test_name(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL,  stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        self.assertEqual(psutil.Process(self.proc.pid).name, os.path.basename(PYTHON))

    def test_uid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        uid = psutil.Process(self.proc.pid).uid
        if hasattr(os, 'getuid'):
            self.assertEqual(uid, os.getuid())
        else:
            # On those platforms where UID doesn't make sense (Windows)
            # we expect it to be -1
            self.assertEqual(uid, -1)

    def test_gid(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        wait_for_pid(self.proc.pid)
        gid = psutil.Process(self.proc.pid).gid
        if hasattr(os, 'getgid'):
            self.assertEqual(gid, os.getgid())
        else:
            # On those platforms where GID doesn't make sense (Windows)
            # we expect it to be -1
            self.assertEqual(gid, -1)

    def test_username(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        # generic test, only access the attribute (twice for testing the
        # caching code)
        p.username
        p.username

        # UNIX tests
        if POSIX:
            import pwd
            user = pwd.getpwuid(p.uid).pw_name
            self.assertEqual(p.username, user)

        # Windows tests
        elif WINDOWS:
            expected_username = os.environ['USERNAME']
            expected_domain = os.environ['USERDOMAIN']
            domain, username = p.username.split('\\')
            self.assertEqual(domain, expected_domain)
            self.assertEqual(username, expected_username)

    if hasattr(psutil.Process, "getcwd"):

        def test_getcwd(self):
            self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
            wait_for_pid(self.proc.pid)
            p = psutil.Process(self.proc.pid)
            self.assertEqual(p.getcwd(), os.getcwd())

        def test_getcwd_2(self):
            cmd = [PYTHON, "-c", "import os; os.chdir('..'); input()"]
            self.proc = subprocess.Popen(cmd, stdout=DEVNULL)
            wait_for_pid(self.proc.pid)
            p = psutil.Process(self.proc.pid)
            time.sleep(0.1)
            expected_dir = os.path.dirname(os.getcwd())
            self.assertEqual(p.getcwd(), expected_dir)

    def test_get_open_files(self):
        thisfile = os.path.join(os.getcwd(), __file__)
        cmdline = "f = open(r'%s', 'r'); input();" %thisfile
        self.proc = subprocess.Popen([PYTHON, "-c", cmdline])
        wait_for_pid(self.proc.pid)
        time.sleep(0.1)
        p = psutil.Process(self.proc.pid)
        files = p.get_open_files()
        self.assertTrue(thisfile in files)

    if hasattr(psutil.Process, "get_connections"):

        def test_get_connections(self):
            arg = "import socket;" \
                  "s = socket.socket();" \
                  "s.bind(('127.0.0.1', 0));" \
                  "s.listen(1);" \
                  "conn, addr = s.accept();" \
                  "raw_input();" 
            self.proc = subprocess.Popen([PYTHON, "-c", arg])
            time.sleep(0.1)
            p = psutil.Process(self.proc.pid)
            cons = p.get_connections()
            self.assertTrue(len(cons) == 1)
            con = cons[0]
            self.assertEqual(con.family, socket.AF_INET)
            self.assertEqual(con.type, socket.SOCK_STREAM)
            self.assertEqual(con.status, "LISTEN")
            ip, port = con.local_address
            self.assertEqual(ip, '127.0.0.1')
            self.assertEqual(con.remote_address, ())
    
        def test_get_connections_all(self):

            def check_address(addr, family):
                if not addr:
                    return
                ip, port = addr
                self.assertTrue(isinstance(port, int))
                if family == socket.AF_INET:
                    ip = map(int, ip.split('.'))
                    self.assertTrue(len(ip) == 4)
                    for num in ip:
                        self.assertTrue(0 <= num <= 255)
                self.assertTrue(0 <= port <= 65535)

            for p in psutil.process_iter():
                for conn in p.get_connections():
                    self.assertTrue(conn.type in (socket.SOCK_STREAM, 
                                                  socket.SOCK_DGRAM))
                    self.assertTrue(conn.family in (socket.AF_INET, 
                                                    socket.AF_INET6))
                    check_address(conn.local_address, conn.family)
                    check_address(conn.remote_address, conn.family)
                    # actually try to bind the local socket
                    s = socket.socket(conn.family, conn.type)
                    s.bind((conn.local_address[0], 0))
                    s.close()

    def test_parent_ppid(self):
        this_parent = os.getpid()
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        self.assertEqual(p.ppid, this_parent)
        self.assertEqual(p.parent.pid, this_parent)
        # no other process is supposed to have us as parent
        for p in psutil.process_iter():
            if p.pid == self.proc.pid:
                continue
            self.assertTrue(p.ppid != this_parent)

    def test_get_children(self):
        p = psutil.Process(os.getpid())
        self.assertEqual(p.get_children(), [])
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        children = p.get_children()
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].pid, self.proc.pid)
        self.assertEqual(children[0].ppid, os.getpid())

    def test_suspend_resume(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        p.suspend()
        p.resume()

    def test_get_pid_list(self):
        plist = [x.pid for x in psutil.get_process_list()]
        pidlist = psutil.get_pid_list()
        self.assertEqual(plist.sort(), pidlist.sort())
        # make sure every pid is unique
        self.assertEqual(len(pidlist), len(set(pidlist)))

    def test_test(self):
        # test for psutil.test() function
        stdout = sys.stdout
        sys.stdout = DEVNULL
        try:
            psutil.test()
        finally:
            sys.stdout = stdout

    def test_types(self):
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        self.assert_(isinstance(p.pid, int))
        self.assert_(isinstance(p.ppid, int))
        self.assert_(isinstance(p.parent, psutil.Process))
        self.assert_(isinstance(p.name, str))
        self.assert_(isinstance(p.path, str))
        self.assert_(isinstance(p.cmdline, list))
        self.assert_(isinstance(p.uid, int))
        self.assert_(isinstance(p.gid, int))
        self.assert_(isinstance(p.create_time, float))
        self.assert_(isinstance(p.username, str) or \
                     isinstance(p.username, type(u'')))
        if hasattr(p, 'getcwd'):
            self.assert_(isinstance(p.getcwd(), str))
        if hasattr(p, 'get_open_files'):
            # XXX
            if not LINUX and self.__class__.__name__ != "LimitedUserTestCase":
                self.assert_(isinstance(p.get_open_files(), list))
                for path in p.get_open_files():
                    self.assert_(isinstance(path, str) or \
                                 isinstance(path, type(u'')))
        if hasattr(p, 'get_connections'):
            self.assert_(isinstance(p.get_connections(), list))
        self.assert_(isinstance(p.is_running(), bool))
        self.assert_(isinstance(p.get_cpu_times(), tuple))
        self.assert_(isinstance(p.get_cpu_times()[0], float))
        self.assert_(isinstance(p.get_cpu_times()[1], float))
        self.assert_(isinstance(p.get_cpu_percent(), float))
        self.assert_(isinstance(p.get_memory_info(), tuple))
        self.assert_(isinstance(p.get_memory_info()[0], int))
        self.assert_(isinstance(p.get_memory_info()[1], int))
        self.assert_(isinstance(p.get_memory_percent(), float))
        self.assert_(isinstance(psutil.get_process_list(), list))
        self.assert_(isinstance(psutil.get_process_list()[0], psutil.Process))
        self.assert_(isinstance(psutil.process_iter(), types.GeneratorType))
        self.assert_(isinstance(psutil.process_iter().next(), psutil.Process))
        self.assert_(isinstance(psutil.get_pid_list(), list))
        self.assert_(isinstance(psutil.get_pid_list()[0], int))
        self.assert_(isinstance(psutil.pid_exists(1), bool))

    def test_no_such_process(self):
        # Refers to Issue #12
        self.assertRaises(psutil.NoSuchProcess, psutil.Process, -1)

    def test_invalid_pid(self):
        self.assertRaises(ValueError, psutil.Process, "1")

    def test_zombie_process(self):
        # Test that NoSuchProcess exception gets raised in the event the
        # process dies after we create the Process object.
        # Example:
        #  >>> proc = Process(1234)
        #  >>> time.sleep(5)  # time-consuming task, process dies in meantime
        #  >>> proc.name
        # Refers to Issue #15
        self.proc = subprocess.Popen(PYTHON, stdout=DEVNULL, stderr=DEVNULL)
        p = psutil.Process(self.proc.pid)
        p.kill()
        self.proc.wait()

        self.assertRaises(psutil.NoSuchProcess, getattr, p, "ppid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "parent")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "name")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "path")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "cmdline")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "uid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "gid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "create_time")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "username")
        if hasattr(p, 'getcwd'):
            self.assertRaises(psutil.NoSuchProcess, p.getcwd)
        if hasattr(p, 'get_open_files'):
            self.assertRaises(psutil.NoSuchProcess, p.get_open_files)
        if hasattr(p, 'get_connections'):
            self.assertRaises(psutil.NoSuchProcess, p.get_connections)
        self.assertRaises(psutil.NoSuchProcess, p.suspend)
        self.assertRaises(psutil.NoSuchProcess, p.resume)
        self.assertRaises(psutil.NoSuchProcess, p.kill)
        self.assertRaises(psutil.NoSuchProcess, p.terminate)
        self.assertRaises(psutil.NoSuchProcess, p.send_signal, signal.SIGTERM)
        self.assertRaises(psutil.NoSuchProcess, p.get_cpu_times)
        self.assertRaises(psutil.NoSuchProcess, p.get_cpu_percent)
        self.assertRaises(psutil.NoSuchProcess, p.get_memory_info)
        self.assertRaises(psutil.NoSuchProcess, p.get_memory_percent)
        self.assertFalse(p.is_running())

    def test_fetch_all(self):
        valid_procs = 0
        attrs = ['__str__', 'create_time', 'username', 'getcwd', 'get_cpu_times',
                 'get_cpu_percent', 'get_memory_info', 'get_memory_percent',
                 'get_open_files']
        for p in psutil.process_iter():
            for attr in attrs:
                # XXX - temporary: skip slow Python implementation 
                if WINDOWS and attr in ('username', 'get_open_files'):
                    continue
                if POSIX and attr == 'get_open_files':
                    continue

                try:
                    attr = getattr(p, attr, None)
                    if attr is not None and callable(attr):
                        attr()
                    valid_procs += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
                except:
                    trace = traceback.format_exc()
                    self.fail('Exception raised for method %s, pid %s:\n%s'
                              %(attr, p.pid, trace))

        # we should always have a non-empty list, not including PID 0 etc.
        # special cases.
        self.assertTrue(valid_procs > 0)

    def test_pid_0(self):
        # Process(0) is supposed to work on all platforms even if with
        # some differences
        p = psutil.Process(0)
        if WINDOWS:
            self.assertEqual(p.name, 'System Idle Process')
        elif LINUX:
            self.assertEqual(p.name, 'sched')
        elif BSD:
            self.assertEqual(p.name, 'swapper')
        elif OSX:
            self.assertEqual(p.name, 'kernel_task')

        # use __str__ to access all common Process properties to check
        # that nothing strange happens
        str(p)

        if OSX and os.geteuid() != 0:
            self.assertRaises(psutil.AccessDenied, p.get_memory_info)
        else:
            p.get_memory_info()

        # username property
        if LINUX:
            self.assertEqual(p.username, 'root')
        elif BSD or OSX:
            self.assertEqual(p.username, 'root')
        elif WINDOWS:
            self.assertEqual(p.username, 'NT AUTHORITY\\SYSTEM')
        else:
            p.username

        # PID 0 is supposed to be available on all platforms
        self.assertTrue(0 in psutil.get_pid_list())
        self.assertTrue(psutil.pid_exists(0))


    # --- OS specific tests

    # UNIX specific tests

    if POSIX:
        if hasattr(os, 'getuid') and os.getuid() > 0:
            def test_unix_access_denied(self):
                p = psutil.Process(1)
                self.assertRaises(psutil.AccessDenied, p.kill)
                self.assertRaises(psutil.AccessDenied, p.send_signal, signal.SIGTERM)
                self.assertRaises(psutil.AccessDenied, p.terminate)
                self.assertRaises(psutil.AccessDenied, p.suspend)
                self.assertRaises(psutil.AccessDenied, p.resume)


if hasattr(os, 'getuid'):
    class LimitedUserTestCase(TestCase):
        """Repeat the previous tests by using a limited user.
        Executed only on UNIX and only if the user who run the test script
        is root.
        """
        # the uid/gid the test suite runs under
        PROCESS_UID = os.getuid()
        PROCESS_GID = os.getgid()

        def setUp(self):
            os.setegid(1000)
            os.seteuid(1000)
            TestCase.setUp(self)

        def tearDown(self):
            os.setegid(self.PROCESS_UID)
            os.seteuid(self.PROCESS_GID)
            TestCase.tearDown(self)

        # overridden tests known to raise AccessDenied when run
        # as limited user on different platforms

        if LINUX:

            def test_getcwd(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_getcwd, self)

            def test_getcwd_2(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_getcwd_2, self)

            def test_get_open_files(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_get_open_files, self)

        if BSD:

            def test_get_open_files(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_get_open_files, self)

            def test_get_connections_all(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_get_connections_all, self)


def test_main():
    tests = []
    test_suite = unittest.TestSuite()

    tests.append(TestCase)

    if hasattr(os, 'getuid') and os.getuid() == 0:
        tests.append(LimitedUserTestCase)

    if POSIX:
        from _posix import PosixSpecificTestCase
        tests.append(PosixSpecificTestCase)

    # import the specific platform test suite
    if LINUX:
        from _linux import LinuxSpecificTestCase as stc
    elif WINDOWS:
        from _windows import WindowsSpecificTestCase as stc
    elif OSX:
        from _osx import OSXSpecificTestCase as stc
    elif BSD:
        from _bsd import BSDSpecificTestCase as stc
    tests.append(stc)

    for test_class in tests:
        test_suite.addTest(unittest.makeSuite(test_class))

    unittest.TextTestRunner(verbosity=2).run(test_suite)
    reap_children()
    DEVNULL.close()

if __name__ == '__main__':
    test_main()


