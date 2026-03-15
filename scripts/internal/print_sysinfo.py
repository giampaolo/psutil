#!/usr/bin/env python3

# Copyright (c) 2009, Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Print system information. Run before CI test run."""

import datetime
import getpass
import locale
import os
import pathlib
import platform
import shlex
import shutil
import subprocess
import sys

import psutil
from psutil._common import bytes2human

try:
    import pip
except ImportError:
    pip = None
try:
    import wheel
except ImportError:
    wheel = None


ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from _bootstrap import load_module  # noqa: E402


def sh(cmd):
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    return subprocess.check_output(cmd, universal_newlines=True).strip()


tests_init = ROOT_DIR / "tests" / "__init__.py"

tests_init_mod = load_module(tests_init)


def main():
    info = {}

    # python
    info['python'] = ', '.join([
        platform.python_implementation(),
        platform.python_version(),
        platform.python_compiler(),
    ])

    # OS
    if psutil.LINUX and shutil.which("lsb_release"):
        info['OS'] = sh('lsb_release -d -s')
    elif psutil.OSX:
        info['OS'] = f"Darwin {platform.mac_ver()[0]}"
    elif psutil.WINDOWS:
        info['OS'] = "Windows " + ' '.join(map(str, platform.win32_ver()))
        if hasattr(platform, 'win32_edition'):
            info['OS'] += ", " + platform.win32_edition()
    else:
        info['OS'] = f"{platform.system()} {platform.version()}"
    info['arch'] = ', '.join(
        list(platform.architecture()) + [platform.machine()]
    )
    if psutil.POSIX:
        info['kernel'] = platform.uname()[2]

    # pip
    info['pip'] = getattr(pip, '__version__', 'not installed')
    if wheel is not None:
        info['pip'] += f" (wheel={wheel.__version__})"

    # UNIX
    if psutil.POSIX:
        if shutil.which("gcc"):
            out = sh(['gcc', '--version'])
            info['gcc'] = str(out).split('\n')[0]
        else:
            info['gcc'] = 'not installed'
        s = platform.libc_ver()[1]
        if s:
            info['glibc'] = s

    # system
    info['fs-encoding'] = sys.getfilesystemencoding()
    lang = locale.getlocale()
    info['lang'] = f"{lang[0]}, {lang[1]}"
    info['boot-time'] = datetime.datetime.fromtimestamp(
        psutil.boot_time()
    ).strftime("%Y-%m-%d %H:%M:%S")
    info['time'] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    info['user'] = getpass.getuser()
    info['home'] = os.path.expanduser("~")
    info['cwd'] = os.getcwd()
    info['pyexe'] = tests_init_mod.PYTHON_EXE
    info['hostname'] = platform.node()
    info['PID'] = os.getpid()

    # metrics
    info['cpus'] = psutil.cpu_count()
    loadavg = tuple(x / psutil.cpu_count() * 100 for x in psutil.getloadavg())
    info['loadavg'] = (
        f"{loadavg[0]:.1f}%, {loadavg[1]:.1f}%, {loadavg[2]:.1f}%"
    )
    mem = psutil.virtual_memory()
    info['memory'] = "{}%%, used={}, total={}".format(
        int(mem.percent),
        bytes2human(mem.used),
        bytes2human(mem.total),
    )
    swap = psutil.swap_memory()
    info['swap'] = "{}%%, used={}, total={}".format(
        int(swap.percent),
        bytes2human(swap.used),
        bytes2human(swap.total),
    )

    # constants
    constants = sorted([
        x
        for x in dir(tests_init_mod)
        if x.isupper() and getattr(tests_init_mod, x) is True
    ])
    info['constants'] = "\n                  ".join(constants)

    # processes
    # info['pids'] = len(psutil.pids())
    # pinfo = psutil.Process().as_dict()
    # pinfo.pop('memory_maps', None)
    # pinfo["environ"] = {k: os.environ[k] for k in sorted(os.environ)}
    # info['proc'] = pprint.pformat(pinfo)

    # print
    print("=" * 70, file=sys.stderr)
    for k, v in info.items():
        print("{:<17} {}".format(k + ":", v), file=sys.stderr)
    print("=" * 70, file=sys.stderr)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
