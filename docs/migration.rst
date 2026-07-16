Migration guide
===============

This page summarises the breaking changes introduced in each major release and
shows the code changes required to upgrade.

.. note::
  Minor and patch releases (e.g. 6.1.x, 7.1.x) never contain breaking changes.
  Only major releases are listed here.

.. _migration-8.0:

Migrating to 8.0
-----------------

Key breaking changes in 8.0:

- :func:`process_iter` pre-fetches values
- :attr:`Process.info` is deprecated: use direct methods.
- Named tuple field order changed: stop positional unpacking.
- Some return types are now enums instead of strings.
- :meth:`Process.memory_full_info` deprecated: use
  :meth:`Process.memory_footprint`.
- New :meth:`Process.memory_info_ex` (unrelated to the old method deprecated in
  4.0 and removed in 7.0).
- New :attr:`Process.attrs`: :class:`frozenset` of valid attribute names;
  ``process_iter(attrs=[])`` is deprecated.
- Python 3.6 dropped.

.. important::

  Do not rely on positional unpacking of named tuples. Always use attribute
  access (e.g. ``t.rss``).

process_iter(): p.info is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`process_iter` now caches pre-fetched values internally, so they can be
accessed via normal method calls instead of the :attr:`Process.info` dict.
``p.info`` still works, but raises :exc:`DeprecationWarning`.

.. code-block:: python

  import psutil

  # before
  for p in psutil.process_iter(attrs=["name", "status"]):
      print(p.info["name"], p.info["status"])

  # after
  for p in psutil.process_iter(attrs=["name", "status"]):
      print(p.name(), p.status())  # return cached values, never raise

When ``attrs`` are specified, method calls return cached values (no extra
syscall), and :exc:`AccessDenied` / :exc:`ZombieProcess` are handled
transparently (returning ``ad_value``).

If you relied on :attr:`Process.info` because you needed a dict structure, use
:meth:`Process.as_dict` instead.

.. code-block:: python

  import psutil

  # before
  for p in psutil.process_iter(attrs=["name", "status"]):
      print(p.info)

  # after
  attrs = ["name", "status"]
  for p in psutil.process_iter(attrs=attrs):
      print(p.as_dict(attrs))  # return cached values, never raise

.. note::
  If ``"name"`` was pre-fetched via ``attrs``, calling ``p.name()`` no longer
  raises :exc:`AccessDenied`. It returns ``ad_value`` instead. If you need the
  exception, do not include the method in ``attrs``.

Named tuple field order changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :func:`cpu_times`: :field:`user`, :field:`system`, :field:`idle` fields
  changed order on Linux, macOS and BSD. They are now always the first 3 fields
  on all platforms, with platform-specific fields (e.g. :field:`nice`)
  following. Positional access (e.g. ``cpu_times()[3]``) will silently return
  the wrong field. Always use attribute access instead (e.g.
  ``cpu_times().idle``).

  .. code-block:: python

    # before
    user, nice, system, idle = psutil.cpu_times()

    # after
    t = psutil.cpu_times()
    user, system, idle = t.user, t.system, t.idle

- :meth:`Process.memory_info`: the returned named tuple changed size and field
  order. Always use attribute access (e.g. ``p.memory_info().rss``) instead of
  positional unpacking.

  - Linux: :field:`lib` and :field:`dirty` fields removed (aliases emitting
    :exc:`DeprecationWarning` are kept).
  - macOS: :field:`pfaults` and :field:`pageins` removed with **no aliases**.
    Use :meth:`Process.page_faults` instead.
  - Windows: old aliases (:field:`wset`, :field:`peak_wset`, :field:`pagefile`,
    :field:`private`, :field:`peak_pagefile`, :field:`num_page_faults`) were
    renamed. Old names still work but raise :exc:`DeprecationWarning`.
    :field:`paged_pool`, :field:`nonpaged_pool`, :field:`peak_paged_pool`,
    :field:`peak_nonpaged_pool` were moved to :meth:`Process.memory_info_ex`.
  - BSD: a new :field:`peak_rss` field was added.

- :func:`virtual_memory`: on Windows, new :field:`cached` and :field:`wired`
  fields were added. Code using positional unpacking will break:

  .. code-block:: python

    # before
    total, avail, percent, used, free = psutil.virtual_memory()

    # after
    m = psutil.virtual_memory()
    total, avail, percent, used, free = m.total, m.available, m.percent, m.used, m.free

cpu_times() interrupt renamed to irq on Windows
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :field:`interrupt` field of :func:`cpu_times` on Windows was renamed to
:field:`irq` to match the name used on Linux and BSD. The old name still works
but raises :exc:`DeprecationWarning`.

Status and connection fields are now enums
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :meth:`Process.status` now returns a :class:`ProcessStatus` member instead of
  a plain ``str``.
- :meth:`Process.net_connections` and :func:`net_connections` :field:`status`
  field now returns a :class:`ConnectionStatus` member instead of a plain
  ``str``.

Because both are :class:`enum.StrEnum` subclasses they compare equal to their
string values, so existing comparisons like
``p.status() == psutil.STATUS_RUNNING`` continue to work unchanged. Code
inspecting :func:`repr` or :class:`type` may need updating.

memory_full_info() is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`Process.memory_full_info` is deprecated. Use
:meth:`Process.memory_footprint` instead (same fields).

New memory_info_ex() method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^

8.0 introduces a new :meth:`Process.memory_info_ex` method that extends
:meth:`Process.memory_info` with platform-specific metrics (e.g.
:field:`peak_rss`, :field:`swap`, :field:`rss_anon` on Linux). This is
**unrelated** to the old :meth:`Process.memory_info_ex` that was deprecated in
4.0 and removed in 7.0 (which corresponded to what later became
:meth:`Process.memory_full_info`).

New Process.attrs class attribute
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:attr:`Process.attrs` is a new :class:`frozenset` exposing the valid attribute
names accepted by :meth:`Process.as_dict` and :func:`process_iter`. It replaces
the previous pattern of creating a throwaway process just to discover available
names:

.. code-block:: python

  # before
  attrs = list(psutil.Process().as_dict().keys())

  # after
  attrs = psutil.Process.attrs

It also makes it easy to pass all or a subset of attributes.
``process_iter(attrs=[])`` (empty list meaning "all") is now deprecated; use
:attr:`Process.attrs` instead:

.. code-block:: python

  # all attrs
  psutil.process_iter(attrs=psutil.Process.attrs)

  # all except connections
  psutil.process_iter(attrs=psutil.Process.attrs - {"net_connections"})

Python 3.6 dropped
^^^^^^^^^^^^^^^^^^^^

Python 3.6 is no longer supported. Minimum version is Python 3.7.

Git tags renamed
^^^^^^^^^^^^^^^^^

Git tags were renamed from ``release-X.Y.Z`` to ``vX.Y.Z`` (e.g.
``release-7.2.2`` → ``v7.2.2``). Old tags are kept for backward compatibility.
If you reference psutil tags in scripts or URLs, update them to the new format.
See :gh:`2788`.

-------------------------------------------------------------------------------

.. _migration-7.0:

Migrating to 7.0
-----------------

Process.memory_info_ex() removed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The long-deprecated :meth:`Process.memory_info_ex` was removed (it was
deprecated since 4.0.0 in 2016). Use :meth:`Process.memory_full_info` instead.

.. note::

  In 8.0, a new :meth:`Process.memory_info_ex` method was introduced with
  different semantics: it extends :meth:`Process.memory_info` with
  platform-specific metrics. It is unrelated to the old method documented here.

.. code-block:: python

  # before
  p.memory_info_ex()

  # after
  p.memory_full_info()

Python 2.7 dropped
^^^^^^^^^^^^^^^^^^^^

Python 2.7 is no longer supported. The last release to support Python 2.7 is
psutil 6.1.x:

.. code-block:: bash

  pip2 install "psutil==6.1.*"

-------------------------------------------------------------------------------

.. _migration-6.0:

Migrating to 6.0
-----------------

Process.connections() renamed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`Process.connections` was renamed to :meth:`Process.net_connections` for
consistency with the system-level :func:`net_connections`. The old name
triggers a :exc:`DeprecationWarning` and will be removed in a future release:

.. code-block:: python

  # before
  p.connections()
  p.connections(kind="tcp")

  # after
  p.net_connections()
  p.net_connections(kind="tcp")

disk_partitions() lost two fields
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The :field:`maxfile` and :field:`maxpath` fields were removed from the named
tuple returned by :func:`disk_partitions`. Code unpacking the tuple
positionally will break:

.. code-block:: python

  # before (broken)
  device, mountpoint, fstype, opts, maxfile, maxpath = part

  # after
  device, mountpoint, fstype, opts = (
      part.device, part.mountpoint, part.fstype, part.opts
  )

process_iter() no longer checks for PID reuse
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:func:`process_iter` no longer preemptively checks whether yielded PIDs have
been reused (this made it ~20× faster). If you need to verify that a process
object is still alive and refers to the same process, use
:meth:`Process.is_running` explicitly:

.. code-block:: python

  for p in psutil.process_iter(["name"]):
      if p.is_running():
          print(p.pid, p.name())

-------------------------------------------------------------------------------

.. _migration-5.0:

Migrating to 5.0
-----------------

5.0.0 was the largest renaming in psutil history. All ``get_*`` and ``set_*``
:class:`Process` methods lost their prefix, and several module-level names were
changed.

Old :class:`Process` method names still worked but raised
:exc:`DeprecationWarning`. They were fully removed in 6.0.

Process methods
^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 40

   * - Old (< 5.0)
     - New (>= 5.0)
   * - ``p.get_children()``
     - ``p.children()``
   * - ``p.get_connections()``
     - ``p.connections()`` → ``p.net_connections()`` in 6.0
   * - ``p.get_cpu_affinity()``
     - ``p.cpu_affinity()``
   * - ``p.get_cpu_percent()``
     - ``p.cpu_percent()``
   * - ``p.get_cpu_times()``
     - ``p.cpu_times()``
   * - ``p.get_ext_memory_info()``
     - ``p.memory_info_ex()`` → ``p.memory_full_info()`` in 4.0
   * - ``p.get_io_counters()``
     - ``p.io_counters()``
   * - ``p.get_ionice()``
     - ``p.ionice()``
   * - ``p.get_memory_info()``
     - ``p.memory_info()``
   * - ``p.get_memory_maps()``
     - ``p.memory_maps()``
   * - ``p.get_memory_percent()``
     - ``p.memory_percent()``
   * - ``p.get_nice()``
     - ``p.nice()``
   * - ``p.get_num_ctx_switches()``
     - ``p.num_ctx_switches()``
   * - ``p.get_num_fds()``
     - ``p.num_fds()``
   * - ``p.get_num_threads()``
     - ``p.num_threads()``
   * - ``p.get_open_files()``
     - ``p.open_files()``
   * - ``p.get_rlimit()``
     - ``p.rlimit()``
   * - ``p.get_threads()``
     - ``p.threads()``
   * - ``p.getcwd()``
     - ``p.cwd()``
   * - ``p.set_nice(v)``
     - ``p.nice(v)``
   * - ``p.set_ionice(cls)``
     - ``p.ionice(cls)``
   * - ``p.set_cpu_affinity(cpus)``
     - ``p.cpu_affinity(cpus)``

Module-level renames
^^^^^^^^^^^^^^^^^^^^^

.. list-table::
   :header-rows: 1
   :widths: 40 40

   * - Old (< 5.0)
     - New (>= 5.0)
   * - ``psutil.NUM_CPUS``
     - ``psutil.cpu_count()``
   * - ``psutil.BOOT_TIME``
     - ``psutil.boot_time()``
   * - ``psutil.TOTAL_PHYMEM``
     - ``psutil.virtual_memory().total``
   * - ``psutil.get_pid_list()``
     - ``psutil.pids()``
   * - ``psutil.get_users()``
     - ``psutil.users()``
   * - ``psutil.get_boot_time()``
     - ``psutil.boot_time()``
   * - ``psutil.network_io_counters()``
     - ``psutil.net_io_counters()``
   * - ``psutil.phymem_usage()``
     - ``psutil.virtual_memory()``
   * - ``psutil.virtmem_usage()``
     - ``psutil.swap_memory()``
