.. post:: 2014-03-10
   :tags: api-design, compatibility, release
   :author: Giampaolo Rodola
   :exclude:

   A major rewrite with breaking API changes

Announcing psutil 2.0
=====================

psutil 2.0 is out. This is a major rewrite and reorganization of both the
Python and C extension modules. It costed me four months of work and more than
**22,000 lines** (the diff against old 1.2.1). Many of the changes are not
backward compatible; I'm sure this will cause some pain, but I think it's for
the better and needed to be done.

API changes
-----------

I already wrote a detailed :doc:`blog post </blog/2014/porting-to-20>` about
this, so use that as the official reference on how to port your code.

RST documentation
-----------------

I've never been happy with the old doc hosted on Google Code. The markup
language provided by Google is pretty limited, plus it's not under revision
control. The new doc is more detailed, uses reStructuredText as the markup
language, lives in the same code repository as psutil, and is hosted on the
excellent Read the Docs: http://psutil.readthedocs.org/

Physical CPUs count
-------------------

You're now able to distinguish between :term:`logical <logical CPU>` and
:term:`physical <physical CPU>` CPUs. The full story is in :gh:`427`.

.. code-block:: pycon

    >>> psutil.cpu_count()  # logical
    4
    >>> psutil.cpu_count(logical=False)  # physical cores only
    2

Process instances are hashable
------------------------------

:class:`psutil.Process` instances can now be compared for equality and used in
sets and dicts. The most useful application is diffing process snapshots:

.. code-block:: pycon

    >>> before = set(psutil.process_iter())
    >>> # ... some time passes ...
    >>> after = set(psutil.process_iter())
    >>> new_procs = after - before  # processes spawned in between

Equality is not just PID-based. It also includes the process creation time, so
a :class:`~psutil.Process` whose PID got reused by the kernel won't be mistaken
for the original. The full story is in :gh:`452`.

Speedups
--------

* :gh:`477`: :meth:`Process.cpu_percent` is about 30% faster.
* :gh:`478`: [Linux] almost all APIs are about 30% faster on Python 3.X.

Other improvements and bugfixes
-------------------------------

* :gh:`424`: published Windows installers for Python 3.X 64-bit.
* :gh:`447`: the :func:`psutil.wait_procs` ``timeout`` parameter is now
  optional.
* :gh:`459`: a
  `Makefile <https://github.com/giampaolo/psutil/blob/v2.0.0/Makefile>`_ is now
  available for running tests and other repetitive tasks (also on Windows).
* :gh:`463`: the ``timeout`` parameter of ``cpu_percent*`` functions defaults
  to 0.0, because the previous default was a common source of slowdowns.
* :gh:`340`: [Windows] :meth:`Process.open_files` no longer hangs.
* :gh:`448`: [Windows] fixed a memory leak affecting :meth:`Process.children`
  and :meth:`Process.ppid`.
* :gh:`461`: namedtuples are now pickle-able.
* :gh:`474`: [Windows] :meth:`Process.cpu_percent` is no longer capped at 100%.

See the :ref:`changelog <200>` for a full list of changes.
