.. currentmodule:: psutil

Performance
===========

This page describes how to use psutil efficiently.

.. _perf-oneshot:

Use oneshot() when reading multiple process attributes
------------------------------------------------------

If you're dealing with a single :class:`Process` instance and need to
retrieve multiple process information, use :meth:`Process.oneshot`.
Each method call issue a separate system call, but the OS often returns
multiple fields at once, which :meth:`Process.oneshot` caches for later use.

Slow:

.. code-block:: python

  import psutil

  p = psutil.Process()
  p.name()           # syscall
  p.cpu_times()      # syscall
  p.memory_info()    # syscall
  p.status()         # syscall

Fast:

.. code-block:: python

  import psutil

  p = psutil.Process()
  with p.oneshot():
      p.name()         # one syscall, result cached
      p.cpu_times()    # from cache
      p.memory_info()  # from cache
      p.status()       # from cache

The speed improvement depends on the platform and on how many attributes
you read. On Linux the gain is typically between 1x and 2x; on Windows it can
be much higher. As a rule of thumb: if you read more than two attributes
from the same process, use :meth:`Process.oneshot`.

.. _perf-process-iter:

Use process_iter() with an attrs list
--------------------------------------

If you iterate over multiple PIDs, use :func:`process_iter`.
It accepts an ``attrs`` argument that pre-fetches only the requested attributes
in a single pass, minimizing system calls by fetching multiple attributes at once.
This is faster than calling individual methods in a loop.

Slow:

.. code-block:: python

  import psutil

  for p in psutil.process_iter():
      try:
          print(p.pid, p.name(), p.status())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
          pass

Fast:

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name", "status"]):
      print(p.pid, p.name(), p.status())

:func:`process_iter(attrs=...) <psutil.process_iter>` is effectively the iterator-friendly
equivalent of using :meth:`Process.oneshot` on each process.

Using :func:`process_iter` also saves you from race conditions (e.g.
if a process disappears while iterating), since attributes are retrieved in a
single pass and exceptions like :exc:`NoSuchProcess` and :exc:`AccessDenied`
are handled internally.

.. _perf-pids:

Avoid pids() + loop
---------------------

A common but inefficient pattern is to call :func:`pids` and then
construct a :class:`Process` for each PID manually:

.. code-block:: python

  import psutil

  for pid in psutil.pids():
      try:
          p = psutil.Process(pid)
          print(p.name())
      except (psutil.NoSuchProcess, psutil.AccessDenied):
          pass

Prefer :func:`process_iter` instead. It supports the ``attrs`` pre-fetch, is
safe from race conditions and caches :class:`Process` instances internally:

.. code-block:: python

  import psutil

  for p in psutil.process_iter(["name"]):
      print(p.pid, p.name())

Measuring oneshot() speedup
---------------------------

There is a
`scripts/internal/bench_oneshot.py <https://github.com/giampaolo/psutil/blob/master/scripts/internal/bench_oneshot.py>`_
script measuring :meth:`Process.oneshot` speedup. E.g. on Linux:

.. code-block::

  $ python3 scripts/internal/bench_oneshot.py --times 10000
  17 methods pre-fetched by oneshot() on platform 'linux' (10,000 times, psutil 8.0.0):

    cpu_num
    cpu_percent
    cpu_times
    gids
    memory_info
    memory_info_ex
    memory_percent
    name
    num_ctx_switches
    num_threads
    page_faults
    parent
    ppid
    status
    terminal
    uids
    username

  regular:  2.766 secs
  oneshot:  1.537 secs
  speedup:  +1.80x

Measuring APIs speed
--------------------

There is a
`scripts/internal/print_api_speed.py <https://github.com/giampaolo/psutil/blob/master/scripts/internal/print_api_speed.py>`_
script measuring individual API calls, from fastest to slowest. E.g. on Linux:

.. code-block::

  $ python3 scripts/internal/print_api_speed.py
  SYSTEM APIS                NUM CALLS      SECONDS
  -------------------------------------------------
  getloadavg                       300      0.00013
  heap_trim                        300      0.00027
  heap_info                        300      0.00028
  cpu_count                        300      0.00066
  disk_usage                       300      0.00071
  pid_exists                       300      0.00249
  users                            300      0.00394
  cpu_times                        300      0.00647
  virtual_memory                   300      0.00648
  boot_time                        300      0.00727
  cpu_percent                      300      0.00745
  net_io_counters                  300      0.00754
  cpu_times_percent                300      0.00870
  net_if_addrs                     300      0.01156
  cpu_stats                        300      0.01195
  swap_memory                      300      0.01292
  net_if_stats                     300      0.01360
  disk_partitions                  300      0.01696
  disk_io_counters                 300      0.02583
  sensors_battery                  300      0.03103
  pids                             300      0.04896
  cpu_count (cores)                300      0.07208
  process_iter (all)               300      0.07900
  cpu_freq                         300      0.15635
  sensors_fans                     300      0.75810
  net_connections                  224      2.00111
  sensors_temperatures              81      2.00266

  PROCESS APIS               NUM CALLS      SECONDS
  -------------------------------------------------
  create_time                      300      0.00013
  exe                              300      0.00016
  nice                             300      0.00024
  ionice                           300      0.00039
  cwd                              300      0.00052
  cpu_affinity                     300      0.00057
  num_fds                          300      0.00100
  memory_info                      300      0.00208
  io_counters                      300      0.00229
  cmdline                          300      0.00232
  cpu_num                          300      0.00254
  terminal                         300      0.00255
  status                           300      0.00258
  page_faults                      300      0.00259
  name                             300      0.00261
  memory_percent                   300      0.00265
  cpu_times                        300      0.00278
  threads                          300      0.00300
  gids                             300      0.00304
  num_threads                      300      0.00305
  num_ctx_switches                 300      0.00308
  uids                             300      0.00321
  cpu_percent                      300      0.00372
  net_connections                  300      0.00376
  open_files                       300      0.00453
  username                         300      0.00505
  ppid                             300      0.00554
  memory_info_ex                   300      0.00651
  environ                          300      0.01013
  memory_footprint                 300      0.02241
  memory_maps                      300      0.30282
