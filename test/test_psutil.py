#!/usr/bin/env python
#
# $Id$
#

"""psutil test suite.
Note: this is targeted for python 2.x.
To run it under python 3.x you need to use 2to3 tool first:

$ 2to3 -w test/test_psutil.py
"""

import unittest
import os
import sys
import subprocess
import time
import signal
import types
import traceback
import socket
import warnings

import psutil


PYTHON = os.path.realpath(sys.executable)
DEVNULL = open(os.devnull, 'r+')

POSIX = os.name == 'posix'
LINUX = sys.platform.lower().startswith("linux")
WINDOWS = sys.platform.lower().startswith("win32")
OSX = sys.platform.lower().startswith("darwin")
BSD = sys.platform.lower().startswith("freebsd")


def get_test_subprocess(cmd=PYTHON, stdout=DEVNULL, stderr=DEVNULL, stdin=None):
    """Return a subprocess.Popen object to use in tests.
    By default stdout and stderr are redirected to /dev/null and the 
    python interpreter is used as test process.
    """
    return subprocess.Popen(cmd, stdout=stdout, stderr=stderr, stdin=stdin)
    

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
        try:
            child.kill()
        except psutil.NoSuchProcess:
            pass
        else:
            waitpid(child)


class TestCase(unittest.TestCase):

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
        sproc = get_test_subprocess()
        test_pid = sproc.pid
        wait_for_pid(test_pid)
        p = psutil.Process(test_pid)
        name = p.name
        p.kill()
        sproc.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_terminate(self):
        sproc = get_test_subprocess()
        test_pid = sproc.pid
        wait_for_pid(test_pid)
        p = psutil.Process(test_pid)
        name = p.name
        p.terminate()
        sproc.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_send_signal(self):
        if POSIX:
            sig = signal.SIGKILL
        else:
            sig = signal.SIGTERM
        sproc = get_test_subprocess()
        test_pid = sproc.pid
        p = psutil.Process(test_pid)
        name = p.name
        p.send_signal(sig)
        sproc.wait()
        self.assertFalse(psutil.pid_exists(test_pid) and name == PYTHON)

    def test_TOTAL_PHYMEM(self):
        x = psutil.TOTAL_PHYMEM
        self.assertTrue(isinstance(x, (int, long)))
        self.assertTrue(x > 0)

    def test_used_phymem(self):
        x = psutil.used_phymem()
        self.assertTrue(isinstance(x, (int, long)))
        self.assertTrue(x > 0)

    def test_avail_phymem(self):
        x = psutil.avail_phymem()
        self.assertTrue(isinstance(x, (int, long)))
        self.assertTrue(x > 0)

    def test_total_virtmem(self):
        x = psutil.total_virtmem()
        self.assertTrue(isinstance(x, (int, long)))
        self.assertTrue(x >= 0)

    def test_used_virtmem(self):
        x = psutil.used_virtmem()
        self.assertTrue(isinstance(x, (int, long)))
        self.assertTrue(x >= 0)

    def test_avail_virtmem(self):
        x = psutil.avail_virtmem()
        self.assertTrue(isinstance(x, (int, long)))
        self.assertTrue(x >= 0)

    if hasattr(psutil, "cached_phymem"):
        def test_cached_phymem(self):
            x = psutil.cached_phymem()
            self.assertTrue(isinstance(x, (int, long)))
            self.assertTrue(x >= 0)

    if hasattr(psutil, "phymem_buffers"):
        def test_phymem_buffers(self):
            x = psutil.phymem_buffers()
            self.assertTrue(isinstance(x, (int, long)))
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

    # os.times() is broken on OS X and *BSD, see:
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
        sproc = get_test_subprocess()
        now = time.time()
        wait_for_pid(sproc.pid)
        p = psutil.Process(sproc.pid)
        create_time = p.create_time

        # Use time.time() as base value to compare our result using a
        # tolerance of +/- 1 second.
        # It will fail if the difference between the values is > 2s.
        difference = abs(create_time - now)
        if difference > 2:
            self.fail("expected: %s, found: %s, difference: %s"
                      % (now, create_time, difference))

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
        sproc = get_test_subprocess()
        self.assertEqual(psutil.Process(sproc.pid).pid, sproc.pid)

    def test_eq(self):
        sproc = get_test_subprocess()
        wait_for_pid(sproc.pid)
        self.assertTrue(psutil.Process(sproc.pid) == psutil.Process(sproc.pid))

    def test_is_running(self):
        sproc = get_test_subprocess()
        wait_for_pid(sproc.pid)
        p = psutil.Process(sproc.pid)
        self.assertTrue(p.is_running())
        psutil.Process(sproc.pid).kill()
        sproc.wait()
        self.assertFalse(p.is_running())

    def test_pid_exists(self):
        if hasattr(os, 'getpid'):
            self.assertTrue(psutil.pid_exists(os.getpid()))
        self.assertFalse(psutil.pid_exists(-1))

    def test_exe(self):
        sproc = get_test_subprocess()
        wait_for_pid(sproc.pid)
        self.assertEqual(psutil.Process(sproc.pid).exe, PYTHON)
        for p in psutil.process_iter():
            if not p.exe:
                continue
            if not os.path.exists(p.exe):
                self.fail("%s does not exist (pid=%s, name=%s, cmdline=%s)" \
                          % (repr(p.exe), p.pid, p.name, p.cmdline))
            if hasattr(os, 'access') and hasattr(os, "X_OK"):
                if not os.access(p.exe, os.X_OK):
                    self.fail("%s is not executable (pid=%s, name=%s, cmdline=%s)" \
                              % (repr(p.exe), p.pid, p.name, p.cmdline))

    def test_path(self):
        proc = psutil.Process(os.getpid())
        warnings.filterwarnings("error")
        try:
            self.assertRaises(DeprecationWarning, getattr, proc, 'path')
        finally:
            warnings.resetwarnings()
        warnings.filterwarnings("ignore")
        try:
            for proc in psutil.process_iter():
                if proc.exe:
                    self.assertEqual(proc.path, os.path.dirname(proc.exe))
                else:
                    self.assertEqual(proc.path, "")
        finally:
            warnings.resetwarnings()

    def test_cmdline(self):
        sproc = get_test_subprocess([PYTHON, "-E"])
        wait_for_pid(sproc.pid)
        self.assertEqual(psutil.Process(sproc.pid).cmdline, [PYTHON, "-E"])

    def test_name(self):
        sproc = get_test_subprocess(PYTHON)
        wait_for_pid(sproc.pid)
        self.assertEqual(psutil.Process(sproc.pid).name, os.path.basename(PYTHON))

    def test_uid(self):
        sproc = get_test_subprocess()
        wait_for_pid(sproc.pid)
        uid = psutil.Process(sproc.pid).uid
        if hasattr(os, 'getuid'):
            self.assertEqual(uid, os.getuid())
        else:
            # On those platforms where UID doesn't make sense (Windows)
            # we expect it to be -1
            self.assertEqual(uid, -1)

    def test_gid(self):
        sproc = get_test_subprocess()
        wait_for_pid(sproc.pid)
        gid = psutil.Process(sproc.pid).gid
        if hasattr(os, 'getgid'):
            self.assertEqual(gid, os.getgid())
        else:
            # On those platforms where GID doesn't make sense (Windows)
            # we expect it to be -1
            self.assertEqual(gid, -1)

    def test_username(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        # generic test, only access the attribute (twice for testing the
        # caching code)
        p.username
        p.username

        if POSIX:
            import pwd
            user = pwd.getpwuid(p.uid).pw_name
            self.assertEqual(p.username, user)
        elif WINDOWS:
            expected_username = os.environ['USERNAME']
            expected_domain = os.environ['USERDOMAIN']
            domain, username = p.username.split('\\')
            self.assertEqual(domain, expected_domain)
            self.assertEqual(username, expected_username)

    if hasattr(psutil.Process, "getcwd"):

        def test_getcwd(self):
            sproc = get_test_subprocess()
            wait_for_pid(sproc.pid)
            p = psutil.Process(sproc.pid)
            self.assertEqual(p.getcwd(), os.getcwd())

        def test_getcwd_2(self):
            cmd = [PYTHON, "-c", "import os, time; os.chdir('..'); time.sleep(10)"]
            sproc = get_test_subprocess(cmd)
            wait_for_pid(sproc.pid)
            p = psutil.Process(sproc.pid)
            time.sleep(0.1)
            expected_dir = os.path.dirname(os.getcwd())
            self.assertEqual(p.getcwd(), expected_dir)

    def test_get_open_files(self):
        thisfile = os.path.join(os.getcwd(), __file__)
        # current process
        p = psutil.Process(os.getpid())
        files = p.get_open_files()
        self.assertFalse(thisfile in files)
        f = open(thisfile, 'r')
        files = p.get_open_files()
        self.assertTrue(thisfile in files)
        f.close()
        for file in files:
            self.assertTrue(os.path.isfile(file))
        # subprocess
        cmdline = "import time; f = open(r'%s', 'r'); time.sleep(100);" % thisfile
        sproc = get_test_subprocess([PYTHON, "-c", cmdline])
        wait_for_pid(sproc.pid)
        time.sleep(0.1)
        p = psutil.Process(sproc.pid)
        files = p.get_open_files()
        self.assertTrue(thisfile in files)
        for file in files:
            self.assertTrue(os.path.isfile(file))
        # all processes
        for proc in psutil.process_iter():
            try:
                files = proc.get_open_files()
            except psutil.Error:
                pass
            else:
                for file in files:
                    self.assertTrue(os.path.isfile(file))

    def test_get_connections(self):
        arg = "import socket, time;" \
              "s = socket.socket();" \
              "s.bind(('127.0.0.1', 0));" \
              "s.listen(1);" \
              "conn, addr = s.accept();" \
              "time.sleep(100);"
        sproc = subprocess.Popen([PYTHON, "-c", arg])
        time.sleep(0.1)
        p = psutil.Process(sproc.pid)
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

        def supports_ipv6():
            if not socket.has_ipv6 or not hasattr(socket, "AF_INET6"):
                return False
            try:
                sock = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
                sock.bind(("::1", 0))
            except (socket.error, socket.gaierror):
                return False
            else:
                sock.close()
                return True

        # all values are supposed to match Linux's tcp_states.h states
        # table across all platforms.
        valid_states = ["ESTABLISHED", "SYN_SENT", "SYN_RECV", "FIN_WAIT1",
                        "FIN_WAIT2", "TIME_WAIT", "CLOSE", "CLOSE_WAIT",
                        "LAST_ACK", "LISTEN", "CLOSING", ""]

        tcp_template = "import socket;" \
                       "s = socket.socket({family}, socket.SOCK_STREAM);" \
                       "s.bind(('{addr}', 0));" \
                       "s.listen(1);" \
                       "conn, addr = s.accept();"

        udp_template = "import socket, time;" \
                       "s = socket.socket({family}, socket.SOCK_DGRAM);" \
                       "s.bind(('{addr}', 0));" \
                       "time.sleep(100);"

        tcp4_template = tcp_template.format(family=socket.AF_INET, addr="127.0.0.1")
        udp4_template = udp_template.format(family=socket.AF_INET, addr="127.0.0.1")
        tcp6_template = tcp_template.format(family=socket.AF_INET6, addr="::1")
        udp6_template = udp_template.format(family=socket.AF_INET6, addr="::1")

        # launch various subprocess instantiating a socket of various
        # families  and tupes to enrich psutil results
        tcp4_proc = subprocess.Popen([PYTHON, "-c", tcp4_template])
        udp4_proc = subprocess.Popen([PYTHON, "-c", udp4_template])
        if supports_ipv6():
            tcp6_proc = subprocess.Popen([PYTHON, "-c", tcp6_template])
            udp6_proc = subprocess.Popen([PYTHON, "-c", udp6_template])
        else:
            tcp6_proc = None
            udp6_proc = None

        time.sleep(0.1)
        this_proc = psutil.Process(os.getpid())
        children_pids = [p.pid for p in this_proc.get_children()]
        for p in psutil.process_iter():
            try:
                cons = p.get_connections()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
            else:
                for conn in cons:
                    self.assertTrue(conn.type in (socket.SOCK_STREAM,
                                                  socket.SOCK_DGRAM))
                    self.assertTrue(conn.family in (socket.AF_INET,
                                                    socket.AF_INET6))
                    check_address(conn.local_address, conn.family)
                    check_address(conn.remote_address, conn.family)
                    if conn.status not in valid_states:
                        self.fail("%s is not a valid status" %conn.status)
                    # actually try to bind the local socket
                    s = socket.socket(conn.family, conn.type)
                    s.bind((conn.local_address[0], 0))
                    s.close()

                # check matches against subprocesses
                if p.pid in children_pids:
                    self.assertTrue(len(cons) == 1)
                    conn = cons[0]
                    # TCP v4
                    if p.pid == tcp4_proc.pid:
                        self.assertEqual(conn.family, socket.AF_INET)
                        self.assertEqual(conn.type, socket.SOCK_STREAM)
                        self.assertEqual(conn.local_address[0], "127.0.0.1")
                        self.assertEqual(conn.remote_address, ())
                        self.assertEqual(conn.status, "LISTEN")
                    # UDP v4
                    elif p.pid == udp4_proc.pid:
                        self.assertEqual(conn.family, socket.AF_INET)
                        self.assertEqual(conn.type, socket.SOCK_DGRAM)
                        self.assertEqual(conn.local_address[0], "127.0.0.1")
                        self.assertEqual(conn.remote_address, ())
                        self.assertEqual(conn.status, "")
                    # TCP v6
                    elif p.pid == getattr(tcp6_proc, "pid", None):
                        self.assertEqual(conn.family, socket.AF_INET6)
                        self.assertEqual(conn.type, socket.SOCK_STREAM)
                        self.assertEqual(conn.local_address[0], "::1")
                        self.assertEqual(conn.remote_address, ())
                        self.assertEqual(conn.status, "LISTEN")
                    # UDP v6
                    elif p.pid == getattr(udp6_proc, "pid", None):
                        self.assertEqual(conn.family, socket.AF_INET6)
                        self.assertEqual(conn.type, socket.SOCK_DGRAM)
                        self.assertEqual(conn.local_address[0], "::1")
                        self.assertEqual(conn.remote_address, ())
                        self.assertEqual(conn.status, "")

    def test_parent_ppid(self):
        this_parent = os.getpid()
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        self.assertEqual(p.ppid, this_parent)
        self.assertEqual(p.parent.pid, this_parent)
        # no other process is supposed to have us as parent
        for p in psutil.process_iter():
            if p.pid == sproc.pid:
                continue
            self.assertTrue(p.ppid != this_parent)

    def test_get_children(self):
        p = psutil.Process(os.getpid())
        self.assertEqual(p.get_children(), [])
        sproc = get_test_subprocess()
        children = p.get_children()
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].pid, sproc.pid)
        self.assertEqual(children[0].ppid, os.getpid())

    def test_suspend_resume(self):
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
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
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        self.assert_(isinstance(p.pid, int))
        self.assert_(isinstance(p.ppid, int))
        self.assert_(isinstance(p.parent, psutil.Process))
        self.assert_(isinstance(p.name, str))
        self.assert_(isinstance(p.exe, str))
        self.assert_(isinstance(p.cmdline, list))
        self.assert_(isinstance(p.uid, int))
        self.assert_(isinstance(p.gid, int))
        self.assert_(isinstance(p.create_time, float))
        self.assert_(isinstance(p.username, (unicode, str)))
        if hasattr(p, 'getcwd'):
            if not POSIX and self.__class__.__name__ != "LimitedUserTestCase":
                self.assert_(isinstance(p.getcwd(), str))
        if not POSIX and self.__class__.__name__ != "LimitedUserTestCase":
            self.assert_(isinstance(p.get_open_files(), list))
            for path in p.get_open_files():
                self.assert_(isinstance(path, (unicode, str)))
        if not POSIX and self.__class__.__name__ != "LimitedUserTestCase":
            self.assert_(isinstance(p.get_connections(), list))
        self.assert_(isinstance(p.is_running(), bool))
        if not OSX or self.__class__.__name__ != "LimitedUserTestCase":
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
        self.assertRaises(ValueError, psutil.Process, None)

    def test_zombie_process(self):
        # Test that NoSuchProcess exception gets raised in the event the
        # process dies after we create the Process object.
        # Example:
        #  >>> proc = Process(1234)
        #  >>> time.sleep(5)  # time-consuming task, process dies in meantime
        #  >>> proc.name
        # Refers to Issue #15
        sproc = get_test_subprocess()
        p = psutil.Process(sproc.pid)
        p.kill()
        sproc.wait()

        self.assertRaises(psutil.NoSuchProcess, getattr, p, "ppid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "parent")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "name")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "exe")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "cmdline")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "uid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "gid")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "create_time")
        self.assertRaises(psutil.NoSuchProcess, getattr, p, "username")
        if hasattr(p, 'getcwd'):
            self.assertRaises(psutil.NoSuchProcess, p.getcwd)
        self.assertRaises(psutil.NoSuchProcess, p.get_open_files)
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
        self.assertRaises(psutil.NoSuchProcess, p.get_children)
        self.assertFalse(p.is_running())

    def test_fetch_all(self):
        valid_procs = 0
        attrs = ['__str__', 'create_time', 'username', 'getcwd', 'get_cpu_times',
                 'get_cpu_percent', 'get_memory_info', 'get_memory_percent',
                 'get_open_files']
        for p in psutil.process_iter():
            for attr in attrs:
                # skip slow Python implementation; we're reasonably sure
                # it works anyway
                if POSIX and attr == 'get_open_files':
                    continue
                try:
                    attr = getattr(p, attr, None)
                    if attr is not None and callable(attr):
                        attr()
                    valid_procs += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied), err:
                    self.assertEqual(err.pid, p.pid)
                    self.assertTrue(str(err))
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

        if OSX : #and os.geteuid() != 0:
            self.assertRaises(psutil.AccessDenied, p.get_memory_info)
            self.assertRaises(psutil.AccessDenied, p.get_cpu_times)
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

    # OS X specific overrides
    if OSX:
        def test_get_connections(self):
            pass
        def test_get_connections_all(self):
            pass
        def test_get_open_files(self):
            pass

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

            def test_get_connections(self):
                pass

        if OSX:
            def test_get_connections(self):
                pass
            def test_get_connections_all(self):
                pass
            def test_get_open_files(self):
                pass
            def test_pid_0(self):
                pass

        if BSD:

            def test_get_open_files(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_get_open_files, self)

            def test_get_connections(self):
                self.assertRaises(psutil.AccessDenied, TestCase.test_get_connections, self)


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


