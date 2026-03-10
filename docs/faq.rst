.. include:: _links.rst

FAQs
====

* Q: Why do I get :class:`AccessDenied` for certain processes?
* A: This may happen when you query processes owned by another user,
  especially on macOS (see issue :gh:`883`) and Windows.
  Unfortunately there's not much you can do about this except running the
  Python process with higher privileges.
  On Unix you may run the Python process as root or use the SUID bit
  (``ps`` and ``netstat`` does this).
  On Windows you may run the Python process as NT AUTHORITY\\SYSTEM or install
  the Python script as a Windows service (ProcessHacker does this).

----

* Q: is MinGW supported on Windows?
* A: no, Visual Studio is the only compiler support on Windows (see
  :doc:`devguide`).
