.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola' <grodola@gmail.com>
.. include:: _links.rst

Psutil documentation
====================

|  |downloads| |stars| |forks| |contributors|

.. |downloads| image:: https://img.shields.io/pypi/dm/psutil.svg
    :target: https://clickpy.clickhouse.com/dashboard/psutil
    :alt: Downloads

.. |stars| image:: https://img.shields.io/github/stars/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/stargazers
    :alt: Github stars

.. |forks| image:: https://img.shields.io/github/forks/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/network/members
    :alt: Github forks

.. |contributors| image:: https://img.shields.io/github/contributors/giampaolo/psutil.svg
    :target: https://github.com/giampaolo/psutil/graphs/contributors
    :alt: Contributors


psutil (python system and process utilities) is a cross-platform library for
retrieving information on running
**processes** and **system utilization** (CPU, memory, disks, network, sensors)
in **Python**.
It is useful mainly for **system monitoring**, **profiling**, **limiting
process resources** and the **management of running processes**.
It implements many functionalities offered by UNIX command line tools
such as: *ps, top, lsof, netstat, ifconfig, who, df, kill, free, nice,
ionice, iostat, iotop, uptime, pidof, tty, taskset, pmap*.
psutil currently supports the following platforms, from **Python 3.7** onwards:

- **Linux**
- **Windows**
- **macOS**
- **FreeBSD, OpenBSD**, **NetBSD**
- **Sun Solaris**
- **AIX**

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
psutil is among the `top 100 <https://clickpy.clickhouse.com/dashboard/psutil>`__
most-downloaded Python packages, and keeping up with bug reports, user support,
and ongoing maintenance has become increasingly difficult to sustain as a
one-person effort.
If you're a company that's making significant use of psutil you can consider
becoming a sponsor via `GitHub <https://github.com/sponsors/giampaolo>`__,
`Open Collective <https://opencollective.com/psutil>`__ or
`PayPal <https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A9ZS7PKKRM3S8>`__.
Sponsors can have their logo displayed here and in the psutil `documentation <https://psutil.readthedocs.io>`__.

Security
--------

To report a security vulnerability, please use the `Tidelift security
contact`_.  Tidelift will coordinate the fix and disclosure.

Table of Contents
-----------------

.. toctree::
   :maxdepth: 2

   Install <install>
   API Reference <api>
   Recipes <recipes>
   Platform support <platform>
   Development guide <devguide>
   FAQs <faq>
   Timeline <timeline>
