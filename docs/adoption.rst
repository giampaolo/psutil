Who uses psutil
===============

.. Numbers below are refreshed by `make refresh-adoption-stats`,
   which writes them in-place from PyPI / GitHub. Run it before
   tagging a release.

psutil is among the
`top 100 <https://clickpy.clickhouse.com/dashboard/psutil>`__ most-downloaded
packages on PyPI, with **390+ million** downloads per month and **780,000+**
`GitHub repositories <https://github.com/giampaolo/psutil/network/dependents>`__
using it. The projects below are a sample of notable software that uses it.
They are grouped by how much of the project depends on psutil, and every usage
links to the code that calls psutil. See also :doc:`alternatives` for related
Python libraries and equivalents in other languages.

.. raw:: html

   <div class="adopter-cards">
     <div class="adopter-card">
       <div class="adopter-head">
         <img src="../_static/images/adopters/datadog.png" alt="">
         <a href="https://github.com/DataDog/integrations-core">Datadog</a>
       </div>
       <div class="adopter-what">Agent checks read processes, disks and network through psutil.</div>
       <div class="adopter-links">
         <a href="https://github.com/DataDog/integrations-core/blob/720d4ded9dffb5ea7eb5e5f4feeb0e240f60ae59/process/datadog_checks/process/process.py#L225">see the code</a>
         <a href="https://www.datadoghq.com/blog/agent-developer-mode/">write-up</a>
       </div>
     </div>
     <div class="adopter-card">
       <div class="adopter-head">
         <img src="../_static/images/adopters/ray.png" alt="">
         <a href="https://github.com/ray-project/ray">Ray</a>
       </div>
       <div class="adopter-what">Ships psutil in its own wheel; OOM monitor, process watcher, autoscaler.</div>
       <div class="adopter-links">
         <a href="https://github.com/ray-project/ray/blob/d39938f27556e367ca43d8af12a9add0ca952456/python/ray/_private/memory_monitor.py#L12">see the code</a>
       </div>
     </div>
     <div class="adopter-card">
       <div class="adopter-head">
         <img src="../_static/images/adopters/home-assistant.png" alt="">
         <a href="https://github.com/home-assistant/core">Home Assistant</a>
       </div>
       <div class="adopter-what">CPU, memory and disk for the system monitor integration.</div>
       <div class="adopter-links">
         <a href="https://github.com/home-assistant/core/blob/d49a9c4780080882c634fa9649e6d7ed10307244/homeassistant/components/systemmonitor/coordinator.py#L165">see the code</a>
       </div>
     </div>
     <div class="adopter-card">
       <div class="adopter-head">
         <img src="../_static/images/adopters/opentelemetry.png" alt="">
         <a href="https://github.com/open-telemetry/opentelemetry-python-contrib">OpenTelemetry</a>
       </div>
       <div class="adopter-what">Its system-metrics instrumentation, which is how Splunk and Honeycomb users get psutil.</div>
       <div class="adopter-links">
         <a href="https://github.com/open-telemetry/opentelemetry-python-contrib/blob/f1b9368aa6e2ad4cb0aaa79d341cd19b0b9cd13b/instrumentation/opentelemetry-instrumentation-system-metrics/src/opentelemetry/instrumentation/system_metrics/__init__.py#L97">see the code</a>
       </div>
     </div>
     <div class="adopter-card">
       <div class="adopter-head">
         <img class="logo-on-light" src="../_static/images/adopters/glances.svg" alt="">
         <img class="logo-on-dark" src="../_static/images/adopters/glances-on-dark.svg" alt="">
         <a href="https://github.com/nicolargo/glances">Glances</a>
       </div>
       <div class="adopter-what">Every metric it displays comes from psutil.</div>
       <div class="adopter-links">
         <a href="https://github.com/nicolargo/glances/blob/7a351ac38cff96cf4fedecfba8d85088dd9885ae/glances/plugins/mem/__init__.py#L142">see the code</a>
       </div>
     </div>
   </div>

Built on psutil
---------------

psutil is a core dependency of these projects and central to how they work.

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Project
     - Description
     - What it uses psutil for
   * - `Ray <https://github.com/ray-project/ray>`__
     - Distributed runtime for AI and Python workloads
     - bundled inside the wheel; `OOM monitor
       <https://github.com/ray-project/ray/blob/d39938f27556e367ca43d8af12a9add0ca952456/python/ray/_private/memory_monitor.py#L12>`__, process watcher, autoscaler, dashboard
   * - `Glances <https://github.com/nicolargo/glances>`__
     - System monitoring tool (top/htop alternative)
     - CPU, `memory
       <https://github.com/nicolargo/glances/blob/7a351ac38cff96cf4fedecfba8d85088dd9885ae/glances/plugins/mem/__init__.py#L142>`__, disk, network, sensors, processes
   * - `Salt <https://github.com/saltstack/salt>`__
     - Infrastructure automation at scale
     - master, minion, the `ps execution module
       <https://github.com/saltstack/salt/blob/2722040c1da29f474adc5dfe013cca31a0455f5f/salt/modules/ps.py#L2>`__, beacons, grains
   * - `bpytop <https://github.com/aristocratos/bpytop>`__
     - Terminal resource monitor
     - `CPU, memory, disk, network, processes
       <https://github.com/aristocratos/bpytop/blob/2034232931324f7b277b9b970a36277297a9ed43/bpytop.py#L265>`__
   * - `auto-cpufreq <https://github.com/AdnanHodzic/auto-cpufreq>`__
     - CPU speed and power optimizer for Linux
     - `CPU load and frequency readings
       <https://github.com/AdnanHodzic/auto-cpufreq/blob/57b77f5cf20d02edff1df07c7bbf02467f78f14e/auto_cpufreq/core.py#L276>`__
   * - `s-tui <https://github.com/amanusk/s-tui>`__
     - Terminal CPU stress and monitoring utility
     - `CPU, frequency and temperature readings
       <https://github.com/amanusk/s-tui/blob/aa3a17194d16e3ff438d5947efe69761b5ac2feb/s_tui/sources/util_source.py#L30>`__
   * - `GRR <https://github.com/google/grr>`__
     - Remote live forensics by Google
     - client actions for processes, `network connections
       <https://github.com/google/grr/blob/ad7e59c4b1ae7c5cf7121b1ddd7bea765d11c994/grr/client/grr_response_client/client_actions/network.py#L6>`__ and memory
   * - `psdash <https://github.com/Jahaja/psdash>`__
     - Web dashboard using psutil and Flask
     - `CPU, memory, disk, network, users, processes
       <https://github.com/Jahaja/psdash/blob/b7c3699ff5934fe797799a52958c0299a9fcafe7/psdash/node.py#L74>`__
   * - `OpenTelemetry Python <https://github.com/open-telemetry/opentelemetry-python-contrib>`__
     - Observability instrumentation for Python
     - the whole `instrumentation-system-metrics
       <https://github.com/open-telemetry/opentelemetry-python-contrib/blob/f1b9368aa6e2ad4cb0aaa79d341cd19b0b9cd13b/instrumentation/opentelemetry-instrumentation-system-metrics/src/opentelemetry/instrumentation/system_metrics/__init__.py#L97>`__ package; Splunk, Honeycomb and New Relic users depend on psutil through it
   * - `psleak <https://github.com/giampaolo/psleak>`__
     - Test framework to detect memory leaks in Python C extensions
     - `heap process memory
       <https://github.com/giampaolo/psleak/blob/508738ef22b1aedecafed0c8b5e6f03404b09a35/psleak.py#L28>`__ (:func:`heap_info`)

Used for a specific feature
---------------------------

In these, psutil backs a single feature rather than the whole project.

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Project
     - Description
     - What it uses psutil for
   * - `Home Assistant <https://github.com/home-assistant/core>`__
     - Home automation platform
     - the `system monitor integration
       <https://github.com/home-assistant/core/blob/d49a9c4780080882c634fa9649e6d7ed10307244/homeassistant/components/systemmonitor/coordinator.py#L165>`__
   * - `Ansible <https://github.com/ansible/ansible>`__
     - IT automation platform
     - `counting active connections
       <https://github.com/ansible/ansible/blob/d772fe65b73e3032f88a9915111b58e743af9d9f/lib/ansible/modules/wait_for.py#L308>`__ in the ``wait_for`` module
   * - `Apache Airflow <https://github.com/apache/airflow>`__
     - Workflow orchestration platform
     - `task subprocess lifecycle
       <https://github.com/apache/airflow/blob/92290dbd64f52205b516668db29fd437435b7dbe/airflow-core/src/airflow/utils/process_utils.py#L45>`__
   * - `Sentry <https://github.com/getsentry/sentry>`__
     - Error tracking and performance monitoring
     - `telemetry metrics
       <https://github.com/getsentry/sentry/blob/b30ef5d3d5cf02d07ba9447d913648e89b34893e/src/sentry/tasks/beacon.py#L156>`__
   * - `Celery <https://github.com/celery/celery>`__
     - Distributed task queue
     - `memory sampling
       <https://github.com/celery/celery/blob/f462a437e3371acb867e94b52c2595b6d0a742d8/celery/utils/debug.py#L13>`__ used to debug leaks
   * - `MLflow <https://github.com/mlflow/mlflow>`__
     - Machine learning lifecycle platform
     - `system metrics logged with each run
       <https://github.com/mlflow/mlflow/blob/a8721e3683f7e3e8bb3885620af04efb5251b405/mlflow/system_metrics/metrics/cpu_monitor.py#L13>`__
   * - `Locust <https://github.com/locustio/locust>`__
     - Scalable load testing in Python
     - `monitoring its own process
       <https://github.com/locustio/locust/blob/15bc3c900d354495cfde3a45e871228ea85f10fd/locust/runners.py#L299>`__
   * - `Dask <https://github.com/dask/dask>`__
     - Parallel computing with task scheduling
     - `worker memory management
       <https://github.com/dask/distributed/blob/5fe4b054a711415aa5b85d5b049e2729c958bc36/distributed/worker_memory.py#L401>`__ in ``distributed``
   * - `Accelerate <https://github.com/huggingface/accelerate>`__
     - Distributed training and inference launcher
     - `physical CPU count
       <https://github.com/huggingface/accelerate/blob/a68e0d50e7afd7c3e2716ca5c5bad83063c04cdc/src/accelerate/state.py#L271>`__, available memory, process launching
   * - `Spyder <https://github.com/spyder-ide/spyder>`__
     - Scientific Python IDE
     - `memory usage in the status bar
       <https://github.com/spyder-ide/spyder/blob/bdfe0b59821951584de3f72768693a151ca8350a/spyder/utils/system.py#L51>`__
   * - `Ajenti <https://github.com/ajenti/ajenti>`__
     - Web-based server administration panel
     - `dashboard widgets
       <https://github.com/ajenti/ajenti/blob/fc4028020f0d8e7a4af2d476b0146611f9d439b2/plugins/dashboard/widgets/cpu.py#L17>`__ for CPU, memory, uptime and traffic
   * - `asitop <https://github.com/tlkh/asitop>`__
     - Apple Silicon performance monitoring CLI
     - `memory and swap readings
       <https://github.com/tlkh/asitop/blob/74ebe2cbc23d5b1eec874aebb1b9bacfe0e670cd/asitop/utils.py#L5>`__
   * - `integrations-core <https://github.com/DataDog/integrations-core>`__
     - Integration checks for the Datadog agent
     - 15 check modules, including `process
       <https://github.com/DataDog/integrations-core/blob/720d4ded9dffb5ea7eb5e5f4feeb0e240f60ae59/process/datadog_checks/process/process.py#L225>`__, disk and network
   * - `Elastic APM <https://github.com/elastic/apm-agent-python>`__
     - Application performance monitoring agent
     - `CPU and memory metrics on Windows and macOS
       <https://github.com/elastic/apm-agent-python/blob/519a1078e230187d553669ceb8dd37704990b34c/elasticapm/metrics/sets/cpu_psutil.py#L34>`__ (its own ``/proc`` parser on Linux)

Used in development only
------------------------

psutil is a test dependency only. Users of these projects never install it.

.. list-table::
   :header-rows: 1
   :widths: 22 30 48

   * - Project
     - Description
     - What it uses psutil for
   * - `TensorFlow <https://github.com/tensorflow/tensorflow>`__
     - Machine learning framework by Google
     - `unit tests
       <https://github.com/tensorflow/tensorflow/blob/61105a4e3bbb7bde37db1d71344624dcf302bc93/tensorflow/python/checkpoint/checkpoint_test.py#L1188>`__
   * - `PyTorch <https://github.com/pytorch/pytorch>`__
     - Deep learning framework with GPU acceleration
     - `benchmark scripts
       <https://github.com/pytorch/pytorch/blob/6fa3592dc65b15195a145a98f344f0c38517b12f/benchmarks/data/dataloader_benchmark.py#L38>`__

How this list was compiled
--------------------------

Candidates came from the `GitHub dependency graph
<https://github.com/giampaolo/psutil/network/dependents>`__ and from code
search. Each one was then checked against the project's packaging metadata and
source, to make sure psutil is a real dependency and not just a mention. The
links in the last column point at the code doing the work, pinned to a commit
so the line numbers keep matching.
