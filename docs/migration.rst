.. currentmodule:: psutil
.. include:: _links.rst

Migration guide
===============

.. contents::
   :local:
   :depth: 2

This page summarises the breaking changes introduced in each major
release and shows the code changes required to upgrade.

.. note::
  Minor and patch releases (e.g. 6.1.x, 7.1.x) do not contain
  breaking changes. Only major releases are listed here.

Migrating to 8.0
-----------------

Named tuple field order changed
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :func:`cpu_times`: ``user, system, idle`` fields changed order on Linux,
  macOS and BSD. They are now always the first 3 fields on all platforms, with
  platform-specific fields (e.g. ``nice``) following. Positional access (e.g.
  ``cpu_times()[3]``) will silently return the wrong field. Always use
  attribute access instead (e.g. ``cpu_times().idle``).

  .. code-block:: python

    # before
    user, nice, system, idle = psutil.cpu_times()

    # after
    t = psutil.cpu_times()
    user, system, idle = t.user, t.system, t.idle

- :meth:`Process.memory_info`:

  - The returned named tuple changed size and field
    order. Positional access (e.g. ``p.memory_info()[3]`` or ``a, b, c =
    p.memory_info()``) may break or silently return the wrong field. Always use
    attribute access instead (e.g. ``p.memory_info().rss``). Also, ``lib`` and ``dirty`` on Linux were removed and turned into aliases emitting `DeprecationWarning`.

    .. code-block:: python

      # Linux before
      rss, vms, shared, text, lib, data, dirty = p.memory_info()

      # Linux after
      t = p.memory_info()
      rss, vms, shared, text, data = t.rss, t.vms, t.shared, t.text, t.data

  - macOS: ``pfaults`` and ``pageins`` fields were removed with **no
    backward-compatible aliases**. Use :meth:`page_faults` instead.

    .. code-block:: python

      # before
      rss, vms, pfaults, pageins = p.memory_info()

      # after
      rss, vms = p.memory_info()
      minor, major = p.page_faults()

  - Windows: eliminated old aliases: ``wset`` → ``rss``, ``peak_wset`` →
    ``peak_rss``, ``pagefile`` / ``private`` → ``vms``, ``peak_pagefile`` →
    ``peak_vms``, ``num_page_faults`` → :meth:`page_faults` method. At the same
    time ``paged_pool``, ``nonpaged_pool``, ``peak_paged_pool``,
    ``peak_nonpaged_pool`` were moved to :meth:`memory_info_ex`. All these old
    names still work but raise `DeprecationWarning`.

  - BSD: a new ``peak_rss`` field was added.

Status and connection fields are now enums
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- :meth:`Process.status` now returns a :class:`psutil.ProcessStatus` member
  instead of a plain ``str``.
- :meth:`Process.net_connections` and :func:`net_connections` ``status`` field
  now returns a :class:`psutil.ConnectionStatus` member instead of a plain
  ``str``.
Because both are `enum.StrEnum`_ subclasses they compare equal to their
string values, so existing comparisons continue to work unchanged:

.. code-block:: python

  # these still work
  p.status() == "running"
  p.status() == psutil.STATUS_RUNNING

  # repr() and type() differ, so code inspecting these may need updating


The individual constants (e.g. :data:`psutil.STATUS_RUNNING`) are kept as
aliases for the enum members, and should be preferred over accessing them via
the enum class:

.. code-block:: python

  # prefer this
  p.status() == psutil.STATUS_RUNNING

  # not this
  p.status() == psutil.ProcessStatus.STATUS_RUNNING

memory_full_info() is deprecated
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

:meth:`Process.memory_full_info` is deprecated. Use the new
:meth:`Process.memory_footprint` instead:

.. code-block:: python

  # before
  mem = p.memory_full_info()
  uss = mem.uss

  # after
  mem = p.memory_footprint()
  uss = mem.uss

Python 3.6 dropped
^^^^^^^^^^^^^^^^^^^^

Python 3.6 is no longer supported. Minimum version is Python 3.7.
