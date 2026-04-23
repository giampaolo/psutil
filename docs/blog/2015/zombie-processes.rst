.. post:: 2015-06-13
   :tags: api-design, compatibility
   :author: Giampaolo Rodola
   :exclude:

   Proper handling of zombies via new :exc:`ZombieProcess` exception

Proper zombie process handling
==============================

This is part of the psutil 3.0 release (see the full
:doc:`release notes </blog/2015/reimplementing-ifconfig-in-python>`).

Except on Linux and Windows (which does not have them), support for
:term:`zombie processes <zombie process>` was broken. The full story is in
:gh:`428`.

The problem
-----------

Say you create a zombie process and instantiate a :class:`~psutil.Process` for
it:

.. code-block:: python

    import os, time

    def create_zombie():
        pid = os.fork()  # the zombie
        if pid == 0:
            os._exit(0)  # child exits immediately
        else:
            time.sleep(1000)  # parent does NOT call wait()

    pid = create_zombie()
    p = psutil.Process(pid)

Up until psutil 2.X, every time you tried to query it you'd get a
:exc:`NoSuchProcess` exception:

.. code-block:: pycon

    >>> p.name()
      File "psutil/__init__.py", line 374, in _init
        raise NoSuchProcess(pid, None, msg)
    psutil.NoSuchProcess: no process found with pid 123

This was misleading, because the PID technically still existed:

.. code-block:: pycon

    >>> psutil.pid_exists(p.pid)
    True

Depending on the platform, some process information could still be retrieved:

.. code-block:: pycon

    >>> p.cmdline()
    ['python']

Worst of all, :func:`psutil.process_iter` didn't return zombies at all. That
was a real problem, because identifying them is a legitimate use case: a zombie
usually indicates a bug where a parent process spawns a child, kills it, but
never calls ``wait()`` to reap it.

What changed
------------

* A new :exc:`ZombieProcess` exception is raised whenever a process cannot be
  queried because it is a zombie.
* It replaces :exc:`NoSuchProcess`, which was incorrect and misleading.
* :exc:`ZombieProcess` inherits from :exc:`NoSuchProcess`, so existing code
  keeps working.
* :func:`psutil.process_iter` now correctly includes zombie processes, so you
  can reliably identify them:

.. code-block:: python

    import psutil

    zombies = []
    for p in psutil.process_iter():
        try:
            if p.status() == psutil.STATUS_ZOMBIE:
                zombies.append(p)
        except psutil.NoSuchProcess:
            pass
