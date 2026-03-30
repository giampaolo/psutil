.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola <grodola@gmail.com>
.. title:: Home

.. raw:: html

   <script>document.body.classList.add('home-page');</script>

   <div class="hero">
     <div class="hero-title"><img src="_static/logo.svg" class="hero-logo" alt="psutil logo"><span>psutil<span/></div>
     <div class="hero-subtitle">Process and System Utilities for Python</div>
     <div class="hero-badges">
       <a href="https://github.com/giampaolo/psutil"><img src="https://img.shields.io/badge/GitHub-repo-blue" alt="GitHub repo"></a>
       <a href="https://clickpy.clickhouse.com/dashboard/psutil"><img src="https://img.shields.io/pypi/dm/psutil.svg?color=green" alt="Downloads"></a>
       <a href="https://pypi.org/project/psutil"><img src="https://img.shields.io/pypi/v/psutil.svg?label=pypi&color=yellowgreen" alt="Latest version"></a>
     </div>
   </div>

-------------------------------------------------------------------------------

psutil is a cross-platform library for retrieving information about running
**processes** and **system utilization** (CPU, memory, disks, network, sensors)
in Python. It is useful mainly for **system monitoring**, **profiling**,
**limiting process resources**, and **managing running processes**.

.. raw:: html

   <div class="home-platforms">
     <span class="home-platform-label">Runs on:</span>
     <span class="home-platform-pill">Linux</span>
     <span class="home-platform-pill">Windows</span>
     <span class="home-platform-pill">macOS</span>
     <span class="home-platform-pill">FreeBSD</span>
     <span class="home-platform-pill">OpenBSD</span>
     <span class="home-platform-pill">NetBSD</span>
     <span class="home-platform-pill">Solaris</span>
     <span class="home-platform-pill">AIX</span>
   </div>

   <div class="home-feature-cards">
     <a class="home-feature-card" href="api.html#cpu">
       <svg class="home-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
         <rect x="6" y="6" width="12" height="12" rx="2"/>
         <line x1="9"  y1="6"  x2="9"  y2="3"/>
         <line x1="12" y1="6"  x2="12" y2="3"/>
         <line x1="15" y1="6"  x2="15" y2="3"/>
         <line x1="9"  y1="18" x2="9"  y2="21"/>
         <line x1="12" y1="18" x2="12" y2="21"/>
         <line x1="15" y1="18" x2="15" y2="21"/>
         <line x1="6"  y1="9"  x2="3"  y2="9"/>
         <line x1="6"  y1="12" x2="3"  y2="12"/>
         <line x1="6"  y1="15" x2="3"  y2="15"/>
         <line x1="18" y1="9"  x2="21" y2="9"/>
         <line x1="18" y1="12" x2="21" y2="12"/>
         <line x1="18" y1="15" x2="21" y2="15"/>
       </svg>
       <div class="home-feature-title">CPU</div>
     </a>
     <a class="home-feature-card" href="api.html#memory">
       <svg class="home-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
         <rect x="1" y="4" width="22" height="13" rx="1.5"/>
         <rect x="3"  y="7.5" width="3" height="6" rx="0.5"/>
         <rect x="8"  y="7.5" width="3" height="6" rx="0.5"/>
         <rect x="13" y="7.5" width="3" height="6" rx="0.5"/>
         <rect x="18" y="7.5" width="3" height="6" rx="0.5"/>
         <line x1="2"    y1="17" x2="2"    y2="20"/>
         <line x1="4.2"  y1="17" x2="4.2"  y2="20"/>
         <line x1="6.4"  y1="17" x2="6.4"  y2="20"/>
         <line x1="8.6"  y1="17" x2="8.6"  y2="20"/>
         <line x1="10.8" y1="17" x2="10.8" y2="20"/>
         <line x1="13.2" y1="17" x2="13.2" y2="20"/>
         <line x1="15.4" y1="17" x2="15.4" y2="20"/>
         <line x1="17.6" y1="17" x2="17.6" y2="20"/>
         <line x1="19.8" y1="17" x2="19.8" y2="20"/>
         <line x1="22"   y1="17" x2="22"   y2="20"/>
         <line x1="2"    y1="20" x2="22"   y2="20"/>
       </svg>
       <div class="home-feature-title">Memory</div>
     </a>
     <a class="home-feature-card" href="api.html#disks">
       <svg class="home-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
         <rect x="1" y="3" width="22" height="18" rx="3"/>
         <line x1="1"  y1="15" x2="23"  y2="15"/>
         <line x1="4"  y1="8"  x2="9"   y2="8"/>
         <line x1="4"  y1="11" x2="9"   y2="11"/>
         <rect x="3"   y="17"  width="9"   height="2" rx="1"/>
         <rect x="14"  y="17"  width="2.5" height="2" rx="1"/>
         <rect x="18"  y="17"  width="2.5" height="2" rx="1"/>
       </svg>
       <div class="home-feature-title">Disks</div>
     </a>
     <a class="home-feature-card" href="api.html#network">
       <svg class="home-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
         <circle cx="12" cy="12" r="10"/>
         <line x1="2" y1="12" x2="22" y2="12"/>
         <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
       </svg>
       <div class="home-feature-title">Network</div>
     </a>
     <a class="home-feature-card" href="api.html#sensors">
       <i class="fa fa-thermometer-half home-icon-fa"></i>
       <div class="home-feature-title">Sensors</div>
     </a>
     <a class="home-feature-card" href="api.html#processes">
       <svg class="home-icon-svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
         <line x1="8"  y1="6"  x2="21" y2="6"/>
         <line x1="8"  y1="12" x2="21" y2="12"/>
         <line x1="8"  y1="18" x2="21" y2="18"/>
         <circle cx="3.5" cy="6"  r="1"/>
         <circle cx="3.5" cy="12" r="1"/>
         <circle cx="3.5" cy="18" r="1"/>
       </svg>
       <div class="home-feature-title">Processes</div>
     </a>
   </div>


It implements many functionalities offered by UNIX command line tool such as
*ps, top, free, iotop, netstat, ifconfig, lsof* and others
(see :doc:`shell equivalents <shell-equivalents>`).
It is used by :doc:`many notable projects <adoption>` including TensorFlow,
PyTorch, Home Assistant, Ansible, and Celery.

-------------------------------------------------------------------------------

Sponsors
--------

.. raw:: html

    <table border="0" cellpadding="10" cellspacing="0" class="sponsor-table">
      <tr>
        <td align="center">
          <a href="https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme">
            <img width="200" src="https://github.com/giampaolo/psutil/raw/master/docs/_static/tidelift-logo.svg" class="sponsor-logo">
          </a>
        </td>
        <td align="center">
          <a href="https://sansec.io/">
            <img src="https://sansec.io/assets/images/logo.svg" class="sponsor-logo">
          </a>
        </td>
        <td align="center">
          <a href="https://www.apivoid.com/">
            <img width="180" src="https://gmpy.dev/images/apivoid-logo.svg" class="sponsor-logo">
          </a>
        </td>
      </tr>
    </table>

    <div style="text-align: center;"><sup><a href="https://github.com/sponsors/giampaolo">add your logo</a></sup></div><br/>

While psutil is free software and will always be, the project would benefit
immensely from some funding.
psutil is among the :doc:`top 100 <adoption>`
most-downloaded Python packages, and keeping up with bug reports, user support,
and ongoing maintenance has become increasingly difficult to sustain as a
one-person effort.
If you're a company that's making significant use of psutil you can consider
becoming a sponsor via `GitHub <https://github.com/sponsors/giampaolo>`_,
`Open Collective <https://opencollective.com/psutil>`_ or
`PayPal <https://www.paypal.com/cgi-bin/webscr?cmd=_s-xclick&hosted_button_id=A9ZS7PKKRM3S8>`_.

-------------------------------------------------------------------------------

.. toctree::
   :maxdepth: 2
   :caption: User guide

   Install <install>
   API overview <api-overview>
   API Reference <api>
   Performance <performance>
   FAQ <faq>
   Recipes <recipes>
   Shell equivalents <shell-equivalents>
   Stdlib equivalents <stdlib-equivalents>

.. toctree::
   :maxdepth: 2
   :caption: Reference

   Glossary <glossary>
   Platform support <platform>

.. toctree::
   :maxdepth: 2
   :caption: Development

   Migration <migration>
   Development guide <devguide>

.. toctree::
   :maxdepth: 2
   :caption: About

   Who uses psutil <adoption>
   Alternatives <alternatives>
   Credits <credits>
   Timeline <timeline>

.. toctree::
   :titlesonly:

   Changelog <changelog>
