#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""List and pretty print tarball & wheel files in the dist/ directory."""

import argparse
import collections
import fnmatch
import os
import pathlib
import sys

ROOT_DIR = pathlib.Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT_DIR))
from _bootstrap import load_module  # noqa: E402

_common = load_module(ROOT_DIR / "psutil" / "_common.py")
bytes2human = _common.bytes2human
print_color = _common.print_color

# Full set of wheels "make ci-check-dist" should find once all platform
# builds are merged, as filename globs (* swallows the volatile
# manylinux / macOS version numbers). cibuildwheel can silently stop
# emitting a variant (e.g. the free-threaded wheels); --check asserts
# this so CI goes red instead of shipping an incomplete release. Update
# when adding/dropping a Python version or platform.
EXPECTED_WHEELS = [
    "*-cp36-abi3-manylinux*_x86_64.whl",
    "*-cp36-abi3-manylinux*_aarch64.whl",
    "*-cp36-abi3-musllinux*_x86_64.whl",
    "*-cp36-abi3-musllinux*_aarch64.whl",
    "*-cp36-abi3-macosx*_x86_64.whl",
    "*-cp36-abi3-macosx*_arm64.whl",
    "*-cp37-abi3-win_amd64.whl",
    "*-cp37-abi3-win_arm64.whl",
    "*-cp313-cp313t-manylinux*_x86_64.whl",
    "*-cp313-cp313t-manylinux*_aarch64.whl",
    "*-cp313-cp313t-macosx*_x86_64.whl",
    "*-cp313-cp313t-macosx*_arm64.whl",
    "*-cp313-cp313t-win_amd64.whl",
    "*-cp313-cp313t-win_arm64.whl",
    "*-cp314-cp314t-manylinux*_x86_64.whl",
    "*-cp314-cp314t-manylinux*_aarch64.whl",
    "*-cp314-cp314t-macosx*_x86_64.whl",
    "*-cp314-cp314t-macosx*_arm64.whl",
    "*-cp314-cp314t-win_amd64.whl",
    "*-cp314-cp314t-win_arm64.whl",
]


class Wheel:
    def __init__(self, path):
        self._path = path
        self._name = os.path.basename(path)

    def __repr__(self):
        return "<{}(name={}, plat={}, arch={}, pyver={})>".format(
            self.__class__.__name__,
            self.name,
            self.platform(),
            self.arch(),
            self.pyver(),
        )

    __str__ = __repr__

    @property
    def name(self):
        return self._name

    def platform(self):
        plat = self.name.split('-')[-1]
        pyimpl = self.name.split('-')[3]
        ispypy = 'pypy' in pyimpl
        if 'linux' in plat:
            if ispypy:
                return 'pypy_on_linux'
            else:
                return 'linux'
        elif 'win' in plat:
            if ispypy:
                return 'pypy_on_windows'
            else:
                return 'windows'
        elif 'macosx' in plat:
            if ispypy:
                return 'pypy_on_macos'
            else:
                return 'macos'
        else:
            raise ValueError(f"unknown platform {self.name!r}")

    def arch(self):
        if self.name.endswith(('x86_64.whl', 'amd64.whl')):
            return '64-bit'
        if self.name.endswith(("i686.whl", "win32.whl")):
            return '32-bit'
        if self.name.endswith("arm64.whl"):
            return 'arm64'
        if self.name.endswith("aarch64.whl"):
            return 'aarch64'
        return '?'

    def pyver(self):
        pyver = 'pypy' if self.name.split('-')[3].startswith('pypy') else 'py'
        pyver += self.name.split('-')[2][2:]
        return pyver

    def size(self):
        return os.path.getsize(self._path)


class Tarball(Wheel):
    def platform(self):
        return "source"

    def arch(self):
        return "-"

    def pyver(self):
        return "-"


def check_dist(wheels, tarballs):
    """Assert the full expected set of wheels + one sdist is present.
    Returns a list of error strings (empty means all good).
    """
    names = [w.name for w in wheels]
    errors = [
        f"missing wheel: {pat}"
        for pat in EXPECTED_WHEELS
        if not any(fnmatch.fnmatch(n, pat) for n in names)
    ]
    errors += [
        f"unexpected wheel: {n}"
        for n in names
        if not any(fnmatch.fnmatch(n, p) for p in EXPECTED_WHEELS)
    ]
    if len(tarballs) != 1:
        errors.append(f"expected 1 sdist, found {len(tarballs)}")
    return errors


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        'dir',
        nargs="?",
        default="dist",
        help='directory containing tar.gz or wheel files',
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="assert the full expected set of wheels is present",
    )
    args = parser.parse_args()

    groups = collections.defaultdict(list)
    ls = sorted(os.listdir(args.dir), key=lambda x: x.endswith("tar.gz"))
    for name in ls:
        path = os.path.join(args.dir, name)
        if path.endswith(".whl"):
            pkg = Wheel(path)
        elif path.endswith(".tar.gz"):
            pkg = Tarball(path)
        else:
            raise ValueError(f"invalid package {path!r}")
        groups[pkg.platform()].append(pkg)

    tot_files = 0
    tot_size = 0
    templ = "{:<120} {:>7} {:>8} {:>7}"
    for platf, pkgs in groups.items():
        ppn = f"{platf} ({len(pkgs)})"
        s = templ.format(ppn, "size", "arch", "pyver")
        print_color('\n' + s, color=None, bold=True)
        for pkg in sorted(pkgs, key=lambda x: x.name):
            tot_files += 1
            tot_size += pkg.size()
            s = templ.format(
                "  " + pkg.name,
                bytes2human(pkg.size()),
                pkg.arch(),
                pkg.pyver(),
            )
            if 'pypy' in pkg.pyver():
                print_color(s, color='violet')
            else:
                print_color(s, color='brown')

    print_color(
        f"\n\ntotals: files={tot_files}, size={bytes2human(tot_size)}",
        bold=True,
    )

    if args.check:
        all_pkgs = [p for pkgs in groups.values() for p in pkgs]
        tarballs = [p for p in all_pkgs if isinstance(p, Tarball)]
        wheels = [p for p in all_pkgs if not isinstance(p, Tarball)]
        errors = check_dist(wheels, tarballs)
        if errors:
            print_color("\ndist check FAILED:", color='red', bold=True)
            for err in errors:
                print_color("  " + err, color='red')
            print_color(
                "\nif intentional, update EXPECTED_WHEELS in "
                + os.path.basename(__file__),
                bold=True,
            )
            sys.exit(1)
        print_color("\ndist check: OK", color='green', bold=True)


if __name__ == '__main__':
    main()
