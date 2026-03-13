.. currentmodule:: psutil

Who uses psutil
===============

psutil is one of the `top 100 <https://clickpy.clickhouse.com/dashboard/psutil>`_
most-downloaded packages on PyPI, with 280+ million downloads per month,
`760,000+ GitHub repositories <https://github.com/giampaolo/psutil/network/dependents>`_ using
it, and 14,000+ packages depending on it. The projects below are a small
sample of notable software that depends on it.

Infrastructure / automation
---------------------------

.. list-table::
   :header-rows: 1
   :widths: 28 32 14 26

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |homeassistant-logo| `Home Assistant <https://github.com/home-assistant/core>`_
     - Open source home automation platform
     - |homeassistant-stars|
     - system monitor integration
   * - |ansible-logo| `Ansible <https://github.com/ansible/ansible>`_
     - IT automation platform
     - |ansible-stars|
     - system fact gathering
   * - |airflow-logo| `Apache Airflow <https://github.com/apache/airflow>`_
     - Workflow orchestration platform
     - |airflow-stars|
     - process supervisor, unit testing
   * - |celery-logo| `Celery <https://github.com/celery/celery>`_
     - Distributed task queue
     - |celery-stars|
     - worker process monitoring, memleak detection
   * - |salt-logo| `Salt <https://github.com/saltstack/salt>`_
     - Infrastructure automation at scale
     - |salt-stars|
     - deep system data collection (grains)
   * - |dask-logo| `Dask <https://github.com/dask/dask>`_
     - Parallel computing with task scheduling
     - |dask-stars|
     - `metrics dashboard <https://github.com/dask/dask/blob/0d40a604284e021d098682b71c55d0387a414925/docs/source/dashboard.rst#L147>`_, profiling
   * - |ajenti-logo| `Ajenti <https://github.com/ajenti/ajenti>`_
     - Web-based server administration panel
     - |ajenti-stars|
     - monitoring plugins, deep integration

AI / Machine learning
---------------------

.. list-table::
   :header-rows: 1
   :widths: 28 32 14 26

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |tensorflow-logo| `TensorFlow <https://github.com/tensorflow/tensorflow>`_
     - Open source machine learning framework by Google
     - |tensorflow-stars|
     - unit tests
   * - |pytorch-logo| `PyTorch <https://github.com/pytorch/pytorch>`_
     - Tensors and dynamic neural networks with GPU acceleration
     - |pytorch-stars|
     - benchmark scripts
   * - |ray-logo| `Ray <https://github.com/ray-project/ray>`_
     - AI compute engine with distributed runtime
     - |ray-stars|
     - metrics dashboard
   * - |mlflow-logo| `MLflow <https://github.com/mlflow/mlflow>`_
     - AI/ML engineering platform
     - |mlflow-stars|
     - deep system monitoring integration

Developer tools
---------------

.. list-table::
   :header-rows: 1
   :widths: 28 32 14 26

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |sentry-logo| `Sentry <https://github.com/getsentry/sentry>`_
     - Error tracking and performance monitoring
     - |sentry-stars|
     - send telemetry metrics
   * - |locust-logo| `Locust <https://github.com/locustio/locust>`_
     - Scalable load testing in Python
     - |locust-stars|
     - monitoring of the Locust process
   * - |spyder-logo| `Spyder <https://github.com/spyder-ide/spyder>`_
     - Scientific Python IDE
     - |spyder-stars|
     - deep integration, UI stats, process management
   * - |psleak-logo| `psleak <https://github.com/giampaolo/psleak>`_
     - Test framework to detect memory in Python C extensions
     - |psleak-stars|
     - heap process memory (:func:`heap_info()`)

System monitoring
-----------------

.. list-table::
   :header-rows: 1
   :widths: 28 32 14 26

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |glances-logo| `Glances <https://github.com/nicolargo/glances>`_
     - System monitoring tool (top/htop alternative)
     - |glances-stars|
     - core dependency for all metrics
   * - |osquery-logo| `OSQuery <https://github.com/osquery/osquery>`_
     - SQL powered OS monitoring and analytics
     - |osquery-stars|
     - unit tests
   * - |bpytop-logo| `bpytop <https://github.com/aristocratos/bpytop>`_
     - Terminal resource monitor
     - |bpytop-stars|
     - core dependency for all metrics
   * - |auto-cpufreq-logo| `auto-cpufreq <https://github.com/AdnanHodzic/auto-cpufreq>`_
     - Automatic CPU speed and power optimizer for Linux
     - |auto-cpufreq-stars|
     - core dependency for CPU monitoring
   * - |grr-logo| `GRR <https://github.com/google/grr>`_
     - Remote live forensics by Google
     - |grr-stars|
     - endpoint system data collection, deep integration
   * - |stui-logo| `s-tui <https://github.com/amanusk/s-tui>`_
     - Terminal CPU stress and monitoring utility
     - |stui-stars|
     - core dependency for metrics
   * - |asitop-logo| `asitop <https://github.com/tlkh/asitop>`_
     - Apple Silicon performance monitoring CLI
     - |asitop-stars|
     - core dependency for system metrics
   * - |psdash-logo| `psdash <https://github.com/Jahaja/psdash>`_
     - Web dashboard using psutil and Flask
     - |psdash-stars|
     - core dependency for all metrics
   * - |dd-agent-logo| `dd-agent <https://github.com/DataDog/dd-agent>`_
     - Original monitoring agent by Datadog
     - |dd-agent-stars|
     - system metrics collection
   * - |ddtrace-logo| `dd-trace-py <https://github.com/DataDog/dd-trace-py>`_
     - Python tracing and profiling library
     - |ddtrace-stars|
     - system metrics collection

How this list was compiled
--------------------------

- `GitHub dependency graph <https://github.com/giampaolo/psutil/network/dependents>`_
  was used to identify packages and repositories that depend on psutil.
- GitHub code search with query "psutil in:readme language:Python", sorted
  by stars, was used to find additional projects that mention psutil in their
  README.
- Each candidate was then manually verified by checking the project's
  pyproject.toml, setup.py, setup.cfg or requirements.txt to confirm that
  psutil is an actual dependency (direct, build-time, or optional), not just
  a passing mention.
- Projects were excluded if they only mention psutil in documentation or
  examples without declaring it as a dependency.
- Star counts are pulled dynamically from `shields.io <https://shields.io/>`_ badges.
- The final list was manually curated to include notable projects and
  meaningful usages of psutil across different areas of the Python ecosystem.

.. ============================================================================
.. ============================================================================
.. ============================================================================

.. Star badges
.. ============================================================================

.. |airflow-stars| image:: https://img.shields.io/github/stars/apache/airflow.svg?style=social&label=%20
.. |ajenti-stars| image:: https://img.shields.io/github/stars/ajenti/ajenti.svg?style=social&label=%20
.. |ansible-stars| image:: https://img.shields.io/github/stars/ansible/ansible.svg?style=social&label=%20
.. |asitop-stars| image:: https://img.shields.io/github/stars/tlkh/asitop.svg?style=social&label=%20
.. |auto-cpufreq-stars| image:: https://img.shields.io/github/stars/AdnanHodzic/auto-cpufreq.svg?style=social&label=%20
.. |bpytop-stars| image:: https://img.shields.io/github/stars/aristocratos/bpytop.svg?style=social&label=%20
.. |celery-stars| image:: https://img.shields.io/github/stars/celery/celery.svg?style=social&label=%20
.. |dask-stars| image:: https://img.shields.io/github/stars/dask/dask.svg?style=social&label=%20
.. |ddtrace-stars| image:: https://img.shields.io/github/stars/DataDog/dd-trace-py.svg?style=social&label=%20
.. |dd-agent-stars| image:: https://img.shields.io/github/stars/DataDog/dd-agent.svg?style=social&label=%20
.. |glances-stars| image:: https://img.shields.io/github/stars/nicolargo/glances.svg?style=social&label=%20
.. |grr-stars| image:: https://img.shields.io/github/stars/google/grr.svg?style=social&label=%20
.. |homeassistant-stars| image:: https://img.shields.io/github/stars/home-assistant/core.svg?style=social&label=%20
.. |locust-stars| image:: https://img.shields.io/github/stars/locustio/locust.svg?style=social&label=%20
.. |mlflow-stars| image:: https://img.shields.io/github/stars/mlflow/mlflow.svg?style=social&label=%20
.. |osquery-stars| image:: https://img.shields.io/github/stars/osquery/osquery.svg?style=social&label=%20
.. |psdash-stars| image:: https://img.shields.io/github/stars/Jahaja/psdash.svg?style=social&label=%20
.. |psleak-stars| image:: https://img.shields.io/github/stars/giampaolo/psleak.svg?style=social&label=%20
.. |pytorch-stars| image:: https://img.shields.io/github/stars/pytorch/pytorch.svg?style=social&label=%20
.. |ray-stars| image:: https://img.shields.io/github/stars/ray-project/ray.svg?style=social&label=%20
.. |salt-stars| image:: https://img.shields.io/github/stars/saltstack/salt.svg?style=social&label=%20
.. |sentry-stars| image:: https://img.shields.io/github/stars/getsentry/sentry.svg?style=social&label=%20
.. |spyder-stars| image:: https://img.shields.io/github/stars/spyder-ide/spyder.svg?style=social&label=%20
.. |stui-stars| image:: https://img.shields.io/github/stars/amanusk/s-tui.svg?style=social&label=%20
.. |tensorflow-stars| image:: https://img.shields.io/github/stars/tensorflow/tensorflow.svg?style=social&label=%20

.. Logo images
.. ============================================================================

.. |airflow-logo| image:: https://github.com/apache.png?s=28 :height: 28
.. |ajenti-logo| image:: https://github.com/ajenti.png?s=28 :height: 28
.. |ansible-logo| image:: https://github.com/ansible.png?s=28 :height: 28
.. |asitop-logo| image:: https://github.com/tlkh.png?s=28 :height: 28
.. |auto-cpufreq-logo| image:: https://github.com/AdnanHodzic.png?s=28 :height: 28
.. |bpytop-logo| image:: https://github.com/aristocratos.png?s=28 :height: 28
.. |celery-logo| image:: https://github.com/celery.png?s=28 :height: 28
.. |dask-logo| image:: https://github.com/dask.png?s=28 :height: 28
.. |ddtrace-logo| image:: https://github.com/DataDog.png?s=28 :height: 28
.. |dd-agent-logo| image:: https://github.com/DataDog.png?s=28 :height: 28
.. |glances-logo| image:: https://github.com/nicolargo.png?s=28 :height: 28
.. |grr-logo| image:: https://github.com/google.png?s=28 :height: 28
.. |homeassistant-logo| image:: https://github.com/home-assistant.png?s=28 :height: 28
.. |locust-logo| image:: https://github.com/locustio.png?s=28 :height: 28
.. |mlflow-logo| image:: https://github.com/mlflow.png?s=28 :height: 28
.. |osquery-logo| image:: https://github.com/osquery.png?s=28 :height: 28
.. |psdash-logo| image:: https://github.com/Jahaja.png?s=28 :height: 28
.. |psleak-logo| image:: https://github.com/giampaolo.png?s=28 :height: 28
.. |pytorch-logo| image:: https://github.com/pytorch.png?s=28 :height: 28
.. |ray-logo| image:: https://github.com/ray-project.png?s=28 :height: 28
.. |salt-logo| image:: https://github.com/saltstack.png?s=28 :height: 28
.. |sentry-logo| image:: https://github.com/getsentry.png?s=28 :height: 28
.. |spyder-logo| image:: https://github.com/spyder-ide.png?s=28 :height: 28
.. |stui-logo| image:: https://github.com/amanusk.png?s=28 :height: 28
.. |tensorflow-logo| image:: https://github.com/tensorflow.png?s=28 :height: 28

.. --- Notes
.. Stars shield:
.. https://shields.io/badges/git-hub-repo-stars
