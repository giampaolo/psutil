.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola <grodola@gmail.com>

Psutil documentation
====================

.. image:: https://img.shields.io/badge/GitHub-repo-blue
   :target: https://github.com/giampaolo/psutil
   :alt: GitHub repo

.. image:: https://readthedocs.org/projects/psutil/badge/?version=latest
   :target: https://app.readthedocs.org/projects/psutil/builds/
   :alt: ReadTheDocs

.. image:: https://img.shields.io/pypi/v/psutil.svg?label=pypi&color=red
    :target: https://pypi.org/project/psutil
    :alt: Latest version

.. image:: https://img.shields.io/pypi/dm/psutil.svg
    :target: https://clickpy.clickhouse.com/dashboard/psutil
    :alt: Downloads

psutil (Python system and process utilities) is a cross-platform library for
retrieving information about running
**processes** and **system utilization** (CPU, memory, disks, network, sensors)
in **Python**.
It is useful mainly for **system monitoring**, **profiling**, **limiting
process resources**, and **managing running processes**.
It implements many functionalities offered by UNIX command line tools
such as *ps, top, free, iotop, netstat, ifconfig, lsof* and others
(see :doc:`shell equivalents <shell_equivalents>`).
psutil currently supports the following platforms, from **Python 3.7** onwards:

- **Linux**
- **Windows**
- **macOS**
- **FreeBSD, OpenBSD**, **NetBSD**
- **Sun Solaris**
- **AIX**

psutil is used by `many notable projects <adoption.html>`__ including
TensorFlow, PyTorch, Home Assistant, Ansible, and Celery.

Sponsors
--------

.. raw:: html

    <table border="0" cellpadding="10" cellspacing="0">
      <tr>
        <td align="center">
          <a href="https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme">
            <img width="200" src="https://github.com/giampaolo/psutil/raw/master/docs/_static/tidelift-logo.svg">
          </a>
        </td>
        <td align="center">
          <a href="https://sansec.io/">
            <img src="https://sansec.io/assets/images/logo.svg">
          </a>
        </td>
        <td align="center">
          <a href="https://www.apivoid.com/">
            <img width="180" src="https://gmpy.dev/images/apivoid-logo.svg">
          </a>
        </td>
      </tr>
    </table>

    &nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<sup><a href="https://github.com/sponsors/giampaolo">add your logo</a></sup><br/><br/>

Funding
-------

While psutil is free software and will always be, the project would benefit
immensely from some funding.
psutil is among the `top 100 <https://clickpy.clickhouse.com/dashboard/psutil>`_
most-downloaded Python packages, and keeping up with bug reports, user support,
and ongoing maintenance has become increasingly difficult to sustain as a
one-person effort.
If you're a company that's making significant use of psutil you can consider
becoming a sponsor via `GitHub <https://github.com/sponsors/giampaolo>`_,
`Open Collective <https://opencollective.com/psutil>`_ or
`PayPal <https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A9ZS7PKKRM3S8>`_.
Sponsors can have their logo displayed here and in the psutil `documentation <https://psutil.readthedocs.io>`_.

Security
--------

To report a security vulnerability, please use the `Tidelift security contact`_.
Tidelift will coordinate the fix and disclosure.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   Install <install>
   API Reference <api>
   FAQ <faq>
   Recipes <recipes>
   Shell equivalents <shell_equivalents>
   Platform support <platform>
   Who uses psutil <adoption>
   Glossary <glossary>
   Credits <credits>
   Development guide <devguide>
   Migration <migration>
   Timeline <timeline>

.. toctree::
   :titlesonly:

   Changelog <changelog>

.. _`Tidelift security contact`: https://tidelift.com/security
..
