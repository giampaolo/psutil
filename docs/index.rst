.. module:: psutil
   :synopsis: psutil module
.. moduleauthor:: Giampaolo Rodola <grodola@gmail.com>
.. title:: Home

.. ============================================================================
.. Hero
.. ============================================================================

.. raw:: html

   <script>document.body.classList.add('home-page');</script>

   <div class="hero">
     <div class="hero-title"><img src="_static/images/logo-psutil.svg" class="hero-logo" alt="psutil logo"><span>psutil<span/></div>
     <div class="hero-subtitle">Process and System Utilities for Python</div>
     <div class="hero-badges">
       <a href="https://github.com/giampaolo/psutil"><img src="https://img.shields.io/badge/GitHub-repo-blue" alt="GitHub repo"></a>
       <a href="https://clickpy.clickhouse.com/dashboard/psutil"><img src="https://img.shields.io/pypi/dm/psutil?label=downloads" alt="Downloads"></a>
     </div>
   </div>

Psutil is a cross-platform library for retrieving information about running
processes and system utilization (CPU, memory, disks, network, sensors) in
Python. It is useful mainly for system monitoring, profiling, limiting process
resources, and managing running processes. Psutil implements many
functionalities offered by UNIX command line tool such as
*ps, top, free, iotop, netstat, ifconfig, lsof* and others (see
:doc:`shell equivalents <shell-equivalents>`). It is used by
:doc:`many notable projects <adoption>` including TensorFlow, PyTorch, Home
Assistant, Ansible, and Celery.

----

.. ============================================================================
.. Platform pills
.. ============================================================================

.. raw:: html

   <div class="home-platforms">
     <a class="home-platforms-label" href="platform.html">Runs on</a>
     <div class="home-platforms-pills">
       <a class="home-platform-pill" href="platform.html">Linux</a>
       <a class="home-platform-pill" href="platform.html">Windows</a>
       <a class="home-platform-pill" href="platform.html">macOS</a>
       <a class="home-platform-pill" href="platform.html">FreeBSD</a>
       <a class="home-platform-pill" href="platform.html">OpenBSD</a>
       <a class="home-platform-pill" href="platform.html">NetBSD</a>
       <a class="home-platform-pill" href="platform.html">Solaris</a>
       <a class="home-platform-pill" href="platform.html">AIX</a>
     </div>
   </div>

.. ============================================================================
.. Feature cards
.. ============================================================================

.. raw:: html

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
       <i class="fa fa-hdd-o home-icon-fa"></i>
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

.. ============================================================================
.. Description cards
.. ============================================================================

.. raw:: html

   <div class="home-desc-cards">
     <div class="home-desc-card">
       <div class="home-desc-card-header">
         <i class="fa fa-cogs home-desc-card-icon"></i>
         <div class="home-desc-card-title">Process management</div>
       </div>
       <p>Query and control running processes: CPU, memory, files, connections, threads, and more.</p>
     </div>
     <div class="home-desc-card">
       <div class="home-desc-card-header">
         <i class="fa fa-heartbeat home-desc-card-icon"></i>
         <div class="home-desc-card-title">System monitoring</div>
       </div>
       <p>Get real-time metrics for CPU, memory, disks, network, and hardware sensors.</p>
     </div>
     <div class="home-desc-card">
       <div class="home-desc-card-header">
         <i class="fa fa-plug home-desc-card-icon"></i>
         <div class="home-desc-card-title">Platform portability</div>
       </div>
       <p>One API for all platforms. Psutil primary goal is to abstract OS differences, so your monitoring code runs unchanged everywhere.</p>
     </div>
   </div>

   <div class="hero-cta">
     <a class="hero-btn hero-btn-primary" href="install.html">Install <i class="fa fa-arrow-right"></i></a>
     <a class="hero-btn hero-btn-secondary" href="api.html">API reference</a>
   </div>

.. ============================================================================
.. Sponsors
.. ============================================================================

Sponsors
--------

.. raw:: html
   :file: _sponsors.html

.. ============================================================================
.. TOC: hidden via CSS, needed by Sphinx for sidebar nav
.. ============================================================================

.. toctree::
   :maxdepth: 2
   :caption: Documentation

   Install <install>
   API overview <api-overview>
   API Reference <api>
   FAQ <faq>
   Performance <performance>
   Recipes <recipes>

.. toctree::
   :maxdepth: 2
   :caption: Reference

   Shell equivalents <shell-equivalents>
   Stdlib equivalents <stdlib-equivalents>
   Glossary <glossary>
   Platform support <platform>
   Migration <migration>

.. toctree::
   :maxdepth: 2
   :caption: About

   Who uses psutil <adoption>
   Alternatives <alternatives>
   Funding <funding>
   Credits <credits>

.. toctree::
   :maxdepth: 2
   :titlesonly:
   :caption: Project

   Blog <blog>
   Changelog <changelog>
   Timeline <timeline>
   Development guide <devguide>
   General Index <genindex>
