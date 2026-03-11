.. include:: _links.rst

Recipes
=======

A collection of standalone, copy-paste solutions to specific problems.
Each recipe focuses on a single problem and provides a minimal, copy-paste
solution which can be adapted to real-world code. The examples are
intentionally short and avoid unnecessary abstractions so that the underlying
psutil APIs are easy to understand.

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

A bit more advanced, check string against :meth:`Process.name()`,
:meth:`Process.exe()` and :meth:`Process.cmdline()`:

.. code-block:: python

  import os
  import psutil

  def find_procs_by_name(name):
      ls = []
      for p in psutil.process_iter(["name", "exe", "cmdline"]):
          if (
              name == p.info["name"]
              or (p.info["exe"] and os.path.basename(p.info["exe"]) == name)
              or (p.info["cmdline"] and p.info["cmdline"][0] == name)
          ):
              ls.append(p)
      return ls

Find the process listening on a given TCP port:

.. code-block:: python

  import psutil

  def find_proc_by_port(port):
      for proc in psutil.process_iter():
          for conn in proc.net_connections(kind="tcp"):
              if conn.laddr.port == port and conn.status == psutil.CONN_LISTEN:
                  return proc
      return None

Find all processes that have a given environment variable set to a specific
value (e.g. to identify processes running inside a virtualenv):

.. code-block:: python

  import psutil

  def find_procs_by_env(key, value):
      ls = []
      for p in psutil.process_iter():
          try:
              if p.environ().get(key) == value:
                  ls.append(p)
          except psutil.Error:
              pass
      return ls

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

Find all zombie (defunct) processes:

.. code-block:: python

  import psutil

  def find_zombies():
      return [p for p in psutil.process_iter(["name", "status"])
              if p.info["status"] == psutil.STATUS_ZOMBIE]

Find all processes that have a given file open (useful on Windows):

.. code-block:: python

  import psutil

  def find_procs_using_file(path):
      ls = []
      for p in psutil.process_iter():
          try:
              for f in p.open_files():
                  if f.path == path:
                      ls.append(p)
                      break
          except psutil.Error:
              pass
      return ls

Filtering and sorting processes
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

A collection of code samples showing how to use :func:`process_iter()` to
filter and sort processes.

Processes owned by user:

.. code-block:: python

  >>> import getpass
  >>> import psutil
  >>> from pprint import pprint as pp
  >>> pp([(p.pid, p.info["name"]) for p in psutil.process_iter(["name", "username"]) if p.info["username"] == getpass.getuser()])
  (16832, 'bash'),
  (19772, 'ssh'),
  (20492, 'python')]

Processes actively running:

.. code-block:: python

  >>> pp([(p.pid, p.info) for p in psutil.process_iter(["name", "status"]) if p.info["status"] == psutil.STATUS_RUNNING])
  [(1150, {'name': 'Xorg', 'status': <ProcessStatus.STATUS_RUNNING: 'running'>}),
   (1776, {'name': 'unity-panel-service', 'status': <ProcessStatus.STATUS_RUNNING: 'running'>}),
   (20492, {'name': 'python', 'status': <ProcessStatus.STATUS_RUNNING: 'running'>})]

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

Processes consuming more than 500M of memory:

.. code-block:: python

  >>> pp([(p.pid, p.info["name"], p.info["memory_info"].rss) for p in psutil.process_iter(["name", "memory_info"]) if p.info["memory_info"].rss > 500 * 1024 * 1024])
  [(2650, 'chrome', 532324352),
   (3038, 'chrome', 1120088064),
   (21915, 'sublime_text', 615407616)]

Top 3 processes which consumed the most CPU time:

.. code-block:: python

  >>> pp([(p.pid, p.info["name"], sum(p.info["cpu_times"])) for p in sorted(psutil.process_iter(["name", "cpu_times"]), key=lambda p: sum(p.info["cpu_times"][:2]))][-3:])
  [(2721, 'chrome', 10219.73),
   (1150, 'Xorg', 11116.989999999998),
   (2650, 'chrome', 18451.97)]

Top N processes by cumulative disk read + write bytes (similar to ``iotop``):

.. code-block:: python

  import psutil

  def top_io_procs(n=5):
      procs = []
      for p in psutil.process_iter():
          try:
              io = p.io_counters()
              procs.append((io.read_bytes + io.write_bytes, p))
          except (psutil.NoSuchProcess, psutil.AccessDenied):
              pass
      procs.sort(key=lambda x: x[0], reverse=True)
      return procs[:n]

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

Inspecting a process
^^^^^^^^^^^^^^^^^^^^

List all files currently opened by a process:

.. code-block:: python

  import psutil

  def files_opened_by(pid):
      p = psutil.Process(pid)
      try:
          return [f.path for f in p.open_files()]
      except psutil.AccessDenied:
          return []

Walk up the parent chain up to PID 1 (``init`` / ``launchd``):

.. code-block:: python

  import psutil

  def parent_chain(pid):
      p = psutil.Process(pid)
      chain = []
      while True:
          parent = p.parent()
          if parent is None:
              break
          chain.append(parent)
          p = parent
      return chain

Compute how long a process has been running:

.. code-block:: python

  import datetime
  import time
  import psutil

  def proc_uptime(pid):
      p = psutil.Process(pid)
      elapsed = time.time() - p.create_time()
      return str(datetime.timedelta(seconds=int(elapsed)))

Collect a process and all its descendants into a flat list:

.. code-block:: python

  import psutil

  def get_proc_tree(pid):
      parent = psutil.Process(pid)
      return [parent] + parent.children(recursive=True)

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
              print("cpu={:<6} mem={}".format(str(cpu) + "%", bytes2human(mem)))
          time.sleep(interval)

Spawn a child process and monitor its resource usage until completion:

.. code-block:: python

  import subprocess
  import time
  import psutil

  proc = subprocess.Popen(["my-app", "--arg"])
  p = psutil.Process(proc.pid)
  while proc.poll() is None:
      with p.oneshot():
          cpu = p.cpu_percent()
          mem = p.memory_info().rss
          print("cpu={:<6} mem={}".format(str(cpu) + "%", bytes2human(mem)))
      time.sleep(1)

Controlling processes
^^^^^^^^^^^^^^^^^^^^^

Kill a process tree (including grandchildren):

.. code-block:: python

  import os
  import signal
  import psutil

  def kill_proc_tree(pid, sig=signal.SIGTERM, include_parent=True,
                     timeout=None, on_terminate=None):
      """Kill a process tree (including grandchildren) with signal
      "sig" and return a (gone, still_alive) tuple.
      "on_terminate", if specified, is a callback function which is
      called as soon as a child terminates.
      """
      assert pid != os.getpid(), "won't kill myself"
      parent = psutil.Process(pid)
      children = parent.children(recursive=True)
      if include_parent:
          children.append(parent)
      for p in children:
          try:
              p.send_signal(sig)
          except psutil.NoSuchProcess:
              pass
      gone, alive = psutil.wait_procs(children, timeout=timeout,
                                      callback=on_terminate)
      return (gone, alive)

Terminate all processes matching a given name:

.. code-block:: python

  import psutil

  def terminate_procs_by_name(name):
      for p in psutil.process_iter(["name"]):
          if p.info["name"] == name:
              p.terminate()

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

Wait for a process to terminate, with an optional timeout:

.. code-block:: python

  import psutil

  def wait_for_proc(pid, timeout=None):
      p = psutil.Process(pid)
      try:
          return p.wait(timeout=timeout)
      except psutil.TimeoutExpired:
          return None

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
      print("RAM:  total={}, used={}, free={}, percent={}%".format(
          bytes2human(ram.total),
          bytes2human(ram.used),
          bytes2human(ram.available),
          ram.percent
      ))
      print("Swap: total={}, used={}, free={}, percent={}%".format(
          bytes2human(swap.total),
          bytes2human(swap.used),
          bytes2human(swap.free),
          swap.percent
      ))

CPU
^^^

Print CPU usage percentage for each core:

.. code-block:: python

  import psutil

  for i, pct in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
      print("CPU-{}: {}%".format(i, pct))

...prints::

  CPU-0: 4.2%
  CPU-1: 10.5%
  CPU-2: 2.1%
  CPU-3: 8.0%

Disks
^^^^^

Show disk usage for all mounted partitions:

.. code-block:: python

  import psutil

  def print_disk_usage():
      for part in psutil.disk_partitions():
          usage = psutil.disk_usage(part.mountpoint)
          print("{}: total={}, used={}, free={}, percent={}%".format(
              part.mountpoint,
              bytes2human(usage.total),
              bytes2human(usage.used),
              bytes2human(usage.free),
              usage.percent)
          )

Network
^^^^^^^

List IP addresses for each network interface:

.. code-block:: python

  import psutil

  def print_net_addrs():
      for iface, addrs in psutil.net_if_addrs().items():
          for addr in addrs:
              if addr.family.name == "AF_INET":
                  print("{}: address={}, netmask={}".format(
                      iface,
                      addr.address,
                      addr.netmask)
                  )

Show bytes sent and received per network interface:

.. code-block:: python

  import psutil

  def print_net_io():
      for iface, stats in psutil.net_io_counters(pernic=True).items():
          print("{}: sent={}, recv={}".format(
              iface,
              bytes2human(stats.bytes_sent),
              bytes2human(stats.bytes_recv)
          ))
