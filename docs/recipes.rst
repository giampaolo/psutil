Recipes
=======

A collection of standalone, copy-paste solutions to specific problems. Each
recipe focuses on a single problem and provides a minimal solution which can be
adapted to real-world code. The examples are intentionally short and avoid
unnecessary abstractions so that the underlying psutil APIs are easy to
understand. Most of them are not meant to be used in production.

.. contents::
   :local:
   :depth: 3

Processes
---------

Finding processes
^^^^^^^^^^^^^^^^^

Find process by name:

.. code-block:: python

  import psutil

  def find_procs_by_name(name):
      ls = []
      for p in psutil.process_iter(["name"]):
          if p.info["name"] == name:
              ls.append(p)
      return ls

----

A bit more advanced, check string against :meth:`Process.name`,
:meth:`Process.exe` and :meth:`Process.cmdline`:

.. code-block:: python

  import os
  import psutil

  def find_procs_by_name_ex(name):
      ls = []
      for p in psutil.process_iter(["name", "exe", "cmdline"]):
          if (
              name == p.info["name"]
              or (p.info["exe"] and os.path.basename(p.info["exe"]) == name)
              or (p.info["cmdline"] and p.info["cmdline"][0] == name)
          ):
              ls.append(p)
      return ls

----

Find the process listening on a given TCP port:

.. code-block:: python

  import psutil

  def find_proc_by_port(port):
      for proc in psutil.process_iter():
          try:
              cons = proc.net_connections(kind="tcp")
          except psutil.Error:
              pass
          else:
              for conn in cons:
                  if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                      return proc
      return None

----

Find all processes that have an active connection to a given remote IP:

.. code-block:: python

  import psutil

  def find_procs_by_remote_host(host):
      ls = []
      for proc in psutil.process_iter():
          try:
              cons = proc.net_connections(kind="inet")
          except psutil.Error:
              pass
          else:
              for conn in cons:
                  if conn.raddr and conn.raddr.ip == host:
                      ls.append(proc)
      return ls

----

Find all processes that have a given file open (useful on Windows):

.. code-block:: python

  import psutil

  def find_procs_using_file(path):
      ls = []
      for p in psutil.process_iter(["open_files"]):
          for f in p.info["open_files"]:
              if f.path == path:
                  ls.append(p)
                  break
      return ls

Filtering and sorting processes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Processes owned by user:

.. code-block:: python

  >>> import getpass
  >>> import psutil
  >>> from pprint import pprint as pp
  >>> pp([(p.pid, p.info["name"]) for p in psutil.process_iter(["name", "username"]) if p.info["username"] == getpass.getuser()])
  (16832, 'bash'),
  (19772, 'ssh'),
  (20492, 'python')]

----

Processes actively running:

.. code-block:: python

  >>> pp([(p.pid, p.info) for p in psutil.process_iter(["name", "status"]) if p.info["status"] == psutil.STATUS_RUNNING])
  [(1150, {'name': 'Xorg', 'status': <ProcessStatus.STATUS_RUNNING: 'running'>}),
   (1776, {'name': 'unity-panel-service', 'status': <ProcessStatus.STATUS_RUNNING: 'running'>}),
   (20492, {'name': 'python', 'status': <ProcessStatus.STATUS_RUNNING: 'running'>})]

----

Processes using log files:

.. code-block:: python

  >>> for p in psutil.process_iter(["name", "open_files"]):
  ...      for file in p.info["open_files"] or []:
  ...          if file.path.endswith(".log"):
  ...               print("{:<5} {:<10} {}".format(p.pid, p.info["name"][:10], file.path))
  ...
  1510  upstart    /home/giampaolo/.cache/upstart/unity-settings-daemon.log
  2174  nautilus   /home/giampaolo/.local/share/gvfs-metadata/home-ce08efac.log
  2650  chrome     /home/giampaolo/.config/google-chrome/Default/data_reduction_proxy_leveldb/000003.log

----

Processes consuming more than 500M of memory:

.. code-block:: python

  >>> pp([(p.pid, p.info["name"], p.info["memory_info"].rss) for p in psutil.process_iter(["name", "memory_info"]) if p.info["memory_info"].rss > 500 * 1024 * 1024])
  [(2650, 'chrome', 532324352),
   (3038, 'chrome', 1120088064),
   (21915, 'sublime_text', 615407616)]

----

Top 3 processes which consumed the most CPU time:

.. code-block:: python

  >>> pp([(p.pid, p.info["name"], sum(p.info["cpu_times"])) for p in sorted(psutil.process_iter(["name", "cpu_times"]), key=lambda p: sum(p.info["cpu_times"][:2]))][-3:])
  [(2721, 'chrome', 10219.73),
   (1150, 'Xorg', 11116.989999999998),
   (2650, 'chrome', 18451.97)]

----

Top N processes by cumulative disk read + write bytes (similar to ``iotop``):

.. code-block:: python

  import psutil


  def top_io_procs(n=5):
      procs = []
      for p in psutil.process_iter(["io_counters"]):
          try:
              io = p.io_counters()
          except psutil.Error:
              pass
          else:
              procs.append((io.read_bytes + io.write_bytes, p))
      procs.sort(key=lambda x: x[0], reverse=True)
      return procs[:n]

----

Top N processes by open file descriptors (useful for diagnosing fd leaks):

.. code-block:: python

  import psutil

  def top_open_files(n=5):
      procs = []
      for p in psutil.process_iter():
          try:
              procs.append((p.num_fds(), p))
          except (psutil.NoSuchProcess, psutil.AccessDenied):
              pass
      procs.sort(key=lambda x: x[0], reverse=True)
      return procs[:n]

Monitoring processes
^^^^^^^^^^^^^^^^^^^^

Periodically monitor CPU and memory usage of a process using
:meth:`Process.oneshot` for efficiency:

.. code-block:: python

  import time
  import psutil

  def monitor(pid, interval=1):
      p = psutil.Process(pid)
      while p.is_running():
          with p.oneshot():
              cpu = p.cpu_percent()
              mem = p.memory_info().rss
              print("cpu={:<6} mem={}".format(str(cpu) + "%", mem / 1024 / 1024))
          time.sleep(interval)

.. code-block:: none

  cpu=4.2%   mem=23.4M
  cpu=3.1%   mem=23.5M

Controlling processes
^^^^^^^^^^^^^^^^^^^^^

Kill a process tree (including grandchildren):

.. code-block:: python

  import os
  import signal

  import psutil


  def kill_proc_tree(
      pid,
      sig=signal.SIGTERM,
      include_parent=True,
      timeout=None,
      on_terminate=None,
  ):
      """Kill a process tree (including grandchildren) with signal
      "sig" and return a (gone, still_alive) tuple.
      "on_terminate", if specified, is a callback function which is
      called as soon as a child terminates.
      """
      assert pid != os.getpid(), "I won't kill myself!"
      parent = psutil.Process(pid)
      children = parent.children(recursive=True)
      if include_parent:
          children.append(parent)
      for p in children:
          try:
              p.send_signal(sig)
          except psutil.NoSuchProcess:
              pass
      gone, alive = psutil.wait_procs(
          children, timeout=timeout, callback=on_terminate
      )
      return (gone, alive)

----

Kill / reap zombie (defunct) processes:


.. code-block:: python

  import psutil

  def kill_zombies():
      for p in psutil.process_iter(["status"]):
          if p.info["status"] == psutil.STATUS_ZOMBIE:
              parent = p.parent()
              if parent:
                  parent.terminate()
                  parent.wait()
                  p.wait()

----

Terminate all processes matching a given name:

.. code-block:: python

  import psutil

  def terminate_procs_by_name(name):
      for p in psutil.process_iter(["name"]):
          if p.info["name"] == name:
              p.terminate()

----

Terminate a process gracefully, falling back to ``SIGKILL`` if it does not
exit within the timeout:

.. code-block:: python

  import psutil

  def graceful_kill(pid, timeout=3):
      p = psutil.Process(pid)
      p.terminate()
      try:
          p.wait(timeout=timeout)
      except psutil.TimeoutExpired:
          p.kill()

----

Restart a process:

.. code-block:: python

  import subprocess
  import psutil

  def restart_process(pid):
      p = psutil.Process(pid)
      cmd = p.cmdline()
      p.terminate()
      p.wait()
      return subprocess.Popen(cmd)

----

Temporarily pause and resume a process using a context manager:

.. code-block:: python

  import contextlib
  import psutil

  @contextlib.contextmanager
  def suspended(pid):
      p = psutil.Process(pid)
      p.suspend()
      try:
          yield p
      finally:
          p.resume()

  # usage
  with suspended(pid):
      pass  # process is paused here

----

CPU throttle: limit a process's CPU usage to a target percentage by
alternating :meth:`Process.suspend` and :meth:`Process.resume`:

.. code-block:: python

  import time
  import psutil

  def throttle(pid, max_cpu_percent=50, interval=0.1):
      """Slow down a process so it uses at most max_cpu_percent% CPU."""
      p = psutil.Process(pid)
      while p.is_running():
          cpu = p.cpu_percent(interval=interval)
          if cpu > max_cpu_percent:
              p.suspend()
              time.sleep(interval * cpu / max_cpu_percent)
              p.resume()

----

Restart a process automatically if it dies:

.. code-block:: python

  import subprocess
  import time

  import psutil


  def watchdog(cmd, max_restarts=None, interval=1):
      """Run cmd as a persistent process. Restart on failure, optionally
      with a max restarts. Logs start, exit, and restart events.
      """
      restarts = 0
      while True:
          proc = subprocess.Popen(cmd)
          p = psutil.Process(proc.pid)
          print(f"started PID {p.pid}")
          proc.wait()

          if proc.returncode == 0:
              # success
              print(f"PID {p.pid} exited cleanly")
              break

          # failure
          restarts += 1
          print(f"PID {p.pid} died, restarting ({restarts})")

          if max_restarts is not None and restarts > max_restarts:
              print("max restarts reached, giving up")
              break

          time.sleep(interval)


  if __name__ == "__main__":
      watchdog(["python3", "script.py"])


System
------

All APIs returning amounts (memory, disk, network I/O) express them in bytes.
This ``bytes2human()`` utility function used in the examples below converts
them to a human-readable string:

.. code-block:: python

  def bytes2human(n):
      """
      >>> bytes2human(10000)
      '9.8K'
      >>> bytes2human(100001221)
      '95.4M'
      """
      symbols = ("K", "M", "G", "T", "P", "E", "Z", "Y")
      prefix = {}
      for i, s in enumerate(symbols):
          prefix[s] = 1 << (i + 1) * 10
      for s in reversed(symbols):
          if abs(n) >= prefix[s]:
              value = float(n) / prefix[s]
              return "{:.1f}{}".format(value, s)
      return "{}B".format(n)

Memory
^^^^^^

Show both RAM and swap usage in human-readable form:

.. code-block:: python

  import psutil

  def print_memory():
      ram = psutil.virtual_memory()
      swap = psutil.swap_memory()
      print(
          "RAM:  total={}, used={}, free={}, percent={}%".format(
              bytes2human(ram.total),
              bytes2human(ram.used),
              bytes2human(ram.available),
              ram.percent,
          )
      )
      print(
          "Swap: total={}, used={}, free={}, percent={}%".format(
              bytes2human(swap.total),
              bytes2human(swap.used),
              bytes2human(swap.free),
              swap.percent,
          )
      )


.. code-block:: none

  RAM:  total=8.0G, used=4.5G, free=3.0G, percent=56.2%
  Swap: total=2.0G, used=0.1G, free=1.9G, percent=4.1%

CPU
^^^

Print real-time CPU usage percentage:

.. code-block:: python

  import psutil

  while True:
      print("CPU: {}%".format(psutil.cpu_percent(interval=1)))

.. code-block:: none

  CPU: 2.1%
  CPU: 1.4%
  CPU: 0.9%

----

For each CPU core:

.. code-block:: python

  import psutil

  while True:
      for i, pct in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
          print("CPU-{}: {}%".format(i, pct))
      print()

.. code-block:: none

  CPU-0: 1.0%
  CPU-1: 2.1%
  CPU-2: 3.0%

Disks
^^^^^

Show disk usage for all mounted partitions:

.. code-block:: python

  import psutil

  def print_disk_usage():
      for part in psutil.disk_partitions():
          usage = psutil.disk_usage(part.mountpoint)
          print("{:<20} total={:<8} used={:<8} free={:<8} percent={}%".format(
              part.mountpoint,
              bytes2human(usage.total), bytes2human(usage.used),
              bytes2human(usage.free), usage.percent))

.. code-block:: none

  /               total=47.8G    used=17.4G    free=27.9G    percent=38.4%
  /boot/efi       total=256.0M   used=73.6M    free=182.4M   percent=28.8%
  /home           total=878.7G   used=497.5G   free=336.5G   percent=59.7%


----

Show real-time disk I/O:

.. code-block:: python

  import psutil, time

  def disk_io():
      while True:
          before = psutil.disk_io_counters()
          time.sleep(1)
          after = psutil.disk_io_counters()
          r = after.read_bytes - before.read_bytes
          w = after.write_bytes - before.write_bytes
          print("Read: {}/s, Write: {}/s".format(bytes2human(r), bytes2human(w)))

.. code-block:: none

  Read: 1.2M/s, Write: 256.0K/s
  Read: 0.0B/s, Write: 128.0K/s

Network
^^^^^^^

List IP addresses for each network interface:

.. code-block:: python

  import psutil, socket

  def print_net_addrs():
      for iface, addrs in psutil.net_if_addrs().items():
          for addr in addrs:
              if addr.family == socket.AF_INET:
                  print(
                      "{:<15} address={:<15} netmask={}".format(
                          iface, addr.address, addr.netmask
                      )
                  )

.. code-block:: none

  lo              address=127.0.0.1       netmask=255.0.0.0
  eth0            address=10.0.0.4        netmask=255.255.255.0

----

Show real-time network I/O per interface:

.. code-block:: python

  import psutil, time

  def net_io():
      while True:
          before = psutil.net_io_counters(pernic=True)
          time.sleep(1)
          after = psutil.net_io_counters(pernic=True)
          for iface in after:
              s = after[iface].bytes_sent - before[iface].bytes_sent
              r = after[iface].bytes_recv - before[iface].bytes_recv
              print(
                  "{:<10} sent={:<10} recv={}".format(
                      iface, bytes2human(s) + "/s", bytes2human(r) + "/s"
                  )
              )
          print()

.. code-block:: none

  lo         sent=0.0B/s    recv=0.0B/s
  eth0       sent=12.3K/s   recv=45.6K/s

----

List all active TCP connections with their status:

.. code-block:: python

  import psutil

  def netstat():
      templ = "{:<20} {:<20} {:<13} {:<6}"
      print(templ.format("Local", "Remote", "Status", "PID"))
      for conn in psutil.net_connections(kind="tcp"):
          laddr = "{}:{}".format(conn.laddr.ip, conn.laddr.port)
          raddr = (
              "{}:{}".format(conn.raddr.ip, conn.raddr.port)
              if conn.raddr
              else "-"
          )
          print(templ.format(laddr, raddr, conn.status, conn.pid or ""))

.. code-block:: none

  Local             Remote              Status        PID
  :::1716           -                   LISTEN        223441
  127.0.0.1:631     -                   LISTEN
  10.0.0.4:45278    20.222.111.74:443   ESTABLISHED   437213
  10.0.0.4:40130    172.14.148.135:443  ESTABLISHED
  0.0.0.0:22        -                   LISTEN        723345
