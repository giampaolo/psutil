.. post:: 2016-05-15
   :tags: windows, new-api, release
   :author: Giampaolo Rodola
   :exclude:

   psutil 4.2.0 introduces :func:`win_service_iter` and :func:`win_service_get`

Windows services support
========================

New psutil 4.2.0 is out. The highlight of this release is the support for
Windows services (executables that run at system startup, similar to UNIX init
scripts):

.. code-block:: pycon

    >>> import psutil
    >>> list(psutil.win_service_iter())
    [<WindowsService(name='AeLookupSvc', display_name='Application Experience') at 38850096>,
     <WindowsService(name='ALG', display_name='Application Layer Gateway Service') at 38850128>,
     <WindowsService(name='APNMCP', display_name='Ask Update Service') at 38850160>,
     <WindowsService(name='AppIDSvc', display_name='Application Identity') at 38850192>,
     ...]
    >>> s = psutil.win_service_get('alg')
    >>> s.as_dict()
    {'binpath': 'C:\\Windows\\System32\\alg.exe',
     'description': 'Provides support for 3rd party protocol plug-ins for Internet Connection Sharing',
     'display_name': 'Application Layer Gateway Service',
     'name': 'alg',
     'pid': None,
     'start_type': 'manual',
     'status': 'stopped',
     'username': 'NT AUTHORITY\\LocalService'}

I decided to do this mainly because I find pywin32 APIs too low levelish.
Having something like this in psutil can be useful to discover and monitor
services more easily. The code was implemented in :pr:`803`. The API for
querying a service is similar to :class:`psutil.Process`. You can get a
reference to a service object by using its name (which is unique for every
service) and then use methods like :meth:`WindowsService.name` and
:meth:`WindowsService.status`:

.. code-block:: pycon

    >>> s = psutil.win_service_get('alg')
    >>> s.name()
    'alg'
    >>> s.status()
    'stopped'

Initially I thought about providing a full set of APIs to handle all aspects of
service management, including ``start()``, ``stop()``, ``restart()``,
``install()``, ``uninstall()`` and ``modify()``. However, I soon realized I
would have ended up reimplementing what pywin32 already provides, at the cost
of overcrowding the psutil API (see my reasoning
`here <https://github.com/giampaolo/psutil/blob/d28de253a2e6d7f368e5260d7a4ab14b285c5083/psutil/_pswindows.py#L426>`__).
I think psutil really focuses on monitoring, not on installing and modifying
system components, especially something as critical as a Windows service.

Considerations about Windows services
-------------------------------------

Typically, a Windows service is an executable (.exe) that runs at system
startup and continues running in the background. It is roughly the equivalent
of a UNIX init script. All services are controlled by a "manager", which keeps
track of their status and metadata (e.g. description, startup type). It is
interesting to note that since (most) services are bound to an executable (and
hence a process) you can reference them via their process PID:

.. code-block:: pycon

    >>> s = psutil.win_service_get('sshd')
    >>> s
    <WindowsService(name='sshd', display_name='Open SSH server') at 38853046>
    >>> s.pid()
    1865
    >>> p = psutil.Process(1865)
    >>> p
    <psutil.Process(pid=19547, name='sshd.exe') at 140461487781328>
    >>> p.exe()
    'C:\CygWin\bin\sshd'

Other improvements
------------------

psutil 4.2.0 comes with 2 other enhancements for Linux:

* :func:`psutil.virtual_memory` returns a new :field:`shared` memory field.
  This is the same value reported by ``free`` cmdline utility.
* I changed how ``/proc`` was parsed. Instead of reading ``/proc/{pid}/status``
  line by line I used a regular expression. Here's the speedups:

  * :meth:`Process.ppid` ~20% faster.

  * :meth:`Process.status` ~28% faster.

  * :meth:`Process.name` ~25% faster.

  * :meth:`Process.num_threads` ~20% faster (on Python 3 only; on Python 2 it's
    a bit slower; I suppose :mod:`re` module received some improvements).

Discussion
----------

* `Reddit <https://www.reddit.com/r/Python/comments/4jf8tz/psutil_420_windows_services_and_python/>`__
* `Hacker News <https://news.ycombinator.com/item?id=11700002>`__
