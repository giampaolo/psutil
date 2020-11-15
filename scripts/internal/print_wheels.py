#!/usr/bin/env python3

# Copyright (c) 2009 Giampaolo Rodola'. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

"""Nicely print wheels print in dist/ directory."""

import collections
import glob
import os

from psutil._common import print_color
from psutil._common import bytes2human


class Wheel:

    def __init__(self, path):
        self._path = path
        self._name = os.path.basename(path)

    def __repr__(self):
        return "<Wheel(name=%s, plat=%s, arch=%s, pyver=%s)>" % (
            self.name, self.platform(), self.arch(), self.pyver())

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
            raise ValueError("unknown platform %r" % self.name)

    def arch(self):
        if self.name.endswith(('x86_64.whl', 'amd64.whl')):
            return '64'
        return '32'

    def pyver(self):
        pyver = 'pypy' if self.name.split('-')[3].startswith('pypy') else 'py'
        pyver += self.name.split('-')[2][2:]
        return pyver

    def size(self):
        return os.path.getsize(self._path)


def main():
    groups = collections.defaultdict(list)
    for path in glob.glob('dist/*.whl'):
        wheel = Wheel(path)
        groups[wheel.platform()].append(wheel)

    tot_files = 0
    tot_size = 0
    templ = "%-54s %7s %7s %7s"
    for platf, wheels in groups.items():
        ppn = "%s (total = %s)" % (platf, len(wheels))
        s = templ % (ppn, "size", "arch", "pyver")
        print_color('\n' + s, color=None, bold=True)
        for wheel in sorted(wheels, key=lambda x: x.name):
            tot_files += 1
            tot_size += wheel.size()
            s = templ % (wheel.name, bytes2human(wheel.size()), wheel.arch(),
                         wheel.pyver())
            if 'pypy' in wheel.pyver():
                print_color(s, color='violet')
            else:
                print_color(s, color='brown')

    print_color("\ntotals: files=%s, size=%s" % (
        tot_files, bytes2human(tot_size)), bold=True)


if __name__ == '__main__':
    main()
