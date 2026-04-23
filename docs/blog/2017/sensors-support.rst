.. post:: 2017-02-01
   :tags: new-api, release, linux
   :author: Giampaolo Rodola
   :exclude:

   psutil 5.1.0 introduces :func:`sensors_temperatures`,
   :func:`sensors_battery` and :func:`cpu_freq`

Sensors: temperatures, battery, CPU frequency
=============================================

psutil 5.1.0 is out. This release introduces new APIs to retrieve hardware
temperatures, battery status, and CPU frequency information.

Temperatures
------------

You can now retrieve hardware temperatures (:pr:`962`). This is currently
available on Linux only.

* On Windows it's hard to do in a hardware-agnostic way. I ran into 3 WMI-based
  approaches, none of which worked with my hardware, so I gave up.
* On macOS it seems relatively easy, but my virtualized macOS box doesn't
  support sensors, so I gave up for lack of hardware. If someone wants to give
  it a try, be my guest (:gh:`371`).

.. code-block:: pycon

    >>> import psutil
    >>> psutil.sensors_temperatures()
    {'acpitz': [shwtemp(label='', current=47.0, high=103.0, critical=103.0)],
     'asus': [shwtemp(label='', current=47.0, high=None, critical=None)],
     'coretemp': [shwtemp(label='Physical id 0', current=52.0, high=100.0, critical=100.0),
                  shwtemp(label='Core 0', current=45.0, high=100.0, critical=100.0),
                  shwtemp(label='Core 1', current=52.0, high=100.0, critical=100.0),
                  shwtemp(label='Core 2', current=45.0, high=100.0, critical=100.0),
                  shwtemp(label='Core 3', current=47.0, high=100.0, critical=100.0)]}

Battery status
--------------

Battery status information is now available on Linux, Windows and FreeBSD
(:pr:`963`).

.. code-block:: pycon

    >>> import psutil
    >>>
    >>> def secs2hours(secs):
    ...     mm, ss = divmod(secs, 60)
    ...     hh, mm = divmod(mm, 60)
    ...     return "%d:%02d:%02d" % (hh, mm, ss)
    ...
    >>> battery = psutil.sensors_battery()
    >>> battery
    sbattery(percent=93, secsleft=16628, power_plugged=False)
    >>> print("charge = %s%%, time left = %s" % (battery.percent, secs2hours(battery.secsleft)))
    charge = 93%, time left = 4:37:08

CPU frequency
-------------

Available on Linux, Windows and macOS (:pr:`952`). Only Linux reports the
real-time value (always changing); other platforms return the nominal "fixed"
value.

.. code-block:: pycon

    >>> import psutil
    >>> psutil.cpu_freq()
    scpufreq(current=931.42925, min=800.0, max=3500.0)
    >>> psutil.cpu_freq(percpu=True)
    [scpufreq(current=2394.945, min=800.0, max=3500.0),
     scpufreq(current=2236.812, min=800.0, max=3500.0),
     scpufreq(current=1703.609, min=800.0, max=3500.0),
     scpufreq(current=1754.289, min=800.0, max=3500.0)]

What CPU a process is on
------------------------

Tells you which CPU a process is currently running on, somewhat related to
:meth:`Process.cpu_affinity` (:pr:`954`). It's interesting for visualizing how
the OS scheduler keeps evenly reassigning processes across CPUs (see the
`scripts/cpu_distribution.py`_ script).

CPU affinity
------------

A new shorthand is available to set affinity against all eligible CPUs:

.. code-block:: python

    Process().cpu_affinity([])

This was added because on Linux (:gh:`956`) it is not always possible to set
affinity against all CPUs directly. It is equivalent to:

.. code-block:: python

    psutil.Process().cpu_affinity(list(range(psutil.cpu_count())))

Other bug fixes
---------------

See the full list in the :ref:`changelog <510>`.
