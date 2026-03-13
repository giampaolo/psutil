.. currentmodule:: psutil

Who uses psutil
===============

psutil is one of the `top 100
<https://clickpy.clickhouse.com/dashboard/psutil>`__ most-downloaded packages
on PyPI, with `760,000+ GitHub repositories
<https://github.com/giampaolo/psutil/network/dependents>`__ and 14,000+
packages depending on it.

Infrastructure / orchestration
------------------------------

.. list-table::
   :header-rows: 1
   :widths: 30 28 15 27

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |ansible-logo| `Ansible <https://github.com/ansible/ansible>`__
     - IT automation platform
     - |ansible-stars|
     - system fact gathering
   * - |homeassistant-logo| `Home Assistant <https://github.com/home-assistant/core>`__
     - Open source home automation platform
     - |homeassistant-stars|
     - system monitor integration
   * - |airflow-logo| `Apache Airflow <https://github.com/apache/airflow>`__
     - Workflow orchestration platform
     - |airflow-stars|
     -
   * - |celery-logo| `Celery <https://github.com/celery/celery>`__
     - Distributed task queue
     - |celery-stars|
     - worker process monitoring, memleak detection
   * - |salt-logo| `Salt <https://github.com/saltstack/salt>`__
     - Infrastructure automation at scale
     - |salt-stars|
     - deep system data collection (grains)
   * - |buildbot-logo| `Buildbot <https://github.com/buildbot/buildbot>`__
     - Continuous integration framework
     - |buildbot-stars|
     -
   * - |ajenti-logo| `Ajenti <https://github.com/ajenti/ajenti>`__
     - Web-based server administration panel
     - |ajenti-stars|
     - monitoring plugins, deep integration

Machine learning / data
-----------------------

.. list-table::
   :header-rows: 1
   :widths: 30 28 15 27

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |tensorflow-logo| `TensorFlow <https://github.com/tensorflow/tensorflow>`__
     - Open source machine learning framework by Google
     - |tensorflow-stars|
     -
   * - |pytorch-logo| `PyTorch <https://github.com/pytorch/pytorch>`__
     - Tensors and dynamic neural networks with GPU acceleration
     - |pytorch-stars|
     - unit tests, benchmark scripts
   * - |ray-logo| `Ray <https://github.com/ray-project/ray>`__
     - AI compute engine with distributed runtime
     - |ray-stars|
     -
   * - |mlflow-logo| `MLflow <https://github.com/mlflow/mlflow>`__
     - AI/ML engineering platform
     - |mlflow-stars|
     - deep system monitoring integration
   * - |optuna-logo| `Optuna <https://github.com/optuna/optuna>`__
     - Hyperparameter optimization framework
     - |optuna-stars|
     -

Developer tools
---------------

.. list-table::
   :header-rows: 1
   :widths: 30 28 15 27

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |sentry-logo| `Sentry <https://github.com/getsentry/sentry>`__
     - Error tracking and performance monitoring
     - |sentry-stars|
     -
   * - |pyinstaller-logo| `PyInstaller <https://github.com/pyinstaller/pyinstaller>`__
     - Package Python programs into stand-alone executables
     - |pyinstaller-stars|
     -
   * - |locust-logo| `Locust <https://github.com/locustio/locust>`__
     - Scalable load testing in Python
     - |locust-stars|
     -
   * - |spyder-logo| `Spyder <https://github.com/spyder-ide/spyder>`__
     - Scientific Python IDE
     - |spyder-stars|
     - deep integration, UI stats, process management
   * - |psleak-logo| `psleak <https://github.com/giampaolo/psleak>`__
     - Test framework to detect memory in Python C extensions
     - |psleak-stars|
     - heap process memory (:func:`heap_info()`)

System monitoring
-----------------

.. list-table::
   :header-rows: 1
   :widths: 30 28 15 27

   * - Project
     - Description
     - Stars
     - psutil usage
   * - |glances-logo| `Glances <https://github.com/nicolargo/glances>`__
     - System monitoring tool (top/htop alternative)
     - |glances-stars|
     - **core dependency for all metrics**
   * - |osquery-logo| `OSQuery <https://github.com/osquery/osquery>`__
     - SQL powered OS monitoring and analytics
     - |osquery-stars|
     - unit tests
   * - |ddtrace-logo| `dd-trace-py <https://github.com/DataDog/dd-trace-py>`__
     - Python tracing and profiling library by Datadog
     - |ddtrace-stars|
     - system metrics collection
   * - |bpytop-logo| `bpytop <https://github.com/aristocratos/bpytop>`__
     - Terminal resource monitor
     - |bpytop-stars|
     - **core dependency for all metrics**
   * - |asitop-logo| `asitop <https://github.com/tlkh/asitop>`__
     - Apple Silicon performance monitoring CLI
     - |asitop-stars|
     - core dependency for system metrics
   * - |stui-logo| `s-tui <https://github.com/amanusk/s-tui>`__
     - Terminal CPU stress and monitoring utility
     - |stui-stars|
     - core dependency for metrics
   * - |auto-cpufreq-logo| `auto-cpufreq <https://github.com/AdnanHodzic/auto-cpufreq>`__
     - Automatic CPU speed and power optimizer for Linux
     - |auto-cpufreq-stars|
     - core dependency for CPU monitoring
   * - |psdash-logo| `psdash <https://github.com/Jahaja/psdash>`__
     - Web dashboard using psutil and Flask
     - |psdash-stars|
     - core dependency for all metrics
   * - |grr-logo| `GRR <https://github.com/google/grr>`__
     - Remote live forensics by Google
     - |grr-stars|
     - endpoint system data collection, deep integration

.. Star badges
.. ============================================================================

.. |airflow-stars| image:: https://img.shields.io/github/stars/apache/airflow.svg?style=plastic
.. |ajenti-stars| image:: https://img.shields.io/github/stars/ajenti/ajenti.svg?style=plastic
.. |ansible-stars| image:: https://img.shields.io/github/stars/ansible/ansible.svg?style=plastic
.. |asitop-stars| image:: https://img.shields.io/github/stars/tlkh/asitop.svg?style=plastic
.. |auto-cpufreq-stars| image:: https://img.shields.io/github/stars/AdnanHodzic/auto-cpufreq.svg?style=plastic
.. |bpytop-stars| image:: https://img.shields.io/github/stars/aristocratos/bpytop.svg?style=plastic
.. |buildbot-stars| image:: https://img.shields.io/github/stars/buildbot/buildbot.svg?style=plastic
.. |celery-stars| image:: https://img.shields.io/github/stars/celery/celery.svg?style=plastic
.. |ddtrace-stars| image:: https://img.shields.io/github/stars/DataDog/dd-trace-py.svg?style=plastic
.. |glances-stars| image:: https://img.shields.io/github/stars/nicolargo/glances.svg?style=plastic
.. |grr-stars| image:: https://img.shields.io/github/stars/google/grr.svg?style=plastic
.. |homeassistant-stars| image:: https://img.shields.io/github/stars/home-assistant/core.svg?style=plastic
.. |locust-stars| image:: https://img.shields.io/github/stars/locustio/locust.svg?style=plastic
.. |mlflow-stars| image:: https://img.shields.io/github/stars/mlflow/mlflow.svg?style=plastic
.. |optuna-stars| image:: https://img.shields.io/github/stars/optuna/optuna.svg?style=plastic
.. |osquery-stars| image:: https://img.shields.io/github/stars/osquery/osquery.svg?style=plastic
.. |psdash-stars| image:: https://img.shields.io/github/stars/Jahaja/psdash.svg?style=plastic
.. |psleak-stars| image:: https://img.shields.io/github/stars/giampaolo/psleak.svg?style=plastic
.. |pyinstaller-stars| image:: https://img.shields.io/github/stars/pyinstaller/pyinstaller.svg?style=plastic
.. |pytorch-stars| image:: https://img.shields.io/github/stars/pytorch/pytorch.svg?style=plastic
.. |ray-stars| image:: https://img.shields.io/github/stars/ray-project/ray.svg?style=plastic
.. |salt-stars| image:: https://img.shields.io/github/stars/saltstack/salt.svg?style=plastic
.. |sentry-stars| image:: https://img.shields.io/github/stars/getsentry/sentry.svg?style=plastic
.. |spyder-stars| image:: https://img.shields.io/github/stars/spyder-ide/spyder.svg?style=plastic
.. |stui-stars| image:: https://img.shields.io/github/stars/amanusk/s-tui.svg?style=plastic
.. |tensorflow-stars| image:: https://img.shields.io/github/stars/tensorflow/tensorflow.svg?style=plastic

.. Logo images
.. ============================================================================

.. |airflow-logo| image:: https://github.com/apache.png?s=28 :height: 28
.. |ajenti-logo| image:: https://github.com/ajenti.png?s=28 :height: 28
.. |ansible-logo| image:: https://github.com/ansible.png?s=28 :height: 28
.. |asitop-logo| image:: https://github.com/tlkh.png?s=28 :height: 28
.. |auto-cpufreq-logo| image:: https://github.com/AdnanHodzic.png?s=28 :height: 28
.. |bpytop-logo| image:: https://github.com/aristocratos.png?s=28 :height: 28
.. |buildbot-logo| image:: https://github.com/buildbot.png?s=28 :height: 28
.. |celery-logo| image:: https://github.com/celery.png?s=28 :height: 28
.. |ddtrace-logo| image:: https://github.com/DataDog.png?s=28 :height: 28
.. |glances-logo| image:: https://github.com/nicolargo.png?s=28 :height: 28
.. |grr-logo| image:: https://github.com/google.png?s=28 :height: 28
.. |homeassistant-logo| image:: https://github.com/home-assistant.png?s=28 :height: 28
.. |locust-logo| image:: https://github.com/locustio.png?s=28 :height: 28
.. |mlflow-logo| image:: https://github.com/mlflow.png?s=28 :height: 28
.. |optuna-logo| image:: https://github.com/optuna.png?s=28 :height: 28
.. |osquery-logo| image:: https://github.com/osquery.png?s=28 :height: 28
.. |psdash-logo| image:: https://github.com/Jahaja.png?s=28 :height: 28
.. |psleak-logo| image:: https://github.com/giampaolo.png?s=28 :height: 28
.. |pyinstaller-logo| image:: https://github.com/pyinstaller.png?s=28 :height: 28
.. |pytorch-logo| image:: https://github.com/pytorch.png?s=28 :height: 28
.. |ray-logo| image:: https://github.com/ray-project.png?s=28 :height: 28
.. |salt-logo| image:: https://github.com/saltstack.png?s=28 :height: 28
.. |sentry-logo| image:: https://github.com/getsentry.png?s=28 :height: 28
.. |spyder-logo| image:: https://github.com/spyder-ide.png?s=28 :height: 28
.. |stui-logo| image:: https://github.com/amanusk.png?s=28 :height: 28
.. |tensorflow-logo| image:: https://github.com/tensorflow.png?s=28 :height: 28
