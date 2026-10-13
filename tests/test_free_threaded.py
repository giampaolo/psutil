# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""Check wheel imports and concurrent native calls on every Python ABI."""

import subprocess
import sys

import pytest


def test_fresh_import_and_concurrent_process_queries():
    subprocess.run(
        [
            sys.executable,
            "-W",
            "error::RuntimeWarning",
            "-c",
            """
import os
import sys
import sysconfig
from concurrent.futures import ThreadPoolExecutor
import psutil
free_threaded = bool(sysconfig.get_config_var("Py_GIL_DISABLED"))
assert not free_threaded or not sys._is_gil_enabled()
def query(_):
    process = psutil.Process()
    assert process.pid == os.getpid()
    assert process.memory_info().rss > 0
    assert process.cpu_times().user >= 0
with ThreadPoolExecutor(max_workers=2) as pool:
    list(pool.map(query, range(100)))
assert not free_threaded or not sys._is_gil_enabled()
""",
        ],
        check=True,
    )


def test_distribution_requires_all_free_threaded_wheels():
    import runpy
    from pathlib import Path

    path = (
        Path(__file__).resolve().parents[1] / "scripts/internal/print/dist.py"
    )
    dist = runpy.run_path(str(path))
    wheels = [
        dist["Wheel"](
            f"psutil-8.0.0-{python}-{abi}-{platform}.whl".replace(
                "manylinux_", "manylinux_2_28_"
            )
        )
        for python, abi, platform in dist["EXPECTED_WHEELS"]
    ]
    assert dist["check_dist"](wheels, ["psutil.tar.gz"]) == []
    for reverse in (False, True):
        aliases = []
        for wheel in wheels:
            platform = wheel.name.rsplit("-", 1)[1].removesuffix(".whl")
            if platform.startswith("manylinux_2_28_"):
                legacy = platform.replace("manylinux_2_28_", "manylinux2014_")
                pair = (platform, legacy) if reverse else (legacy, platform)
                wheel = dist["Wheel"](
                    wheel.name.replace(platform, ".".join(pair))
                )
            aliases.append(wheel)
        assert dist["check_dist"](aliases, ["psutil.tar.gz"]) == []
    for legacy in ("manylinux1_", "manylinux2010_"):
        aliases = [
            dist["Wheel"](
                w.name.replace("manylinux_2_28_x86_64", legacy + "x86_64")
            )
            for w in wheels
        ]
        assert dist["check_dist"](aliases, ["psutil.tar.gz"]) == []
        invalid = [
            dist["Wheel"](
                w.name.replace("manylinux_2_28_aarch64", legacy + "aarch64")
            )
            for w in wheels
        ]
        assert len(dist["check_dist"](invalid, ["psutil.tar.gz"])) == 6
    too_new = [
        dist["Wheel"](w.name.replace("manylinux_2_28_", "manylinux_2_34_"))
        for w in wheels
    ]
    assert len(dist["check_dist"](too_new, ["psutil.tar.gz"])) == 24
    newer = [
        dist["Wheel"](wheel.name.replace("-cp39-abi3-", "-cp310-abi3-"))
        for wheel in wheels
    ]
    assert len(dist["check_dist"](newer, ["psutil.tar.gz"])) == 20
    for fragment, label, count in (
        ("-cp315t-", "cp315t", 10),
        ("t-musllinux_", "musllinux", 4),
        ("t-manylinux_2_28_ppc64le", "ppc64le", 2),
        ("t-manylinux_2_28_s390x", "s390x", 2),
    ):
        missing = [wheel for wheel in wheels if fragment not in wheel.name]
        errors = dist["check_dist"](missing, ["psutil.tar.gz"])
        assert len(errors) == count
        assert all(label in error for error in errors)


@pytest.mark.parametrize("minor", [9, 10])
def test_pip_bootstrap_matches_python(minor, monkeypatch):
    import runpy
    from pathlib import Path

    # URL selection must not import pip under a simulated Python version.
    monkeypatch.setitem(sys.modules, "pip", None)
    monkeypatch.setattr(sys, "version_info", (3, minor))
    source = (
        Path(__file__).resolve().parents[1] / "scripts/internal/install_pip.py"
    )
    url = runpy.run_path(str(source))["URL"]
    prefix = "pip/3.9/" if minor == 9 else ""
    assert url == f"https://bootstrap.pypa.io/{prefix}get-pip.py"
