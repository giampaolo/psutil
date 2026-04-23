.. post:: 2017-09-03
   :tags: api-design, compatibility, python-core
   :author: Giampaolo Rodola
   :exclude:

   How psutil 5.3.0 got non-ASCII strings right on both Python 2 and
   Python 3.

Fixing Unicode across Python 2 and 3
====================================

This one took a while. Adding proper Unicode support to psutil took four months
of auditing, design decisions, and rewriting nearly every API that returned a
string. The full journey is documented in :gh:`1040`, and what follows is a
summary.

This can serve as a case study for any Python library with a C extension that
needs to support both Python 2 *and* Python 3, as it will encounter the exact
same set of problems.

What was broken
---------------

psutil has different APIs returning a string, many of which misbehaved when it
came to unicode. There were three distinctive problems (:gh:`1040`). Each API
could:

* **A**: raise a decoding error for non-ASCII strings (Python 3).
* **B**: return ``unicode`` instead of ``str`` (Python 2).
* **C**: return incorrect / invalid encoded data for non-ASCII strings (both).

:meth:`Process.memory_maps` hit all three on various OSes.
:func:`disk_partitions` raised decoding errors on every UNIX except Linux.
Windows service methods leaked ``unicode`` into Python 2 return values. The C
extension had accumulated years of ad-hoc encode/decode decisions, with no
single rule covering all of them.

It was a mess.

Filesystem or locale encoding?
------------------------------

First problem was that the C extension was using 2 approaches when it came to
decoding and returning a string: :c:func:`PyUnicode_DecodeFSDefault`
(filesystem encoding) for path-like APIs, and :c:func:`PyUnicode_DecodeLocale`
(user locale) for non-path strings like :meth:`Process.username`.

It appeared clear that I had to use :c:func:`PyUnicode_DecodeFSDefault` for all
filesystem-related APIs like :meth:`Process.exe` and
:meth:`Process.open_files`.

It was less clear, though, when to use :c:func:`PyUnicode_DecodeLocale`.

After some back and forth, I decided to use a single encoding for all APIs: the
**filesystem encoding** (:c:func:`PyUnicode_DecodeFSDefault`). This makes the
encoding choice an implementation detail of psutil, not something the user has
to care about.

Error handling
--------------

Second question was what to do in case the string cannot be correctly decoded
(because invalid, corrupted or whatever). On Python 3 + UNIX the natural choice
was ``'surrogateescape'``, which is also the default for
:c:func:`PyUnicode_DecodeFSDefault`. On Windows the default is
``'surrogatepass'`` (Python 3.6) or ``'replace'`` as per
`PEP 529 <https://www.python.org/dev/peps/pep-0529/>`__.

And here come the troubles: Python 2 is different. To correctly handle all
kinds of strings on Python 2 we should return ``unicode`` instead of ``str``,
but I didn't want to do that, nor have APIs which return two different types
depending on the circumstance.

Since unicode support is already broken in Python 2 and its stdlib (see
`bpo-18695 <https://bugs.python.org/issue18695>`__), I was happy to always
return ``str``, use ``'replace'`` as the error handler, and simply consider
unicode support in psutil + Python 2 broken.

Final behavior
--------------

Starting from 5.3.0, psutil behaves consistently across all APIs that return a
string. The rules are intentionally simple, even if the underlying
implementation is not.

The notes below apply to *any* method returning a string such as
:meth:`Process.exe` or :meth:`Process.cwd`, including non-filesystem-related
methods such as :meth:`Process.username`:

* all strings are encoded using the OS filesystem encoding
  (:c:func:`PyUnicode_DecodeFSDefault`), which varies depending on the platform
  you're on (e.g. ``'UTF-8'`` on Linux, ``'mbcs'`` on Windows).
* no API call is supposed to crash with :exc:`UnicodeDecodeError`.
* in case of badly encoded data returned by the OS, the following error
  handlers are used to replace the bad characters in the string:

  - Python 2: ``'replace'``.
  - Python 3: ``'surrogateescape'`` on POSIX, ``'replace'`` on Windows.

* on Python 2 all APIs return bytes (``str`` type), never ``unicode``.
* on Python 2 you can go back to unicode by doing:

  .. code-block:: pycon

      >>> unicode(proc.exe(), sys.getdefaultencoding(), errors="replace")

The full journey was implemented in :pr:`1052`, and shipped in 5.3.0 (see the
:ref:`changelog <530>`).
