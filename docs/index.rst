.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola <grodola@gmail.com>
.. title:: Home

.. raw:: html

   <script>document.body.classList.add('home-page');</script>

   <div class="hero">
     <div class="hero-title"><img src="_static/images/logo-psutil.svg" class="hero-logo" alt="psutil logo"><span>psutil<span/></div>
     <div class="hero-subtitle">Process and System Utilities for Python</div>
     <div class="hero-badges">
       <a href="https://github.com/giampaolo/psutil"><img src="https://img.shields.io/badge/GitHub-repo-blue" alt="GitHub repo"></a>
       <a href="https://clickpy.clickhouse.com/dashboard/psutil"><img src="https://img.shields.io/pypi/dm/psutil?label=downloads" alt="Downloads"></a>
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
       <img class="home-icon-svg" src="_static/images/icon-cpu.svg" alt="CPU">
       <div class="home-feature-title">CPU</div>
     </a>
     <a class="home-feature-card" href="api.html#memory">
       <img class="home-icon-svg" src="_static/images/icon-memory.svg" alt="Memory">
       <div class="home-feature-title">Memory</div>
     </a>
     <a class="home-feature-card" href="api.html#disks">
       <img class="home-icon-svg" src="_static/images/icon-disks.svg" alt="Disks">
       <div class="home-feature-title">Disks</div>
     </a>
     <a class="home-feature-card" href="api.html#network">
       <img class="home-icon-svg" src="_static/images/icon-network.svg" alt="Network">
       <div class="home-feature-title">Network</div>
     </a>
     <a class="home-feature-card" href="api.html#sensors">
       <i class="fa fa-thermometer-half home-icon-fa"></i>
       <div class="home-feature-title">Sensors</div>
     </a>
     <a class="home-feature-card" href="api.html#processes">
       <img class="home-icon-svg" src="_static/images/icon-processes.svg" alt="Processes">
       <div class="home-feature-title">Processes</div>
     </a>
   </div>


psutil implements many functionalities offered by UNIX command line tool such
as *ps, top, free, iotop, netstat, ifconfig, lsof* and others
(see :doc:`shell equivalents <shell-equivalents>`).
It is used by :doc:`many notable projects <adoption>` including TensorFlow,
PyTorch, Home Assistant, Ansible, and Celery.

-------------------------------------------------------------------------------

Sponsors
--------

.. raw:: html

    <table border="0" cellpadding="10" cellspacing="0" class="sponsor-table">
      <tr>
        <td align="center" style="vertical-align: middle;">
          <a href="https://tidelift.com/subscription/pkg/pypi-psutil?utm_source=pypi-psutil&utm_medium=referral&utm_campaign=readme">
            <img width="160" src="_static/images/logo-tidelift.svg" class="sponsor-logo">
          </a>
        </td>
        <td align="center" style="vertical-align: middle;">
          <a href="https://sansec.io/">
            <img width="145" src="_static/images/logo-sansec.svg" class="sponsor-logo">
          </a>
        </td>
        <td align="center" style="vertical-align: middle;">
          <a href="https://www.apivoid.com/">
            <img width="130" src="_static/images/logo-apivoid.svg" class="sponsor-logo">
          </a>
        </td>
      </tr>
    </table>

    <div style="text-align: center;"><sup><a href="funding.html">add your logo</a></sup></div><br/>

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
   Funding <funding>
   Timeline <timeline>

.. toctree::
   :titlesonly:

   Changelog <changelog>
